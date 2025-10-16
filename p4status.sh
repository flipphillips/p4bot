#!/usr/bin/env bash
# p4status.sh — depot-centric Perforce status snapshot

set -euo pipefail

# Set P4 environment for ticket-based authentication
export P4TICKETS=/p4/1/.p4tickets

# Set P4 password from file if it exists
if [ -f "${P4PASSWD_FILE:-}" ] && [ -r "${P4PASSWD_FILE}" ]; then
    export P4PASSWD=$(cat "${P4PASSWD_FILE}")
fi

PATHSPEC="//..."
LIMIT=20
OUTPUT_MODE="text"
while [[ $# -gt 0 ]]; do
  case "$1" in
  --limit)
    LIMIT="${2:-20}"
    shift 2
    ;;
  --json)
    OUTPUT_MODE="json"
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
if ! command -v p4 >/dev/null 2>&1; then
  echo "p4status: 'p4' not found in PATH" >&2
  exit 127
fi

if [[ "$OUTPUT_MODE" == "json" ]]; then
  PATHSPEC="$PATHSPEC" LIMIT="$LIMIT" python3 <<'PY'
import collections
import datetime as _dt
import json
import os
import subprocess
import sys

PATHSPEC = os.environ.get("PATHSPEC", "//...")
LIMIT = int(os.environ.get("LIMIT", "20"))


def run_p4(args):
    """Run a Perforce command, returning stdout on success."""
    result = subprocess.run([
        "p4",
        "-ztag",
        *args,
    ], capture_output=True, text=True)
    if result.returncode != 0:
        return None, {
            "status": result.returncode,
            "stderr": result.stderr.strip(),
            "command": " ".join(["p4", "-ztag", *args]),
        }
    return result.stdout, None


def parse_info(output):
    info = {}
    for line in output.splitlines():
        if not line.startswith("... "):
            continue
        parts = line[4:].split(" ", 1)
        key = parts[0]
        value = parts[1] if len(parts) > 1 else ""
        info[key] = value
    return info


def parse_records(output, start_key):
    records = []
    current = None
    for raw_line in output.splitlines():
        if not raw_line.startswith("... "):
            continue
        parts = raw_line[4:].split(" ", 1)
        key = parts[0]
        value = parts[1] if len(parts) > 1 else ""
        if key == start_key:
            if current:
                records.append(current)
            current = {key: value}
        else:
            if current is None:
                current = {}
            current[key] = value
    if current:
        records.append(current)
    return records


def parse_opened(output):
    records = parse_records(output, "depotFile")
    opened = []
    for record in records:
        opened.append({
            "file": record.get("depotFile", ""),
            "user": record.get("user"),
            "client": record.get("client"),
            "host": record.get("host"),
            "action": record.get("action"),
            "change": record.get("change"),
            "type": record.get("type"),
        })
    return opened


def parse_changes(output):
    records = parse_records(output, "change")
    parsed = []
    for record in records:
        desc = record.get("desc", "").replace("\r", "")
        first_line = desc.splitlines()[0] if desc else ""
        when_iso = None
        when_epoch = None
        time_value = record.get("time")
        if time_value:
            try:
                when_epoch = int(time_value)
                when_iso = _dt.datetime.fromtimestamp(
                    when_epoch, tz=_dt.timezone.utc
                ).isoformat()
            except ValueError:
                when_epoch = None
        parsed.append({
            "change": record.get("change"),
            "user": record.get("user"),
            "client": record.get("client"),
            "time_epoch": when_epoch,
            "time_iso": when_iso,
            "description": first_line,
        })
    return parsed


def section_with_limit(items):
    total = len(items)
    visible = items[:LIMIT]
    return {
        "total": total,
        "items": visible,
        "has_more": total > LIMIT,
    }

def file_is_locked(file, user, client):
    out = subprocess.run(
        ["p4", "opened", "-a", file], capture_output=True, text=True
    ).stdout
    for line in out.splitlines():
        if f"by {user}@{client}" in line and "*locked*" in line:
            return True
    return False

def main():
    data = {
        "metadata": {
            "path": PATHSPEC,
            "limit": LIMIT,
            "generated_at": _dt.datetime.now(tz=_dt.timezone.utc).isoformat(),
        },
        "opened_files": [],
        "opened_conflicts": [],
        "pending_changes": {
            "total": 0,
            "items": [],
            "has_more": False,
        },
        "submitted_changes": {
            "total": 0,
            "items": [],
            "has_more": False,
        },
        "shelved_changes": {
            "total": 0,
            "items": [],
            "has_more": False,
        },
        "errors": {},
    }

    info_out, info_err = run_p4(["info"])
    if info_err:
        data["errors"]["info"] = info_err
    else:
        info = parse_info(info_out)
        data["metadata"].update({
            "server": info.get("serverAddress"),
            "client": info.get("clientName"),
            "user": info.get("userName"),
            "host": info.get("clientHost"),
        })

    opened_out, opened_err = run_p4(["opened", "-a", PATHSPEC])
    opened_entries = []
    if opened_err:
        data["errors"]["opened"] = opened_err
    else:
        opened_entries = []
        base_entries = parse_opened(opened_out)
        for entry in base_entries:
            locked = file_is_locked(entry["file"], entry.get("user"), entry.get("client"))
            entry["locked"] = locked
            opened_entries.append(entry)
        data["opened_files"] = opened_entries

        grouped = collections.defaultdict(list)
        for entry in opened_entries:
            grouped[entry.get("file")].append(entry)
        conflicts = []
        for file_path, entries in grouped.items():
            if file_path and len(entries) > 1:
                conflicts.append({
                    "file": file_path,
                    "entries": entries,
                })
        data["opened_conflicts"] = conflicts

    pending_out, pending_err = run_p4(["changes", "-s", "pending", PATHSPEC])
    if pending_err:
        data["errors"]["pending"] = pending_err
    else:
        pending = parse_changes(pending_out)
        data["pending_changes"] = section_with_limit(pending)

    submitted_out, submitted_err = run_p4([
        "changes",
        "-s",
        "submitted",
        "-m",
        str(LIMIT),
        PATHSPEC,
    ])
    if submitted_err:
        data["errors"]["submitted"] = submitted_err
    else:
        submitted = parse_changes(submitted_out)
        data["submitted_changes"] = {
            "total": len(submitted),
            "items": submitted,
            "has_more": len(submitted) == LIMIT,
        }

    shelved_out, shelved_err = run_p4(["changes", "-s", "shelved", PATHSPEC])
    if shelved_err:
        data["errors"]["shelved"] = shelved_err
    else:
        shelved = parse_changes(shelved_out)
        data["shelved_changes"] = section_with_limit(shelved)

    json.dump(data, sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    try:
        main()
    except FileNotFoundError:
        # surfaced earlier in shell, but keep failure readable.
        json.dump({"errors": {"python": "p4 not found"}}, sys.stdout)
        sys.stdout.write("\n")
        sys.exit(1)
PY
  exit 0
fi

SCRATCH=$(mktemp -d "${TMPDIR:-/tmp}/p4status.XXXXXX")
trap 'rm -rf "$SCRATCH"' EXIT

show_p4_error() {
  local errfile="$1" status="$2"
  if [[ -s "$errfile" ]]; then
    sed 's/^/  /' "$errfile"
  else
    printf '  (p4 command failed; exit %s)\n' "$status"
  fi
}

USER=$(p4 -ztag info 2>/dev/null | awk '/^\.\.\. userName/ {print $3}')
CLIENT=$(p4 -ztag info 2>/dev/null | awk '/^\.\.\. clientName/ {print $3}')
PORT=$(p4 -ztag info 2>/dev/null | awk '/^\.\.\. serverAddress/ {print $3}')
HOST=$(p4 -ztag info 2>/dev/null | awk '/^\.\.\. clientHost/ {print $3}')
DATE=$(date '+%Y-%m-%d %H:%M:%S %Z')

hr() { printf '%*s\n' 80 '' | tr ' ' '-'; }

echo "Perforce Status Report"
echo "Path:     $PATHSPEC"
echo "Server:   ${PORT:-<unknown>}"
echo "Client:   ${CLIENT:-<none>}"
echo "User/Host:${USER:-<unknown>} @ ${HOST:-<unknown>}"
echo "When:     $DATE"
hr

echo "OPENED FILES (any user/client)"
opened_out="$SCRATCH/opened"
opened_err="$SCRATCH/opened.err"
if p4 -ztag opened -a "$PATHSPEC" >"$opened_out" 2>"$opened_err"; then
  awk -f - "$opened_out" <<'AWK'
BEGIN {
  count = 0
  fmt = "%-16s %-8s %-10s %-20s %-16s %s\n"
}
($1 == "..." && $2 == "depotFile") { file = $3 }
($1 == "..." && $2 == "user")      { user = $3 }
($1 == "..." && $2 == "client")    { client = $3 }
($1 == "..." && $2 == "host")      { host = $3 }
($1 == "..." && $2 == "action")    { action = $3 }
($1 == "..." && $2 == "change")    { change = $3 }
($1 == "..." && $2 == "type") {
  if (!count++) {
    printf fmt, "USER", "ACTION", "CL", "CLIENT", "HOST", "FILE"
    printf fmt, "----", "------", "--", "------", "----", "----"
  }
  printf fmt, (user ? user : "<none>"), action, change, client, host, file
}
END {
  if (!count) {
    print "  (none)"
  }
}
AWK

  echo "FILES OPENED BY MULTIPLE WORKSPACES"
  awk -f - "$opened_out" <<'AWK'
function shorten_client(raw) {
  if (raw == "") {
    return "<none>"
  }
  if (raw ~ /^\/\// && match(raw, /^\/\/[^\/]+/)) {
    raw = substr(raw, RSTART, RLENGTH)
  }
  if (length(raw) > 16) {
    return substr(raw, 1, 13) "..."
  }
  return raw
}

BEGIN {
  printed = 0
  fmt = "  %-16s %-16s %-8s %-8s\n"
}

($1 == "..." && $2 == "depotFile") { file = $3 }
($1 == "..." && $2 == "user")      { user = $3 }
($1 == "..." && $2 == "client")    { client = $3 }
($1 == "..." && $2 == "action")    { action = $3 }
($1 == "..." && $2 == "change")    { change = $3 }
($1 == "..." && $2 == "type") {
  key = file
  info[key] = info[key] sprintf(fmt, (user ? user : "<unknown>"), shorten_client(client), (action ? action : "?"), (change ? change : "?"))
  count[key]++
}

END {
  for (k in count) {
    if (count[k] > 1) {
      if (!printed) {
        printf "  %-16s %-16s %-8s %-8s\n", "USER", "CLIENT", "ACTION", "CL"
        printf "  %-16s %-16s %-8s %-8s\n", "----", "------", "------", "--"
        printed = 1
      }
      print k
      printf "%s", info[k]
      print ""
    }
  }
  if (!printed) {
    print "  (none)"
  }
}
AWK
else
  status=$?
  show_p4_error "$opened_err" "$status"
fi
hr

format_changes() {
  local heading="$1" outfile="$2" errfile="$3"
  shift 3
  echo "$heading"
  if "$@" >"$outfile" 2>"$errfile"; then
    awk -v limit="$LIMIT" -f - "$outfile" <<'AWK'
BEGIN {
  fmt = "%-8s %-16s %-18s %-20s %s\n"
  count = 0
  total = 0
}
($1 == "..." && $2 == "change") {
  chg = $3
  user = client = when = ""
}
($1 == "..." && $2 == "user")   { user = $3 }
($1 == "..." && $2 == "client") { client = $3 }
($1 == "..." && $2 == "time")   {
  epoch = $3
  when = epoch
  cmd = "date -r " epoch " '+%Y-%m-%d %H:%M:%S' 2>/dev/null"
  if ((cmd | getline out) > 0) {
    when = out
  }
  close(cmd)
  if (when == epoch) {
    cmd = "date -u -d @" epoch " '+%Y-%m-%d %H:%M:%S' 2>/dev/null"
    if ((cmd | getline out) > 0) {
      when = out
    }
    close(cmd)
  }
}
($1 == "..." && $2 == "desc") {
  desc = $0
  sub(/^\.\.\. desc /, "", desc)
  gsub(/\r/, "", desc)
  split(desc, lines, /\n/)
  first = lines[1]
  gsub(/\t/, "  ", first)
  total++
  if (count < limit) {
    if (!count) {
      printf fmt, "CL", "USER", "CLIENT", "WHEN", "DESC"
      printf fmt, "--", "----", "------", "----", "----"
    }
    usercol = (user != "" ? user : "<unknown>")
    clientcol = (client != "" ? client : "<none>")
    if (clientcol ~ /^\/\//) {
      # keep depot-style prefix but drop trailing path after workspace name
      if (match(clientcol, /^\/\/[^\/]+/)) {
        clientcol = substr(clientcol, RSTART, RLENGTH)
      }
    }
    if (length(clientcol) > 16) {
      clientcol = substr(clientcol, 1, 13) "..."
    }
    if (clientcol == "") { clientcol = "<none>" }
    printf fmt, chg, usercol, clientcol, when, first
    count++
  }
}
END {
  if (!count) {
    print "  (none)"
  } else if (total > limit) {
    printf "  ... (%d more)\n", total - limit
  }
}
AWK
  else
    status=$?
    show_p4_error "$errfile" "$status"
  fi
  hr
}

format_changes "PENDING CHANGELISTS touching $PATHSPEC" \
  "$SCRATCH/pending" "$SCRATCH/pending.err" \
  p4 -ztag changes -s pending "$PATHSPEC"

format_changes "RECENT SUBMITTED CHANGES (limit $LIMIT)" \
  "$SCRATCH/submitted" "$SCRATCH/submitted.err" \
  p4 -ztag changes -s submitted -m "$LIMIT" "$PATHSPEC"

format_changes "SHELVED CHANGELISTS touching $PATHSPEC" \
  "$SCRATCH/shelved" "$SCRATCH/shelved.err" \
  p4 -ztag changes -s shelved "$PATHSPEC"

echo "Done."
