"""Turns rot risk + mandi price into ONE instruction, in Marathi and English.

Actions:
  HOLD           safe, price not unusually high
  CONSIDER_SELL  safe, price >= 10 % above recent average
  VENTILATE      watch, price flat/falling
  SELL_SOON      watch, price rising >= 5 %
  SORT_SELL      rot detected
  NO_DATA        sensors not reporting

Marathi text must be checked by a native speaker before filming (data-integrity-auditor flags this).
"""
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Optional

IST = timezone(timedelta(hours=5, minutes=30))

LAYER_MR = {"top": "वरच्या", "mid": "मधल्या", "bot": "खालच्या"}
LAYER_EN = {"top": "top", "mid": "middle", "bot": "bottom"}
MARKET_MR = {"lasalgaon": "लासलगाव", "pimpalgaon": "पिंपळगाव", "niphad": "निफाड", "nashik": "नाशिक",
             "pune": "पुणे", "ahmednagar": "अहिल्यानगर", "solapur": "सोलापूर", "yeola": "येवला",
             "chandvad": "चांदवड", "manmad": "मनमाड", "vani": "वणी", "rahuri": "राहुरी"}


def market_mr(m: str) -> str:
    key = (m or "").lower()
    for k, v in MARKET_MR.items():
        if key.startswith(k):
            return v
    return m


@dataclass
class Advice:
    action: str
    text_mr: str
    text_en: str
    severity: str  # green | amber | red | grey
    rule: str = ""  # which branch of decide() fired, e.g. "WATCH & trend >= +5%"
    why: str = ""   # that branch's condition filled in with the actual inputs


def _price_bits(price: Optional[dict], today: Optional[date] = None) -> tuple[str, str]:
    """Price sentence for the farmer. Live today -> "today's rate"; cached -> "rate on <date>";
    fallback / undated -> no price at all (a config value must never reach a farmer as a mandi rate)."""
    if not price or price.get("modal") is None or price.get("source") not in ("data.gov.in", "cache"):
        return "", ""
    arrival = price.get("arrival_date")
    if not arrival:
        return "", ""
    p = int(round(price["modal"]))
    m = price.get("market", "")
    today = today or datetime.now(IST).date()
    if price["source"] == "data.gov.in" and arrival == today.isoformat():
        return f" आजचा {market_mr(m)} भाव ₹{p}/क्विंटल.", f" Today's {m} rate ₹{p}/quintal."
    d = date.fromisoformat(arrival).strftime("%d-%m-%Y")
    return f" {d} रोजीचा {market_mr(m)} भाव ₹{p}/क्विंटल.", f" {m} rate on {d}: ₹{p}/quintal."


def decide(level: str, price: Optional[dict], worst_layer: Optional[str] = None) -> Advice:
    trend = (price or {}).get("trend_pct")
    pmr, pen = _price_bits(price)
    layer_mr = LAYER_MR.get(worst_layer or "", "")
    layer_en = LAYER_EN.get(worst_layer or "", "")
    tr = "unknown (<2 earlier price days)" if trend is None else f"{trend:+.1f}% vs earlier-days avg"

    if level == "UNKNOWN":
        return Advice("NO_DATA", "सेन्सरकडून माहिती मिळत नाही. कृपया यंत्र तपासा.",
                      "No data from sensors. Please check the device.", "grey",
                      "UNKNOWN", "no valid sensor reading, so no risk score; price is not used")

    if level == "ROT":
        where_mr = f"{layer_mr} थरात " if layer_mr else ""
        where_en = f" in the {layer_en} layer" if layer_en else ""
        return Advice(
            "SORT_SELL",
            f"धोका: {where_mr}कांदा सडायला सुरुवात झाली आहे. आज निवडणी करा आणि खराब कांदा वेगळा करा.{pmr}",
            f"Alert: rot has started{where_en}. Sort today and separate the damaged onions.{pen}",
            "red",
            "ROT", f"risk ROT (score >= 65): sort today, whatever the price (trend {tr})",
        )

    if level == "WATCH":
        if trend is not None and trend >= 5:
            return Advice(
                "SELL_SOON",
                f"कांद्यात ओलावा वाढत आहे आणि भाव वाढत आहे.{pmr} या आठवड्यात विका.",
                f"Moisture is rising in the heap and prices are rising.{pen} Sell this week.",
                "amber",
                "WATCH & trend >= +5%", f"risk WATCH, price trend {tr} meets >= +5%: sell while the price is rising",
            )
        return Advice(
            "VENTILATE",
            f"कांद्यात ओलावा/उष्णता वाढत आहे. बाहेरची हवा कोरडी असताना पंखा आपोआप चालेल. आज एकदा कांदा तपासा.{pmr}",
            f"Moisture/heat is rising in the heap. The fan runs automatically when outside air is drier. Check the onions once today.{pen}",
            "amber",
            "WATCH & trend < +5%", f"risk WATCH, price trend {tr} does not meet >= +5%: ventilate and inspect",
        )

    # SAFE
    if trend is not None and trend >= 10:
        return Advice(
            "CONSIDER_SELL",
            f"तुमचा कांदा सुरक्षित आहे.{pmr} भाव गेल्या आठवड्यापेक्षा {trend:.0f}% जास्त आहे. काही माल विकण्याचा विचार करा.",
            f"Your onions are safe.{pen} Price is {trend:.0f}% above last week. Consider selling part of the stock.",
            "green",
            "SAFE & trend >= +10%", f"risk SAFE, price trend {tr} meets >= +10%: price is unusually high",
        )
    return Advice(
        "HOLD",
        f"तुमचा कांदा सुरक्षित आहे. आत्ता विकू नका, थांबा.{pmr}",
        f"Your onions are safe. Don't sell yet, hold.{pen}",
        "green",
        "SAFE & trend < +10%", f"risk SAFE, price trend {tr} does not meet >= +10%: no reason to sell yet",
    )
