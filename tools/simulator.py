"""Fake ESP32 for building the software before hardware arrives.

Device IDs MUST start with SIM- (enforced). The dashboard labels them SIMULATED.
Never use simulator output as evidence in the deck or video.

Usage:
  python tools/simulator.py --url http://localhost:8000 --scenario rot --interval 2
Scenarios: fresh | rot | humid
"""
import argparse
import math
import random
import time

import httpx


def reading(device: str, step: int, scenario: str) -> dict:
    k = min(step / 60.0, 1.0)                     # 0 -> 1 over 60 steps
    amb_t, amb_rh = 27 + random.uniform(-.3, .3), 58 + random.uniform(-2, 2)
    base = 420.0
    if scenario == "fresh":
        rh, dt, gas = 64, 0.3, base
    elif scenario == "humid":
        rh, dt, gas = 64 + 22 * k, 0.6 * k, base * (1 + 0.1 * k)
    else:  # rot
        rh, dt, gas = 66 + 22 * k, 3.5 * k, base * (1 + 0.8 * k)
    noise = lambda s: random.uniform(-s, s)
    fan = rh > 78
    return {
        "device_id": device, "fw": "sim", "uptime_s": step * 30, "age_s": 0,
        "layers": {
            "top": {"t": round(amb_t + dt * .6 + noise(.2), 1), "rh": round(rh - 2 + noise(1), 1)},
            "mid": {"t": round(amb_t + dt * .8 + noise(.2), 1), "rh": round(rh + noise(1), 1)},
            "bot": {"t": round(amb_t + dt + noise(.2), 1), "rh": round(min(rh + 3, 99) + noise(1), 1)},
            "amb": {"t": round(amb_t, 1), "rh": round(amb_rh, 1)},
        },
        "gas": {"mq135_mv": round(gas + noise(8) + 5 * math.sin(step / 5), 1),
                "mq136_mv": round(gas * .8 + noise(6), 1),
                "mq135_base_mv": base, "mq136_base_mv": base * .8},
        "gas_alert": gas > base * 1.35, "fan_on": fan, "fan_mode": "A", "dropped": 0, "rssi": -55,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:8000")
    ap.add_argument("--device", default="SIM-01")
    ap.add_argument("--token", default="change-me-same-as-firmware-secrets")
    ap.add_argument("--scenario", choices=["fresh", "rot", "humid"], default="rot")
    ap.add_argument("--interval", type=float, default=2.0)
    ap.add_argument("--steps", type=int, default=120)
    a = ap.parse_args()
    if not a.device.upper().startswith("SIM-"):
        raise SystemExit("simulated device ids must start with SIM-")
    with httpx.Client(timeout=10) as c:
        for i in range(a.steps):
            r = c.post(f"{a.url}/api/v1/readings", json=reading(a.device, i, a.scenario),
                       headers={"X-Device-Token": a.token})
            print(i, r.status_code, r.json() if r.status_code == 200 else r.text)
            time.sleep(a.interval)


if __name__ == "__main__":
    main()
