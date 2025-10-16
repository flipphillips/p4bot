# Slack Bot Secrets

This directory holds the Perforce trust and ticket material used by the Slack bot run from `slack-files.py`.

- `p4status.tix` – the long-lived ticket for the `p4status` user.
- `p4trust` – the trust file entry for the Perforce server.
- `p4tickets` – optional ticket cache if you prefer that workflow.

Populate the files with secure permissions (recommended `chmod 600` owned by `perforce`) and keep them out of revision control if they contain production credentials.
