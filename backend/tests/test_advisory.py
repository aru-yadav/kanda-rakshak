from datetime import datetime

from app.advisory import IST, decide

TODAY = datetime.now(IST).date().isoformat()
P = {"market": "Lasalgaon", "modal": 2400, "trend_pct": 0, "source": "data.gov.in", "arrival_date": TODAY}


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


def test_every_branch_reports_rule_and_why():
    cases = [("UNKNOWN", P, "UNKNOWN"), ("ROT", P, "ROT"), ("WATCH", {**P, "trend_pct": 6}, "WATCH & trend >= +5%"),
             ("WATCH", P, "WATCH & trend < +5%"), ("SAFE", {**P, "trend_pct": 12}, "SAFE & trend >= +10%"),
             ("SAFE", None, "SAFE & trend < +10%")]
    for level, price, rule in cases:
        a = decide(level, price)
        assert a.rule == rule and a.why
    assert "+6.0%" in decide("WATCH", {**P, "trend_pct": 6}).why
    assert "unknown" in decide("SAFE", None).why


def test_live_price_today_is_todays_rate():
    a = decide("SAFE", P)
    assert "Today's Lasalgaon rate ₹2400" in a.text_en and "आजचा लासलगाव भाव ₹2400" in a.text_mr


def test_live_price_from_earlier_day_shows_date():
    a = decide("SAFE", {**P, "arrival_date": "2026-10-27"})
    assert "Today" not in a.text_en and "27-10-2026" in a.text_en
