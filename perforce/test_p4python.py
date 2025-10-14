#!/usr/bin/env python3
"""p4python connectivity test that attempts to authenticate using the
secrets file and then runs a simple `info` command via P4Python.

This script will try a CLI `p4 login` using the password found at
P4PASSWD_FILE (default: /scripts/secrets/p4passwd) and then import
P4 to run `info`. Output is JSON for easy parsing.
"""

import json
import os
import subprocess
import sys

P4PASSWD_FILE = os.environ.get("P4PASSWD_FILE", "/scripts/secrets/p4passwd")

def read_password(path: str) -> str:
    if not os.path.exists(path):
        return ""
    with open(path, "r") as f:
        data = f.read().strip()
    # accept either raw password or key=value style
    if data.startswith("password="):
        return data.split("=", 1)[1]
    return data

password = read_password(P4PASSWD_FILE)

# Try CLI login first if we have a password
if password:
    try:
        # p4 login reads password from stdin
        subprocess.run(["p4", "login"], input=password + "\n", text=True, check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        # print a JSON object describing the CLI login failure, then continue
        print(json.dumps({"ok": False, "phase": "cli-login", "error": "p4 login failed", "stderr": e.stderr}))
        # continue to attempt P4Python which may succeed for non-authenticated info

try:
    from P4 import P4, P4Exception
except Exception as e:
    print(json.dumps({"ok": False, "phase": "import", "error": f"import failed: {e}"}))
    sys.exit(1)

p4 = P4()
try:
    p4.connect()
    info = p4.run("info")
    p4.disconnect()
    print(json.dumps({"ok": True, "phase": "info", "info": info}))
    sys.exit(0)
except P4Exception as e:
    try:
        p4.disconnect()
    except Exception:
        pass
    print(json.dumps({"ok": False, "phase": "p4python", "error": str(e)}))
    sys.exit(2)
