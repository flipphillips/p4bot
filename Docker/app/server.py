"""Slim Slack-facing Flask server that uses P4Python only.

This file intentionally keeps the server minimal for local/dev use.
It logs incoming requests and implements a simple `/slack/command` handler
and a `/slack/locked` action which returns opened (locked) files for a
given pathspec. By default it will use //vp25-ue/... as the depot path.
"""
from __future__ import annotations

import os
from typing import Iterable

from flask import Flask, jsonify, request
from P4 import P4, P4Exception


DEFAULT_PATHSPEC = "//vp25-ue/..."


def create_app() -> Flask:
    app = Flask(__name__)

    @app.get("/healthz")
    def healthcheck():  # pragma: no cover - trivial route
        return jsonify(status="ok"), 200

    @app.post("/slack/command")
    def slack_command():
        # Log the incoming form for debugging; Slack sends form-encoded payloads
        payload = {k: request.form.get(k) for k in request.form.keys()}
        app.logger.debug("/slack/command received: %s", payload)

        # Quick response to acknowledge work in progress
        text = request.form.get("text", "").strip()
        command = request.form.get("command", "").strip()

        # If the user typed `/locked` or the command is `/locked`, handle it
        if command == "/locked" or text.startswith("locked") or text == "locked":
            # Extract optional pathspec after the word 'locked'
            parts = text.split()
            pathspec = parts[1] if len(parts) > 1 else DEFAULT_PATHSPEC
            try:
                lines = list(_p4_opened(pathspec))
                if not lines:
                    reply = f"No opened files under {pathspec}."
                else:
                    reply = "\n".join(lines[:250])  # keep replies bounded
            except Exception as e:
                app.logger.exception("p4 error for locked files")
                reply = f"Error querying Perforce: {e}"
            return jsonify({"response_type": "ephemeral", "text": reply})

        # Default response for other commands: debug info + in-progress
        return jsonify({
            "response_type": "ephemeral",
            "text": f"Received command {command!r} with text {text!r}. Working on it."
        })

    @app.post("/slack/locked")
    def slack_locked():
        payload = {k: request.form.get(k) for k in request.form.keys()}
        app.logger.debug("/slack/locked received: %s", payload)

        text = request.form.get("text", "").strip()
        pathspec = text or DEFAULT_PATHSPEC
        try:
            lines = list(_p4_opened(pathspec))
            if not lines:
                reply = f"No opened files under {pathspec}."
            else:
                reply = "\n".join(lines[:250])
        except Exception as e:
            app.logger.exception("p4 error for locked endpoint")
            reply = f"Error querying Perforce: {e}"
        return jsonify({"response_type": "ephemeral", "text": reply})

    return app


def _p4_opened(pathspec: str) -> Iterable[str]:
    """Yield human-friendly lines for opened files under pathspec using P4Python.

    Use P4(debug=3) and let P4Python pick up `P4CONFIG` or environment values like
    `P4PORT`/`P4USER` automatically (same behavior as `simple.py`). Avoid forcing
    overrides from the environment here unless explicitly needed.
    """
    # create P4 like simple.py so p4config is respected
    p4 = P4(debug=3)

    try:
        p4.connect()

        # Use read-only behavior like p4status: always list opened across all clients
        # This avoids depending on a configured P4CLIENT.
        try:
            opened = p4.run("opened", "-a", pathspec)
        except P4Exception:
            # Let the caller handle any P4 errors (no trust logic here).
            raise

        for o in opened:
            if isinstance(o, dict):
                depot = o.get("depotFile") or o.get("clientFile") or "(file)"
                action = o.get("action", "(action)")
                user = o.get("user", "?")
                client = o.get("client", "?")
                yield f"{depot} - {action} by {user} ({client})"
            else:
                yield str(o)
    finally:
        try:
            p4.disconnect()
        except Exception:
            pass


# application instance
app = create_app()


if __name__ == "__main__":  # pragma: no cover
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
