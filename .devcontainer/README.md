Open this repository in VS Code and choose "Reopen in Container" to start the
devcontainer. The devcontainer uses the existing Docker Compose service
defined in `Docker/p4bot/docker-compose.yml` and binds the repo into
`/workspace` inside the container.

The container will expose port 8080 and run `/scripts/login.sh` after start to
automate `p4 trust -y` and a non-interactive `p4 login` using
`/scripts/secrets/p4passwd` (if present).

If you prefer not to run the login step automatically, edit `.devcontainer/devcontainer.json`
and remove or change `postStartCommand`.
