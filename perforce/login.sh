#!/usr/bin/env bash
set -euo pipefail

# login.sh - trust Perforce server and attempt non-interactive p4 login
# Usage: ./login.sh [password-file]

PWD_FILE=${1:-${P4PASSWD_FILE:-/scripts/secrets/p4passwd}}

echo "[p4-login] Using password file: ${PWD_FILE}"

if ! command -v p4 >/dev/null 2>&1; then
  echo "[p4-login] p4: not found in PATH" >&2
  exit 2
fi

echo "[p4-login] Running: p4 trust -y"
if p4 trust -y; then
  echo "[p4-login] p4 trust succeeded"
else
  echo "[p4-login] p4 trust failed" >&2
fi

if [[ -f "$PWD_FILE" && -r "$PWD_FILE" ]]; then
  # read first non-empty line
  line=$(head -n1 "$PWD_FILE" || true)
  P4PASSWD=${line#password=}
  P4PASSWD=$(printf "%s" "$P4PASSWD" | tr -d '\r\n')
  if [[ -z "$P4PASSWD" ]]; then
    echo "[p4-login] password file empty or not in expected format" >&2
  else
    echo "[p4-login] Attempting non-interactive p4 login"
    if printf '%s\n' "$P4PASSWD" | p4 login >/dev/null 2>&1; then
      echo "[p4-login] p4 login succeeded"
      exit 0
    else
      echo "[p4-login] p4 login failed (password may be invalid)" >&2
    fi
  fi
else
  echo "[p4-login] Password file $PWD_FILE not found or unreadable" >&2
fi

echo "[p4-login] Done (see messages above)." >&2
exit 1
