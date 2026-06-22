import json
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "launcher"))

import services  # noqa: E402


class _FakeResponse:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return b'{"threshold": 5000}'


def test_whatsapp_bridge_is_not_a_normal_stack_service(tmp_path, monkeypatch):
    root = tmp_path / "apps"
    for name in ("mcp-memu-server", "hermes-agent", "sillytavern"):
        (root / name).mkdir(parents=True)
    monkeypatch.setattr(services, "_resolve_apps_root", lambda: root)

    names = [spec.name for spec in services.all_services()]

    assert "hermes-gateway" in names
    assert "whatsapp-bridge" not in names
    assert "whatsapp-web-source" not in names


def test_memorize_pending_sends_user_id(monkeypatch):
    seen = {}

    def fake_urlopen(url, timeout):
        seen["url"] = url
        seen["timeout"] = timeout
        return _FakeResponse()

    monkeypatch.setattr(services, "all_services", lambda: [])
    monkeypatch.setattr(services.urllib.request, "urlopen", fake_urlopen)

    out = services.memorize_pending("Siri", "Marcos")
    query = parse_qs(urlparse(seen["url"]).query)

    assert out == {"threshold": 5000}
    assert query == {"soul_id": ["Siri"], "user_id": ["Marcos"]}
    assert seen["timeout"] == 2


def test_hermes_gateway_status_uses_whatsapp_degraded_state(tmp_path, monkeypatch):
    hermes_home = tmp_path / ".hermes"
    hermes_home.mkdir()
    (hermes_home / "gateway_state.json").write_text(
        json.dumps({
            "platforms": {
                "whatsapp": {
                    "state": "degraded",
                    "bridge": {"state": "ready", "mode": "bot"},
                    "web_source": {"state": "degraded", "error": "writer exited"},
                    "soul_history": {"state": "degraded", "error": "history failed"},
                }
            }
        }),
        encoding="utf-8",
    )
    monkeypatch.setattr(services, "HERMES_HOME", hermes_home)
    monkeypatch.setattr(services, "is_running", lambda _spec: True)
    spec = services.ServiceSpec(
        name="hermes-gateway",
        label="hermes-agent gateway",
        cmd=[],
        cwd=tmp_path,
        log_path=tmp_path / "gateway.log",
        pid_path=tmp_path / "gateway.pid",
    )

    status = services.status(spec)

    assert status["running"] is True
    assert status["state"] == "degraded"
    assert status["status_label"] == "▲ degraded"
    assert status["children"] == [
        {"name": "bridge", "state": "ready", "detail": "mode bot"},
        {"name": "web-source", "state": "degraded", "detail": "writer exited"},
        {"name": "soul-history", "state": "degraded", "detail": "history failed"},
    ]


def test_hermes_gateway_status_ignores_stale_runtime_pid(tmp_path, monkeypatch):
    hermes_home = tmp_path / ".hermes"
    hermes_home.mkdir()
    (hermes_home / "gateway_state.json").write_text(
        json.dumps({
            "pid": 111,
            "platforms": {
                "whatsapp": {
                    "state": "healthy",
                    "bridge": {"state": "ready", "mode": "bot"},
                }
            },
        }),
        encoding="utf-8",
    )
    pid_path = tmp_path / "gateway.pid"
    pid_path.write_text("222", encoding="utf-8")
    monkeypatch.setattr(services, "HERMES_HOME", hermes_home)
    monkeypatch.setattr(services, "is_running", lambda _spec: True)
    spec = services.ServiceSpec(
        name="hermes-gateway",
        label="hermes-agent gateway",
        cmd=[],
        cwd=tmp_path,
        log_path=tmp_path / "gateway.log",
        pid_path=pid_path,
    )

    status = services.status(spec)

    assert status["running"] is True
    assert status["state"] == "starting"
    assert status["status_label"] == "◐ starting"
    assert status["detail"] == "waiting for Hermes status"
