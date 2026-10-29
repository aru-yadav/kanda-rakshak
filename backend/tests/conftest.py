import os
import sys
import tempfile
from pathlib import Path

# isolated DB + known tokens for every test run (before app import)
os.environ["KR_NO_DOTENV"] = "1"   # never read the developer's backend/.env
_tmp = tempfile.mkdtemp()
os.environ["DB_PATH"] = str(Path(_tmp) / "test.db")
os.environ["DEVICE_TOKEN"] = "test-device-token-0123456789"
os.environ["ADMIN_TOKEN"] = "test-admin-token-0123456789"
os.environ["DATAGOV_API_KEY"] = ""
os.environ["PRICE_FALLBACK_MODAL"] = "1850"
os.environ["TELEGRAM_BOT_TOKEN"] = ""
# pin everything else the tests depend on, so a developer's backend/.env can't change results
os.environ["TELEGRAM_CHAT_ID"] = ""
os.environ["DEMO_MODE"] = "true"
os.environ["NOTIFY_DEVICES"] = "SIM-NSK-01,KR-01"
os.environ["NOTIFY_MIN_INTERVAL_S"] = "3600"
os.environ["PRICE_MARKETS"] = "Lasalgaon"
os.environ["PRICE_FALLBACK_MARKET"] = "Lasalgaon"
os.environ["DATAGOV_RESOURCE_ID"] = "9ef84268-d588-465a-a308-a864a43d0070"
os.environ["PRICE_STATE"] = "Maharashtra"
os.environ["PRICE_COMMODITY"] = "Onion"
os.environ["PRICE_DISTRICT"] = "Nashik"
os.environ["NOTIFY_VOICE"] = "true"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
