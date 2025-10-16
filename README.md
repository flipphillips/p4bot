# Scripts Directory

### fp
### fall 2025

## About

Mainly files created by flip (fxpppr@rit.edu) for Slack integration.

## p4status.sh

A `bash` script that dumps Perforce changelists and locked files. Important when students accidentally leave files checked out. This happens often in a classroom setting.

## submit-slack.py

A Python script that pushes changes to a depot to a Slack channel. It should run as the low-privilege `p4status` user. That user belongs to a group with limited permissions and a long-lived ticket.

To provision the ticket once you have credentials:

```bash
P4PORT=ssl:mss-perforce-01.rit.edu:1666 P4USER=p4status p4 login -a -p
# enter the password and copy the printed ticket string

install -m 0600 -o perforce -g perforce /dev/stdin /p4/scripts/slackbot/p4status.tix <<'TIX'
<PASTE_TICKET_STRING_HERE>
TIX
```

Populate the Perforce trust file for the bot:

```bash
sudo -u perforce p4 -p ssl:mss-perforce-01.rit.edu:1666 trust -f -y
sudo install -m 0600 -o perforce -g perforce /dev/stdin /p4/scripts/slackbot/p4trust <<'TRUST'
<PASTE_SERVER_FINGERPRINT_HERE>
TRUST
```

`submit-slack.py` respects `P4_TICKET` but will also auto-load from `P4_TICKET_FILE` if present (see the environment file below).

## slack-files.py (Socket Mode bot)

Interactive Slack slash-command bot that queries Perforce. Configuration lives entirely in this directory now:

- `slackbot.env` – primary environment file consumed by both scripts and the systemd unit.
- `slackbot/` – secure storage for tickets and trust data, plus the `slackbot.service` unit template.

### Environment file

`scripts/slackbot.env` contains simple `KEY=value` pairs so it can be sourced by `bash` or read by systemd. Important entries:

```
SLACK_BOT_TOKEN="..."
SLACK_APP_TOKEN="..."
P4PORT="ssl:mss-perforce-01.rit.edu:1666"
P4USER="p4status"
P4_TICKET_FILE="/p4/scripts/slackbot/p4status.tix"
P4TRUST="/p4/scripts/slackbot/p4trust"
P4TICKETS="/p4/scripts/slackbot/p4tickets"
P4CHARSET=utf8
```

When sourcing in a shell, remember to export the values:

```bash
set -a
source /p4/scripts/slackbot.env
set +a
```

The helper script `test.bash` already performs the above and will run the bot locally with the configured credentials.

### Commands

Run `./dump-slackbot-commands.py` from this directory to emit a Markdown summary of the available slash commands. The current set includes `/files`, `/describe`, `/changes`, `/locked`, and `/health`; update `slackbot_commands.py` if you add more.

### Systemd unit

A ready-to-link unit lives at `scripts/slackbot/slackbot.service`. To deploy:

```bash
sudo install -m 0600 -o perforce -g perforce /dev/null /p4/scripts/slackbot/p4status.tix
sudo install -m 0600 -o perforce -g perforce /dev/null /p4/scripts/slackbot/p4trust
# populate both files with the real ticket and fingerprint

sudo ln -s /p4/scripts/slackbot/slackbot.service /etc/systemd/system/slackbot.service
sudo systemctl daemon-reload
sudo systemctl enable --now slackbot
```

The unit references `EnvironmentFile=/p4/scripts/slackbot.env`, so keeping that file updated ensures both local runs and the service stay in sync.

Restart the service after updating secrets:

```bash
sudo systemctl restart slackbot
sudo systemctl status slackbot
```

## Socket communication dependencies

Needs the `p4python` and `slack_bolt` packages. Those in turn need the build prerequisites.

```bash
sudo apt-get update
sudo apt-get install -y libssl-dev build-essential python3-dev
pip install --no-cache-dir p4python slack_bolt
```

Keep the `scripts/slackbot` directory out of backups or version control that leave the machine; it now contains all secrets required to rebuild the bot.
