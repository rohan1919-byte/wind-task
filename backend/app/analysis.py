"""Pure analysis functions (no I/O) so they are easy to unit-test.

Key idea
--------
A day-ahead purchase for delivery day D is decided on D-1 at a cutoff time
(default 09:00 London). The only forecast the trader could have seen for a
given half-hour is the LATEST one published at or before that cutoff.
Everything on the accuracy side is built from exactly that "decision-time"
forecast, so we never grade a forecast the desk could not have used.
Sign convention: error = forecast - actual (positive = wind over-forecast,
i.e. the desk would have bought too little).
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta

import numpy as np
import pandas as pd

from .config import DELIVERY_END, DELIVERY_START, LONDON


def cutoff_for(delivery: date, hour: int, minute: int) -> pd.Timestamp:
    local = datetime.combine(delivery - timedelta(days=1), time(hour, minute), tzinfo=LONDON)
    return pd.Timestamp(local).tz_convert("UTC")


def _delivery_date(ts: pd.Series) -> pd.Series:
    return ts.dt.tz_convert(LONDON).dt.date


def decision_forecasts(
    actuals: pd.DataFrame,
    forecasts: pd.DataFrame,
    hour: int,
    minute: int,
    start: date = DELIVERY_START,
    end: date = DELIVERY_END,
) -> pd.DataFrame:
    """One row per target half-hour: the forecast available at the cutoff, joined to actuals."""
    f = forecasts.copy()
    f["delivery_date"] = _delivery_date(f["startTime"])
    f = f[(f["delivery_date"] >= start) & (f["delivery_date"] <= end)]
    cutoffs = {d: cutoff_for(d, hour, minute) for d in f["delivery_date"].unique()}
    f["cutoff"] = f["delivery_date"].map(cutoffs)
    f = f[f["publishTime"] <= f["cutoff"]]
    f = f.sort_values("publishTime").groupby("startTime", as_index=False).last()
    f = f.rename(columns={"generation": "forecast"})
    f["horizon_h"] = (f["startTime"] - f["publishTime"]).dt.total_seconds() / 3600

    a = actuals[["startTime", "generation"]].rename(columns={"generation": "actual"})
    out = f.merge(a, on="startTime", how="left")
    out["error"] = out["forecast"] - out["actual"]
    return out.sort_values("startTime").reset_index(drop=True)


def _num(x):
    if x is None:
        return None
    x = float(x)
    return None if np.isnan(x) or np.isinf(x) else round(x, 2)


def metrics(df: pd.DataFrame) -> dict:
    d = df.dropna(subset=["forecast", "actual"])
    if d.empty:
        return {"n": 0}
    e = d["error"]
    ae = e.abs()
    total_actual = d["actual"].sum()
    # actual - forecast: negative tail = wind came in BELOW forecast (shortfall risk)
    shortfall = -e
    return {
        "n": int(len(d)),
        "mae": _num(ae.mean()),
        "rmse": _num(np.sqrt((e**2).mean())),
        "bias": _num(e.mean()),
        "wmape": _num(ae.sum() / total_actual * 100) if total_actual > 0 else None,
        "mean_actual": _num(d["actual"].mean()),
        "mean_forecast": _num(d["forecast"].mean()),
        "p50_abs": _num(ae.quantile(0.5)),
        "p90_abs": _num(ae.quantile(0.9)),
        "p95_abs": _num(ae.quantile(0.95)),
        # P10 of (actual - forecast): wind falls short of forecast by at least this much only 10% of the time
        "q10_actual_minus_forecast": _num(shortfall.quantile(0.1)),
        "q90_actual_minus_forecast": _num(shortfall.quantile(0.9)),
        "max_overforecast": _num(e.max()),
        "max_underforecast": _num(-e.min()),
    }


def daily(df: pd.DataFrame) -> list[dict]:
    out = []
    for d, g in df.groupby("delivery_date"):
        m = metrics(g)
        if m["n"]:
            out.append({"date": d.isoformat(), **{k: m[k] for k in ("n", "mae", "rmse", "bias", "wmape", "mean_actual", "mean_forecast", "max_overforecast")}})
    return out


def by_hour(df: pd.DataFrame) -> list[dict]:
    d = df.dropna(subset=["forecast", "actual"]).copy()
    d["hour"] = d["startTime"].dt.tz_convert(LONDON).dt.hour
    out = []
    for h, g in d.groupby("hour"):
        out.append({"hour": int(h), "mae": _num(g["error"].abs().mean()), "bias": _num(g["error"].mean()), "n": int(len(g))})
    return out


def histogram(df: pd.DataFrame, width: int = 500) -> list[dict]:
    e = df.dropna(subset=["error"])["error"].to_numpy()
    if e.size == 0:
        return []
    lim = int(np.ceil(max(abs(e.min()), abs(e.max())) / width) * width) or width
    edges = np.arange(-lim, lim + width, width)
    counts, _ = np.histogram(e, bins=edges)
    return [{"start": int(edges[i]), "end": int(edges[i + 1]), "count": int(c)} for i, c in enumerate(counts)]


def horizon_profile(actuals: pd.DataFrame, forecasts: pd.DataFrame, cutoff_hour: int, cutoff_minute: int, bucket: int = 6, max_h: int = 72) -> dict:
    """Error vs. forecast age (hours between publish and target) using EVERY
    forecast, not just the decision-time one. Shows how quickly skill decays and
    where the day-ahead decision sits on that curve."""
    f = forecasts.copy()
    f["delivery_date"] = _delivery_date(f["startTime"])
    f = f[(f["delivery_date"] >= DELIVERY_START) & (f["delivery_date"] <= DELIVERY_END)]
    a = actuals[["startTime", "generation"]].rename(columns={"generation": "actual"})
    f = f.merge(a, on="startTime", how="inner")
    f["horizon_h"] = (f["startTime"] - f["publishTime"]).dt.total_seconds() / 3600
    f = f[(f["horizon_h"] > 0) & (f["horizon_h"] <= max_h)]
    f["error"] = f["generation"] - f["actual"]
    f["bucket"] = (f["horizon_h"] // bucket * bucket).astype(int)
    rows = [
        {"from": int(b), "to": int(b + bucket), "mae": _num(g["error"].abs().mean()), "bias": _num(g["error"].mean()), "n": int(len(g))}
        for b, g in f.groupby("bucket")
    ]
    lo = 24 - (cutoff_hour + cutoff_minute / 60)
    return {"buckets": rows, "decision_window": {"from": round(lo, 2), "to": round(lo + 24, 2)}}


def day_view(decisions: pd.DataFrame, actuals: pd.DataFrame, d: date, band: tuple[float, float] | None) -> dict:
    """Half-hourly series for one delivery day, incl. a planning range from historical error quantiles."""
    start = pd.Timestamp(datetime.combine(d, time(0, 0), tzinfo=LONDON)).tz_convert("UTC")
    end = pd.Timestamp(datetime.combine(d + timedelta(days=1), time(0, 0), tzinfo=LONDON)).tz_convert("UTC")
    grid = pd.DataFrame({"startTime": pd.date_range(start, end, freq="30min", inclusive="left")})
    fc = decisions[decisions["delivery_date"] == d][["startTime", "forecast", "publishTime"]]
    ac = actuals[["startTime", "generation"]].rename(columns={"generation": "actual"})
    g = grid.merge(fc, on="startTime", how="left").merge(ac, on="startTime", how="left")

    q10, q90 = band if band else (None, None)
    pts = []
    for r in g.itertuples():
        f = None if pd.isna(r.forecast) else float(r.forecast)
        pts.append(
            {
                "t": r.startTime.isoformat(),
                "forecast": f,
                "actual": None if pd.isna(r.actual) else float(r.actual),
                "lo": None if f is None or q10 is None else max(0.0, round(f + q10, 1)),
                "hi": None if f is None or q90 is None else max(0.0, round(f + q90, 1)),
            }
        )
    valid = g.dropna(subset=["forecast"])
    summary: dict = {"has_forecast": bool(len(valid))}
    if len(valid):
        i_max, i_min = valid["forecast"].idxmax(), valid["forecast"].idxmin()
        summary.update(
            {
                "mean_forecast": _num(valid["forecast"].mean()),
                "peak_forecast": _num(valid.loc[i_max, "forecast"]),
                "peak_time": valid.loc[i_max, "startTime"].isoformat(),
                "min_forecast": _num(valid.loc[i_min, "forecast"]),
                "min_time": valid.loc[i_min, "startTime"].isoformat(),
                "forecast_gwh": _num(valid["forecast"].mean() * 24 / 1000),
                "latest_publish": valid["publishTime"].max().isoformat(),
                "earliest_publish": valid["publishTime"].min().isoformat(),
                "conservative_mean": _num(max(0.0, valid["forecast"].mean() + q10)) if q10 is not None else None,
            }
        )
        both = g.dropna(subset=["forecast", "actual"])
        if len(both):
            e = both["forecast"] - both["actual"]
            summary.update({"day_mae": _num(e.abs().mean()), "day_bias": _num(e.mean()), "actual_gwh": _num(both["actual"].mean() * 24 / 1000)})
    return {"points": pts, "summary": summary}
