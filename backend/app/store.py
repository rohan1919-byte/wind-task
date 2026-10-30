"""Holds the data in memory and the derived analysis. Load order:
   1) cached file (backend/data/january_2026.json.gz)  -> source "elexon"
   2) live Elexon API (then writes the cache)           -> source "elexon"
   3) generated demo data                                -> source "demo"
"""
from __future__ import annotations

import gzip
import json
import threading
from datetime import datetime, timezone

import pandas as pd

from . import analysis, demo, elexon
from .config import CACHE_FILE, CUTOFF_HOUR, CUTOFF_MINUTE, DATA_DIR, FORCE_DEMO


class Store:
    def __init__(self) -> None:
        self.lock = threading.RLock()
        self.actuals: pd.DataFrame | None = None
        self.forecasts: pd.DataFrame | None = None
        self.decisions: pd.DataFrame | None = None
        self.source = "none"
        self.fetched_at: str | None = None
        self.note = ""

    # ---- loading -------------------------------------------------------
    def load(self) -> None:
        with self.lock:
            if FORCE_DEMO:
                self._use_demo("FORCE_DEMO=1")
            elif CACHE_FILE.exists() and self._read_cache():
                pass
            else:
                self.refresh()

    def refresh(self) -> None:
        """Pull fresh data from Elexon; fall back to demo data if that fails."""
        with self.lock:
            try:
                actuals = elexon.fetch_actuals()
                forecasts = elexon.fetch_forecasts()
                self._set(actuals, forecasts, "elexon", datetime.now(timezone.utc).isoformat(), "")
                self._write_cache()
            except Exception as exc:  # network blocked, API change, etc.
                self._use_demo(f"Live Elexon fetch failed: {exc}")

    def _use_demo(self, why: str) -> None:
        a, f = demo.generate()
        self._set(a, f, "demo", None, why)

    def _set(self, actuals, forecasts, source, fetched_at, note) -> None:
        self.actuals, self.forecasts = actuals, forecasts
        self.source, self.fetched_at, self.note = source, fetched_at, note
        self.decisions = analysis.decision_forecasts(actuals, forecasts, CUTOFF_HOUR, CUTOFF_MINUTE)

    # ---- cache ---------------------------------------------------------
    def _write_cache(self) -> None:
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            blob = {
                "fetched_at": self.fetched_at,
                "actuals": [[t.isoformat(), g] for t, g in zip(self.actuals["startTime"], self.actuals["generation"])],
                "forecasts": [
                    [p.isoformat(), t.isoformat(), g]
                    for p, t, g in zip(self.forecasts["publishTime"], self.forecasts["startTime"], self.forecasts["generation"])
                ],
            }
            with gzip.open(CACHE_FILE, "wt") as fh:
                json.dump(blob, fh)
        except OSError:
            pass  # read-only filesystem (e.g. serverless) - not fatal

    def _read_cache(self) -> bool:
        try:
            with gzip.open(CACHE_FILE, "rt") as fh:
                blob = json.load(fh)
            a = pd.DataFrame(blob["actuals"], columns=["startTime", "generation"])
            f = pd.DataFrame(blob["forecasts"], columns=["publishTime", "startTime", "generation"])
            for col in ("startTime",):
                a[col] = pd.to_datetime(a[col], utc=True)
            f["startTime"] = pd.to_datetime(f["startTime"], utc=True)
            f["publishTime"] = pd.to_datetime(f["publishTime"], utc=True)
            self._set(a, f, "elexon", blob.get("fetched_at"), "loaded from cache file")
            return True
        except Exception:
            return False


store = Store()
