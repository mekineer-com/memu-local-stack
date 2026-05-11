"""Entry point for the memU stack launcher."""
from __future__ import annotations

import argparse
import socket
import threading
import time

import uvicorn

import browser


def _wait_for_port(host: str, port: int, timeout: float = 5.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        with socket.socket() as s:
            s.settimeout(0.2)
            try:
                s.connect((host, port))
                return True
            except OSError:
                time.sleep(0.1)
    return False


def main() -> None:
    parser = argparse.ArgumentParser(description="memU stack launcher")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    url = f"http://{args.host}:{args.port}"

    if not args.no_browser:
        def _open() -> None:
            if _wait_for_port(args.host, args.port):
                browser.open_app(url)

        threading.Thread(target=_open, daemon=True).start()

    uvicorn.run("app:app", host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
