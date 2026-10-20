import os
import sys
import tempfile
from pathlib import Path

# isolated DB + known tokens for every test run (before app import)
_tmp = tempfile.mkdtemp()
os.environ["DB_PATH"] = str(Path(_tmp) / "test.db")
os.environ["DEVICE_TOKEN"] = "dev-token"
os.environ["ADMIN_TOKEN"] = "admin-token"
os.environ["DATAGOV_API_KEY"] = ""
os.environ["PRICE_FALLBACK_MODAL"] = "1850"
os.environ["TELEGRAM_BOT_TOKEN"] = ""
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
