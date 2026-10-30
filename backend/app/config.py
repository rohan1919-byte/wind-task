"""Central configuration. Everything tunable lives here (or in env vars)."""
import os
from datetime import date
from pathlib import Path
from zoneinfo import ZoneInfo

LONDON = ZoneInfo("Europe/London")

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR / "data"))
CACHE_FILE = DATA_DIR / "january_2026.json.gz"

ELEXON_BASE = os.getenv("ELEXON_BASE", "https://data.elexon.co.uk/bmrs/api/v1")

# Delivery days we care about: purchase decisions made during January 2026
# are for delivery days 1..31 Jan 2026 (see README for the interpretation).
DELIVERY_START = date(2026, 1, 1)
DELIVERY_END = date(2026, 1, 31)

# Day-ahead decision cutoff, London local time on the day BEFORE delivery.
# Only forecasts published at or before this moment may be used.
CUTOFF_HOUR = int(os.getenv("DECISION_CUTOFF_HOUR", "9"))
CUTOFF_MINUTE = int(os.getenv("DECISION_CUTOFF_MINUTE", "0"))

# Set to "1" to skip the live Elexon call and use generated demo data.
FORCE_DEMO = os.getenv("FORCE_DEMO", "0") == "1"

STATIC_DIR = os.getenv("STATIC_DIR", "")
