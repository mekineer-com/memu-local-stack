"""FastAPI app for the memU stack launcher."""
from __future__ import annotations

import subprocess
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

import policy
import services

ROOT = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(ROOT / "templates"))

EDITABLE_CONFIGS: dict[str, Path] = {
    "memu-server-config": Path("/home/marcos/apps-codex/mcp-memu-server/config.json"),
    "hermes-config": Path.home() / ".hermes" / "config.yaml",
    "hermes-persona": Path.home() / ".hermes" / "SOUL.md",
}

CONFIG_LABELS: dict[str, str] = {
    "memu-server-config": "mcp-memu-server/config.json",
    "hermes-config": "~/.hermes/config.yaml",
    "hermes-persona": "~/.hermes/SOUL.md  (Hermes persona, not our soul)",
}

app = FastAPI(title="memU Stack")


def _find_service(name: str) -> services.ServiceSpec:
    for s in services.all_services():
        if s.name == name:
            return s
    raise HTTPException(status_code=404, detail=f"Unknown service: {name}")


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    specs = services.all_services()
    rows = [
        {
            "name": s.name,
            "label": s.label,
            "running": services.is_running(s),
            "supports_terminal": s.supports_terminal,
        }
        for s in specs
    ]
    chats = policy.list_whatsapp_chats()
    current = policy.read_policies()
    chat_rows = [
        {
            "id": str(c.get("id", "")),
            "name": str(c.get("name", "")),
            "type": str(c.get("type", "")),
            "policy": current.get(str(c.get("id", "")), "full"),
        }
        for c in chats
    ]
    editable = [
        {"key": k, "label": CONFIG_LABELS[k], "path": str(p)}
        for k, p in EDITABLE_CONFIGS.items()
    ]
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "services": rows,
            "chats": chat_rows,
            "policies": policy.ALL_POLICIES,
            "editable_configs": editable,
        },
    )


@app.get("/logs/{service_name}", response_class=HTMLResponse)
def logs(request: Request, service_name: str, lines: int = 200) -> HTMLResponse:
    spec = _find_service(service_name)
    try:
        text = spec.log_path.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        text = ""
    tail = "\n".join(text.splitlines()[-lines:])
    return templates.TemplateResponse(
        request,
        "logs.html",
        {
            "service": spec.name,
            "label": spec.label,
            "log_path": str(spec.log_path),
            "content": tail,
            "lines": lines,
        },
    )


@app.post("/service/{service_name}/start")
def service_start(
    service_name: str,
    show_terminal: str = Form(default=""),
) -> RedirectResponse:
    spec = _find_service(service_name)
    services.start(spec, show_terminal=bool(show_terminal))
    return RedirectResponse("/", status_code=303)


@app.post("/service/{service_name}/stop")
def service_stop(service_name: str) -> RedirectResponse:
    spec = _find_service(service_name)
    services.stop(spec)
    return RedirectResponse("/", status_code=303)


@app.post("/policy")
async def policy_save(request: Request) -> RedirectResponse:
    form = await request.form()
    updates: dict[str, str] = {}
    for key, val in form.items():
        if isinstance(key, str) and key.startswith("policy[") and key.endswith("]"):
            chat_id = key[len("policy["):-1]
            if val in policy.ALL_POLICIES:
                updates[chat_id] = val  # type: ignore[assignment]
    if updates:
        policy.write_policies(updates)  # type: ignore[arg-type]
    return RedirectResponse("/", status_code=303)


@app.post("/edit/{key}")
def edit_config(key: str) -> RedirectResponse:
    target = EDITABLE_CONFIGS.get(key)
    if target is None:
        raise HTTPException(status_code=404, detail=f"Unknown config: {key}")
    subprocess.Popen(["xdg-open", str(target)], start_new_session=True)
    return RedirectResponse("/", status_code=303)
