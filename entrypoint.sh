#!/bin/sh
# =============================================================================
# entrypoint.sh — SmartHome-Boot2Root startup
#
# 1. Generates random flags
# 2. Runs SSHOLE precondition smoke tests (fail-fast)
# 3. Configures donor account
# 4. Starts crond, Flask, sshd
# =============================================================================
set -eu

echo "[+] SmartHome-Boot2Root starting..."

# ---------------------------------------------------------------------------
# Generate flags (idempotent — skip if already present)
# ---------------------------------------------------------------------------
mkdir -p /home/automation

if [ ! -f /home/automation/user.txt ]; then
    USER_FLAG=$(od -An -N16 -tx1 /dev/urandom | tr -d ' \n')
    printf 'user{%s}\n' "$USER_FLAG" > /home/automation/user.txt
fi

if [ ! -f /root/root.txt ]; then
    ROOT_FLAG=$(od -An -N16 -tx1 /dev/urandom | tr -d ' \n')
    printf 'root{%s}\n' "$ROOT_FLAG" > /root/root.txt
fi

chown automation:automation /home/automation/user.txt
chmod 600 /home/automation/user.txt
chmod 600 /root/root.txt

# ---------------------------------------------------------------------------
# Generate fresh SSH host keys
# ---------------------------------------------------------------------------
ssh-keygen -A

# ---------------------------------------------------------------------------
# Configure donor account with real password hash (required by SSHOLE)
# Generated dynamically at runtime and immediately wiped from environment
# ---------------------------------------------------------------------------
DONOR_PASS=$(od -An -N16 -tx1 /dev/urandom | tr -d ' \n')
printf 'sshole-donor:%s\n' "$DONOR_PASS" | chpasswd
unset DONOR_PASS
unset SSHOLE_DONOR_PASSWORD 2>/dev/null || true

# ---------------------------------------------------------------------------
# SSHOLE precondition smoke tests
# ---------------------------------------------------------------------------
echo "[*] Running SSHOLE precondition checks..."

FAIL=0

# 1. sshd must NOT be linked against PAM
if ldd /usr/sbin/sshd 2>/dev/null | grep -qi pam; then
    echo "[FAIL] sshd is linked against PAM — SSHOLE exploit will not work."
    FAIL=1
else
    echo "[OK]   sshd has no PAM linkage."
fi

# 2. sshd must report PasswordAuthentication yes
sshd -T 2>/dev/null | grep -qi "passwordauthentication yes"
if [ $? -ne 0 ]; then
    echo "[FAIL] sshd PasswordAuthentication is not 'yes'."
    FAIL=1
else
    echo "[OK]   sshd PasswordAuthentication = yes."
fi

# 3. automation shadow field must be exactly '*'
SHADOW_HASH=$(getent shadow automation | cut -d: -f2)
if [ "$SHADOW_HASH" != "*" ]; then
    echo "[FAIL] automation shadow hash is '$SHADOW_HASH', expected '*'."
    FAIL=1
else
    echo "[OK]   automation shadow field = '*'."
fi

# 4. Donor account must have a real SHA-512 or SHA-256 hash ($5$ or $6$)
DONOR_HASH=$(getent shadow sshole-donor | cut -d: -f2)
case "$DONOR_HASH" in
    \$5\$*|\$6\$*)
        echo "[OK]   sshole-donor has valid crypt hash."
        ;;
    *)
        echo "[FAIL] sshole-donor hash '$DONOR_HASH' is not \$5\$/\$6\$ — SSHOLE will not work."
        FAIL=1
        ;;
esac

if [ "$FAIL" -ne 0 ]; then
    echo ""
    echo "[ERROR] One or more SSHOLE preconditions failed."
    echo "        The lab environment is broken — fix and rebuild before use."
    exit 1
fi

echo "[+] All precondition checks passed."

# ---------------------------------------------------------------------------
# Start services
# ---------------------------------------------------------------------------
crond -f -l 8 &

# Generate Flask secret key
export FLASK_SECRET=$(od -An -N32 -tx1 /dev/urandom | tr -d ' \n')

# Run Flask as unprivileged websvc user
su websvc -s /bin/sh -c 'cd /app && exec python3 app.py' &

# Forward standard HTTP port 80 to Flask on 5000 so students can access http://10.10.10.100 directly
python3 /app/forwarder.py &

# Keep sshd in foreground
exec /usr/sbin/sshd -D -e
