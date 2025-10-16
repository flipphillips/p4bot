#!/usr/bin/env python3
""" p4python helper to run `p4 trust -y` once.

This script assumes P4CONFIG / environment are already set up. It performs
the minimum: connect, run trust -y, print a JSON result, disconnect.
"""
import json
import sys
from P4 import P4, P4Exception

def main():
    p4 = P4()
    try:
        p4.connect()
    except Exception as e:
        print(json.dumps({"ok": False, "error": f"connect failed: {e}"}))
        sys.exit(2)

    try:
        try:
            result = p4.run("trust", "-y")
        except P4Exception as e:
            print(json.dumps({"ok": False, "error": str(e)}))
            p4.disconnect()
            sys.exit(2)

        print(json.dumps({"ok": True, "result": result}))
    finally:
        try:
            p4.disconnect()
        except Exception:
            pass

if __name__ == "__main__":
    main()
