"""Rot-risk score (0-100) from heap conditions. Pure functions, fully tested.

v0 is a transparent rule-based score, deliberately simple so a juror and an
agri-scientist can read it. Weights/thresholds get calibrated in the pilot
with NHRDF/KVK data. Each component is 0..100:

  gas    : % rise of MQ reading over the device's fresh baseline (60 % rise = 100)
  humid  : worst heap RH between 70 % (0) and 90 % (100)
  heat   : hottest heap layer minus ambient, 0 C (0) to 4 C (100)

score = weighted mean of available components (gas 0.5, humid 0.3, heat 0.2)
level : SAFE < 35 <= WATCH < 65 <= ROT
"""
from dataclasses import dataclass, field
from typing import Optional

WEIGHTS = {"gas": 0.5, "humid": 0.3, "heat": 0.2}
GAS_FULL_RISE = 0.60
RH_LOW, RH_HIGH = 70.0, 90.0
HOTSPOT_FULL_C = 4.0
WATCH_AT, ROT_AT = 35.0, 65.0
LAYERS = ("top", "mid", "bot")


@dataclass
class Risk:
    score: float
    level: str                      # SAFE | WATCH | ROT | UNKNOWN
    components: dict = field(default_factory=dict)
    worst_layer: Optional[str] = None
    reasons: list = field(default_factory=list)


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def _gas_rise(mv: Optional[float], base: Optional[float]) -> Optional[float]:
    if mv is None or base is None or base <= 1.0:
        return None
    return (mv - base) / base


def level_for(score: float) -> str:
    if score >= ROT_AT:
        return "ROT"
    if score >= WATCH_AT:
        return "WATCH"
    return "SAFE"


def compute(layers: dict, gas: dict) -> Risk:
    """layers: {'top': {'t':..,'rh':..}, 'mid':.., 'bot':.., 'amb':..}
    gas: {'mq135_mv','mq136_mv','mq135_base_mv','mq136_base_mv'} (values may be None)"""
    comps: dict[str, float] = {}
    reasons: list[str] = []

    rises = [r for r in (_gas_rise(gas.get("mq135_mv"), gas.get("mq135_base_mv")),
                         _gas_rise(gas.get("mq136_mv"), gas.get("mq136_base_mv"))) if r is not None]
    if rises:
        rise = max(rises)
        comps["gas"] = round(100 * _clamp01(rise / GAS_FULL_RISE), 1)
        if rise > 0.15:
            reasons.append(f"rot gas {rise * 100:.0f}% above fresh baseline")

    heap = {k: layers.get(k) or {} for k in LAYERS}
    rhs = {k: v.get("rh") for k, v in heap.items() if v.get("rh") is not None}
    temps = {k: v.get("t") for k, v in heap.items() if v.get("t") is not None}
    worst_layer = None

    if rhs:
        worst_layer = max(rhs, key=rhs.get)
        rh = rhs[worst_layer]
        comps["humid"] = round(100 * _clamp01((rh - RH_LOW) / (RH_HIGH - RH_LOW)), 1)
        if rh > 80:
            reasons.append(f"high humidity {rh:.0f}% in {worst_layer} layer")

    amb_t = (layers.get("amb") or {}).get("t")
    if temps:
        hot_layer = max(temps, key=temps.get)
        ref = amb_t if amb_t is not None else (min(temps.values()) if len(temps) > 1 else None)
        if ref is not None:
            hotspot = temps[hot_layer] - ref
            comps["heat"] = round(100 * _clamp01(hotspot / HOTSPOT_FULL_C), 1)
            if hotspot > 1.5:
                reasons.append(f"{hot_layer} layer {hotspot:.1f}°C warmer than {'outside' if amb_t is not None else 'coolest layer'}")
                if comps["heat"] >= comps.get("humid", 0):
                    worst_layer = hot_layer

    if not comps:
        return Risk(score=0.0, level="UNKNOWN", components={}, reasons=["no valid sensor data"])

    wsum = sum(WEIGHTS[k] for k in comps)
    score = round(sum(WEIGHTS[k] * v for k, v in comps.items()) / wsum, 1)
    if not reasons:
        reasons.append("conditions normal")
    return Risk(score=score, level=level_for(score), components=comps, worst_layer=worst_layer, reasons=reasons)
