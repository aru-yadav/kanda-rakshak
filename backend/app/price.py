"""Mandi price from data.gov.in (Agmarknet), cached in SQLite.

Every price returned carries: market, arrival_date, modal (Rs/quintal), source.
source = "data.gov.in" (fetched today) | "cache" (older fetch) | "fallback" (.env, last resort)
The dashboard MUST show source and date. Never present cache/fallback as live.
"""
import logging
from datetime import datetime, timezone
from statistics import mean
from typing import Optional

from urllib.parse import quote, quote_plus

import httpx

from .config import settings
from .db import DB

log = logging.getLogger("price")
API = "https://api.data.gov.in/resource/{rid}"
# data.gov.in stalls requests with the default python-httpx User-Agent (curl answers in 0.4 s); send our own.
HEADERS = {"User-Agent": "KandaRakshak/0.2 (+https://github.com/aru-yadav/kanda-rakshak)", "Accept": "application/json"}
TIMEOUT = httpx.Timeout(30.0, connect=10.0)
REFRESH_S = 3 * 3600          # background refresh interval
RETRY_S = 10 * 60             # sooner retry after a failed fetch (e.g. no network at startup)


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


def norm_market(name: str) -> str:
    """'APMC Lasalgaon ' -> 'lasalgaon'. Matching only; the original name is kept for display."""
    n = (name or "").strip().lower()
    return n[5:].strip() if n.startswith("apmc ") else n


def pick_market(rows: list[dict], preferred: list[str]) -> Optional[dict]:
    """Preferred market order first (normalised name starts with or contains it, so 'Lasalgaon' matches
    'Lasalgaon(Vinchur)' and 'APMC Lasalgaon'); otherwise the state median row. Pure, tested."""
    if not rows:
        return None
    latest = max(r["arrival_date"] for r in rows)
    today_rows = [r for r in rows if r["arrival_date"] == latest]
    for name in preferred:
        want = norm_market(name)
        if not want:
            continue
        hits = [r for r in today_rows if norm_market(r["market"]).startswith(want) or want in norm_market(r["market"])]
        if hits:
            return max(hits, key=lambda r: r["modal"])  # if several varieties, take the highest modal (usually main red onion)
    s = sorted(today_rows, key=lambda r: r["modal"])
    return s[len(s) // 2]


REDACTED = "REDACTED"


def redact(text: str) -> str:
    """Remove the data.gov.in key from any string, in raw and URL-encoded forms (httpx errors embed the URL)."""
    key = settings.datagov_api_key
    if not key:
        return text
    for form in sorted({key, quote_plus(key), quote(key, safe=""), str(httpx.QueryParams({"k": key}))[2:]},
                       key=len, reverse=True):
        text = text.replace(form, REDACTED)
    return text


def describe_error(e: Exception) -> str:
    """Safe one-line error for logs and /explain. HTTP errors are reduced to their status code."""
    if isinstance(e, httpx.HTTPStatusError):
        return f"HTTP {e.response.status_code} from data.gov.in"
    return redact(f"{type(e).__name__}: {e}")


def _params(key: str) -> list[dict]:
    """Query variants in order; fetch_live stops at the first one that returns rows.
    (a) our district (Nashik: Lasalgaon, Pimpalgaon, Chandwad...), small; (b) the whole state, wider."""
    base = {"api-key": key, "format": "json"}
    state = {"filters[state.keyword]": settings.price_state, "filters[commodity]": settings.price_commodity}
    return [
        {**base, **state, "filters[district]": settings.price_district, "limit": 50},
        {**base, **state, "limit": 200},
    ]


def redacted_urls() -> list[str]:
    """The exact request URLs fetch_live() sends, built with the key replaced, in order."""
    url = API.format(rid=settings.datagov_resource_id)
    return [str(httpx.URL(url, params=p)) for p in _params(REDACTED)]


def fetch_live(client: Optional[httpx.Client] = None, trace: Optional[list] = None) -> list[dict]:
    """trace (optional) gets one {url (key redacted), status, rows} entry per request sent."""
    if not settings.datagov_api_key:
        raise RuntimeError("DATAGOV_API_KEY not set")
    url = API.format(rid=settings.datagov_resource_id)
    shown = redacted_urls()
    own = client is None
    client = client or httpx.Client(timeout=TIMEOUT)
    try:
        for i, params in enumerate(_params(settings.datagov_api_key)):
            step = {"url": shown[i], "status": None, "rows": 0}
            if trace is not None:
                trace.append(step)
            resp = client.get(url, params=params, headers=HEADERS)
            step["status"] = resp.status_code
            resp.raise_for_status()
            rows = parse_records(resp.json().get("records", []), settings.price_markets)
            step["rows"] = len(rows)
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
        # what the most recent fetch attempt did (in memory; reset on restart). Never holds the api key.
        self.last_fetch: Optional[dict] = None

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
        """Blocking network call. Runs from the background refresher (main.lifespan) or an explicit
        /price?refresh=true, never from ingest or a dashboard read."""
        now = datetime.now(timezone.utc)
        if not force and self._last_try and (now - self._last_try).total_seconds() < REFRESH_S:
            return
        self._last_try = now
        attempts: list[dict] = []
        self.last_fetch = {"at": now.isoformat(), "ok": False, "rows": 0, "error": None, "attempts": attempts}
        try:
            rows = fetch_live(trace=attempts)
            self.last_fetch.update(ok=bool(rows), rows=len(rows))
            if rows:
                self._store(rows)
                log.info("price: stored %d rows", len(rows))
        except Exception as e:  # network, key, schema — never crash the API
            self.last_fetch["error"] = describe_error(e)
            log.warning("price fetch failed: %s", self.last_fetch["error"])

    def next_refresh_s(self) -> int:
        """Seconds until the background refresher should try again: sooner after a failed fetch."""
        return REFRESH_S if self.last_fetch and self.last_fetch["ok"] else RETRY_S

    def current(self) -> Optional[dict]:
        """Cache (or fallback) only: no network, so it is safe inside any request."""
        c = self._from_cache()
        if c:
            today = datetime.now(timezone.utc).date().isoformat()
            source = "data.gov.in" if c["fetched_at"][:10] == today else "cache"
            return {
                "market": c["market"], "arrival_date": c["arrival_date"], "modal": c["modal"],
                "min_price": c["min_price"], "max_price": c["max_price"], "variety": c["variety"],
                "unit": "Rs/quintal", "source": source, "fetched_at": c["fetched_at"],
                "trend_pct": self._trend(c["market"], c["modal"], c["arrival_date"]),
            }
        if settings.price_fallback_modal:
            return {"market": settings.price_fallback_market, "arrival_date": None,
                    "modal": settings.price_fallback_modal, "unit": "Rs/quintal",
                    "source": "fallback", "fetched_at": None, "trend_pct": None}
        return None
