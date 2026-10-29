import logging
from datetime import date
from urllib.parse import quote, quote_plus

import httpx
import pytest
from fastapi.testclient import TestClient

from app import advisory, main, price as price_mod
from app.config import settings

c = TestClient(main.app)
H = {"X-Device-Token": "test-device-token-0123456789"}
SECRET = "SECRET-KEY-must-never-appear-123"


def body(device, rh=88, mq=720, base=400, age_s=0):
    gas = {"mq135_mv": mq} if base is None else {"mq135_mv": mq, "mq135_base_mv": base}
    return {"device_id": device, "age_s": age_s, "layers": {"top": {"t": 27, "rh": rh}, "mid": {"t": 26, "rh": 70},
            "bot": {"t": 25, "rh": 70}, "amb": {"t": 25, "rh": 55}}, "gas": gas}


@pytest.fixture
def notify_all(monkeypatch):
    monkeypatch.setattr(settings, "notify_devices", [])


def test_404_unknown_device():
    assert c.get("/api/v1/devices/NOPE-X/explain").status_code == 404


def test_trace_matches_latest_and_formulas():
    c.post("/api/v1/readings", json=body("KR-E1"), headers=H)
    e = c.get("/api/v1/devices/KR-E1/explain").json()
    d = c.get("/api/v1/devices/KR-E1/latest").json()

    assert e["sensors"]["layers"]["top"] == {"t": 27, "rh": 88} and e["sensors"]["layers"]["amb"]["t"] == 25
    assert e["sensors"]["baseline_source"]["mq135"] == "device"

    comp = {x["name"]: x for x in e["score"]["components"]}
    assert comp["gas"]["inputs"]["sensor"] == "mq135" and comp["gas"]["inputs"]["rise_pct"] == 80.0
    assert comp["gas"]["value"] == 100.0 and comp["gas"]["weight"] == 0.5
    assert comp["humid"]["inputs"]["layer"] == "top" and comp["humid"]["value"] == 90.0
    assert comp["heat"]["inputs"]["ref"] == "ambient" and comp["heat"]["inputs"]["hotspot_c"] == 2.0
    assert abs(sum(x["contribution"] for x in comp.values()) - e["score"]["score"]) < 0.2
    assert e["score"]["score"] == d["risk"]["score"] and e["score"]["level"] == "ROT"

    assert e["rule"]["action"] == "SORT_SELL" == d["advice"]["action"] and e["rule"]["rule"] == "ROT"
    assert e["message"] == {"text_mr": d["advice"]["text_mr"], "text_en": d["advice"]["text_en"]}

    p = e["price"]
    assert p["source"] == "fallback" and p["modal"] == 1850.0 and p["fetched_at"] is None
    assert "api-key=REDACTED" in p["request"]["url"] and "not set" in p["request"]["url_note"]


def test_missing_component_renormalises_weights():
    c.post("/api/v1/readings", json=body("KR-E2", base=None), headers=H)   # no baseline yet -> no gas component
    e = c.get("/api/v1/devices/KR-E2/explain").json()
    comp = {x["name"]: x for x in e["score"]["components"]}
    assert comp["gas"]["available"] is False and comp["gas"]["contribution"] is None
    assert comp["humid"]["effective_weight"] == 0.6 and comp["heat"]["effective_weight"] == 0.4
    assert e["sensors"]["baseline_source"]["mq135"] is None


def test_debounce_blocks_until_three_identical_levels(notify_all):
    c.post("/api/v1/readings", json=body("KR-E3"), headers=H)
    n = c.get("/api/v1/devices/KR-E3/explain").json()["notification"]
    gate = {x["name"]: x for x in n["checks"]}["3-reading debounce"]
    assert n["sent"] is False and gate["passed"] is False and "3-reading debounce" in n["reason"]

    c.post("/api/v1/readings", json=body("KR-E3"), headers=H)
    c.post("/api/v1/readings", json=body("KR-E3"), headers=H)
    n = c.get("/api/v1/devices/KR-E3/explain").json()["notification"]
    assert n["sent"] is True and n["message"]["action"] == "SORT_SELL"
    assert {x["name"]: x for x in n["checks"]}["3-reading debounce"]["passed"] is True


def test_backlog_reading_never_notifies(notify_all):
    for _ in range(3):
        c.post("/api/v1/readings", json=body("KR-E4", age_s=3600), headers=H)
    n = c.get("/api/v1/devices/KR-E4/explain").json()["notification"]
    assert n["sent"] is False and {x["name"]: x for x in n["checks"]}["fresh reading"]["passed"] is False


@pytest.fixture
def live_api(monkeypatch):
    """Route data.gov.in calls to a mock; clean the shared price cache afterwards."""
    monkeypatch.setattr(settings, "datagov_api_key", SECRET)
    state = {"status": 200, "key": SECRET, "modal": "2400"}

    def handler(req: httpx.Request) -> httpx.Response:
        assert req.url.params["api-key"] == state["key"]   # the real request does carry the key
        if state["status"] != 200:
            return httpx.Response(state["status"], json={"error": "forbidden"})
        return httpx.Response(200, json={"records": [{"market": "Lasalgaon", "variety": "Red",
                              "arrival_date": date.today().strftime("%d/%m/%Y"), "modal_price": state["modal"]}]})

    real = price_mod.fetch_live
    monkeypatch.setattr(price_mod, "fetch_live",
                        lambda client=None, trace=None: real(httpx.Client(transport=httpx.MockTransport(handler)), trace))
    yield state
    main.db.execute("DELETE FROM prices")
    main.prices.last_fetch = None
    main.prices._last_try = None


def test_live_price_traced_and_key_redacted(live_api):
    c.post("/api/v1/readings", json=body("KR-E5"), headers=H)
    assert c.get("/api/v1/price?refresh=true").status_code == 200
    r = c.get("/api/v1/devices/KR-E5/explain")
    assert SECRET not in r.text
    p = r.json()["price"]
    assert p["source"] == "data.gov.in" and p["market"] == "Lasalgaon" and p["modal"] == 2400.0
    assert p["fetched_at"] and p["arrival_date"] == date.today().isoformat()
    assert p["request"]["url"].startswith("https://api.data.gov.in/resource/")
    assert "api-key=REDACTED" in p["request"]["url"] and "returned these rows" in p["request"]["url_note"]
    assert p["last_fetch"]["ok"] is True


def test_failed_fetch_error_is_redacted(live_api):
    live_api["status"] = 403   # httpx puts the full URL (with key) in the error message
    c.post("/api/v1/readings", json=body("KR-E6"), headers=H)
    c.get("/api/v1/price?refresh=true")
    r = c.get("/api/v1/devices/KR-E6/explain")
    assert SECRET not in r.text
    lf = r.json()["price"]["last_fetch"]
    assert lf["ok"] is False and lf["error"] == "HTTP 403 from data.gov.in"   # no URL echoed at all
    assert r.json()["price"]["source"] == "fallback"


def test_sent_reading_shows_all_gates_green_then_repeat_is_blocked(notify_all):
    for _ in range(3):
        c.post("/api/v1/readings", json=body("KR-E7"), headers=H)
    n = c.get("/api/v1/devices/KR-E7/explain").json()["notification"]
    assert n["sent"] is True and all(x["passed"] for x in n["checks"])   # judged as of that reading, not after it
    c.post("/api/v1/readings", json=body("KR-E7"), headers=H)              # same advice, minutes later
    n = c.get("/api/v1/devices/KR-E7/explain").json()["notification"]
    gate = {x["name"]: x for x in n["checks"]}["advice changed or repeat interval passed"]
    assert n["sent"] is False and gate["passed"] is False and "already sent" in gate["detail"]


# --- red-team regressions (C1, H1, H2, H3) ---------------------------------------------------------
def test_key_not_in_logs_on_success_or_failure(live_api, caplog):          # C1: httpx INFO logs the full URL
    caplog.set_level(logging.DEBUG)
    c.get("/api/v1/price?refresh=true")
    live_api["status"] = 403
    c.get("/api/v1/price?refresh=true")
    assert SECRET not in caplog.text and quote_plus(SECRET) not in caplog.text


def test_percent_encoded_key_is_redacted(live_api, monkeypatch, caplog):    # H1: httpx errors carry the encoded key
    odd = "abc+def/ghi=jkl&x y"
    monkeypatch.setattr(settings, "datagov_api_key", odd)
    live_api["key"] = odd
    live_api["status"] = 500
    c.post("/api/v1/readings", json=body("KR-E8"), headers=H)
    c.get("/api/v1/price?refresh=true")
    r = c.get("/api/v1/devices/KR-E8/explain")
    for leak in (odd, quote_plus(odd), quote(odd, safe="")):
        assert leak not in r.text and leak not in caplog.text
    assert "500" in r.json()["price"]["last_fetch"]["error"]


def test_explain_shows_what_was_actually_sent_after_price_changes(notify_all, live_api):   # H2
    live_api["status"] = 500                                             # API down at ingest -> fallback price
    wb = body("KR-E9", rh=84, mq=500)                                    # WATCH + no trend -> VENTILATE
    for _ in range(3):
        c.post("/api/v1/readings", json=wb, headers=H)
    live_api.update(status=200, modal="9000")                            # API back, price very different
    main.db.execute("INSERT INTO prices(market, arrival_date, modal, variety, fetched_at) VALUES "
                    "('Lasalgaon','2026-01-01',2000,'Red','2026-01-01T00:00:00+00:00'),"
                    "('Lasalgaon','2026-01-02',2000,'Red','2026-01-02T00:00:00+00:00')")
    c.get("/api/v1/price?refresh=true")
    n = c.get("/api/v1/devices/KR-E9/explain").json()
    assert n["rule"]["action"] == "SELL_SOON"                            # what the rules say NOW
    sent = n["notification"]
    assert sent["sent"] is True and sent["message"]["action"] == "VENTILATE"
    assert sent["message"]["text_en"].startswith("Moisture/heat") and sent["message"]["price"]["source"] == "fallback"
    assert sent["now_differs"] is True


def test_fallback_price_never_called_todays_rate():                     # H3
    a = advisory.decide("SAFE", {"market": "Lasalgaon", "modal": 1850, "source": "fallback", "trend_pct": None})
    assert "₹" not in a.text_mr and "Today" not in a.text_en


def test_cached_price_shows_its_date_not_today():                       # H3
    a = advisory.decide("SAFE", {"market": "Lasalgaon", "modal": 2400, "source": "cache",
                                 "arrival_date": "2026-10-20", "trend_pct": 0})
    assert "Today" not in a.text_en and "20-10-2026" in a.text_en and "20-10-2026" in a.text_mr and "आजचा" not in a.text_mr


def test_telegram_error_never_logs_bot_token(monkeypatch, caplog):      # C1 (Telegram half)
    from app import notify
    token = "123456:SECRET-bot-token_xyz"
    monkeypatch.setattr(settings, "telegram_token", token)
    monkeypatch.setattr(settings, "telegram_chat_id", "42")
    monkeypatch.setattr(settings, "notify_voice", False)
    real = httpx.Client
    monkeypatch.setattr(notify.httpx, "Client",
                        lambda **kw: real(transport=httpx.MockTransport(lambda req: httpx.Response(401, json={}))))
    caplog.set_level(logging.DEBUG)
    adv = advisory.decide("SAFE", None)
    assert main.notifier.send("KR-E10", adv) == "console(telegram-failed)"
    assert token not in caplog.text and quote(token, safe="") not in caplog.text
    assert "HTTP 401 from Telegram" in caplog.text


def test_manual_notify_is_shown_as_sent(notify_all):                    # H2 (manual /notify path)
    c.post("/api/v1/readings", json=body("KR-E11"), headers=H)          # 1 reading: debounce fails, no auto send
    assert c.post("/api/v1/devices/KR-E11/notify", headers={"X-Admin-Token": "test-admin-token-0123456789"}).status_code == 200
    n = c.get("/api/v1/devices/KR-E11/explain").json()["notification"]
    assert n["sent"] is True and n["message"]["action"] == "SORT_SELL"
    assert n["message"]["price"]["source"] == "fallback" and "manual" in n["reason"]
