#!/bin/sh

# SmartHome automated maintenance task
# Intentionally writable by the automation user for this lab.

echo "[+] SmartHome maintenance completed: $(date)" >> /var/log/smarthome-maintenance.log
