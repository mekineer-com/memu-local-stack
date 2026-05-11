"""Browser detection for chromeless app windows."""
from __future__ import annotations

import shutil
import subprocess
import webbrowser

# Priority order: Chromium-family browsers support `--app=URL` (chromeless window).
# Firefox dropped SSB years ago and cannot deliver a solitary window.
CHROMIUM_FAMILY = [
    "google-chrome",
    "google-chrome-stable",
    "chromium",
    "chromium-browser",
    "microsoft-edge",
    "microsoft-edge-stable",
    "brave-browser",
    "brave",
    "vivaldi",
    "vivaldi-stable",
]


def find_chromium() -> str | None:
    for name in CHROMIUM_FAMILY:
        if shutil.which(name):
            return name
    return None


def open_app(url: str) -> None:
    chromium = find_chromium()
    if chromium:
        subprocess.Popen(
            [chromium, f"--app={url}", "--new-window"],
            start_new_session=True,
        )
        return
    webbrowser.open(url)
