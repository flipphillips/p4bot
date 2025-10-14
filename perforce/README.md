# Perforce Class Depot Bootstrap (`p4create.sh`)

This script sets up a clean **class depot** (`//vp25-ue`) in Perforce with
Unreal Engine–friendly defaults. It also creates a "seed" client (`vpseed`)
to prime initial project directories and ignore files.

---

## What it does

1. **Creates a depot**  
   - Defines `vp25-ue` as a classic depot (no streams).

2. **Normalizes the typemap**  
   - Adds exclusive lock rules (`binary+l`) for Unreal Engine assets (`.uasset`, `.umap`, etc.).

3. **Creates the `vpseed` client**  
   - Maps only:
     ```
     //vp25-ue/pac/...   //vpseed/pac/...
     //vp25-ue/narn/...  //vpseed/narn/...
     ```
   - This guarantees no `//playpen/...` junk.

4. **Primes projects with `.p4ignore`**  
   - Seeds both `pac/` and `narn/` with an Unreal Engine–friendly ignore file.

5. **(Optional) Seeds from Templates**  
   - If you set environment variables like:
     ```bash
     export TEMPLATE_pac='//vp-stream/Templates/UE5/ThirdPerson'
     export TEMPLATE_narn='//vp-stream/Templates/UE5/Blank'
     ```
     the script will copy those template projects into the class depot using
     `p4 populate`.

6. **Updates protections**  
   - Grants write access for `vp-group` to `//vp25-ue/...`.

---

## How to run it

1. Make sure you can log in as the **Perforce superuser**:
   ```bash
   export P4PORT="ssl:mss-perforce-01.rit.edu:1666"
   export P4USER="perforce"
   p4 login
   ```

2. Run the bootstrap script:
```bash
   bash /Users/fxpppr/Desktop/p4create.sh
```

3. Watch the output for:
   - Depot creation confirmation
   - Typemap verification
   - Client spec (should show only pac and narn)
   - Submitted .p4ignore
   - Optional template populate preview + results
   - Protection table update

   ## Slack Bot

   1. Create a Slack App with permissions to post messages via webhook.
   2. Add task to perforce:
```
Triggers:

   slacknotify change-commit //vp25-ue/... "/usr/bin/python3 /p4/scripts/submit-slack.py %change% %user%"
```
   3. Test by submitting a change to `//vp25-ue/...` and check Slack.

   ### Slash Commands

   I started to create some slash commends to interact rather than adding the service via `cron`. Right now, the p4-blame-slack script runs every 15 minutes to look for locked files and report them. The interactive version requires some server stuff to get it to work correctly, so we'll get to that later.
   
   ### Underpriv User

   ```bash
      # Run as Perforce admin shell where p4 is configured
   if p4 user -o p4status >/dev/null 2>&1; then
     echo "user p4status already exists; skipping creation"
   else
     p4 user -f -i <<'EOF'
   User: p4status
   Email: ops@example.com
   FullName: Perforce Status Monitor Service
   Type: service
   AuthMethod: perforce
   EOF
   fi
   ```

   Group

   ```bash
   if p4 group -o p4status-readonly >/dev/null 2>&1; then
     echo "group exists; ensure p4status is in Users"
     p4 group -o p4status-readonly
   else
     p4 group -i <<'EOF'
   Group: p4status-readonly
   Timeout: 43200
   Owners: yourAdminUser
   Users: p4status
   EOF
   fi
   ```

   Privs

   ```bash
      # Export current protections and append candidate lines
   p4 protect -o > /tmp/protect.orig
   cat >> /tmp/protect.orig <<'EOF'
   
   # monitoring user read/list - adjust depot paths if desired
   read user p4status * //...
   list user p4status * //...
   EOF
   
   # Review /tmp/protect.orig carefully, then:
   p4 protect -i < /tmp/protect.orig
   ```

   Workspace

   ```bash
   HOST=$(hostname -s)
   CLIENT=p4status-$HOST
   if p4 client -o "$CLIENT" >/dev/null 2>&1; then
     echo "client exists; skipping"
   else
     p4 client -i <<EOF
   Client: $CLIENT
   Owner: p4status
   Host: $HOST
   Root: /tmp/${CLIENT}
   Options: noallwrite noclobber nocompress unlocked nomodtime rmdir
   SubmitOptions: submitunchanged
   LineEnd: local
   View:
       //... //$CLIENT/...
   EOF
   fi
   ```

   Durable Ticket

   ```bash
   # On the host that will run triggers (Perforce server or dedicated trigger host)
   # create/ensure local system user 'p4status' and homedir
   sudo useradd -m -s /bin/bash p4status || true
   sudo -u p4status bash -c 'P4USER=p4status p4 login'
   # This prompts for the password and writes ~/.p4tickets for the service user. Then move it:
   sudo -u p4status mv ~/.p4tickets /opt/p4status/.p4tickets
   sudo chown p4status:p4status /opt/p4status/.p4tickets
   sudo chmod 600 /opt/p4status/.p4tickets
   ```