"""Day-1 gate check: does data.gov.in return Maharashtra onion prices with our key?
Run from repo root: python tools/check_price_api.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.config import settings  # noqa: E402
from app.price import fetch_live, pick_market  # noqa: E402

if not settings.datagov_api_key:
    raise SystemExit("Set DATAGOV_API_KEY in backend/.env first (register free at data.gov.in).")
rows = fetch_live()
print(f"records: {len(rows)}  markets: {sorted({r['market'] for r in rows})[:15]}")
best = pick_market(rows, settings.price_markets)
if not best:
    raise SystemExit("NO DATA. Check DATAGOV_RESOURCE_ID on data.gov.in ('Current Daily Price of Various Commodities "
                     "from Various Markets (Mandi)') and the filter names in backend/app/price.py.")
print(f"PICKED: {best['market']} {best['variety']} {best['arrival_date']} modal Rs {best['modal']}/quintal  -> G0 price check PASS")
