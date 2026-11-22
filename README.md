# SmartHome-Boot2Root

A self-contained, Docker-based Boot2Root cybersecurity lab built around a deliberately vulnerable smart-home web application. Designed for local, isolated training use.

---

## ⚠️ Rules of Engagement

> **This lab is for local, isolated use only.**
> All ports are bound to `127.0.0.1` by default.
> Never expose this container to a public network or the internet.
> You are responsible for running this in a safe, contained environment.

---

## Prerequisites

| Tool | Min version |
|------|-------------|
| Docker | 20.x |
| Docker Compose | v2 (plugin) |
| Python 3 | 3.9+ (for verification script) |

---

## Quick Start

```bash
git clone <repo-url> SmartHome-Boot2Root
cd SmartHome-Boot2Root

# Build and start (one command)
docker compose up -d --build

# Or use the Makefile
make build
make up
```

The lab will be available at a dedicated IP (`10.10.10.100`) on standard ports, exactly like a real CTF machine:

| Service | Target IP & Standard Port | Loopback Fallback |
|---------|---------------------------|-------------------|
| Web App | `http://10.10.10.100` (port 80) | `http://127.0.0.1:5000` |
| SSH     | `ssh automation@10.10.10.100` (port 22) | `ssh -p 2222 automation@127.0.0.1` |
| Ping / Recon | `ping 10.10.10.100` & `nmap -sV -sC 10.10.10.100` | N/A |

---

## Objective

Obtain **both flags**:

- `user{...}` — located on the system, readable by a low-privilege user
- `root{...}` — located in root's home directory

No stage-by-stage hints are provided here. Enumerate the application and the host.

---

## Helper Commands

```bash
make build    # Rebuild the Docker image
make up       # Start the lab
make down     # Stop the lab
make reset    # Destroy and restart with fresh flags
make verify   # Run the automated end-to-end exploit verification
make logs     # Tail container logs
make shell    # Drop a debug root shell (host use only)
```

---

## Configuration

The lab runs with self-contained randomized flags and credentials. Each time the container starts, fresh flags (`user.txt` and `root.txt`) and SSH host keys are generated automatically. The SSHOLE donor account hash is also dynamically generated at runtime.

---

## Credits & Attribution

The SSH authentication bypass technique used in this lab is based on the
**BYO-CTF-SSHOLE** project. Attribution is retained in the source materials.

> **Spoiler warning:** A detailed technical writeup of the SSHOLE technique is
> available in the project's supplementary materials — read it *after* you've
> rooted the box, or you'll spoil the challenge.

---

## License

This lab is provided for educational and research purposes only.

