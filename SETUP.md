# SmartHome-Boot2Root — Student Setup & Lab Guide

Welcome to the **SmartHome-Boot2Root** lab environment. This document outlines everything you need to start, access, and verify the lab machine.

---

## 1. Prerequisites

Make sure the following tools are installed on your host system:

- **Docker Engine** (v20.10 or higher)
- **Docker Compose** (v2 plugin or `docker-compose`)
- **nmap**, **curl**, and **ssh** (for recon and interaction)
- *Optional:* Python 3.9+ with `paramiko` and `requests`

---

## 2. Starting the Lab

Clone the repository and launch the container using Docker Compose:

```bash
# 1. Clone the repository
git clone <repo-url> SmartHome-Boot2Root
cd SmartHome-Boot2Root

# 2. Build and launch the container
docker compose up -d --build
```

Alternatively, you can use the provided `Makefile`:

```bash
make build
make up
```

---

## 3. Network & Connection Details

The lab runs on a dedicated, isolated Docker bridge network with a static IP address:

| Service | Target Address & Port | Fallback Address (Loopback) |
|---|---|---|
| **Web Gateway** | `http://10.10.10.100` (port 80) | `http://127.0.0.1:5000` |
| **SSH Server** | `10.10.10.100:22` | `127.0.0.1:2222` |
| **ICMP Ping** | `10.10.10.100` | N/A |

### Testing Connectivity

Verify that your host machine can reach the lab container:

```bash
ping -c 3 10.10.10.100
curl -I http://10.10.10.100/
```

If you receive a response (HTTP 302 redirecting to `/login`), the lab is ready.

---

## 4. Lab Objectives

The goal of this challenge is to simulate an end-to-end assessment of an IoT smart home gateway:

1. **User Flag (`user.txt`)**: Locate and read the initial user flag.
2. **Root Flag (`root.txt`)**: Escalate privileges to obtain the root flag in `/root/root.txt`.

Flags follow the standard format:
- `user{[0-9a-f]{32}}`
- `root{[0-9a-f]{32}}`

> **Note:** Flags are dynamically generated on container startup and are unique to each run.

---

## 5. Recommended Workflow

1. **Reconnaissance**: Start by scanning the target host:
   ```bash
   nmap -Pn -sC -sV -p 22,80 10.10.10.100
   ```
2. **Web Portal Assessment**: Browse to `http://10.10.10.100` and investigate the authentication mechanism and dashboard functionality.
3. **Exploitation & Pivot**: Chain vulnerabilities across the web tier and system services.
4. **Privilege Escalation**: Inspect local processes, scheduled tasks, and filesystem permissions.

---

## 6. Managing the Lab

- **View Container Logs**:
  ```bash
  docker compose logs -f
  # or: make logs
  ```

- **Stop the Lab**:
  ```bash
  docker compose down
  # or: make down
  ```

- **Reset Lab (Fresh Flags & DB)**:
  ```bash
  docker compose down -v
  docker compose up -d
  # or: make reset
  ```

---

## 7. Troubleshooting

- **Target IP `10.10.10.100` unreachable?**
  - Ensure the Docker daemon is running and no other container is using `10.10.10.100`.
  - On non-Linux hosts (e.g. macOS Docker Desktop), container IPs may not be directly routable from the host. Use the mapped fallback ports instead:
    - Web: `http://127.0.0.1:5000`
    - SSH: `ssh -p 2222 <user>@127.0.0.1`
- **Need to rebuild after edits?**
  ```bash
  docker compose build --no-cache
  docker compose up -d
  ```

