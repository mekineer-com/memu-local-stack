"""Browser detection for chromeless app windows."""
from __future__ import annotations

import json
import math
import shutil
import subprocess
import webbrowser
from pathlib import Path

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

# Dedicated profile dir for the launcher's app window. Without this,
# Chrome routes the --app invocation through the user's already-running
# Chrome instance — which ignores --window-size on the new window.
_PROFILE_DIR = Path.home() / ".cache" / "memu-stack-launcher" / "chrome-profile"
_PROFILE_PREFS = _PROFILE_DIR / "Default" / "Preferences"
_ZOOM_HOSTS = ("127.0.0.1", "localhost")
_DEFAULT_ZOOM_PERCENT = 75.0
_DEFAULT_PARTITION_KEY = "x"


def find_chromium() -> str | None:
    for name in CHROMIUM_FAMILY:
        if shutil.which(name):
            return name
    return None


def _scan_host_zoom_levels(node: object) -> float | None:
    if not isinstance(node, dict):
        return None
    for host in _ZOOM_HOSTS:
        host_data = node.get(host)
        if isinstance(host_data, dict):
            zoom_level = host_data.get("zoom_level")
            if isinstance(zoom_level, (int, float)):
                return float(zoom_level)
        elif isinstance(host_data, (int, float)):
            return float(host_data)
    for value in node.values():
        zoom_level = _scan_host_zoom_levels(value)
        if zoom_level is not None:
            return zoom_level
    return None


def _zoom_percent_to_level(percent: float) -> float:
    # Chromium stores zoom level where scale = 1.2 ** level.
    return math.log(percent / 100.0, 1.2)


def _ensure_default_zoom_level() -> None:
    if not _PROFILE_PREFS.exists():
        return
    try:
        payload = json.loads(_PROFILE_PREFS.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return

    partition = payload.get("partition")
    if not isinstance(partition, dict):
        return

    per_host = partition.get("per_host_zoom_levels")
    host_zoom = _scan_host_zoom_levels(per_host)
    if host_zoom is None:
        host_zoom = _zoom_percent_to_level(_DEFAULT_ZOOM_PERCENT)

    existing_default = partition.get("default_zoom_level")
    if isinstance(existing_default, dict):
        # Partitioned shape seen in this profile family.
        current = existing_default.get(_DEFAULT_PARTITION_KEY)
        if isinstance(current, (int, float)) and float(current) == host_zoom:
            return
        existing_default[_DEFAULT_PARTITION_KEY] = host_zoom
        partition["default_zoom_level"] = existing_default
    elif isinstance(existing_default, (int, float)):
        # Migrate legacy scalar shape to Chromium's partitioned dictionary
        # format used by kPartitionDefaultZoomLevel.
        if float(existing_default) == host_zoom:
            partition["default_zoom_level"] = {_DEFAULT_PARTITION_KEY: host_zoom}
        else:
            partition["default_zoom_level"] = {_DEFAULT_PARTITION_KEY: host_zoom}
    else:
        # Prefer partitioned default to match per_host_zoom_levels shape.
        partition["default_zoom_level"] = {_DEFAULT_PARTITION_KEY: host_zoom}

    payload["partition"] = partition
    try:
        _PROFILE_PREFS.write_text(
            json.dumps(payload, ensure_ascii=True, separators=(",", ":")),
            encoding="utf-8",
        )
    except OSError:
        return


def _has_saved_window_placement() -> bool:
    """True if Chromium has already remembered an app-window size/position.

    Chromium stores app-window dimensions under
    ``browser.app_window_placement`` in the profile's ``Preferences``
    file. Once that key exists, subsequent launches respect the saved
    size and ``--window-size`` would override what the user resized to.
    """
    try:
        data = json.loads(_PROFILE_PREFS.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    browser_node = data.get("browser") if isinstance(data, dict) else None
    placements = browser_node.get("app_window_placement") if isinstance(browser_node, dict) else None
    return isinstance(placements, dict) and bool(placements)


def open_app(url: str, *, width: int = 574, height: int = 740) -> subprocess.Popen | None:
    """Open the launcher UI in a chromeless app window.

    Uses a dedicated ``--user-data-dir`` so Chrome treats this as a
    separate instance (not a second window of the user's running
    browser). That is the only way ``--window-size`` actually applies.

    On the first run (no saved app-window placement in the profile),
    seeds the window at ``width × height``. On later runs, omits
    ``--window-size`` so Chromium restores whatever size the user
    resized to last time.

    Returns the chromium ``Popen`` object so the caller can watch it
    and quit the launcher when the window is closed. Returns ``None``
    for the default-browser fallback (no separate process to watch).
    """
    chromium = find_chromium()
    if chromium:
        has_saved = _has_saved_window_placement()
        _PROFILE_DIR.mkdir(parents=True, exist_ok=True)
        _ensure_default_zoom_level()
        cmd = [
            chromium,
            f"--app={url}",
            f"--user-data-dir={_PROFILE_DIR}",
            "--no-first-run",
            "--no-default-browser-check",
        ]
        if not has_saved:
            cmd.insert(2, f"--window-size={int(width)},{int(height)}")
        return subprocess.Popen(cmd, start_new_session=True)
    webbrowser.open(url)
    return None
