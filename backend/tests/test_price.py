from app.price import parse_records, pick_market

RAW = [
    {"state": "Maharashtra", "market": "Lasalgaon", "commodity": "Onion", "variety": "Red",
     "arrival_date": "20/10/2026", "min_price": "1500", "max_price": "2611", "modal_price": "2400"},
    {"state": "Maharashtra", "market": "Pune", "commodity": "Onion", "variety": "Other",
     "arrival_date": "20/10/2026", "min_price": "1000", "max_price": "2200", "modal_price": "1800"},
    {"market": "Broken", "arrival_date": "bad", "modal_price": "x"},
]


def test_parse_skips_bad_rows():
    rows = parse_records(RAW, ["Lasalgaon"])
    assert len(rows) == 2 and rows[0]["arrival_date"] == "2026-10-20" and rows[0]["modal"] == 2400.0


def test_pick_preferred_market():
    rows = parse_records(RAW, [])
    assert pick_market(rows, ["Lasalgaon", "Pune"])["market"] == "Lasalgaon"


def test_pick_falls_back_to_median():
    rows = parse_records(RAW, [])
    assert pick_market(rows, ["Nowhere"])["market"] in ("Lasalgaon", "Pune")


def test_empty():
    assert pick_market([], ["Lasalgaon"]) is None


def test_redact_covers_raw_and_url_encoded_key(monkeypatch):
    from urllib.parse import quote, quote_plus

    from app import price
    key = "abc+def/ghi=jkl&x y"
    monkeypatch.setattr(price.settings, "datagov_api_key", key)
    s = price.redact(f"raw {key} plus {quote_plus(key)} pct {quote(key, safe='')}")
    assert key not in s and quote_plus(key) not in s and quote(key, safe="") not in s and s.count("REDACTED") == 3


def test_fetch_errors_and_logs_never_contain_key(monkeypatch, caplog):
    import logging

    import httpx

    from app import main, price
    key = "SECRET-log-key-42"
    monkeypatch.setattr(price.settings, "datagov_api_key", key)
    real = price.fetch_live
    mock = httpx.MockTransport(lambda req: httpx.Response(403, json={}))
    monkeypatch.setattr(price, "fetch_live", lambda **kw: real(httpx.Client(transport=mock), **kw))
    caplog.set_level(logging.DEBUG)
    svc = price.PriceService(main.db)
    svc.refresh(force=True)
    assert "HTTP 403 from data.gov.in" in caplog.text
    assert key not in caplog.text       # neither our warning nor httpx's own INFO request line
