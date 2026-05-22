"""Soul selector helpers for the memU stack launcher."""
from __future__ import annotations

from pathlib import Path
import tempfile

import yaml

HERMES_CONFIG_PATH = Path.home() / ".hermes" / "config.yaml"


def _load_config() -> dict:
    try:
        raw = HERMES_CONFIG_PATH.read_text(encoding="utf-8")
    except OSError as exc:
        raise RuntimeError(f"Failed to read {HERMES_CONFIG_PATH}: {exc}") from exc
    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        raise RuntimeError(f"Invalid YAML in {HERMES_CONFIG_PATH}: {exc}") from exc
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise RuntimeError(f"Expected mapping at top level in {HERMES_CONFIG_PATH}")
    return data


def _write_config(config: dict) -> None:
    HERMES_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    dumped = yaml.safe_dump(
        config,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
    )
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=str(HERMES_CONFIG_PATH.parent),
        delete=False,
    ) as tmp:
        tmp.write(dumped)
        tmp_path = Path(tmp.name)
    tmp_path.replace(HERMES_CONFIG_PATH)


def _soul_agents(config: dict) -> list[dict]:
    soul_mode = config.get("soul_mode")
    if soul_mode is None:
        return []
    if not isinstance(soul_mode, dict):
        raise RuntimeError("Invalid config: soul_mode must be a mapping")
    agents = soul_mode.get("agents")
    if agents is None:
        return []
    if not isinstance(agents, dict):
        raise RuntimeError("Invalid config: soul_mode.agents must be a mapping")
    out: list[dict] = []
    for agent_cfg in agents.values():
        if not isinstance(agent_cfg, dict):
            raise RuntimeError("Invalid config: each soul_mode.agents entry must be a mapping")
        role = str(agent_cfg.get("role") or "").strip().lower()
        if role == "soul":
            out.append(agent_cfg)
    return out


def read_active_soul_id() -> str:
    config = _load_config()
    agents = _soul_agents(config)
    if not agents:
        return ""
    first = agents[0]
    return str(first.get("soul_id") or "").strip()


def list_soul_ids() -> list[str]:
    config = _load_config()
    out: set[str] = set()
    for agent_cfg in _soul_agents(config):
        soul_id = str(agent_cfg.get("soul_id") or "").strip()
        if soul_id:
            out.add(soul_id)
    return sorted(out, key=lambda value: value.lower())


def set_active_soul_id(soul_id: str) -> None:
    selected = str(soul_id or "").strip()
    if not selected:
        raise RuntimeError("Soul ID cannot be empty")

    config = _load_config()
    soul_mode = config.get("soul_mode")
    if soul_mode is None:
        soul_mode = {}
        config["soul_mode"] = soul_mode
    elif not isinstance(soul_mode, dict):
        raise RuntimeError("Invalid config: soul_mode must be a mapping")
    agents = soul_mode.get("agents")
    if agents is None:
        agents = {}
        soul_mode["agents"] = agents
    elif not isinstance(agents, dict):
        raise RuntimeError("Invalid config: soul_mode.agents must be a mapping")

    updated = False
    for agent_cfg in agents.values():
        if not isinstance(agent_cfg, dict):
            raise RuntimeError("Invalid config: each soul_mode.agents entry must be a mapping")
        role = str(agent_cfg.get("role") or "").strip().lower()
        if role != "soul":
            continue
        agent_cfg["soul_id"] = selected
        updated = True

    if not updated:
        main_cfg = agents.get("main")
        if main_cfg is None:
            main_cfg = {}
            agents["main"] = main_cfg
        elif not isinstance(main_cfg, dict):
            raise RuntimeError("Invalid config: soul_mode.agents.main must be a mapping")
        if "enabled" not in main_cfg:
            main_cfg["enabled"] = True
        main_cfg["role"] = "soul"
        main_cfg["soul_id"] = selected

    _write_config(config)
