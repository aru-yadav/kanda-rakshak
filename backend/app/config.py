"""Settings loaded from backend/.env (gitignored)."""
import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_DIR / ".env")


def _get(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


class Settings:
    def __init__(self) -> None:
        db = _get("DB_PATH", "../data/kanda.db")
        self.db_path = str((BACKEND_DIR / db).resolve()) if not os.path.isabs(db) else db
        self.device_token = _get("DEVICE_TOKEN", "change-me-same-as-firmware-secrets")
        self.admin_token = _get("ADMIN_TOKEN", "change-me-admin")
        self.datagov_api_key = _get("DATAGOV_API_KEY")
        self.datagov_resource_id = _get("DATAGOV_RESOURCE_ID", "9ef84268-d588-465a-a308-a864a43d0070")
        self.price_state = _get("PRICE_STATE", "Maharashtra")
        self.price_commodity = _get("PRICE_COMMODITY", "Onion")
        self.price_markets = [m.strip() for m in _get("PRICE_MARKETS", "Lasalgaon").split(",") if m.strip()]
        fb = _get("PRICE_FALLBACK_MODAL")
        self.price_fallback_modal = float(fb) if fb else None
        self.price_fallback_market = _get("PRICE_FALLBACK_MARKET", "Lasalgaon")
        self.telegram_token = _get("TELEGRAM_BOT_TOKEN")
        self.telegram_chat_id = _get("TELEGRAM_CHAT_ID")
        self.notify_voice = _get("NOTIFY_VOICE", "true").lower() == "true"
        self.notify_min_interval_s = int(_get("NOTIFY_MIN_INTERVAL_S", "3600"))
        # DEMO_MODE: lets the dashboard drive simulated (SIM-*) sheds without an admin token.
        nd = _get("NOTIFY_DEVICES", "SIM-NSK-01,KR-01")
        self.notify_devices = [d.strip() for d in nd.split(",") if d.strip()]  # empty = all devices
        self.demo_mode = _get("DEMO_MODE", "true").lower() == "true"


settings = Settings()
