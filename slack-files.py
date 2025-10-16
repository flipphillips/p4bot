#!/usr/bin/env python3
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from P4 import P4, P4Exception

from slackbot_commands import COMMAND_DESCRIPTIONS


def load_ticket() -> str:
    """Return ticket string, hydrating from file if necessary."""
    ticket = os.environ.get("P4_TICKET", "").strip()
    if ticket:
        return ticket
    ticket_path = os.environ.get("P4_TICKET_FILE")
    if not ticket_path:
        return ""
    try:
        ticket_text = Path(ticket_path).read_text(encoding="utf-8").strip()
    except OSError:
        return ""
    os.environ["P4_TICKET"] = ticket_text
    return ticket_text


@contextmanager
def connect_p4() -> Iterable[P4]:
    """Context manager that yields a connected P4 client."""
    p4 = P4()
    p4.port = os.environ.get("P4PORT")
    p4.user = os.environ.get("P4USER")
    charset = os.environ.get("P4CHARSET")
    if charset:
        p4.charset = charset
    ticket_file = os.environ.get("P4TICKETS")
    if ticket_file:
        p4.ticket_file = ticket_file
    trust_file = os.environ.get("P4TRUST")
    if trust_file:
        p4.trust_file = trust_file
    ticket = load_ticket()
    if ticket:
        p4.password = ticket
    try:
        p4.connect()
        yield p4
    finally:
        try:
            p4.disconnect()
        except Exception:
            pass


REGISTERED_COMMANDS = {"/files", "/describe", "/changes", "/locked", "/health"}
_missing_docs = REGISTERED_COMMANDS - COMMAND_DESCRIPTIONS.keys()
if _missing_docs:
    raise RuntimeError(
        f"slackbot_commands.py is missing descriptions for: {', '.join(sorted(_missing_docs))}"
    )


_bot_token = os.environ.get("SLACK_BOT_TOKEN")
if not _bot_token:
    raise RuntimeError("SLACK_BOT_TOKEN is required to run the Slack bot.")

app = App(token=_bot_token)


def p4_list_files(pattern: str, limit: int = 20) -> List[str]:
    with connect_p4() as p4:
        try:
            results = p4.run_files(pattern)
        except P4Exception as exc:
            return [f"ERROR: {exc}"]
    return [item.get("depotFile", "") for item in results[:limit]]


def describe_change(cl: str) -> Tuple[bool, str]:
    with connect_p4() as p4:
        try:
            result = p4.run_describe("-s", cl)
        except P4Exception as exc:
            return False, f":x: unable to describe changelist `{cl}`:\n```\n{exc}\n```"
    if not result:
        return False, f":x: changelist `{cl}` not found."
    data = result[0]
    header = "Change {change} by {user}@{client}".format(
        change=data.get("change", cl),
        user=data.get("user", "unknown"),
        client=data.get("client", "unknown"),
    )
    desc = (data.get("desc") or data.get("description") or "").strip()
    if not desc:
        desc = "_No description provided._"
    files = data.get("depotFile") or []
    actions = data.get("action") or []
    revs = data.get("rev") or []
    lines = []
    truncated = len(files) > 25
    for depot, action, rev in zip(files[:25], actions[:25], revs[:25]):
        lines.append(f"• `{action} {depot}#{rev}`")
    body = [f"*{header}*", "", desc]
    if lines:
        body.extend(["", "*Files:*", *lines])
        if truncated:
            body.append("_(truncated)_")
    body_text = "\n".join(body)
    if len(body_text) > 3000:
        body_text = body_text[:2997] + '...'
    return True, body_text


def recent_changes(path: str, limit: int = 10) -> Tuple[bool, str]:
    with connect_p4() as p4:
        try:
            rows = p4.run_changes("-m", str(limit), path)
        except P4Exception as exc:
            return False, f":x: unable to list changes for `{path}`:\n```\n{exc}\n```"
    if not rows:
        return True, f"No submitted changes match `{path}`."
    lines = []
    for row in rows:
        change = row.get("change", "?")
        user = row.get("user", "unknown")
        summary = (row.get("desc", "").strip().splitlines() or [""])[0]
        status = row.get("status", "submitted")
        lines.append(f"`{change}` ({status}) — {summary} _by {user}_")
    text = "*Recent changes*\n" + "\n".join(lines)
    return True, text[:3000]


def list_locked_files(path: str, limit: int = 25) -> Tuple[List[Tuple[str, bool]], bool, str]:
    with connect_p4() as p4:
        try:
            entries = p4.run("opened", "-a", path)
        except P4Exception as exc:
            message = str(exc)
            if "File(s) not opened anywhere." in message:
                return [], False, ""
            return [], False, f":warning: `p4 opened` failed:\n```\n{message[:2900]}\n```"
    if not isinstance(entries, Sequence):
        entries = []
    truncated = len(entries) > limit
    rows = []
    for entry in entries[:limit]:
        depot = entry.get("depotFile", "<unknown>")
        rev = entry.get("rev") or entry.get("workRev") or entry.get("haveRev")
        location = f"{depot}#{rev}" if rev else depot
        action = entry.get("action", "edit")
        change = entry.get("change", "default")
        user = entry.get("user", "unknown")
        client = entry.get("client", entry.get("clientName", ""))
        client_part = f"@{client}" if client else ""
        summary = f"{location} — {action} change {change} by {user}{client_part}"
        file_type = entry.get("type", "")
        is_exclusive = "+l" in file_type or bool(entry.get("ourLock")) or bool(entry.get("otherLock"))
        rows.append((summary, is_exclusive))
    return rows, truncated, ""


def login_status() -> Tuple[bool, str]:
    with connect_p4() as p4:
        try:
            output = p4.run("login", "-s")
        except P4Exception as exc:
            return False, f":warning: p4 auth issue:\n```\n{exc}\n```"
    if not output:
        return True, "`p4 login -s` returned no output."
    if isinstance(output, list):
        text = "\n".join(str(item) for item in output)
    else:
        text = str(output)
    return True, f"```\n{text}\n```"


@app.command("/files")
def files_cmd(ack, say, command):
    ack("Looking that up…")
    pattern = (command.get("text") or "").strip() or "//..."
    files = p4_list_files(pattern, limit=25)
    if not files:
        say(f"No matches for `{pattern}`")
        return
    if len(files) == 1 and files[0].startswith("ERROR:"):
        say(files[0])
        return
    body = "*Files:*\n" + "\n".join(f"• `{f}`" for f in files)
    if len(files) == 25:
        body += "\n_(truncated)_"
    say(body)


@app.command("/describe")
def describe_cmd(ack, say, command):
    ack("describing…")
    cl = (command.get("text") or "").strip()
    if not cl.isdigit():
        say("Usage: `/describe <changelist>`")
        return
    ok, message = describe_change(cl)
    say(message)


@app.command("/changes")
def changes_cmd(ack, say, command):
    ack("fetching changes…")
    path = (command.get("text") or "").strip() or "//..."
    ok, message = recent_changes(path, limit=10)
    say(message)


@app.command("/locked")
def locked_cmd(ack, say, command):
    ack("checking locks…")
    path = (command.get("text") or "").strip() or "//..."
    rows, truncated, warning = list_locked_files(path, limit=25)
    if warning:
        say(warning)
        return
    if not rows:
        say(f"No files are currently open for edit under `{path}`.")
        return
    bullets = []
    for summary, exclusive in rows:
        prefix = ":lock: " if exclusive else ""
        bullets.append(f"• {prefix}{summary}")
    body = "*Opened files*\n" + "\n".join(bullets)
    if truncated:
        body += "\n_(truncated)_"
    say(body)


@app.command("/health")
def health_cmd(ack, say, command):
    ack("checking…")
    ok, message = login_status()
    say(message)


# Uncomment to lock bot to particular channels
# allowed = {c for c in os.getenv("ALLOWED_CHANNELS", "").split(",") if c}
# chan = command.get("channel_id")
# if allowed and chan not in allowed:
#     ack(":no_entry: not allowed here")
#     return


if __name__ == "__main__":
    app_token = os.environ.get("SLACK_APP_TOKEN")
    if not app_token:
        raise RuntimeError("SLACK_APP_TOKEN is required to start the Socket Mode handler.")
    SocketModeHandler(app, app_token).start()
