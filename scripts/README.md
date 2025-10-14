Repository scripts used in container runtime.

Do NOT commit secrets. Place runtime secrets in `scripts/secrets/` on your host machine. This repo's `.gitignore` already excludes `**/secrets/*` except for `.gitkeep` and `README.md`.

Example:

mkdir -p scripts/secrets
echo "p4password" > scripts/secrets/p4passwd

The `login.sh` script is a tiny placeholder used when starting the devcontainer. Replace it with your real login steps if needed.
