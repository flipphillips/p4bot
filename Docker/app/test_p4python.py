#!/usr/bin/env python3
import json
import os
import sys
from P4 import P4, P4Exception

# Minimal p4python test: read env, connect, run info. Auto-trust once on SSL
# errors and persist a small container-local marker.
P4PORT = os.environ.get("P4PORT")
P4USER = os.environ.get("P4USER")
P4TICKETS = os.environ.get("P4TICKETS")

# If a P4CONFIG file is provided, read values from it when env vars are missing
cfg_path = os.environ.get("P4CONFIG") or "/root/.p4config"
if os.path.exists(cfg_path):
    try:
        for ln in open(cfg_path, "r").read().splitlines():
            ln = ln.strip()
            if not ln or ln.startswith("#"):
                continue
            if "=" in ln:
                k, v = ln.split("=", 1)
                k = k.strip()
                v = v.strip()
                if k == "P4PORT" and not P4PORT:
                    P4PORT = v
                elif k == "P4USER" and not P4USER:
                    P4USER = v
                elif k == "P4TICKETS" and not P4TICKETS:
                    P4TICKETS = v
    except Exception:
        # if parsing fails, continue with env values
        pass

# default values
P4USER = P4USER or "p4status"
P4TICKETS = P4TICKETS or "/root/.p4tickets"
TRUST_MARKER = "/root/.p4trusted"

if not P4PORT:
    print(json.dumps({"ok": False, "error": "P4PORT not set"}))
    sys.exit(2)

os.environ["P4TICKETS"] = P4TICKETS

p4 = P4(debug=3)

config = p4.p4config_file

p4.port = P4PORT
p4.user = P4USER

def out_err(msg):
    print(json.dumps({"ok": False, "error": msg}))
    sys.exit(2)

try:
    p4.connect()
    client=p4.fetch_client()
    info = p4.run("info")
    p4.disconnect()
    print(json.dumps({"ok": True, "info": info}))
    sys.exit(0)
except P4Exception as e:
    msg = str(e)
    if any(x in msg.lower() for x in ("ssl", "trust", "certificate", "fingerprint")):
        if os.path.exists(TRUST_MARKER):
            out_err(msg)
        try:
            p4.connect()
            try:
                p4.run("trust", "-y")
            except P4Exception:
                pass
            info = p4.run("info")
            p4.disconnect()
            try:
                with open(TRUST_MARKER, "w") as f:
                    f.write("trusted\n")
            except Exception:
                pass
            print(json.dumps({"ok": True, "info": info}))
            sys.exit(0)
        except Exception as e2:
            out_err(str(e2))
    out_err(msg)
