#!/usr/bin/env python3
"""Emit Slack slash-command documentation in Markdown."""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from slackbot_commands import COMMAND_DESCRIPTIONS

if __name__ == "__main__":
    print("# Slack Bot Commands\n")
    for command, description in COMMAND_DESCRIPTIONS.items():
        print(f"- `{command}` — {description}")
