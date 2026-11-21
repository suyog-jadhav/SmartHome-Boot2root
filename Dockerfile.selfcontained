# =============================================================================
# Dockerfile.selfcontained
#
# Self-contained, single-command build for SmartHome-Boot2Root.
# Vendors the pinned OpenSSH 9.0p1-r5 .apk files (SHA256-verified) so no
# external package download is needed at build time.
#
# Attack chain preserved:
#   SQLi → SSTI → SSHOLE (OpenSSH 9.0p1-r5 / musl) → cron privesc
#
# Attribution: SSHOLE technique from BYO-CTF-SSHOLE project.
# =============================================================================

FROM alpine:3.16

# ---------------------------------------------------------------------------
# System dependencies
# ---------------------------------------------------------------------------
RUN apk add --no-cache python3 py3-pip libedit shadow

# ---------------------------------------------------------------------------
# Vendor + verify pinned OpenSSH 9.0p1-r5 packages (SHA256 checked)
# ---------------------------------------------------------------------------
COPY openssh/ /tmp/openssh/

# Verify every .apk against the committed checksum file — fail loudly on drift
RUN cd /tmp/openssh && sha256sum -c checksums.sha256 \
    || { echo "[ERROR] OpenSSH package checksum mismatch — build aborted."; exit 1; }

# Install from local copies only (no network)
RUN apk add --no-network /tmp/openssh/*.apk \
    && rm -rf /tmp/openssh

# ---------------------------------------------------------------------------
# Build-time version gate: fail if sshd version drifts from 9.0_p1-r5
# ---------------------------------------------------------------------------
RUN INSTALLED_PKG=$(apk info -v | grep '^openssh-server-[0-9]') \
    && echo "[INFO] Installed package: $INSTALLED_PKG" \
    && [ "$INSTALLED_PKG" = "openssh-server-9.0_p1-r5" ] \
    || { echo "[ERROR] Expected openssh-server-9.0_p1-r5 but got $INSTALLED_PKG — aborting."; exit 1; }

# ---------------------------------------------------------------------------
# Create lab accounts
# ---------------------------------------------------------------------------
RUN adduser -D -s /bin/sh automation \
    && adduser -D -s /bin/sh sshole-donor \
    && adduser -D -s /bin/sh websvc

# ---------------------------------------------------------------------------
# Lock automation (shadow field must be '*' for SSHOLE to work)
# ---------------------------------------------------------------------------
RUN sed -i 's/^automation:[^:]*:/automation:*:/' /etc/shadow

# ---------------------------------------------------------------------------
# Configure sshd
# ---------------------------------------------------------------------------
RUN mkdir -p /run/sshd \
    && printf '\nPermitRootLogin no\nPasswordAuthentication yes\n' \
       >> /etc/ssh/sshd_config

# ---------------------------------------------------------------------------
# Cron privilege escalation setup
# ---------------------------------------------------------------------------
COPY cron/maintenance.sh /opt/maintenance.sh
RUN chown root:root /opt/maintenance.sh \
    && chmod 777 /opt/maintenance.sh \
    && printf '* * * * * /bin/sh /opt/maintenance.sh\n' > /etc/crontabs/root \
    && chmod 600 /etc/crontabs/root

# ---------------------------------------------------------------------------
# Flask application
# ---------------------------------------------------------------------------
COPY requirements.txt /requirements.txt
RUN python3 -m pip install --no-cache-dir -r /requirements.txt

COPY app/ /app/
RUN chown -R websvc:websvc /app \
    && chmod 755 /app

# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 22 5000

ENTRYPOINT ["/entrypoint.sh"]

