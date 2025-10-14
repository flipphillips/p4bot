<!-- Auto-generated guidance for AI coding agents working on the p4bot repo. -->
# Copilot instructions for p4bot

Be brief and specific. This repository is a tiny Flask-based Slack command runner that invokes Perforce (p4) operations via P4Python or helper scripts. The goal of contributors is to maintain a small, secure, and predictable runtime that executes p4-related checks and returns plain text/json suitable for Slack.

Key files to reference
- `app/server.py` — the Flask app and the most important integration points: `/slack/command` (generic mapped commands) and `/slack/status` (p4status implementation via P4Python). Prefer changes here when altering Slack behavior or P4 invocation.
- `app/p4status.py` and `app/p4status.sh` — the status report generator and shell wrapper used by CLI and scripts. Use these as canonical formatting and behavior for status output.
- `app/test_p4python.py` — small connectivity test used in development to validate P4Python and credentials.
- `Dockerfile`, `docker-compose.yml`, `docker-compose.dev.yml` — build and dev/run behaviors. Follow existing build-arg and volume conventions.

Project-specific conventions
- P4 interaction must use P4Python where available. `server.py` implements P4Python-backed commands; avoid adding shell-based `p4` fallbacks in the Slack endpoints unless it's explicit and gated.
- Secrets: passwords are read from `/scripts/secrets/p4passwd` by default (see env `P4PASSWD_FILE`). Do not hardcode credentials. For local development the compose files mount `./app` -> `/scripts` and may mount `./scripts/secrets`.
- Script root: runtime scripts live under `P4_SCRIPT_ROOT` (default `/scripts`). The Docker images set `P4_SCRIPT_ROOT=/scripts` and compose mounts follow that. Refer to this env var when modifying paths.
- Response limits: Slack responses are truncated to ~2900 characters in `server.py`. Any change to output size or formatting must keep Slack limits in mind.

Developer workflows & common commands
- Priority: I am using VS Code Insiders, I Prefer using those tools when possible and to take advantage of features it provides -especially- via devcontainers. 
- I prefer vs code 'tasks' over CLI and Makefile. 
- I -am- very CLI / UNIX proficient but prefer to take advantage of VSCode's features and integrations.
- Build and run (compose): `docker compose up --build -d` (See top-level `README.md`). The service listens on 8080.
- Development (live code): `docker compose -f docker-compose.dev.yml up --build` uses `gunicorn --reload` and mounts source for live edits.
- Health check: `GET /healthz` (returns JSON {status: ok}).
- Manual Slack POST test (example in README): POST form to `/slack/command` or `/slack/status` with `text` field.
- Quick connectivity test inside container or host: run `app/test_p4python.py` or `make test_p4python` (See repo README and Makefile targets).

Patterns & examples to follow when coding
- Command mapping: `SLACK_COMMAND_MAP` is JSON mapping of slash commands to either a string (shell words) or a list of strings. `server._parse_command_map` normalizes these; use shlex-compatible splitting for string values.
  Example map entry in compose: `{"/status": "p4status.sh"}` or `{"/locked": ["p4","opened","-a"]}`.
- P4Python usage: use `_p4_instance()` in `server.py` to pick up `p4config` from `P4_SCRIPT_ROOT` and the `P4PASSWD_FILE`. Always `connect()` and `disconnect()`; use `run(cmd, *args)` and handle dict/list outputs by converting dicts to `key: value` lines (see `_run_p4_command`).
- Error handling: prefer returning formatted user-facing messages (see `_format`) rather than raising raw exceptions from Flask endpoints. For internal tooling use exceptions but endpoints should return a short message.

Testing and validation
- Unit tests are minimal in this repo. Use `app/test_p4python.py` to validate runtime access to P4 and `p4status.py` for formatting consistency.
- When changing Python code, run a quick syntax/type scan (linting not required here). In the container, Python runtime is v3.11 (see Dockerfile). The image uses a venv at `/opt/venv` — use the same interpreter for dev if reproducing the container.

Risky or out-of-scope changes
- Do not embed secrets into the repo. The Dockerfile documents an embedding mode but the README warns against it — keep that warning.
- Avoid adding network calls or background jobs in the Flask app; the service is intended to be request-driven and simple.

If unsure, reference these implementation hotspots
- `server.py` — Slack endpoints, command map parsing, P4 helpers
- `p4status.py` — JSON report structure, parsing `p4 -ztag` output and text formatter
- `p4status.sh` — CLI wrapper with allowed flags and default behavior

End: After applying changes, run the container with the dev compose to sanity-check behavior and run `app/test_p4python.py`. Ask maintainers if Perforce test credentials are required for CI runs.
