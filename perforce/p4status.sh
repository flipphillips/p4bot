#!/usr/bin/env bash
set -euo pipefail

# p4status.sh - minimal wrapper that delegates formatting to p4status.py

# Default P4 tickets path if not provided
if [ -z "${P4TICKETS:-}" ]; then
  export P4TICKETS="$HOME/.p4tickets"
fi

FORMAT="text"
LIMIT=20
PATHSPEC="//..."

while [[ $# -gt 0 ]]; do
  case "$1" in
    --limit)
      LIMIT="${2:-20}"
      shift 2
      ;;
    --json)
      FORMAT="json"
      shift
      ;;
    --text)
      FORMAT="text"
      shift
      ;;
    *)
      PATHSPEC="$1"
      shift
      ;;
  esac
done

if [[ "$PATHSPEC" != *"..." ]]; then
  PATHSPEC="${PATHSPEC%/}/..."
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "${SCRIPT_DIR}/p4status.py" --limit "$LIMIT" --format "$FORMAT" "$PATHSPEC"

