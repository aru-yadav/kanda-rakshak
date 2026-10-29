"""data.gov.in fetch: headers, query variants, APMC market names, timeouts, and no fetch inside a request."""
import logging
from datetime import date, datetime, timedelta, timezone

import httpx
from fastapi.testclient import TestClient

from app import main, price
from app.db import DB
from app.price import PriceService, parse_records, pick_market

KEY = "SECRET-fetch-key-77"
TODAY = date.today().strftime("%d/%m/%Y")


def rec(market, modal="2400", d=TODAY):
    return {"market": market, "variety": "Red", "arrival_date": d, "modal_price": modal}


def run_fetch(monkeypatch, handler):
    monkeypatch.setattr(price.settings, "datagov_api_key", KEY)
    seen = []

    def h(req):
        seen.append(req)
        return handler(req)
    trace = []
    rows = price.fetch_live(httpx.Client(transport=httpx.MockTransport(h)), trace)
    return rows, seen, trace


def test_every_request_sends_project_user_agent(monkeypatch):
    rows, seen, _ = run_fetch(monkeypatch, lambda req: httpx.Response(200, json={"records": []}))
    assert len(seen) == 2
    for req in seen:
        assert req.headers["user-agent"].startswith("KandaRakshak/") and "python-httpx" not in req.headers["user-agent"]
        assert req.headers["accept"] == "application/json"


def test_district_variant_first_then_state(monkeypatch):
    rows, seen, trace = run_fetch(monkeypatch, lambda req: httpx.Response(200, json={"records": []}))
    a, b = (r.url.params for r in seen)
    assert a["filters[state.keyword]"] == "Maharashtra" and a["filters[district]"] == "Nashik"
    assert a["filters[commodity]"] == "Onion" and a["limit"] == "50"
    assert "filters[district]" not in b and b["filters[state.keyword]"] == "Maharashtra" and b["limit"] == "200"
    assert [t["url"] for t in trace] == price.redacted_urls() and all(KEY not in t["url"] for t in trace)


def test_stops_at_first_variant_with_rows(monkeypatch):
    rows, seen, _ = run_fetch(monkeypatch, lambda req: httpx.Response(200, json={"records": [rec("Lasalgaon(Vinchur)")]}))
    assert len(seen) == 1 and rows[0]["market"] == "Lasalgaon(Vinchur)"


def test_market_names_stripped_and_apmc_names_matched():
    rows = parse_records([rec("APMC Chandwad ", "1900"), rec("Lasalgaon(Vinchur)", "2100"),
                          rec("APMC Pimpalgaon Baswant ", "2000")], [])
    assert [r["market"] for r in rows] == ["APMC Chandwad", "Lasalgaon(Vinchur)", "APMC Pimpalgaon Baswant"]
    assert pick_market(rows, ["Lasalgaon"])["market"] == "Lasalgaon(Vinchur)"     # display keeps the original name
    assert pick_market(rows, ["Pimpalgaon"])["market"] == "APMC Pimpalgaon Baswant"
    assert pick_market(parse_records([rec("APMC Lasalgaon"), rec("Pune")], []), ["lasalgaon"])["market"] == "APMC Lasalgaon"
    assert pick_market(rows, ["Chandwad", "Lasalgaon"])["market"] == "APMC Chandwad"  # preference order still wins


def test_read_timeout_falls_back_to_cache_with_key_redacted(monkeypatch, tmp_path, caplog):
    monkeypatch.setattr(price.settings, "datagov_api_key", KEY)
    svc = PriceService(DB(str(tmp_path / "p.db")))
    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    svc.db.execute("INSERT INTO prices(market, arrival_date, modal, min_price, max_price, variety, fetched_at) "
                   "VALUES ('Lasalgaon', '2026-10-28', 1500, NULL, NULL, 'Red', ?)", (yesterday,))

    def timeout(req):
        raise httpx.ReadTimeout(f"timed out reading {req.url}", request=req)   # httpx errors embed the URL + key
    real = price.fetch_live
    monkeypatch.setattr(price, "fetch_live",
                        lambda client=None, trace=None: real(httpx.Client(transport=httpx.MockTransport(timeout)), trace))
    caplog.set_level(logging.DEBUG)
    svc.refresh(force=True)
    assert svc.last_fetch["ok"] is False and "ReadTimeout" in svc.last_fetch["error"]
    assert KEY not in svc.last_fetch["error"] and KEY not in caplog.text and "REDACTED" in svc.last_fetch["error"]
    p = svc.current()
    assert p["source"] == "cache" and p["modal"] == 1500 and p["arrival_date"] == "2026-10-28"


def test_no_outbound_http_during_ingest_or_reads(monkeypatch):
    monkeypatch.setattr(price.settings, "datagov_api_key", KEY)
    main.prices._last_try = None                     # a stale throttle must not matter either
    calls = []

    def boom(self, request):
        calls.append(str(request.url))
        raise AssertionError("outbound HTTP inside a request")
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", boom)
    c = TestClient(main.app)                         # no `with`: lifespan (the background refresher) is not started
    H = {"X-Device-Token": main.settings.device_token}
    r = c.post("/api/v1/readings", json={"device_id": "KR-PF1", "layers": {"top": {"t": 25, "rh": 60}}}, headers=H)
    assert r.status_code == 200
    for path in ("/api/v1/devices/KR-PF1/latest", "/api/v1/devices/KR-PF1/explain", "/api/v1/fleet", "/api/v1/price"):
        c.get(path)
    assert calls == []


def test_lifespan_starts_refresher_and_stops_it(monkeypatch):
    calls = []
    monkeypatch.setattr(main.prices, "refresh", lambda force=False: calls.append(force))
    with TestClient(main.app) as c:
        c.get("/api/v1/fleet")
    assert calls and calls[0] is True                # fetched once at startup, off the request path
