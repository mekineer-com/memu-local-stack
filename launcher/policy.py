"""WhatsApp channel policy reader/writer for the launcher GUI."""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path
from typing import Literal

HERMES_HOME = Path.home() / ".hermes"
DIRECTORY_PATH = HERMES_HOME / "channel_directory.json"
POLICY_PATH = HERMES_HOME / "memu.json"
CREDS_PATH = HERMES_HOME / "whatsapp" / "session" / "creds.json"
GROUP_NAME_CACHE_PATH = HERMES_HOME / "whatsapp_group_names.json"
BRIDGE_BASE_URL = "http://127.0.0.1:3000"

Policy = Literal["full", "listen_only", "excluded"]
ALL_POLICIES: tuple[Policy, ...] = ("full", "listen_only", "excluded")


def _normalize_wa_id(value: str) -> str:
    """Strip WhatsApp JID/LID syntax to the bare numeric id."""
    return (
        str(value or "")
        .strip()
        .replace("+", "", 1)
        .split(":", 1)[0]
        .split("@", 1)[0]
    )


def _self_identifiers() -> set[str]:
    """Return the normalized ids that represent the human's own account.

    WhatsApp gives the same person both a phone JID
    (``15133278228@s.whatsapp.net``) and a privacy LID
    (``114628432556258@lid``); the bridge stores both in ``creds.json``'s
    ``me`` block. The launcher uses this set to collapse Marcos's two
    entries into a single "you" row in the policy editor.
    """
    try:
        data = json.loads(CREDS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return set()
    me = data.get("me") if isinstance(data, dict) else None
    if not isinstance(me, dict):
        return set()
    out: set[str] = set()
    for key in ("id", "lid"):
        norm = _normalize_wa_id(me.get(key, ""))
        if norm:
            out.add(norm)
    return out


def _looks_like_raw_id(name: str) -> bool:
    """Detect a directory `name` that is the raw chat id (a number string)."""
    bare = name.replace("-", "").replace("@", "")
    return bool(bare) and bare.isdigit()


def _fetch_group_subject(chat_id: str, *, timeout: float = 1.5) -> str:
    """Ask the WhatsApp bridge for a group's display subject.

    The channel_directory builder writes the raw chat id as the group
    `name` when it can't resolve a subject from session history. The
    bridge's ``/chat/<id>`` endpoint calls ``sock.groupMetadata(id)``
    live, which is the only path that returns the user-visible group
    name (e.g. "Familia"). Returns "" on any failure so the UI falls
    back to the directory's raw name.
    """
    if not chat_id:
        return ""
    encoded = urllib.request.quote(chat_id, safe="")
    url = f"{BRIDGE_BASE_URL}/chat/{encoded}"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            if resp.status != 200:
                return ""
            payload = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, json.JSONDecodeError, ValueError):
        return ""
    if not isinstance(payload, dict):
        return ""
    name = payload.get("name")
    return str(name).strip() if isinstance(name, str) else ""


def _load_group_name_cache() -> dict[str, str]:
    """Load persisted WhatsApp group names keyed by chat id."""
    try:
        raw = json.loads(GROUP_NAME_CACHE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(raw, dict):
        return {}
    out: dict[str, str] = {}
    for key, value in raw.items():
        if not isinstance(key, str) or not isinstance(value, str):
            continue
        chat_id = key.strip()
        name = value.strip()
        if chat_id and name:
            out[chat_id] = name
    return out


def _write_group_name_cache(cache: dict[str, str]) -> None:
    """Persist normalized group names; ignore write errors in launcher UI."""
    try:
        GROUP_NAME_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        GROUP_NAME_CACHE_PATH.write_text(
            json.dumps(cache, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    except OSError:
        return


def list_whatsapp_chats() -> list[dict]:
    try:
        data = json.loads(DIRECTORY_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    platforms = data.get("platforms") if isinstance(data, dict) else None
    whatsapp = platforms.get("whatsapp") if isinstance(platforms, dict) else None
    if not isinstance(whatsapp, list):
        return []

    self_ids = _self_identifiers()
    group_name_cache = _load_group_name_cache()
    cache_changed = False
    self_kept: dict | None = None  # First (preferably named) entry that is the human.
    enriched: list[dict] = []
    for chat in whatsapp:
        if not isinstance(chat, dict):
            continue
        chat_id = str(chat.get("id") or "").strip()
        name = str(chat.get("name") or "").strip()
        is_group = str(chat.get("type") or "") == "group"
        # Enrich group names that came in as the raw id (the directory
        # builder fell back when no subject was available in session
        # history). DM names are already populated by the directory.
        chat_id_bare = chat_id.split("@", 1)[0]
        if is_group and chat_id and (
            not name or name == chat_id or name == chat_id_bare
        ):
            subject = _fetch_group_subject(chat_id)
            if not subject:
                subject = group_name_cache.get(chat_id, "")
            if subject:
                chat = {**chat, "name": subject}
                name = subject
                if group_name_cache.get(chat_id) != subject:
                    group_name_cache[chat_id] = subject
                    cache_changed = True
        elif is_group and chat_id and name and name != chat_id and name != chat_id_bare:
            # Keep a stable local name source for future launcher loads when
            # bridge metadata is temporarily unavailable.
            if group_name_cache.get(chat_id) != name:
                group_name_cache[chat_id] = name
                cache_changed = True

        # Collapse the human's two WhatsApp identities (phone JID + LID)
        # into a single row. Keep the entry whose directory name isn't a
        # bare numeric id — that's the one already labeled "Marcos".
        chat_id_norm = _normalize_wa_id(chat_id)
        if chat_id_norm and chat_id_norm in self_ids:
            keep_this = self_kept is None or (
                _looks_like_raw_id(str(self_kept.get("name") or "")) and not _looks_like_raw_id(name)
            )
            if keep_this:
                self_kept = chat
            continue

        enriched.append(chat)

    if self_kept is not None:
        # Surface the human at the top of the list with a guaranteed name.
        kept_name = str(self_kept.get("name") or "").strip()
        if not kept_name or _looks_like_raw_id(kept_name):
            self_kept = {**self_kept, "name": "you"}
        enriched.insert(0, self_kept)

    if cache_changed:
        _write_group_name_cache(group_name_cache)

    return enriched


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
