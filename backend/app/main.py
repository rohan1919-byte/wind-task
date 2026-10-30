from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import analysis
from .config import CUTOFF_HOUR, CUTOFF_MINUTE, DELIVERY_END, DELIVERY_START, LONDON, STATIC_DIR
from .store import store

app = FastAPI(title="WindDesk API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET", "POST"], allow_headers=["*"])


@app.on_event("startup")
def _startup() -> None:
    store.load()


def _ready():
    if store.decisions is None:  # serverless cold start where startup hook did not run
        store.load()


def _overall_band() -> tuple[float, float] | None:
    m = analysis.metrics(store.decisions)
    if not m.get("n"):
        return None
    return m["q10_actual_minus_forecast"], m["q90_actual_minus_forecast"]


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/meta")
def meta():
    _ready()
    days = []
    d = DELIVERY_START
    while d <= DELIVERY_END:
        days.append(d.isoformat())
        d += timedelta(days=1)
    return {
        "source": store.source,
        "note": store.note,
        "fetched_at": store.fetched_at,
        "delivery_days": days,
        "cutoff": f"{CUTOFF_HOUR:02d}:{CUTOFF_MINUTE:02d}",
        "timezone": str(LONDON),
        "rows": {"actuals": len(store.actuals), "forecasts": len(store.forecasts)},
    }


@app.get("/api/day/{day}")
def day(day: date):
    _ready()
    if not (DELIVERY_START <= day <= DELIVERY_END):
        raise HTTPException(404, "Delivery day outside January 2026")
    body = analysis.day_view(store.decisions, store.actuals, day, _overall_band())
    cutoff = analysis.cutoff_for(day, CUTOFF_HOUR, CUTOFF_MINUTE)
    return {
        "delivery_date": day.isoformat(),
        "decision_cutoff": cutoff.isoformat(),
        "decision_cutoff_local": cutoff.tz_convert(LONDON).strftime("%a %d %b %Y, %H:%M"),
        "band_note": "Planning range = forecast + P10/P90 of (actual - forecast) across January",
        **body,
    }


@app.get("/api/accuracy")
def accuracy():
    _ready()
    d = store.decisions
    return {
        "overall": analysis.metrics(d),
        "daily": analysis.daily(d),
        "by_hour": analysis.by_hour(d),
        "histogram": analysis.histogram(d),
        "horizon": analysis.horizon_profile(store.actuals, store.forecasts, CUTOFF_HOUR, CUTOFF_MINUTE),
        "definition": "Forecast = latest WINDFOR value published at or before the day-ahead cutoff. error = forecast - actual.",
    }


@app.post("/api/refresh")
def refresh():
    store.refresh()
    return meta()


# ---- serve the built React app when present (Docker / single-host deploys) ----
_static = Path(STATIC_DIR) if STATIC_DIR else None
if _static and _static.exists():
    app.mount("/assets", StaticFiles(directory=_static / "assets"), name="assets")

    @app.get("/{path:path}")
    def spa(path: str):
        candidate = _static / path
        if path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(_static / "index.html")
