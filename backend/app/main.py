"""Kanda Rakshak backend — FastAPI.

Run: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload   (from backend/)
Docs: http://localhost:8000/docs
"""
import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from fastapi import BackgroundTasks, FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import advisory, rotrisk
from .config import settings
from .db import DB
from .models import DeviceMeta, FanCommand, ReadingIn, SimControl
from .notify import Notifier
from .price import PriceService

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
# httpx logs every request URL at INFO: that would print the data.gov.in api-key and the Telegram bot token.
for _noisy in ("httpx", "httpcore"):
    logging.getLogger(_noisy).setLevel(logging.WARNING)

DASHBOARD = Path(__file__).resolve().parents[2] / "dashboard"

app = FastAPI(title="Kanda Rakshak API", version="0.1.0")
db = DB(settings.db_path)
prices = PriceService(db)
notifier = Notifier(db)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def is_sim(device_id: str) -> bool:
    return device_id.upper().startswith("SIM-")


def require(token: Optional[str], expected: str) -> None:
    if not token or token != expected:
        raise HTTPException(status_code=401, detail="bad token")


def _layers_gas(row) -> tuple[dict, dict]:
    layers = {k: {"t": row[f"{k}_t"], "rh": row[f"{k}_rh"]} for k in ("top", "mid", "bot", "amb")}
    gas = {"mq135_mv": row["mq135"], "mq136_mv": row["mq136"],
           "mq135_base_mv": row["mq135_base"], "mq136_base_mv": row["mq136_base"]}
    return layers, gas


def _backend_baseline(device_id: str, col: str) -> Optional[float]:
    """If the device didn't send a baseline, use the median of its first 20 gas readings."""
    rows = db.query(f"SELECT {col} AS v FROM readings WHERE device_id=? AND {col} IS NOT NULL "  # col is internal constant
                    "ORDER BY id ASC LIMIT 20", (device_id,))
    vals = sorted(r["v"] for r in rows)
    return vals[len(vals) // 2] if len(vals) >= 5 else None


def _override(device_id: str) -> tuple[str, int]:
    rows = db.query("SELECT mode, until_utc FROM overrides WHERE device_id=?", (device_id,))
    if not rows:
        return "auto", 0
    until = datetime.fromisoformat(rows[0]["until_utc"])
    ttl = int((until - now_utc()).total_seconds())
    if ttl <= 0 or rows[0]["mode"] == "auto":
        return "auto", 0
    return rows[0]["mode"], ttl


@app.get("/health")
def health():
    return {"ok": True, "time_utc": now_utc().isoformat()}


@app.post("/api/v1/readings")
def ingest(r: ReadingIn, background: BackgroundTasks, x_device_token: Optional[str] = Header(default=None)):
    require(x_device_token, settings.device_token)
    received = now_utc()
    measured = received - timedelta(seconds=r.age_s)
    g = r.gas.model_dump()
    if g["mq135_base_mv"] is None:
        g["mq135_base_mv"] = _backend_baseline(r.device_id, "mq135")
    if g["mq136_base_mv"] is None:
        g["mq136_base_mv"] = _backend_baseline(r.device_id, "mq136")
    layers = r.layers.model_dump()
    risk = rotrisk.compute(layers, g)

    db.execute(
        "INSERT INTO readings(device_id, received_at, measured_at, top_t, top_rh, mid_t, mid_rh, bot_t, bot_rh, "
        "amb_t, amb_rh, mq135, mq136, mq135_base, mq136_base, fan_on, fan_mode, gas_alert, risk_score, risk_level, payload) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (r.device_id, received.isoformat(), measured.isoformat(),
         layers["top"]["t"], layers["top"]["rh"], layers["mid"]["t"], layers["mid"]["rh"],
         layers["bot"]["t"], layers["bot"]["rh"], layers["amb"]["t"], layers["amb"]["rh"],
         g["mq135_mv"], g["mq136_mv"], g["mq135_base_mv"], g["mq136_base_mv"],
         int(r.fan_on), r.fan_mode, int(r.gas_alert), risk.score, risk.level, r.model_dump_json()),
    )

    # only notify on fresh readings (not on a backlog flush)
    if r.age_s < 300:
        price = prices.current()
        adv = advisory.decide(risk.level, price, risk.worst_layer)
        allowed = not settings.notify_devices or r.device_id in settings.notify_devices
        # debounce: only message the farmer once the risk level has held for 3 readings in a row
        recent = [x["risk_level"] for x in db.query(
            "SELECT risk_level FROM readings WHERE device_id=? ORDER BY id DESC LIMIT 3", (r.device_id,))]
        stable = len(recent) == 3 and len(set(recent)) == 1
        if allowed and stable and notifier.should_send(r.device_id, adv):
            background.add_task(notifier.send, r.device_id, adv, is_sim(r.device_id))

    mode, ttl = _override(r.device_id)
    return {"ok": True, "risk_score": risk.score, "risk_level": risk.level,
            "fan_override": mode, "override_ttl_s": ttl}


@app.get("/api/v1/devices")
def devices():
    rows = db.query("SELECT device_id, MAX(received_at) AS last_seen, COUNT(*) AS n FROM readings GROUP BY device_id")
    return [{"device_id": x["device_id"], "last_seen": x["last_seen"], "readings": x["n"],
             "simulated": is_sim(x["device_id"])} for x in rows]


@app.get("/api/v1/devices/{device_id}/latest")
def latest(device_id: str):
    rows = db.query("SELECT * FROM readings WHERE device_id=? ORDER BY measured_at DESC LIMIT 1", (device_id,))
    if not rows:
        raise HTTPException(404, "no readings for this device")
    row = rows[0]
    layers, gas = _layers_gas(row)
    risk = rotrisk.compute(layers, gas)
    price = prices.current()
    adv = advisory.decide(risk.level, price, risk.worst_layer)
    last_n = db.query("SELECT * FROM notifications WHERE device_id=? ORDER BY id DESC LIMIT 1", (device_id,))
    mode, ttl = _override(device_id)
    return {
        "device_id": device_id, "simulated": is_sim(device_id),
        "measured_at": row["measured_at"], "received_at": row["received_at"],
        "layers": layers, "gas": gas, "gas_alert": bool(row["gas_alert"]),
        "fan_on": bool(row["fan_on"]), "fan_mode": row["fan_mode"], "fan_override": mode, "override_ttl_s": ttl,
        "risk": {"score": risk.score, "level": risk.level, "components": risk.components,
                 "worst_layer": risk.worst_layer, "reasons": risk.reasons},
        "price": price,
        "advice": {"action": adv.action, "text_mr": adv.text_mr, "text_en": adv.text_en, "severity": adv.severity},
        "last_notification": dict(last_n[0]) if last_n else None,
    }


@app.get("/api/v1/devices/{device_id}/history")
def history(device_id: str, hours: float = 24):
    since = (now_utc() - timedelta(hours=min(hours, 24 * 14))).isoformat()
    rows = db.query("SELECT measured_at, top_t, top_rh, mid_t, mid_rh, bot_t, bot_rh, amb_t, amb_rh, mq135, mq136, "
                    "fan_on, risk_score FROM readings WHERE device_id=? AND measured_at>=? ORDER BY measured_at",
                    (device_id, since))
    return {"device_id": device_id, "simulated": is_sim(device_id), "rows": [dict(x) for x in rows]}


@app.post("/api/v1/devices/{device_id}/fan")
def fan(device_id: str, cmd: FanCommand, x_admin_token: Optional[str] = Header(default=None)):
    require(x_admin_token, settings.admin_token)
    until = now_utc() + timedelta(seconds=cmd.ttl_s)
    db.execute("INSERT OR REPLACE INTO overrides(device_id, mode, until_utc) VALUES (?,?,?)",
               (device_id, cmd.mode, until.isoformat()))
    return {"ok": True, "mode": cmd.mode, "until_utc": until.isoformat(),
            "note": "applied on the device's next POST; device falls back to AUTO when TTL expires or offline"}


@app.post("/api/v1/devices/{device_id}/notify")
def notify_now(device_id: str, x_admin_token: Optional[str] = Header(default=None)):
    require(x_admin_token, settings.admin_token)
    data = latest(device_id)
    adv = advisory.Advice(**{k: data["advice"][k] for k in ("action", "text_mr", "text_en", "severity")})
    channel = notifier.send(device_id, adv, is_sim(device_id))
    return {"ok": True, "channel": channel, "advice": data["advice"]}


@app.get("/api/v1/price")
def price(refresh: bool = False):
    if refresh:
        prices.refresh(force=True)
    p = prices.current()
    if not p:
        raise HTTPException(503, "no price available: set DATAGOV_API_KEY or PRICE_FALLBACK_MODAL")
    return p


# ------------------------------------------------------------------ digital twin (SIM-* devices only)
def _require_sim(device_id: str) -> None:
    if not is_sim(device_id):
        raise HTTPException(400, "simulation endpoints only accept SIM-* devices")


@app.post("/api/v1/sim/register")
def sim_register(meta: DeviceMeta, x_device_token: Optional[str] = Header(default=None)):
    require(x_device_token, settings.device_token)
    _require_sim(meta.device_id)
    db.execute("INSERT OR REPLACE INTO device_meta(device_id, farmer, village, taluka, lat, lon, tonnes, crop) VALUES (?,?,?,?,?,?,?,?)",
               (meta.device_id, meta.farmer, meta.village, meta.taluka, meta.lat, meta.lon, meta.tonnes, meta.crop))
    db.execute("INSERT OR IGNORE INTO sim_control(device_id) VALUES (?)", (meta.device_id,))
    return {"ok": True}


def _control(device_id: str) -> dict:
    rows = db.query("SELECT scenario, offline, kit_on, reset FROM sim_control WHERE device_id=?", (device_id,))
    if not rows:
        return {"scenario": "humid", "offline": False, "kit_on": True, "reset": False}
    r = rows[0]
    return {"scenario": r["scenario"], "offline": bool(r["offline"]), "kit_on": bool(r["kit_on"]), "reset": bool(r["reset"])}


@app.get("/api/v1/sim/{device_id}/control")
def sim_get_control(device_id: str, ack_reset: bool = False):
    _require_sim(device_id)
    c = _control(device_id)
    if ack_reset and c["reset"]:
        db.execute("UPDATE sim_control SET reset=0 WHERE device_id=?", (device_id,))
    return c


@app.post("/api/v1/sim/{device_id}/control")
def sim_set_control(device_id: str, cmd: SimControl, x_admin_token: Optional[str] = Header(default=None)):
    _require_sim(device_id)
    if not settings.demo_mode:
        require(x_admin_token, settings.admin_token)
    db.execute("INSERT OR IGNORE INTO sim_control(device_id) VALUES (?)", (device_id,))
    for field in ("scenario", "offline", "kit_on", "reset"):
        v = getattr(cmd, field)
        if v is not None:
            db.execute(f"UPDATE sim_control SET {field}=? WHERE device_id=?",  # field is from a fixed whitelist
                       (int(v) if isinstance(v, bool) else v, device_id))
    if cmd.reset:  # wipe this shed's history so the demo restarts cleanly
        db.execute("DELETE FROM readings WHERE device_id=?", (device_id,))
        db.execute("DELETE FROM notifications WHERE device_id=?", (device_id,))
    return _control(device_id)


@app.get("/api/v1/fleet")
def fleet():
    out = []
    devs = db.query("SELECT device_id, MAX(received_at) AS last_seen FROM readings GROUP BY device_id")
    metas = {m["device_id"]: dict(m) for m in db.query("SELECT * FROM device_meta")}
    price = prices.current()
    for d in devs:
        rows = db.query("SELECT * FROM readings WHERE device_id=? ORDER BY measured_at DESC LIMIT 1", (d["device_id"],))
        row = rows[0]
        layers, gas = _layers_gas(row)
        risk = rotrisk.compute(layers, gas)
        adv = advisory.decide(risk.level, price, risk.worst_layer)
        age = (now_utc() - datetime.fromisoformat(d["last_seen"])).total_seconds()
        m = metas.get(d["device_id"], {})
        out.append({"device_id": d["device_id"], "simulated": is_sim(d["device_id"]), "online": age < 45,
                    "last_seen": d["last_seen"], "farmer": m.get("farmer"), "village": m.get("village"),
                    "taluka": m.get("taluka"), "lat": m.get("lat"), "lon": m.get("lon"), "tonnes": m.get("tonnes"),
                    "crop": m.get("crop") or "onion", "risk_score": risk.score, "risk_level": risk.level,
                    "worst_layer": risk.worst_layer, "fan_on": bool(row["fan_on"]), "action": adv.action,
                    "severity": adv.severity, "control": _control(d["device_id"]) if is_sim(d["device_id"]) else None})
    order = {"ROT": 0, "WATCH": 1, "UNKNOWN": 2, "SAFE": 3}
    out.sort(key=lambda x: (order.get(x["risk_level"], 9), -x["risk_score"]))
    return {"price": price, "devices": out}


@app.get("/api/v1/devices/{device_id}/messages")
def messages(device_id: str, limit: int = 10):
    rows = db.query("SELECT sent_at, action, text_mr, text_en, channel FROM notifications WHERE device_id=? "
                    "ORDER BY id DESC LIMIT ?", (device_id, max(1, min(limit, 50))))
    return [dict(r) for r in rows]


AUDIO_DIR = Path(settings.db_path).parent / "audio"


@app.get("/api/v1/devices/{device_id}/voice.mp3")
def voice(device_id: str):
    """Marathi voice of today's advice (gTTS, cached). Production would use Bhashini TTS."""
    import hashlib
    data = latest(device_id)
    text = data["advice"]["text_mr"]
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    f = AUDIO_DIR / (hashlib.sha1(text.encode()).hexdigest()[:16] + ".mp3")
    if not f.exists():
        try:
            from gtts import gTTS
            gTTS(text=text, lang="mr").save(str(f))
        except Exception as e:  # no internet / gTTS blocked
            raise HTTPException(503, f"voice unavailable: {e}")
    return FileResponse(f, media_type="audio/mpeg")


@app.get("/farmer")
def farmer_page():
    return FileResponse(DASHBOARD / "farmer.html")


@app.get("/dept")
def dept_page():
    return FileResponse(DASHBOARD / "dept.html")


@app.get("/")
def index():
    return FileResponse(DASHBOARD / "index.html")


if DASHBOARD.exists():
    app.mount("/static", StaticFiles(directory=DASHBOARD), name="static")
