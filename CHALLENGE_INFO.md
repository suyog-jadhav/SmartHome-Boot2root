# SmartHome-Boot2Root — Challenge Info

> Like a HackTheBox machine card. No spoilers.

---

## Overview

| Field | Detail |
|-------|--------|
| **Name** | SmartHome-Boot2Root |
| **OS** | Linux (Alpine) |
| **Difficulty** | Medium |
| **Category** | Web / Network / Privilege Escalation |
| **Flags** | 2 (user + root) |
| **Estimated time** | 2–4 hours |
| **Platform** | Local Docker (self-hosted) |

---

## Skills Exercised

- Web application enumeration and recon
- SQL injection — authentication bypass
- Server-Side Template Injection (SSTI) — input filter bypass required
- SSH exploitation — version-specific authentication bypass
- Linux privilege escalation — writable cron script

---

## Attack Surface

- Flask web application (HTTP 5000)
- OpenSSH daemon (TCP 2222)

---

## Difficulty Notes

- The SQLi is straightforward once found — enumeration is the key step.
- The SSTI requires bypassing an input filter using real Jinja2 knowledge.
- The SSH exploit is a known CVE-class bug — version fingerprinting and research are needed.
- The privilege escalation is intentionally discoverable from the application itself.

---

## Intended for

- CTF players wanting a realistic multi-stage web + system challenge
- Penetration testing students learning chained exploitation
- Security trainers looking for a self-hosted, reproducible lab

---

*Created for local, isolated training use only. Never expose to a public network.*

