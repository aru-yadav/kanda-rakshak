"""Notifications. Demo channel: Telegram (Marathi text + Marathi voice note).
Production: DLT-registered SMS + IVR (see docs/TECH_STACK.md)."""
import json
import logging
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import httpx

from .advisory import Advice
from .config import settings
from .db import DB

log = logging.getLogger("notify")


def make_voice(text_mr: str) -> Optional[Path]:
    try:
        from gtts import gTTS
        f = Path(tempfile.gettempdir()) / f"kr_voice_{abs(hash(text_mr))}.mp3"
        if not f.exists():
            gTTS(text=text_mr, lang="mr").save(str(f))
        return f
    except Exception as e:
        log.warning("voice generation failed: %s", e)
        return None


class Notifier:
    def __init__(self, db: DB) -> None:
        self.db = db

    def _last(self, device_id: str, before: Optional[datetime] = None):
        if before is None:
            rows = self.db.query("SELECT * FROM notifications WHERE device_id=? ORDER BY id DESC LIMIT 1", (device_id,))
        else:
            rows = self.db.query("SELECT * FROM notifications WHERE device_id=? AND sent_at<? ORDER BY id DESC LIMIT 1",
                                 (device_id, before.isoformat()))
        return rows[0] if rows else None

    def check(self, device_id: str, advice: Advice, as_of: Optional[datetime] = None) -> tuple[bool, str]:
        """(send?, why) — the farmer gets a message only when the advice changes, or the same advice after the min interval.
        as_of: judge against message history as it was at that moment (default: now)."""
        if advice.action == "NO_DATA":
            return False, "NO_DATA advice is never messaged to the farmer"
        last = self._last(device_id, as_of)
        if last is None:
            return True, "first message for this device"
        if last["action"] != advice.action:
            return True, f"advice changed from {last['action']} to {advice.action}"
        age = ((as_of or datetime.now(timezone.utc)) - datetime.fromisoformat(last["sent_at"])).total_seconds()
        if age >= settings.notify_min_interval_s:
            return True, f"same advice, last sent {age / 60:.0f} min ago (>= {settings.notify_min_interval_s // 60} min)"
        return False, f"same advice already sent {age / 60:.0f} min ago (repeat after {settings.notify_min_interval_s // 60} min)"

    def should_send(self, device_id: str, advice: Advice) -> bool:
        return self.check(device_id, advice)[0]

    def send(self, device_id: str, advice: Advice, simulated: bool = False,
             reading_id: Optional[int] = None, price: Optional[dict] = None) -> str:
        """reading_id/price: which reading triggered this and the price snapshot used, so /explain shows what was sent."""
        tag = "[SIMULATED] " if simulated else ""
        text = f"{tag}कांदा रक्षक · {device_id}\n\n{advice.text_mr}\n\n— {advice.text_en}"
        channel = "console"
        log.info("NOTIFY %s %s: %s", device_id, advice.action, advice.text_en)
        if settings.telegram_token and settings.telegram_chat_id:
            base = f"https://api.telegram.org/bot{settings.telegram_token}"
            try:
                with httpx.Client(timeout=20) as c:
                    c.post(f"{base}/sendMessage", data={"chat_id": settings.telegram_chat_id, "text": text}).raise_for_status()
                    if settings.notify_voice:
                        mp3 = make_voice(advice.text_mr)
                        if mp3:
                            with open(mp3, "rb") as fh:
                                c.post(f"{base}/sendAudio", data={"chat_id": settings.telegram_chat_id,
                                       "title": "कांदा रक्षक सल्ला"}, files={"audio": fh}).raise_for_status()
                channel = "telegram"
            except Exception as e:
                log.warning("telegram failed: %s", e)
                channel = "console(telegram-failed)"
        self.db.execute(
            "INSERT INTO notifications(device_id, sent_at, action, text_mr, text_en, channel, reading_id, price) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (device_id, datetime.now(timezone.utc).isoformat(), advice.action, advice.text_mr, advice.text_en, channel,
             reading_id, json.dumps(price) if price else None),
        )
        return channel
