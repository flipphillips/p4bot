#!/usr/bin/env bash
set -euo pipefail

# Minimal diagnostic helper used during devcontainer start. This no longer
# attempts to use the p4 CLI. It prints the P4CONFIG and P4TICKETS settings
# visible inside the container.

echo "[p4-login] diagnostic"
echo "P4CONFIG=${P4CONFIG:-/root/.p4config}"
echo "P4TICKETS=${P4TICKETS:-/root/.p4tickets}"
if [[ -f "${P4TICKETS:-/root/.p4tickets}" ]]; then
  ls -l "${P4TICKETS:-/root/.p4tickets}"
else
  echo "ticket file not found"
fi

if [[ -f "${P4CONFIG:-/root/.p4config}" ]]; then
  echo "P4CONFIG contents:"
  sed -n '1,200p' "${P4CONFIG:-/root/.p4config}"
else
  echo "p4config not found"
fi

exit 0
