#!/usr/bin/env bash
# Minimal login helper for devcontainer. Intentionally simple and safe.
set -euo pipefail

echo "Running /scripts/login.sh (placeholder)"
# If a p4 password file exists, show masked info for debugging
if [ -f /scripts/secrets/p4passwd ]; then
  echo "Found /scripts/secrets/p4passwd (content hidden)"
else
  echo "/scripts/secrets/p4passwd not found"
fi

# Keep exit 0 to not break container startup flows that expect login to succeed
exit 0
