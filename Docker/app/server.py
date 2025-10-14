"""Tiny Slack command runner for the Perforce helper scripts."""
from __future__ import annotations

import json
import os
import shlex
import subprocess
from pathlib import Path

from flask import Flask, jsonify, request


def create_app() -> Flask:
    app = Flask(__name__)

    script_root = Path(os.environ.get("P4_SCRIPT_ROOT", "/scripts")).resolve()
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
            return _format("Tell me which script to run.")

        script = (script_root / parts[0]).resolve()
        if not script.exists():
            return _format(f"Script '{parts[0]}' not found.")
        try:
            script.relative_to(script_root)
        except ValueError:
            return _format("Script path must stay under the script root.")

        result = subprocess.run(
            [str(script), *parts[1:]],
            capture_output=True,
            text=True,
        )

        output = result.stdout.strip() or "Command completed successfully with no output."
        if result.returncode:
            output = f"exit {result.returncode}: {result.stderr.strip() or output}"

        return _format(output[:2900])

    @app.post("/slack/status")
    def slack_status():
        """Run p4status.sh for a given pathspec and return text output.

        Expects form fields:
        - text: optional pathspec (defaults to //...)
        - repo: optional - kept for future multi-repo support
        """
        text = request.form.get("text", "").strip()
        pathspec = text or "//..."

        # script and script_root
        script_root = Path(os.environ.get("P4_SCRIPT_ROOT", "/scripts")).resolve()
        script = (script_root / "p4status.sh").resolve()
        if not script.exists():
            return _format("p4status.sh not found on server"), 404

        # load simple perforce config if present: a minimal KEY=VALUE per line file
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


app = create_app()

if __name__ == "__main__":  # pragma: no cover
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
