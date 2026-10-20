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
