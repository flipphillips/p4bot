#!/usr/bin/env python3
"""
p4status.py - Generate JSON status report for Perforce depot
"""

import argparse
import collections
import datetime as _dt
import json
import subprocess
import sys
from typing import Dict, List, Optional, Tuple, Any


def run_p4(args: List[str]) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
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


def parse_info(output: str) -> Dict[str, str]:
    """Parse p4 info output into a dictionary."""
    info = {}
    for line in output.splitlines():
        if not line.startswith("... "):
            continue
        parts = line[4:].split(" ", 1)
        key = parts[0]
        value = parts[1] if len(parts) > 1 else ""
        info[key] = value
    return info


def parse_records(output: str, start_key: str) -> List[Dict[str, str]]:
    """Parse p4 tagged output into records starting with start_key."""
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


def parse_opened(output: str) -> List[Dict[str, Optional[str]]]:
    """Parse p4 opened output into structured data."""
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


def parse_changes(output: str) -> List[Dict[str, Any]]:
    """Parse p4 changes output into structured data."""
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


def section_with_limit(items: List[Any], limit: int) -> Dict[str, Any]:
    """Create a section dictionary with pagination info."""
    total = len(items)
    visible = items[:limit]
    return {
        "total": total,
        "items": visible,
        "has_more": total > limit,
    }


def file_is_locked(file: str, user: Optional[str], client: Optional[str]) -> bool:
    """Check if a file is locked by checking p4 opened output."""
    try:
        result = subprocess.run(
            ["p4", "opened", "-a", file], 
            capture_output=True, 
            text=True,
            timeout=30
        )
        out = result.stdout
        for line in out.splitlines():
            if f"by {user}@{client}" in line and "*locked*" in line:
                return True
    except (subprocess.TimeoutExpired, subprocess.SubprocessError):
        pass
    return False


def generate_status_report(pathspec: str, limit: int) -> Dict[str, Any]:
    """Generate the complete status report."""
    data = {
        "metadata": {
            "path": pathspec,
            "limit": limit,
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

    # Get server info
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

    # Get opened files
    opened_out, opened_err = run_p4(["opened", "-a", pathspec])
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

        # Find conflicts (files opened by multiple clients)
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

    # Get pending changes
    pending_out, pending_err = run_p4(["changes", "-s", "pending", pathspec])
    if pending_err:
        data["errors"]["pending"] = pending_err
    else:
        pending = parse_changes(pending_out)
        data["pending_changes"] = section_with_limit(pending, limit)

    # Get submitted changes
    submitted_out, submitted_err = run_p4([
        "changes",
        "-s",
        "submitted",
        "-m",
        str(limit),
        pathspec,
    ])
    if submitted_err:
        data["errors"]["submitted"] = submitted_err
    else:
        submitted = parse_changes(submitted_out)
        data["submitted_changes"] = {
            "total": len(submitted),
            "items": submitted,
            "has_more": len(submitted) == limit,
        }

    # Get shelved changes
    shelved_out, shelved_err = run_p4(["changes", "-s", "shelved", pathspec])
    if shelved_err:
        data["errors"]["shelved"] = shelved_err
    else:
        shelved = parse_changes(shelved_out)
        data["shelved_changes"] = section_with_limit(shelved, limit)

    return data


def print_text_report(data: Dict[str, Any], limit: int) -> None:
    """Render the JSON-style report as human-readable text similar to the shell script output."""
    md = data.get("metadata", {})
    path = md.get("path", "//...")
    server = md.get("server") or "<unknown>"
    client = md.get("client") or "<none>"
    user = md.get("user") or "<unknown>"
    host = md.get("host") or "<unknown>"
    print("Perforce Status Report")
    print(f"Path:     {path}")
    print(f"Server:   {server}")
    print(f"Client:   {client}")
    print(f"User/Host:{user} @ {host}")
    print(f"When:     {md.get('generated_at')}")
    print("-" * 80)

    def shorten_middle(s: str, max_len: int) -> str:
        if not s:
            return "<none>"
        if len(s) <= max_len:
            return s
        pref = (max_len - 3) // 2
        suf = (max_len - 3) - pref
        return s[:pref] + "..." + s[-suf:]

    # Opened files
    print("OPENED FILES (any user/client)")
    opened = data.get("opened_files", [])
    if not opened:
        print("  (none)")
    else:
        print(f"{'USER':<12} {'ACTION':<6} {'CL':<8} {'CLIENT':<22} FILE")
        print(f"{'----':<12} {'------':<6} {'--':<8} {'------':<22} {'----'}")
        for e in opened:
            u = shorten_middle(e.get("user") or "<none>", 12)
            action = e.get("action") or ""
            change = e.get("change") or ""
            clientcol = shorten_middle(e.get("client") or "<none>", 22)
            filecol = e.get("file") or ""
            print(f"{u:<12} {action:<6} {change:<8} {clientcol:<22} {filecol}")

    print("FILES OPENED BY MULTIPLE WORKSPACES")
    conflicts = data.get("opened_conflicts", [])
    if not conflicts:
        print("  (none)")
    else:
        for c in conflicts:
            print("  " + shorten_middle(c.get("file", ""), 60))
            for ent in c.get("entries", []):
                usercol = ent.get("user") or "<unknown>"
                clientcol = shorten_middle(ent.get("client") or "<none>", 16)
                action = ent.get("action") or "?"
                chg = ent.get("change") or "?"
                print(f"    {usercol:<16} {clientcol:<16} {action:<8} {chg:<8}")

    print("-" * 80)
    # Pending
    pending = data.get("pending_changes", {})
    print(f"PENDING CHANGELISTS touching {path}")
    if not pending.get("items"):
        print("  (none)")
    else:
        for it in pending.get("items", []):
            print(f"{it.get('change', ''):<8} {it.get('user',''):<16} {it.get('client',''):<20} {it.get('time_iso',''):<20} {it.get('description','')}")

    print("-" * 80)
    submitted = data.get("submitted_changes", {})
    print(f"RECENT SUBMITTED CHANGES (limit {limit})")
    if not submitted.get("items"):
        print("  (none)")
    else:
        print(f"{'CL':<8} {'USER':<16} {'CLIENT':<18} {'WHEN':<20} DESC")
        for it in submitted.get("items", []):
            print(f"{it.get('change',''):<8} {it.get('user',''):<16} {it.get('client',''):<18} {it.get('time_iso',''):<20} {it.get('description','')}")

    print("-" * 80)
    shelved = data.get("shelved_changes", {})
    print(f"SHELVED CHANGELISTS touching {path}")
    if not shelved.get("items"):
        print("  (none)")
    else:
        for it in shelved.get("items", []):
            print(f"{it.get('change',''):<8} {it.get('user',''):<16} {it.get('client',''):<20} {it.get('time_iso',''):<20} {it.get('description','')}")

    print("-" * 80)
    if data.get("errors"):
        print("Errors:")
        for k, v in data.get("errors", {}).items():
            print(f"  {k}: {v}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Generate JSON status report for Perforce depot")
    parser.add_argument("pathspec", nargs="?", default="//...",
                       help="Perforce path specification (default: //...)")
    parser.add_argument("--limit", type=int, default=20,
                       help="Limit number of results (default: 20)")
    parser.add_argument("--format", choices=["json", "text"], default="json",
                        help="Output format: json (default) or text")
    
    args = parser.parse_args()
    
    # Ensure pathspec ends with ...
    pathspec = args.pathspec
    if not pathspec.endswith("..."):
        pathspec = f"{pathspec.rstrip('/')}/..."
    
    # Check if p4 is available (existence). If p4 runs but returns non-zero due to
    # authentication, continue; that will be captured per-command later.
    try:
        subprocess.run(["p4", "info"], capture_output=True, check=False)
    except FileNotFoundError:
        json.dump({"errors": {"python": "p4 not found or not accessible"}}, sys.stdout, indent=2)
        sys.stdout.write("\n")
        sys.exit(1)
    
    try:
        data = generate_status_report(pathspec, args.limit)
        if args.format == "json":
            json.dump(data, sys.stdout, indent=2)
            sys.stdout.write("\n")
        else:
            # Text formatter
            print_text_report(data, args.limit)
    except Exception as e:
        json.dump({"errors": {"python": str(e)}}, sys.stdout, indent=2)
        sys.stdout.write("\n")
        sys.exit(1)


if __name__ == "__main__":
    main()


def print_text_report(data: Dict[str, Any], limit: int) -> None:
    """Render the JSON-style report as human-readable text similar to the shell script output."""
    md = data.get("metadata", {})
    path = md.get("path", "//...")
    server = md.get("server") or "<unknown>"
    client = md.get("client") or "<none>"
    user = md.get("user") or "<unknown>"
    host = md.get("host") or "<unknown>"
    print("Perforce Status Report")
    print(f"Path:     {path}")
    print(f"Server:   {server}")
    print(f"Client:   {client}")
    print(f"User/Host:{user} @ {host}")
    print(f"When:     {md.get('generated_at')}")
    print("-" * 80)

    def shorten_middle(s: str, max_len: int) -> str:
        if not s:
            return "<none>"
        if len(s) <= max_len:
            return s
        pref = (max_len - 3) // 2
        suf = (max_len - 3) - pref
        return s[:pref] + "..." + s[-suf:]

    # Opened files
    print("OPENED FILES (any user/client)")
    opened = data.get("opened_files", [])
    if not opened:
        print("  (none)")
    else:
        print(f"{'USER':<12} {'ACTION':<6} {'CL':<8} {'CLIENT':<22} FILE")
        print(f"{'----':<12} {'------':<6} {'--':<8} {'------':<22} {'----'}")
        for e in opened:
            u = shorten_middle(e.get("user") or "<none>", 12)
            action = e.get("action") or ""
            change = e.get("change") or ""
            clientcol = shorten_middle(e.get("client") or "<none>", 22)
            filecol = e.get("file") or ""
            print(f"{u:<12} {action:<6} {change:<8} {clientcol:<22} {filecol}")

    print("FILES OPENED BY MULTIPLE WORKSPACES")
    conflicts = data.get("opened_conflicts", [])
    if not conflicts:
        print("  (none)")
    else:
        for c in conflicts:
            print("  " + shorten_middle(c.get("file", ""), 60))
            for ent in c.get("entries", []):
                usercol = ent.get("user") or "<unknown>"
                clientcol = shorten_middle(ent.get("client") or "<none>", 16)
                action = ent.get("action") or "?"
                chg = ent.get("change") or "?"
                print(f"    {usercol:<16} {clientcol:<16} {action:<8} {chg:<8}")

    print("-" * 80)
    # Pending
    pending = data.get("pending_changes", {})
    print(f"PENDING CHANGELISTS touching {path}")
    if not pending.get("items"):
        print("  (none)")
    else:
        for it in pending.get("items", []):
            print(f"{it.get('change', ''):<8} {it.get('user',''):<16} {it.get('client',''):<20} {it.get('time_iso',''):<20} {it.get('description','')}")

    print("-" * 80)
    submitted = data.get("submitted_changes", {})
    print(f"RECENT SUBMITTED CHANGES (limit {limit})")
    if not submitted.get("items"):
        print("  (none)")
    else:
        print(f"{'CL':<8} {'USER':<16} {'CLIENT':<18} {'WHEN':<20} DESC")
        for it in submitted.get("items", []):
            print(f"{it.get('change',''):<8} {it.get('user',''):<16} {it.get('client',''):<18} {it.get('time_iso',''):<20} {it.get('description','')}")

    print("-" * 80)
    shelved = data.get("shelved_changes", {})
    print(f"SHELVED CHANGELISTS touching {path}")
    if not shelved.get("items"):
        print("  (none)")
    else:
        for it in shelved.get("items", []):
            print(f"{it.get('change',''):<8} {it.get('user',''):<16} {it.get('client',''):<20} {it.get('time_iso',''):<20} {it.get('description','')}")

    print("-" * 80)
    if data.get("errors"):
        print("Errors:")
        for k, v in data.get("errors", {}).items():
            print(f"  {k}: {v}")