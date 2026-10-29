import os
import sys
import tempfile
from pathlib import Path

# isolated DB + known tokens for every test run (before app import)
_tmp = tempfile.mkdtemp()
os.environ["DB_PATH"] = str(Path(_tmp) / "test.db")
os.environ["DEVICE_TOKEN"] = "test-device-token-0123456789"
os.environ["ADMIN_TOKEN"] = "test-admin-token-0123456789"
os.environ["DATAGOV_API_KEY"] = ""
os.environ["PRICE_FALLBACK_MODAL"] = "1850"
os.environ["TELEGRAM_BOT_TOKEN"] = ""
os.environ["DEMO_MODE"] = "true"   # tests drive SIM-* sheds; the app default is now off
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
