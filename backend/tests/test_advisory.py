from app.advisory import decide

P = {"market": "Lasalgaon", "modal": 2400, "trend_pct": 0}


def test_hold_when_safe():
    a = decide("SAFE", P)
    assert a.action == "HOLD" and "थांबा" in a.text_mr and "₹2400" in a.text_en


def test_consider_sell_when_price_high():
    assert decide("SAFE", {**P, "trend_pct": 12}).action == "CONSIDER_SELL"


def test_watch_rising_price_sell_soon():
    assert decide("WATCH", {**P, "trend_pct": 6}).action == "SELL_SOON"


def test_watch_flat_price_ventilate():
    assert decide("WATCH", P).action == "VENTILATE"


def test_rot_names_layer_in_marathi():
    a = decide("ROT", P, "bot")
    assert a.action == "SORT_SELL" and "खालच्या" in a.text_mr and a.severity == "red"


def test_no_price_still_advises():
    a = decide("SAFE", None)
    assert a.action == "HOLD" and "₹" not in a.text_mr


def test_unknown():
    assert decide("UNKNOWN", P).action == "NO_DATA"


def test_market_name_in_marathi():
    assert "लासलगाव" in decide("SAFE", P).text_mr
