#!/usr/bin/env python3

import json
import os
import sys
from P4 import P4, P4Exception

def out_err(msg):
    print(json.dumps({"ok": False, "error": msg}))
    sys.exit(2)

p4 = P4(debug=3)

try:
    p4.connect()
    client=p4.fetch_client()
    info = p4.run("info")
    p4.disconnect()
    print(json.dumps({"ok": True, "info": info}))
    sys.exit(0)
except P4Exception as e:
    msg = str(e)
    out_err(msg)
