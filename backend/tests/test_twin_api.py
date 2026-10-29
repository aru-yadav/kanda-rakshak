from fastapi.testclient import TestClient

from app.main import app

c = TestClient(app)
H = {"X-Device-Token": "test-device-token-0123456789"}


def reading(dev, rh=60, mq=400):
    return {"device_id": dev, "layers": {"top": {"t": 25, "rh": rh}, "mid": {"t": 25, "rh": rh}, "bot": {"t": 25, "rh": rh},
            "amb": {"t": 25, "rh": 55}}, "gas": {"mq135_mv": mq, "mq135_base_mv": 400}}


def test_register_rejects_real_devices():
    assert c.post("/api/v1/sim/register", json={"device_id": "KR-01"}, headers=H).status_code == 400


def test_register_and_fleet_meta():
    assert c.post("/api/v1/sim/register", json={"device_id": "SIM-T1", "village": "Lasalgaon", "lat": 20.15, "lon": 74.23, "tonnes": 25}, headers=H).status_code == 200
    c.post("/api/v1/readings", json=reading("SIM-T1", rh=90, mq=720), headers=H)
    f = c.get("/api/v1/fleet").json()
    d = [x for x in f["devices"] if x["device_id"] == "SIM-T1"][0]
    assert d["village"] == "Lasalgaon" and d["simulated"] and d["risk_level"] == "ROT"
    assert f["devices"][0]["risk_level"] == "ROT"   # sorted worst first


def test_control_roundtrip_and_reset():
    c.post("/api/v1/sim/register", json={"device_id": "SIM-T2"}, headers=H)
    r = c.post("/api/v1/sim/SIM-T2/control", json={"scenario": "rot", "offline": True})
    assert r.status_code == 200 and r.json()["scenario"] == "rot" and r.json()["offline"] is True
    c.post("/api/v1/readings", json=reading("SIM-T2"), headers=H)
    c.post("/api/v1/sim/SIM-T2/control", json={"reset": True})
    assert c.get("/api/v1/devices/SIM-T2/history?hours=1").json()["rows"] == []
    assert c.get("/api/v1/sim/SIM-T2/control?ack_reset=true").json()["reset"] is True
    assert c.get("/api/v1/sim/SIM-T2/control").json()["reset"] is False


def test_control_rejects_real_device():
    assert c.post("/api/v1/sim/KR-01/control", json={"scenario": "rot"}).status_code == 400
