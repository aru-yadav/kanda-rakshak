"""Kanda Rakshak digital twin: virtual onion sheds that behave like real ones.

Each virtual shed runs a simple physics model of a stored onion heap (humidity, heat,
rot spread, rot gas) plus the SAME fan rule as the firmware, and posts readings to the
real backend exactly like an ESP32 would. All device IDs start with SIM- and every
screen labels them SIMULATED. Use this to demo the software while hardware is built.

Scenario / offline / kit on-off for each shed are controlled live from the dashboard.

Usage (backend must be running):
  python tools/digital_twin.py --url http://localhost:8000 --token <DEVICE_TOKEN>
Options: --interval 2 (real seconds per tick)  --minutes 30 (simulated minutes per tick)
"""
import argparse
import math
import random
import time
from dataclasses import dataclass, field

import httpx

# Illustrative demo sheds around the Nashik onion belt. Farmer names are placeholders.
SHEDS = [
    ("SIM-NSK-01", "Lasalgaon", "Niphad", 20.150, 74.230, 25, "humid", True),
    ("SIM-NSK-02", "Pimpalgaon Baswant", "Niphad", 20.170, 73.990, 30, "rot", True),
    ("SIM-NSK-03", "Niphad", "Niphad", 20.080, 74.110, 20, "fresh", True),
    ("SIM-NSK-04", "Yeola", "Yeola", 20.040, 74.490, 25, "humid", True),
    ("SIM-NSK-05", "Chandwad", "Chandwad", 20.330, 74.250, 15, "fresh", True),
    ("SIM-NSK-06", "Sinnar", "Sinnar", 19.850, 74.000, 25, "humid", False),   # kit OFF: traditional chawl for comparison
    ("SIM-NSK-07", "Satana", "Baglan", 20.600, 74.200, 20, "fresh", True),
    ("SIM-NSK-08", "Malegaon", "Malegaon", 20.550, 74.530, 30, "rot", True),
]

SC = {
    "fresh": dict(amb_rh=55, offset=6, rot0=0.00, seed=0.000),
    "humid": dict(amb_rh=78, offset=14, rot0=0.00, seed=0.000),
    "rot":   dict(amb_rh=66, offset=12, rot0=0.15, seed=0.030),
}
LAYERS = ("top", "mid", "bot")
W = {"top": 0.45, "mid": 0.75, "bot": 1.0}
BASE_MV = 420.0


@dataclass
class Shed:
    device_id: str
    scenario: str
    kit_on: bool
    jitter: float = field(default_factory=lambda: random.uniform(-3, 3))
    t: float = 6.0
    rot: float = 0.0
    rh: dict = field(default_factory=dict)
    fan: bool = False
    fan_changed: float = -99.0
    queue: list = field(default_factory=list)
    offline: bool = False

    def reset(self) -> None:
        sc = SC[self.scenario]
        self.t, self.rot, self.fan, self.fan_changed = 6.0, sc["rot0"], False, -99.0
        base = sc["amb_rh"] + self.jitter + sc["offset"]
        self.rh = {"top": base - 2, "mid": base, "bot": base + 3}

    def ambient(self) -> tuple[float, float]:
        ph = 2 * math.pi * (self.t - 9) / 24
        sc = SC[self.scenario]
        return 27 + 4.5 * math.sin(ph), min(98, max(30, sc["amb_rh"] + self.jitter - 14 * math.sin(ph)))

    def layer_t(self, L: str, amb_t: float) -> float:
        return 27 + 0.4 + 4.2 * self.rot * W[L] - (0.8 if self.fan else 0) + 0.25 * (amb_t - 27)

    def step(self, dt: float) -> None:
        sc = SC[self.scenario]
        amb_t, amb_rh = self.ambient()
        heap_rh = max(self.rh.values())
        heap_t = self.layer_t("bot", amb_t)
        # --- fan rule: identical logic to firmware decideFan() ---
        if self.kit_on:
            drier, cooler = amb_rh < heap_rh - 5, amb_t < heap_t - 1.5
            want_on = (heap_rh > 78 and drier) or (heap_t > 30 and cooler)
            want_off = (heap_rh < 72 or not drier) and (heap_t < 28.5 or not cooler)
            if not self.fan and want_on and self.t - self.fan_changed >= 0.5:
                self.fan, self.fan_changed = True, self.t
            elif self.fan and want_off and self.t - self.fan_changed >= 0.5:
                self.fan, self.fan_changed = False, self.t
        else:
            self.fan = False
        # --- humidity ---
        for L in LAYERS:
            off = sc["offset"] + (3 if L == "bot" else -2 if L == "top" else 0) + 18 * self.rot * W[L]
            target = min(99, sc["amb_rh"] + self.jitter + off)
            rate = 0.35 if self.fan else 0.06
            goal = amb_rh + 2 if self.fan else target
            self.rh[L] = max(30, min(99, self.rh[L] + (goal - self.rh[L]) * min(1, rate * dt)))
        # --- rot spread ---
        wet = max(0.0, (max(self.rh["mid"], self.rh["bot"]) - 82) / 12)
        seeded = sc["seed"] * (1 + 1.5 * self.rot) if self.rot > 0 else 0
        humid = (0.010 * wet + 0.012 * self.rot * wet) * (0.35 if self.fan else 1)
        self.rot = min(1.0, self.rot + (seeded + humid) * dt)
        self.t += dt

    def reading(self) -> dict:
        amb_t, amb_rh = self.ambient()
        gas = BASE_MV * (1 + 0.95 * self.rot) + random.uniform(-6, 6)
        n = lambda s: random.uniform(-s, s)
        layers = {L: {"t": round(self.layer_t(L, amb_t) + n(0.15), 1), "rh": round(min(99.9, self.rh[L] + n(0.6)), 1)} for L in LAYERS}
        layers["amb"] = {"t": round(amb_t, 1), "rh": round(amb_rh, 1)}
        return {
            "device_id": self.device_id, "fw": "twin-0.2", "uptime_s": int(self.t * 3600), "age_s": 0,
            "layers": layers,
            "gas": {"mq135_mv": round(gas, 1), "mq136_mv": round(gas * 0.8, 1),
                    "mq135_base_mv": BASE_MV, "mq136_base_mv": BASE_MV * 0.8},
            "gas_alert": gas > BASE_MV * 1.35, "fan_on": self.fan if self.kit_on else False,
            "fan_mode": "A", "dropped": 0, "rssi": -60,
        }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:8000")
    ap.add_argument("--token", default="change-me-same-as-firmware-secrets")
    ap.add_argument("--interval", type=float, default=2.0, help="real seconds per tick")
    ap.add_argument("--minutes", type=float, default=30.0, help="simulated minutes per tick")
    ap.add_argument("--sheds", type=int, default=len(SHEDS))
    a = ap.parse_args()
    H = {"X-Device-Token": a.token}
    sheds: dict[str, Shed] = {}
    with httpx.Client(timeout=10) as c:
        for dev, village, taluka, lat, lon, tonnes, scen, kit in SHEDS[: a.sheds]:
            r = c.post(f"{a.url}/api/v1/sim/register", headers=H, json={
                "device_id": dev, "farmer": "Demo farmer", "village": village, "taluka": taluka,
                "lat": lat, "lon": lon, "tonnes": tonnes, "crop": "onion"})
            r.raise_for_status()
            ctl = c.get(f"{a.url}/api/v1/sim/{dev}/control").json()
            # first run: seed the default scenario for this shed; later runs: respect what the dashboard set
            if ctl.get("scenario") == "humid" and scen != "humid" or not kit:
                c.post(f"{a.url}/api/v1/sim/{dev}/control", json={"scenario": scen, "kit_on": kit})
            s = Shed(dev, scen, kit)
            s.reset()
            sheds[dev] = s
        print(f"Digital twin running: {len(sheds)} SIMULATED sheds, {a.minutes:g} sim-min every {a.interval:g}s. Ctrl+C to stop.")
        while True:
            for dev, s in sheds.items():
                try:
                    ctl = c.get(f"{a.url}/api/v1/sim/{dev}/control", params={"ack_reset": True}).json()
                except httpx.HTTPError as e:
                    print("backend unreachable:", e); time.sleep(a.interval); continue
                changed = ctl["scenario"] != s.scenario or ctl["kit_on"] != s.kit_on or ctl["reset"]
                s.scenario, s.kit_on, s.offline = ctl["scenario"], ctl["kit_on"], ctl["offline"]
                if changed:
                    s.reset(); s.queue.clear()
                    print(f"{dev}: scenario={s.scenario} kit={'ON' if s.kit_on else 'OFF'} (restarted)")
                steps = max(1, int(a.minutes / 6))
                for _ in range(steps):
                    s.step(a.minutes / 60 / steps)
                s.queue.append((time.time(), s.reading()))
                s.queue = s.queue[-500:]
                if s.offline:
                    continue   # like the ESP32: keep deciding the fan locally, buffer readings
                while s.queue:
                    ts, body = s.queue[0]
                    body = {**body, "age_s": int(time.time() - ts)}
                    try:
                        r = c.post(f"{a.url}/api/v1/readings", headers=H, json=body)
                    except httpx.HTTPError:
                        break
                    if r.status_code != 200:
                        print(dev, r.status_code, r.text[:200]); break
                    s.queue.pop(0)
            time.sleep(a.interval)


if __name__ == "__main__":
    main()
