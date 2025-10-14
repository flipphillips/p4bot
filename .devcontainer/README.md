Open this repository in VS Code and choose "Reopen in Container" to start the
devcontainer. The devcontainer uses the existing Docker Compose service
defined in `Docker/p4bot/docker-compose.yml` and binds the repo into
`/workspace` inside the container.

The container will expose port 8080. Perforce credentials and config can be provided via
`P4TICKETS` and `P4CONFIG` files mounted from the host (by default we mount
`~/.p4tickets` and `~/.p4config` into `/root/.p4tickets` and `/root/.p4config`).

If you prefer to authenticate interactively or with the Perforce CLI, perform the
`p4 trust` and `p4 login` steps on your host and copy the resulting `~/.p4tickets` file
into the container mount.
