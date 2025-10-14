# p4bot

A tiny Flask service that receives Slack slash command payloads and runs
Perforce helper scripts from this repository. Responses are returned to Slack so
p4bot can surface command results back to a channel or DM.

## Layout

- `Dockerfile` — builds a tiny Python image with Flask, Gunicorn and Slack SDK.
- `docker-compose.yml` — convenience wrapper for runtime configuration.
- `app/server.py` — small Flask app that uses P4Python and reads perforce settings from `P4CONFIG` or environment variables.
- `requirements.txt` — Python dependencies for the service.

## Prerequisites

1. Slack app with a Slash Command pointing at
   `https://<host>/slack/command`.
2. The Perforce helper scripts live in `./app` and are mounted into the container
   at `/srv/p4bot/app` for development.

## Quick start

```bash
docker compose up --build -d
```

The service listens on port `8080`. Update the compose file or use
`-p HOSTPORT:8080` if you need a different exposed port.

### Building with P4 CLI and P4Python

The image now installs `P4Python` by default (via pip). If you also want
the Perforce `p4` CLI binary inside the container, provide a download URL as
a build-arg when building the image. Example (replace URL with a valid
Perforce client binary for your platform):

```bash
docker build --build-arg P4_CLI_URL="https://example.com/path/to/p4" -t local/p4bot:latest .
```

If you don't provide `P4_CLI_URL`, the image will still contain `P4Python`
but not the `p4` binary; you can mount a `p4` binary at runtime into
`/usr/local/bin/p4` or use a package-managed p4 client on the host.

### Using local p4 assets (native builds)

If you prefer to keep p4 binaries alongside the repo (not recommended for
committing secrets), place them under `Docker/p4bot/assets/` named by
architecture, for example:

```
Docker/p4bot/assets/p4-arm64   # linux/arm64 p4 binary
Docker/p4bot/assets/p4-amd64   # linux/amd64 p4 binary
Docker/p4bot/assets/p4         # generic p4 binary
```

The Dockerfile will copy `assets/p4-${TARGETARCH}` into `/usr/local/bin/p4`
during build when present, or `assets/p4` as a fallback. When building for
Apple Silicon natively, build with `--platform linux/arm64` so `TARGETARCH`
matches `arm64` and the ARM binary will be used.

### Embedding secrets into the image (not recommended for production)

If you want a fully self-contained image that includes the `perforce/p4config`
and `perforce/secrets/p4passwd` files baked in, you can enable embedding at
build time. This will copy the files into `/etc/p4` inside the image and set
`P4PASSWD_FILE=/etc/p4/p4passwd` so the runtime uses the embedded password.

Warning: embedding secrets into images is convenient for testing but is
insecure for production. Prefer bind-mounting secrets or using Docker
secrets/secret managers in production.

Build with embedded secrets (example):

```bash
cd Docker/p4bot
docker build --platform linux/amd64 --build-arg BUILD_EMBED_SECRETS=1 -t local/p4bot:with-secrets .
```

This requires that `Docker/app/p4config` and `Docker/app/secrets/p4passwd` exist
in the build context. They will be copied into the image if present.

## Health check

Verify the container is running locally:

```bash
curl http://localhost:8080/healthz
```

For manual testing of the Slack endpoint you can mimic Slack's POST body:

```bash
curl \
  -X POST http://localhost:8080/slack/command \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data "command=/p4&text=p4status.sh"
```

## Environment variables

- `P4CONFIG` / `P4TICKETS` — prefer using a `P4CONFIG` file or environment variables (`P4PORT`, `P4USER`, `P4TICKETS`) for Perforce settings.
- `SLACK_COMMAND_MAP` — optional JSON map of slash commands to scripts and
  arguments. See below.

### Mapping slash commands

If you expose multiple Slack slash commands (for example `/status`, `/locked`,
`/co`) that should run different scripts or arguments, configure
`SLACK_COMMAND_MAP`. Provide JSON that maps a command to a script (string) or
list of `script` + arguments:

```yaml
environment:
  SLACK_COMMAND_MAP: |
    {
      "/status": "p4status.sh",
      "/locked": ["p4status", "locked"],
      "/co": "p4status co"
    }
```

Incoming slash command parameters are appended to the mapped command. If you
omit a mapping, users must supply the script name in the slash command text
(`/p4 p4status.sh`).

## Notes

- Script output is truncated to 2,900 characters to stay within Slack limits.
- Scripts must be executable inside the container (`chmod +x`).
- Errors and stdout/stderr are visible via `docker compose logs -f`.

## Simple /slack/status endpoint (convenience)

The service exposes a minimal `/slack/status` POST endpoint that runs the
`p4status.sh` script and returns its text output. It accepts form-encoded
requests identical to Slack slash commands; the `text` field may contain a
Perforce pathspec (e.g. `//depot/...`).

The endpoint will load a simple perforce config file from the `P4_SCRIPT_ROOT`
directory named `p4config`. The file is plain text with `KEY=VALUE` lines and
may contain `P4PORT`, `P4USER`, `P4PASSWD`, or `P4TICKETS`. Example:

```
P4PORT=perforce:1666
P4USER=monitor
P4PASSWD=secret-password
```

This is intentionally minimal — the service will set these environment
variables for the `p4status.sh` run. Keep real secrets out of the repo and
mount them into the container at runtime (for example via Docker secrets).

## Development: helper Makefile and quick commands

To avoid invoking docker compose from the wrong directory or forgetting the
compose file, a small `Makefile` at the repo root provides common targets
that always use the correct compose file.

At the repo root you can run:

```bash
# build and start the service in detached mode
make up

# run the login helper (accept trust + non-interactive login)
make login

# view a short status report (limit defaults to 3, override with LIMIT=5)
make p4status
make p4status LIMIT=5

# run the P4Python test script
make test_p4python

# run an arbitrary command inside the container
make exec CMD="bash -lc 'ls -la /srv/p4bot/app'"

# stop the service
make down
```

These targets are thin wrappers around `docker compose -f Docker/p4bot/docker-compose.yml ...`
so you won't accidentally hit the "no configuration file provided" error by using the wrong
working directory.
