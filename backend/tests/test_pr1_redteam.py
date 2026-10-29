"""Regression tests for the full-PR #1 red-team findings (C1, H2, H3, H4)."""
import sys
import types

import pytest
from fastapi.testclient import TestClient

from app import advisory, main
from app.config import Settings, settings

c = TestClient(main.app)
H = {"X-Device-Token": settings.device_token}
A = {"X-Admin-Token": settings.admin_token}
TODAY = advisory.datetime.now(advisory.IST).date().isoformat()


# C1: price headings come from one function; a fallback is never "today's" and never shown to the farmer
def test_price_view_live_today():
    v = advisory.price_view({"modal": 2400, "source": "data.gov.in", "arrival_date": TODAY})
    assert v["kind"] == "today" and v["farmer_visible"] and v["heading_mr"].startswith("आजचा")


def test_price_view_cache_is_dated():
    v = advisory.price_view({"modal": 2400, "source": "cache", "arrival_date": "2026-10-20"})
    assert v["kind"] == "dated" and "20-10-2026" in v["heading_en"] and "Today" not in v["heading_en"]
    assert "आजचा" not in v["heading_mr"]


def test_price_view_fallback_not_live_and_hidden_from_farmer():
    v = advisory.price_view({"modal": 1850, "source": "fallback", "arrival_date": None})
    assert v["kind"] == "not_live" and v["farmer_visible"] is False and "NOT LIVE" in v["heading_en"]


def test_latest_and_fleet_carry_price_view():
    c.post("/api/v1/readings", json={"device_id": "KR-V1", "layers": {"top": {"t": 25, "rh": 60}}}, headers=H)
    assert c.get("/api/v1/devices/KR-V1/latest").json()["price"]["view"]["kind"] == "not_live"
    assert c.get("/api/v1/fleet").json()["price"]["view"]["kind"] == "not_live"


# H2: refuse public default or short tokens; demo mode must be opted into
@pytest.mark.parametrize("dev,adm", [("change-me-same-as-firmware-secrets", "x" * 32), ("x" * 32, "change-me-admin"),
                                     ("short", "x" * 32), ("x" * 32, "x" * 32)])
def test_weak_or_shared_tokens_refused(monkeypatch, dev, adm):
    monkeypatch.setenv("DEVICE_TOKEN", dev)
    monkeypatch.setenv("ADMIN_TOKEN", adm)
    with pytest.raises(RuntimeError):
        Settings().check_tokens()


def test_demo_mode_defaults_off(monkeypatch):
    monkeypatch.delenv("DEMO_MODE", raising=False)
    assert Settings().demo_mode is False


# H3: names that end up in dashboards are plain text only
@pytest.mark.parametrize("field", ["village", "taluka", "farmer"])
def test_register_rejects_markup(field):
    r = c.post("/api/v1/sim/register", json={"device_id": "SIM-X1", field: "<img src=x onerror=alert(1)>"}, headers=H)
    assert r.status_code == 422


def test_register_accepts_marathi_and_punctuation():
    r = c.post("/api/v1/sim/register", json={"device_id": "SIM-X2", "village": "पिंपळगाव बसवंत", "taluka": "Niphad (N.)",
                                             "farmer": "D'Souza-Patil"}, headers=H)
    assert r.status_code == 200


# H4: a failed TTS run must not leave a partial mp3 that is served forever
def test_voice_failure_leaves_no_partial_file(monkeypatch, tmp_path):
    monkeypatch.setattr(main, "AUDIO_DIR", tmp_path)

    class BrokenTTS:
        def __init__(self, text, lang): pass
        def save(self, path):
            open(path, "wb").write(b"x")       # gTTS opens the target first, then streams
            raise ConnectionError("network down")

    monkeypatch.setitem(sys.modules, "gtts", types.SimpleNamespace(gTTS=BrokenTTS))
    c.post("/api/v1/readings", json={"device_id": "KR-V2", "layers": {"top": {"t": 25, "rh": 60}}}, headers=H)
    assert c.get("/api/v1/devices/KR-V2/voice.mp3").status_code == 503
    assert c.get("/api/v1/devices/KR-V2/voice.mp3").status_code == 503   # not a cached 1-byte "success"
    assert list(tmp_path.iterdir()) == []


def test_voice_success_is_cached(monkeypatch, tmp_path):
    monkeypatch.setattr(main, "AUDIO_DIR", tmp_path)
    calls = []

    class OkTTS:
        def __init__(self, text, lang): calls.append(text)
        def save(self, path): open(path, "wb").write(b"\xff" * 4096)

    monkeypatch.setitem(sys.modules, "gtts", types.SimpleNamespace(gTTS=OkTTS))
    c.post("/api/v1/readings", json={"device_id": "KR-V3", "layers": {"top": {"t": 25, "rh": 60}}}, headers=H)
    assert c.get("/api/v1/devices/KR-V3/voice.mp3").status_code == 200
    assert c.get("/api/v1/devices/KR-V3/voice.mp3").status_code == 200 and len(calls) == 1
