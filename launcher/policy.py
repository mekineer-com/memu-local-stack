"""WhatsApp channel policy reader/writer for the launcher GUI."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

HERMES_HOME = Path.home() / ".hermes"
DIRECTORY_PATH = HERMES_HOME / "channel_directory.json"
POLICY_PATH = HERMES_HOME / "memu.json"

Policy = Literal["full", "listen_only", "excluded"]
ALL_POLICIES: tuple[Policy, ...] = ("full", "listen_only", "excluded")


def list_whatsapp_chats() -> list[dict]:
    try:
        data = json.loads(DIRECTORY_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    platforms = data.get("platforms") if isinstance(data, dict) else None
    whatsapp = platforms.get("whatsapp") if isinstance(platforms, dict) else None
    return whatsapp if isinstance(whatsapp, list) else []


def read_policies() -> dict[str, Policy]:
    try:
        data = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    whatsapp = data.get("whatsapp") if isinstance(data, dict) else None
    channels = whatsapp.get("channels") if isinstance(whatsapp, dict) else None
    if not isinstance(channels, dict):
        return {}
    out: dict[str, Policy] = {}
    for chat_id, entry in channels.items():
        if isinstance(entry, dict):
            p = entry.get("policy")
            if p in ALL_POLICIES:
                out[str(chat_id)] = p  # type: ignore[assignment]
    return out


def write_policies(updates: dict[str, Policy]) -> None:
    """Apply `updates` to the policy file. 'full' removes the entry (absence = full)."""
    try:
        data = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        data = {}
    if not isinstance(data, dict):
        data = {}
    whatsapp = data.setdefault("whatsapp", {})
    if not isinstance(whatsapp, dict):
        whatsapp = {}
        data["whatsapp"] = whatsapp
    channels = whatsapp.setdefault("channels", {})
    if not isinstance(channels, dict):
        channels = {}
        whatsapp["channels"] = channels
    for chat_id, p in updates.items():
        if p == "full":
            channels.pop(chat_id, None)
        elif p in ALL_POLICIES:
            channels[chat_id] = {"policy": p}
    POLICY_PATH.parent.mkdir(parents=True, exist_ok=True)
    POLICY_PATH.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
