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
from typing import Optional

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


def _price_bits(price: Optional[dict]) -> tuple[str, str]:
    if not price or price.get("modal") is None:
        return "", ""
    p = int(round(price["modal"]))
    m = price.get("market", "")
    return f" आजचा {market_mr(m)} भाव ₹{p}/क्विंटल.", f" Today's {m} rate ₹{p}/quintal."


def decide(level: str, price: Optional[dict], worst_layer: Optional[str] = None) -> Advice:
    trend = (price or {}).get("trend_pct")
    pmr, pen = _price_bits(price)
    layer_mr = LAYER_MR.get(worst_layer or "", "")
    layer_en = LAYER_EN.get(worst_layer or "", "")

    if level == "UNKNOWN":
        return Advice("NO_DATA", "सेन्सरकडून माहिती मिळत नाही. कृपया यंत्र तपासा.",
                      "No data from sensors. Please check the device.", "grey")

    if level == "ROT":
        where_mr = f"{layer_mr} थरात " if layer_mr else ""
        where_en = f" in the {layer_en} layer" if layer_en else ""
        return Advice(
            "SORT_SELL",
            f"धोका: {where_mr}कांदा सडायला सुरुवात झाली आहे. आज निवडणी करा आणि खराब कांदा वेगळा करा.{pmr}",
            f"Alert: rot has started{where_en}. Sort today and separate the damaged onions.{pen}",
            "red",
        )

    if level == "WATCH":
        if trend is not None and trend >= 5:
            return Advice(
                "SELL_SOON",
                f"कांद्यात ओलावा वाढत आहे आणि भाव वाढत आहे.{pmr} या आठवड्यात विका.",
                f"Moisture is rising in the heap and prices are rising.{pen} Sell this week.",
                "amber",
            )
        return Advice(
            "VENTILATE",
            f"कांद्यात ओलावा/उष्णता वाढत आहे. बाहेरची हवा कोरडी असताना पंखा आपोआप चालेल. आज एकदा कांदा तपासा.{pmr}",
            f"Moisture/heat is rising in the heap. The fan runs automatically when outside air is drier. Check the onions once today.{pen}",
            "amber",
        )

    # SAFE
    if trend is not None and trend >= 10:
        return Advice(
            "CONSIDER_SELL",
            f"तुमचा कांदा सुरक्षित आहे.{pmr} भाव गेल्या आठवड्यापेक्षा {trend:.0f}% जास्त आहे. काही माल विकण्याचा विचार करा.",
            f"Your onions are safe.{pen} Price is {trend:.0f}% above last week. Consider selling part of the stock.",
            "green",
        )
    return Advice(
        "HOLD",
        f"तुमचा कांदा सुरक्षित आहे. आत्ता विकू नका, थांबा.{pmr}",
        f"Your onions are safe. Don't sell yet, hold.{pen}",
        "green",
    )
