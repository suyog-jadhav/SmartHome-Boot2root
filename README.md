# SmartHome-Boot2Root

A self-contained, Docker-based Boot2Root cybersecurity lab simulating an enterprise smart-home device management gateway. Designed for local, isolated security training and hands-on penetration testing.

---

## Quick Start

```bash
# Clone the repository
git clone https://github.com/suyog-jadhav/SmartHome-Boot2root SmartHome-Boot2Root
cd SmartHome-Boot2Root

# Build and start the lab
docker compose up -d --build
```

The lab environment exposes standard ports on a dedicated IP address (`10.10.10.100`), simulating a standalone machine on a local subnet:

| Service | Dedicated IP & Standard Port | Fallback Port (Loopback) |
|---|---|---|
| **Web Gateway** | `http://10.10.10.100` (port 80) | `http://127.0.0.1:5000` |
| **SSH Service** | `10.10.10.100:22` | `127.0.0.1:2222` |
| **ICMP Ping** | `ping 10.10.10.100` | N/A |

For detailed startup instructions, networking notes, and troubleshooting, see the [Student Setup Guide](SETUP.md).

---

## Documentation

- [Student Setup Guide](SETUP.md) — prerequisites, networking details, recommended workflow, and troubleshooting

---

## Challenge Overview

- **Difficulty**: Medium
- **Category**: Web Security / Linux Privilege Escalation
- **Target OS**: Linux (Alpine embedded)
- **Objective**: Capture both flags (`ThunderCipher{...}` format):
  - `user.txt` — Standard user flag
  - `root.txt` — Root administrator flag in `/root/root.txt`

---

## Management Commands

Using `docker compose`:
```bash
docker compose up -d       # Start lab
docker compose down        # Stop lab
docker compose logs -f     # View live logs
docker compose down -v     # Reset lab state (generates fresh flags on next start)
```

Or using `make`:
```bash
make up                    # Start lab and wait for health check
make down                  # Stop lab
make reset                 # Wipe state, rebuild and restart with fresh flags
make logs                  # Follow container logs
make verify                # Run automated verification suite
```

---

## Rules of Engagement

- This lab is strictly for local, isolated educational use.
- Do not expose the container to public networks or the internet.
- Flags follow the format `ThunderCipher{...}`.

---

## License

Provided for educational and security training purposes only.
