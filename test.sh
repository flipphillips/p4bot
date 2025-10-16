#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
set -a
source "${SCRIPT_DIR}/slackbot.env"
set +a
if [[ -z "${P4_TICKET:-}" && -n "${P4_TICKET_FILE:-}" && -f "${P4_TICKET_FILE}" ]]; then
  export P4_TICKET="$(<"${P4_TICKET_FILE}")"
fi
python3 "${SCRIPT_DIR}/slack-files.py"
