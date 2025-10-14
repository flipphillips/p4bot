# TODO — p4bot (snapshot)

This file is an exported snapshot of the assistant's internal todo list and pinned items. It's intended to keep high-level tasks visible in the repository.

## Current tasks

- [x] Confirm minimal devcontainer — keep `.devcontainer/devcontainer.json` minimal (uses Docker Compose service and runs `/scripts/login.sh` on start).
- [x] Verify Dockerfile installs P4Python — ensure `Docker/Dockerfile` creates venv at `/opt/venv` and installs `P4Python` and build deps.
- [x] Provide rebuild & test commands — document one-line commands to rebuild image, recreate devcontainer, and run `test_p4python.py`.
- [ ] Add optional Make target (PINNED) — add a single `make dev` or `make dev-test` target to automate build + login + test. Add only if requested.
- [x] Create PROJECT.md — add concise project brief with goals, constraints, secrets policy, tests, and allowed-file edits.
- [x] Add usage section to PROJECT.md — insert a 'Usage' section into `PROJECT.md` with commands for build, start, login, and running the test.
- [x] Mount host repo into container workspace — bind-mount the repository root into the container at `/srv/p4bot` so edits in the devcontainer persist to the host repo.
- [x] Verify launch.json works in-container — confirm `.vscode/launch.json` is available inside the devcontainer and is configured with workspace-relative paths so it works both in-host and in-container.
- [x] Unify launch configs for host + container — update `.vscode/launch.json` to include clear "in-container" and "on-host" configurations and use the Python debugger type so it works in both environments.
- [x] Explain devcontainer philosophy and validate assumptions — review the user's assumptions and provide migration recommendations.

## Pinned / future work

These items are intentionally deferred so development can focus on getting the application logic working first.

- Prepare production split: convert `Docker/Dockerfile` to a multi-stage build and add a `docker-compose.prod.yml` that creates a small runtime image without host mounts.
- Create deployment guide and registry workflow: add `deploy.md` with steps to build, tag, push to a container registry, and run the image on the lab server.
- Add convenience Make targets: `rebuild-reopen` and `rebuild-deploy` to automate build, stop, start, and optional push to registry.


---

(If you want this snapshot refreshed later, tell me and I'll update `TODO.md`.)
