#!/usr/bin/env python3
"""p4python connectivity test that attempts to authenticate using the
secrets file and then runs a simple `info` command via P4Python.

This script will attempt to use the environment or `P4TICKETS`/`P4CONFIG` to
authenticate and then import P4 to run `info`. It no longer expects a
`/scripts` hierarchy.
P4 to run `info`. Output is JSON for easy parsing.
"""

import json
import os
import subprocess
import sys
from P4 import P4, P4Exception

P4USER = os.environ.get("P4USER", "p4status")
P4PORT = os.environ.get("P4PORT")
P4TICKETS = os.environ.get("P4TICKETS", "/root/.p4tickets")

def _json_err(msg, phase="p4python", extra=None, code=2):
    out = {"ok": False, "phase": phase, "error": msg}
    if extra:
        out.update(extra)
    print(json.dumps(out))
    sys.exit(code)


# Make sure P4TICKETS env is visible to P4Python
os.environ["P4TICKETS"] = P4TICKETS

if not P4PORT:
    _json_err("P4PORT not set. Please set the Perforce server in $P4PORT (e.g. perforce:1666)")

p4 = P4()
p4.port = P4PORT
p4.user = P4USER

# Basic diagnostics helpful for debugging
diag = {
    "P4PORT": P4PORT,
    "P4USER": P4USER,
    "P4TICKETS": P4TICKETS,
    "ticket_exists": os.path.exists(P4TICKETS),
}

try:
    p4.connect()
    info = p4.run("info")
    p4.disconnect()
    print(json.dumps({"ok": True, "phase": "info", "info": info, "diag": diag}))
    sys.exit(0)
except P4Exception as e:
    # try to disconnect cleanly
    try:
        p4.disconnect()
    except Exception:
        pass

    msg = str(e)
    extra = {"diag": diag}

    # Helpful hint for SSL/trust problems
    if any(x in msg.lower() for x in ("ssl", "trust", "certificate", "fingerprint")):
        hint = (
            "SSL/trust error detected. If this is the first time connecting to the server, "
            "you may need to accept the server fingerprint. Two options:\n"
            "  1) On a host with the Perforce CLI: run `p4 trust -y` against $P4PORT, then copy ~/.p4tickets into the container.\n"
            "  2) Programmatically accept via P4Python using `p4.run('trust','-y')` (requires P4Python & connect).\n"
            "Current error: " + msg
        )
        _json_err(hint, extra=extra)

    _json_err(msg, extra=extra)
