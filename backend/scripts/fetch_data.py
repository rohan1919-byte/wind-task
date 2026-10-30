"""Download January 2026 data from Elexon once and save it to backend/data/.

    cd backend && python -m scripts.fetch_data

Commit the resulting file so deployments (e.g. Vercel) start instantly and
never depend on the live API.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.store import Store  # noqa: E402
from app import elexon  # noqa: E402
from datetime import datetime, timezone  # noqa: E402

if __name__ == "__main__":
    s = Store()
    print("Fetching FUELHH (WIND)...")
    a = elexon.fetch_actuals()
    print(f"  {len(a)} half-hours")
    print("Fetching WINDFOR...")
    f = elexon.fetch_forecasts()
    print(f"  {len(f)} forecast rows")
    s._set(a, f, "elexon", datetime.now(timezone.utc).isoformat(), "")
    s._write_cache()
    print("Saved backend/data/january_2026.json.gz")
