"""Export real (non-SIM) readings to CSV + PNG graphs for the deck/video.
python tools/export_evidence.py --device KR-01 --hours 48
Requires: pip install matplotlib (dev only)
"""
import argparse
import csv
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ap = argparse.ArgumentParser()
ap.add_argument("--device", required=True)
ap.add_argument("--hours", type=float, default=48)
ap.add_argument("--db", default=str(ROOT / "data" / "kanda.db"))
a = ap.parse_args()
if a.device.upper().startswith("SIM-"):
    raise SystemExit("Refusing: simulated devices are never evidence.")
out = ROOT / "docs" / "evidence"
out.mkdir(parents=True, exist_ok=True)
con = sqlite3.connect(a.db); con.row_factory = sqlite3.Row
since = (datetime.now(timezone.utc) - timedelta(hours=a.hours)).isoformat()
rows = [dict(r) for r in con.execute(
    "SELECT measured_at, top_t, top_rh, mid_t, mid_rh, bot_t, bot_rh, amb_t, amb_rh, mq135, mq136, fan_on, risk_score "
    "FROM readings WHERE device_id=? AND measured_at>=? ORDER BY measured_at", (a.device, since))]
if not rows:
    raise SystemExit("no rows")
stamp = datetime.now().strftime("%Y%m%d-%H%M")
csv_path = out / f"{a.device}-{stamp}.csv"
with open(csv_path, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)
print("wrote", csv_path, len(rows), "rows")
try:
    import matplotlib.pyplot as plt
    t = [datetime.fromisoformat(r["measured_at"]).astimezone(timezone(timedelta(hours=5, minutes=30))) for r in rows]
    fig, ax = plt.subplots(3, 1, figsize=(11, 9), sharex=True)
    for k, lab in (("top", "Top"), ("mid", "Middle"), ("bot", "Bottom"), ("amb", "Outside")):
        ax[0].plot(t, [r[f"{k}_rh"] for r in rows], label=lab); ax[1].plot(t, [r[f"{k}_t"] for r in rows], label=lab)
    ax[2].plot(t, [r["mq135"] for r in rows], label="MQ-135 mV"); ax[2].plot(t, [r["mq136"] for r in rows], label="MQ-136 mV")
    ax[0].set_ylabel("RH %"); ax[1].set_ylabel("Temp °C"); ax[2].set_ylabel("Gas mV")
    for x in ax: x.legend(loc="upper left"); x.grid(alpha=.3)
    fig.suptitle(f"Kanda Rakshak {a.device} — raw sensor log, {t[0]:%d %b %H:%M} to {t[-1]:%d %b %H:%M} IST (unsmoothed)")
    png = out / f"{a.device}-{stamp}.png"; fig.tight_layout(); fig.savefig(png, dpi=150); print("wrote", png)
except ImportError:
    print("matplotlib not installed; CSV only")
