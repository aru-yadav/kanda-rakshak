"""SQLite storage. Parameterised queries only."""
import sqlite3
import threading
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS readings (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  device_id TEXT NOT NULL,
  received_at TEXT NOT NULL,
  measured_at TEXT NOT NULL,
  top_t REAL, top_rh REAL, mid_t REAL, mid_rh REAL, bot_t REAL, bot_rh REAL, amb_t REAL, amb_rh REAL,
  mq135 REAL, mq136 REAL, mq135_base REAL, mq136_base REAL,
  fan_on INTEGER, fan_mode TEXT, gas_alert INTEGER,
  risk_score REAL, risk_level TEXT, payload TEXT
);
CREATE INDEX IF NOT EXISTS ix_readings_dev_time ON readings(device_id, measured_at);
CREATE TABLE IF NOT EXISTS prices (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  market TEXT NOT NULL, arrival_date TEXT NOT NULL, modal REAL NOT NULL,
  min_price REAL, max_price REAL, variety TEXT, fetched_at TEXT NOT NULL,
  UNIQUE(market, arrival_date, variety)
);
CREATE TABLE IF NOT EXISTS overrides (
  device_id TEXT PRIMARY KEY, mode TEXT NOT NULL, until_utc TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS device_meta (
  device_id TEXT PRIMARY KEY, farmer TEXT, village TEXT, taluka TEXT,
  lat REAL, lon REAL, tonnes REAL, crop TEXT
);
CREATE TABLE IF NOT EXISTS sim_control (
  device_id TEXT PRIMARY KEY, scenario TEXT NOT NULL DEFAULT 'humid',
  offline INTEGER NOT NULL DEFAULT 0, kit_on INTEGER NOT NULL DEFAULT 1, reset INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS notifications (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  device_id TEXT NOT NULL, sent_at TEXT NOT NULL, action TEXT NOT NULL,
  text_mr TEXT, text_en TEXT, channel TEXT
);
"""


class DB:
    def __init__(self, path: str) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.lock = threading.Lock()
        with self.lock:
            self.conn.executescript(SCHEMA)
            self.conn.commit()

    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        with self.lock:
            cur = self.conn.execute(sql, params)
            self.conn.commit()
            return cur

    def query(self, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        with self.lock:
            return self.conn.execute(sql, params).fetchall()
