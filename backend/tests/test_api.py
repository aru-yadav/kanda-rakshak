from fastapi.testclient import TestClient

from app.main import app

c = TestClient(app)
H = {"X-Device-Token": "test-device-token-0123456789"}


def body(device="KR-T1", rh=60, mq=400, base=400):
    return {"device_id": device, "layers": {"top": {"t": 25, "rh": rh}, "mid": {"t": 25, "rh": 60},
            "bot": {"t": 25, "rh": 60}, "amb": {"t": 25, "rh": 55}},
            "gas": {"mq135_mv": mq, "mq135_base_mv": base}, "fan_on": False}


def test_rejects_missing_token():
    assert c.post("/api/v1/readings", json=body()).status_code == 401


def test_rejects_impossible_values():
    b = body(); b["layers"]["top"]["t"] = 999
    assert c.post("/api/v1/readings", json=b, headers=H).status_code == 422


def test_ingest_and_latest_flow():
    r = c.post("/api/v1/readings", json=body("KR-T2", rh=88, mq=720), headers=H)
    assert r.status_code == 200 and r.json()["risk_level"] == "ROT"
    d = c.get("/api/v1/devices/KR-T2/latest").json()
    assert d["advice"]["action"] == "SORT_SELL"
    assert d["price"]["source"] == "fallback" and d["price"]["modal"] == 1850.0
    assert d["simulated"] is False


def test_sim_device_flagged():
    c.post("/api/v1/readings", json=body("SIM-01"), headers=H)
    assert c.get("/api/v1/devices/SIM-01/latest").json()["simulated"] is True


def test_fan_override_requires_admin_and_is_returned():
    assert c.post("/api/v1/devices/KR-T3/fan", json={"mode": "on"}).status_code == 401
    ok = c.post("/api/v1/devices/KR-T3/fan", json={"mode": "on", "ttl_s": 60}, headers={"X-Admin-Token": "test-admin-token-0123456789"})
    assert ok.status_code == 200
    r = c.post("/api/v1/readings", json=body("KR-T3"), headers=H).json()
    assert r["fan_override"] == "on" and 0 < r["override_ttl_s"] <= 60


def test_history():
    c.post("/api/v1/readings", json=body("KR-T4"), headers=H)
    assert len(c.get("/api/v1/devices/KR-T4/history?hours=1").json()["rows"]) == 1


def test_404_unknown_device():
    assert c.get("/api/v1/devices/NOPE/latest").status_code == 404
