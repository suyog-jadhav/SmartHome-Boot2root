#!/usr/bin/env python3
"""
Lightweight TCP port 80 -> 5000 forwarder.
Allows students to reach the smart home web app at http://10.10.10.100 directly.
"""
import socket
import threading
import sys


def pipe(src, dst):
    try:
        while True:
            data = src.recv(4096)
            if not data:
                break
            dst.sendall(data)
    except Exception:
        pass
    finally:
        try:
            src.close()
        except Exception:
            pass
        try:
            dst.close()
        except Exception:
            pass


def main():
    listen_port = 80
    target_port = 5000

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        server.bind(("0.0.0.0", listen_port))
    except Exception as e:
        print(f"[!] Forwarder could not bind to port {listen_port}: {e}", file=sys.stderr)
        sys.exit(1)

    server.listen(64)
    print(f"[+] HTTP forwarder listening on port {listen_port} -> {target_port}")

    while True:
        try:
            client, _ = server.accept()
            target = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            target.connect(("127.0.0.1", target_port))
            t1 = threading.Thread(target=pipe, args=(client, target), daemon=True)
            t2 = threading.Thread(target=pipe, args=(target, client), daemon=True)
            t1.start()
            t2.start()
        except Exception:
            continue


if __name__ == "__main__":
    main()

