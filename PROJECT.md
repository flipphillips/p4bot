# p4bot — Project Brief

Purpose
-------
Provide a minimal devcontainer-based development environment for a Slack-bot that runs Perforce helper scripts and/or P4 Python API calls. The devcontainer should let developers edit, run, and debug Python code (or shell scripts) locally in VS Code and be easy to transition into a Docker image later.

Primary use-cases
-----------------
1. Open repository in VS Code → Reopen in Container; be able to run/debug `Docker/app/test_p4python.py` using `P4Python`.
2. Run shell-based helpers under `/scripts` (mounted from `Docker/app`) inside the running container for quick testing.
3. Keep perforce secrets local and out of repo; test scripts should use `/scripts/secrets/p4passwd` when available.

Constraints / Non-goals
-----------------------
- No CI, no production deployment config, no secret managers. Keep the project lightweight.
- Do not restructure the repository beyond small, explicit path fixes needed for the dev flow.
- Avoid adding extra automation or complex fallback logic unless explicitly requested.

Acceptance criteria (how to verify)
-----------------------------------
- After rebuilding the dev image and reopening in container, `python3 -c "import P4"` must succeed inside the container.
- The following should return a successful JSON response (ok: true) after running the login helper:

```
# start service (detached)
docker compose -f .devcontainer/../Docker/docker-compose.yml up -d

# accept trust and login
docker compose -f .devcontainer/../Docker/docker-compose.yml exec p4bot bash -lc "chmod +x /scripts/login.sh && /scripts/login.sh"

# run the P4Python test inside the running container
docker compose -f .devcontainer/../Docker/docker-compose.yml exec p4bot python3 /srv/p4bot/app/test_p4python.py
```

Secrets policy
--------------
- Keep secrets (e.g., `p4passwd`) in `Docker/app/secrets/` on the developer's machine. Never commit real secrets. Add `.gitkeep` if you need the directory tracked.

Files allowed to change
-----------------------
- `.devcontainer/devcontainer.json` (minimal config only)
- `Docker/docker-compose.yml` (mounting /scripts during dev)
- `Docker/Dockerfile` (to install P4/P4Python and minimal build deps)
- `.vscode/launch.json` (debug target adjustments)
- Small README/PROJECT.md additions

Commit and push policy
----------------------
- Make minimal, explicit commits and push to `origin/main` by default unless asked to use a branch.

Communication style
-------------------
- Minimal, precise. If you give me a short instruction and an acceptance test, I will perform exactly that and stop.

---

If you want this file changed, edit and commit it yourself or tell me how to adjust it and I will update it.
