"""M6: the test run must never read the developer's backend/.env."""
import importlib

from app import config


def test_dotenv_skipped_when_kr_no_dotenv(monkeypatch):
    calls = []
    monkeypatch.setenv("KR_NO_DOTENV", "1")
    monkeypatch.setattr("dotenv.load_dotenv", lambda *a, **k: calls.append(a))
    importlib.reload(config)
    assert calls == []


def test_dotenv_loaded_normally(monkeypatch):
    calls = []
    monkeypatch.delenv("KR_NO_DOTENV", raising=False)
    monkeypatch.setattr("dotenv.load_dotenv", lambda *a, **k: calls.append(a))
    try:
        importlib.reload(config)
        assert len(calls) == 1
    finally:
        monkeypatch.setenv("KR_NO_DOTENV", "1")
        importlib.reload(config)
