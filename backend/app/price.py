"""Mandi price from data.gov.in (Agmarknet), cached in SQLite.

Every price returned carries: market, arrival_date, modal (Rs/quintal), source.
source = "data.gov.in" (fetched today) | "cache" (older fetch) | "fallback" (.env, last resort)
The dashboard MUST show source and date. Never present cache/fallback as live.
"""
import logging
from datetime import datetime, timezone
from statistics import mean
from typing import Optional

import httpx

from .config import settings
from .db import DB

log = logging.getLogger("price")
API = "https://api.data.gov.in/resource/{rid}"


def _num(v) -> Optional[float]:
    try:
        return float(str(v).replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def _iso_date(d: str) -> Optional[str]:
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(d.strip(), fmt).date().isoformat()
        except (ValueError, AttributeError):
            continue
    return None


def parse_records(records: list[dict], markets: list[str]) -> list[dict]:
    """Normalise API rows, keep Onion rows with a valid modal price. Pure, tested."""
    out = []
    for r in records:
        modal = _num(r.get("modal_price") or r.get("Modal_Price") or r.get("Modal_x0020_Price"))
        date = _iso_date(str(r.get("arrival_date") or r.get("Arrival_Date") or ""))
        market = (r.get("market") or r.get("Market") or "").strip()
        if modal is None or modal <= 0 or not date or not market:
            continue
        out.append({
            "market": market, "arrival_date": date, "modal": modal,
            "min_price": _num(r.get("min_price") or r.get("Min_Price")),
            "max_price": _num(r.get("max_price") or r.get("Max_Price")),
            "variety": (r.get("variety") or r.get("Variety") or "").strip(),
        })
    return out


def pick_market(rows: list[dict], preferred: list[str]) -> Optional[dict]:
    """Preferred market order first; otherwise the state median row. Pure, tested."""
    if not rows:
        return None
    latest = max(r["arrival_date"] for r in rows)
    today_rows = [r for r in rows if r["arrival_date"] == latest]
    for name in preferred:
        hits = [r for r in today_rows if r["market"].lower().startswith(name.lower())]
        if hits:
            return max(hits, key=lambda r: r["modal"])  # if several varieties, take the highest modal (usually main red onion)
    s = sorted(today_rows, key=lambda r: r["modal"])
    return s[len(s) // 2]


def fetch_live(client: Optional[httpx.Client] = None) -> list[dict]:
    if not settings.datagov_api_key:
        raise RuntimeError("DATAGOV_API_KEY not set")
    url = API.format(rid=settings.datagov_resource_id)
    base = {"api-key": settings.datagov_api_key, "format": "json", "limit": 500}
    # The API has used both 'filters[state]' and 'filters[state.keyword]' styles; try both.
    variants = [
        {"filters[state.keyword]": settings.price_state, "filters[commodity]": settings.price_commodity},
        {"filters[state]": settings.price_state, "filters[commodity]": settings.price_commodity},
    ]
    own = client is None
    client = client or httpx.Client(timeout=15)
    try:
        for v in variants:
            resp = client.get(url, params={**base, **v})
            resp.raise_for_status()
            rows = parse_records(resp.json().get("records", []), settings.price_markets)
            if rows:
                return rows
        return []
    finally:
        if own:
            client.close()


class PriceService:
    def __init__(self, db: DB) -> None:
        self.db = db
        self._last_try: Optional[datetime] = None

    def _store(self, rows: list[dict]) -> None:
        now = datetime.now(timezone.utc).isoformat()
        for r in rows:
            self.db.execute(
                "INSERT OR REPLACE INTO prices(market, arrival_date, modal, min_price, max_price, variety, fetched_at) "
                "VALUES (?,?,?,?,?,?,?)",
                (r["market"], r["arrival_date"], r["modal"], r["min_price"], r["max_price"], r["variety"], now),
            )

    def _from_cache(self) -> Optional[dict]:
        rows = [dict(r) for r in self.db.query("SELECT * FROM prices ORDER BY arrival_date DESC LIMIT 2000")]
        best = pick_market(rows, settings.price_markets)
        if not best:
            return None
        fetched = max(r["fetched_at"] for r in rows if r["market"] == best["market"])
        return {**best, "fetched_at": fetched}

    def _trend(self, market: str, modal: float, date: str) -> Optional[float]:
        hist = self.db.query(
            "SELECT arrival_date, MAX(modal) AS modal FROM prices WHERE market=? AND arrival_date<? "
            "GROUP BY arrival_date ORDER BY arrival_date DESC LIMIT 7", (market, date))
        if len(hist) < 2:
            return None
        avg = mean(r["modal"] for r in hist)
        return round(100 * (modal - avg) / avg, 1) if avg else None

    def refresh(self, force: bool = False) -> None:
        now = datetime.now(timezone.utc)
        if not force and self._last_try and (now - self._last_try).total_seconds() < 3 * 3600:
            return
        self._last_try = now
        try:
            rows = fetch_live()
            if rows:
                self._store(rows)
                log.info("price: stored %d rows", len(rows))
        except Exception as e:  # network, key, schema — never crash the API
            log.warning("price fetch failed: %s", e)

    def current(self) -> Optional[dict]:
        self.refresh()
        c = self._from_cache()
        if c:
            today = datetime.now(timezone.utc).date().isoformat()
            source = "data.gov.in" if c["fetched_at"][:10] == today else "cache"
            return {
                "market": c["market"], "arrival_date": c["arrival_date"], "modal": c["modal"],
                "min_price": c["min_price"], "max_price": c["max_price"], "variety": c["variety"],
                "unit": "Rs/quintal", "source": source,
                "trend_pct": self._trend(c["market"], c["modal"], c["arrival_date"]),
            }
        if settings.price_fallback_modal:
            return {"market": settings.price_fallback_market, "arrival_date": None,
                    "modal": settings.price_fallback_modal, "unit": "Rs/quintal",
                    "source": "fallback", "trend_pct": None}
        return None
