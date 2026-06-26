import json
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "launcher"))

import policy  # noqa: E402


def test_write_channel_settings_preserves_metadata_on_default_policy(tmp_path, monkeypatch):
    policy_path = tmp_path / "memu.json"
    policy_path.write_text(
        json.dumps({
            "whatsapp": {
                "channels": {
                    "270699038040215@lid": {
                        "policy": "listen_only",
                        "memorize": False,
                        "display_name": "Annie Gottlieb",
                        "lid_jid": "270699038040215@lid",
                    }
                }
            }
        }),
        encoding="utf-8",
    )
    monkeypatch.setattr(policy, "POLICY_PATH", policy_path)

    policy.write_channel_settings({
        "270699038040215@lid": {"policy": "full", "memorize": True}
    })

    data = json.loads(policy_path.read_text(encoding="utf-8"))
    assert data["whatsapp"]["channels"]["270699038040215@lid"] == {
        "policy": "full",
        "memorize": True,
        "display_name": "Annie Gottlieb",
        "lid_jid": "270699038040215@lid",
    }


def test_write_channel_settings_removes_pure_default_policy_row(tmp_path, monkeypatch):
    policy_path = tmp_path / "memu.json"
    policy_path.write_text(
        json.dumps({
            "whatsapp": {
                "channels": {
                    "270699038040215@lid": {"policy": "listen_only", "memorize": False}
                }
            }
        }),
        encoding="utf-8",
    )
    monkeypatch.setattr(policy, "POLICY_PATH", policy_path)

    policy.write_channel_settings({
        "270699038040215@lid": {"policy": "full", "memorize": True}
    })

    data = json.loads(policy_path.read_text(encoding="utf-8"))
    assert data["whatsapp"]["channels"] == {}
