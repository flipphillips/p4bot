#!/usr/bin/python3

import sys
import subprocess
import os
from pathlib import Path
try:
    import requests
    _have_requests = True
except Exception:
    _have_requests = False
    import json
    from urllib.request import Request, urlopen
    from urllib.error import URLError, HTTPError

webhook_url = os.environ.get("SLACK_WEBHOOK")
if not webhook_url:
    print("Environment variable SLACK_WEBHOOK is required (no default allowed)", file=sys.stderr)
    sys.exit(2)

if len(sys.argv) < 3:
    print("Usage: submit-slack.py <change> <user>", file=sys.stderr)
    sys.exit(2)



def load_ticket():
    """Resolve a P4 ticket from env variables or the configured file."""
    ticket = (os.getenv("P4_TICKET") or os.getenv("P4TICKET") or "").strip()
    if ticket:
        return ticket
    ticket_path = os.getenv("P4_TICKET_FILE") or os.getenv("P4TICKETS")
    if not ticket_path:
        return ""
    try:
        ticket_text = Path(ticket_path).read_text(encoding="utf-8").strip()
    except OSError:
        return ""
    if ticket_text:
        os.environ["P4_TICKET"] = ticket_text
    return ticket_text


# ---- Perforce helpers: respect P4PORT/P4USER and optional ticket

def p4_cmd(*args):
    cmd = ["p4"]
    p4port = os.getenv("P4PORT")
    p4user = os.getenv("P4USER")
    ptok = load_ticket()
    if p4port:
        cmd += ["-p", p4port]
    if p4user:
        cmd += ["-u", p4user]
    if ptok:
        cmd += ["-P", ptok]
    cmd += list(args)
    return cmd


# Optional: preflight (helps logs if ticket missing/expired but doesn't fail hard)
try:
    subprocess.run(p4_cmd("login", "-s"),
                   stdout=subprocess.DEVNULL,
                   stderr=subprocess.DEVNULL,
                   check=False)
except Exception:
    pass
change = sys.argv[1]
user = sys.argv[2]


def get_description_from_describe(change):
    try:
        out = subprocess.run(["p4", "-Ztag", "describe", change], capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError:
        return None
    lines = []
    for line in out.stdout.splitlines():
        # p4 -ztag describe emits description lines as: '... desc <text>'
        if line.startswith("... desc "):
            lines.append(line[len("... desc "):])
    return "\n".join(lines).strip() if lines else None


def get_description_from_change_spec(change):
    try:
        out = subprocess.run(["p4", "-ztag", "change", "-o", change], capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError:
        return None
    lines = out.stdout.splitlines()
    desc_lines = []
    in_desc = False
    for l in lines:
        # In 'p4 change -o' the Description: field is followed by indented lines
        if in_desc:
            if l.startswith('\t') or l.startswith('    '):
                desc_lines.append(l.lstrip('\t').lstrip())
            else:
                break
        if l.startswith('Description:'):
            in_desc = True
    return "\n".join(desc_lines).strip() if desc_lines else None


commit_message = get_description_from_describe(change)
if not commit_message:
    commit_message = get_description_from_change_spec(change)
if not commit_message:
    commit_message = "_No commit message provided_"

message = (
    f"User *{user}* submitted changelist `{change}`:\n"
    f"*Commit message:*\n{commit_message}\n"
)


def post_to_slack(payload_text):
    if _have_requests:
        try:
            requests.post(webhook_url, json={"text": payload_text}, timeout=8)
            return True
        except Exception as e:
            print(f"Failed to post to Slack (requests): {e}", file=sys.stderr)
            return False
    else:
        data = json.dumps({"text": payload_text}).encode("utf-8")
        req = Request(webhook_url, data=data, headers={"Content-Type": "application/json"})
        try:
            with urlopen(req, timeout=5) as resp:
                resp.read()
            return True
        except (HTTPError, URLError) as e:
            print(f"Failed to post to Slack (urllib): {e}", file=sys.stderr)
            return False


post_to_slack(message)
