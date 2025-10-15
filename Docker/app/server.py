"""Tiny Slack command runner for the Perforce helper scripts."""
from __future__ import annotations

import json
import os
import shlex
import subprocess
from pathlib import Path

from flask import Flask, jsonify, request
from P4 import P4, P4Exception


def create_app() -> Flask:
    app = Flask(__name__)

    # script_root removed; prefer P4CONFIG and environment variables for perforce settings
    script_root = None
    command_map = _parse_command_map(os.environ.get("SLACK_COMMAND_MAP", "{}"))

    @app.get("/healthz")
    def healthcheck():  # pragma: no cover - trivial route
        return jsonify(status="ok"), 200

    @app.post("/slack/command")
    def run_command():
        command = request.form.get("command", "").strip()
        text = request.form.get("text", "").strip()

        mapped = command_map.get(command)
        args = shlex.split(text) if text else []
        parts = [*(mapped or []), *args]
        if not parts:
            return _format("Tell me which command to run. Use a mapping that begins with 'p4'.")

        # Only support P4 commands executed via P4Python. No shell/script fallbacks.
        if parts[0] != "p4":
            return _format("Only p4-based commands are supported. Update SLACK_COMMAND_MAP to map the slash command to ['p4', '<cmd>', ...].")

        try:
            out = _run_p4_command(parts, script_root=script_root)
        except Exception as e:  # include P4Exception
            return _format(f"p4 error: {e}")
        return _format(out[:2900])

    @app.post("/slack/status")
    def slack_status():
        """Run p4status.sh for a given pathspec and return text output.

        Expects form fields:
        - text: optional pathspec (defaults to //...)
        - repo: optional - kept for future multi-repo support
        """
        text = request.form.get("text", "").strip()
        pathspec = text or "//..."

        # Always use Python-backed status via P4Python. No shell fallback.
        try:
            out = _run_p4_status(pathspec, script_root=None)
            return _format(out[:2900])
        except Exception as e:
            return _format(f"p4 status error: {e}"), 500

        # (dead code removed)
        cfg = {}
        cfgfile = script_root / "p4config"
        if cfgfile.exists():
            for ln in cfgfile.read_text().splitlines():
                ln = ln.strip()
                if not ln or ln.startswith('#'):
                    continue
                if '=' in ln:
                    k, v = ln.split('=', 1)
                    cfg[k.strip()] = v.strip()

        env = os.environ.copy()
        # allow keys P4PORT, P4USER, P4PASSWD in the file
        for k in ("P4PORT", "P4USER", "P4PASSWD", "P4TICKETS"):
            if k in cfg:
                env[k] = cfg[k]

        # run the script
        result = subprocess.run([str(script), pathspec], capture_output=True, text=True, env=env)
        out = result.stdout.strip() or "(no output)"
        if result.returncode != 0:
            return _format(f"exit {result.returncode}: {result.stderr.strip() or out}")
        return _format(out[:2900])

    return app


def _parse_command_map(raw: str) -> dict[str, list[str]]:
    data = json.loads(raw or "{}")
    if not isinstance(data, dict):
        raise ValueError("SLACK_COMMAND_MAP must be a JSON object")

    mapping: dict[str, list[str]] = {}
    for key, value in data.items():
        if not isinstance(key, str):
            continue
        norm = key if key.startswith("/") else f"/{key}"
        if isinstance(value, str):
            mapping[norm] = shlex.split(value)
        elif isinstance(value, list) and all(isinstance(v, str) for v in value):
            mapping[norm] = value
        else:
            raise ValueError(f"Invalid mapping for {norm}")
    return mapping


def _format(message: str):
    return {"response_type": "ephemeral", "text": message}


def read_password(path: str) -> str:
    # Be defensive: the mounted path may be a directory (user mounted a folder)
    # or otherwise unreadable. In those cases return empty string so the
    # application doesn't crash at import time.
    try:
        if os.path.isdir(path):
            return ""
        if not os.path.exists(path):
            return ""
        with open(path, "r") as f:
            data = f.read().strip()
    except (IsADirectoryError, PermissionError, OSError):
        return ""
    # accept either raw password or key=value style
    if data.startswith("password="):
        return data.split("=", 1)[1]
    return data

### P4 helpers ---------------------------------------------------------------

# Create a P4 instance on demand so module import doesn't attempt network ops.
def _p4_instance(script_root: Path | str | None = None) -> P4:
    p4 = P4()
    # load optional p4config file if present (P4CONFIG or /root/.p4config)
    cfgpath = os.environ.get("P4CONFIG") or "/root/.p4config"
    cfgfile = Path(cfgpath)
    if cfgfile.exists():
        for ln in cfgfile.read_text().splitlines():
            ln = ln.strip()
            if not ln or ln.startswith('#'):
                continue
            if '=' in ln:
                k, v = ln.split('=', 1)
                k = k.strip()
                v = v.strip()
                if k == 'P4PASSWD' and v:
                    p4.password = v
                elif k == 'P4PORT':
                    p4.port = v
                elif k == 'P4USER':
                    p4.user = v
    # also respect environment-derived password/tickets
    if password:
        p4.password = password
    # If P4TICKETS present in env, P4Python will use it automatically
    return p4


def _run_p4_command(parts: list[str], script_root: Path | None = None) -> str:
    """Run a p4 command using P4Python. parts begins with 'p4' then the command and args.

    Example: ['p4', 'files', '//depot/...']
    """
    if len(parts) < 2:
        raise ValueError("no p4 command provided")
    cmd = parts[1]
    args = parts[2:]
    p4 = _p4_instance(script_root)
    try:
        p4.connect()
        # login if password available
        if getattr(p4, 'password', None):
            try:
                p4.run_login(p4.password)
            except P4Exception:
                # continue; some servers may not require login
                pass
        # run the command; use run(cmd, *args) which returns list/dicts
        result = p4.run(cmd, *args)
        # format result: join by newline, for dict results try to stringify
        out_lines: list[str] = []
        for item in result:
            if isinstance(item, dict):
                # convert dict to key: value lines
                for k, v in item.items():
                    out_lines.append(f"{k}: {v}")
            else:
                out_lines.append(str(item))
        return "\n".join(out_lines) or "(no output)"
    finally:
        try:
            p4.disconnect()
        except Exception:
            pass


def _run_p4_status(pathspec: str, script_root: Path | None = None) -> str:
    """Simple status summary using P4Python similar to p4status.sh's expected output.

    This is a minimal implementation: it runs `opened` and `changes` or `files` as needed
    to produce some useful text for Slack.
    """
    p4 = _p4_instance(script_root)
    try:
        p4.connect()
        if getattr(p4, 'password', None):
            try:
                p4.run_login(p4.password)
            except P4Exception:
                pass

        lines: list[str] = []
        # show opened files under the pathspec
        try:
            opened = p4.run('opened', pathspec)
            if opened:
                lines.append(f"Opened files ({len(opened)}):")
                for o in opened:
                    if isinstance(o, dict):
                        lines.append(f"{o.get('clientFile') or o.get('depotFile')} - {o.get('action')}")
                    else:
                        lines.append(str(o))
            else:
                lines.append("No opened files.")
        except P4Exception:
            lines.append("Could not fetch opened files.")

        # show recent changelists touching the pathspec
        try:
            changes = p4.run('changes', '-m', '10', pathspec)
            if changes:
                lines.append(f"Recent changes ({len(changes)}):")
                for ch in changes:
                    if isinstance(ch, dict):
                        lines.append(f"{ch.get('change')}: {ch.get('desc','').splitlines()[0]}")
                    else:
                        lines.append(str(ch))
            else:
                lines.append("No recent changes.")
        except P4Exception:
            lines.append("Could not fetch recent changes.")

        return "\n".join(lines) or "(no output)"
    finally:
        try:
            p4.disconnect()
        except Exception:
            pass

# instance reserved for backwards-compat if needed
p4 = None

### main

app = create_app()

if __name__ == "__main__":  # pragma: no cover
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
