"""Thin client for the Elexon Insights (BMRS) stream endpoints.

Only two datasets are used:
  * FUELHH  - half-hourly outturn by fuel type (we keep fuelType == WIND)
  * WINDFOR - national wind generation forecasts (startTime, publishTime, generation)
"""
from __future__ import annotations

import time
from datetime import date, datetime, timedelta, timezone

import httpx
import pandas as pd

from .config import DELIVERY_END, DELIVERY_START, ELEXON_BASE


def _get(client: httpx.Client, path: str, params: dict) -> list[dict]:
    last_exc: Exception | None = None
    for attempt in range(4):
        try:
            resp = client.get(f"{ELEXON_BASE}/{path}", params=params, timeout=60)
            if resp.status_code == 429 or resp.status_code >= 500:
                raise httpx.HTTPStatusError("retryable", request=resp.request, response=resp)
            resp.raise_for_status()
            payload = resp.json()
            return payload if isinstance(payload, list) else payload.get("data", [])
        except (httpx.HTTPError, ValueError) as exc:
            last_exc = exc
            time.sleep(2**attempt)
    raise RuntimeError(f"Elexon request failed for {path}: {last_exc}")


def _chunks(start: date, end: date, days: int):
    cur = start
    while cur <= end:
        nxt = min(cur + timedelta(days=days - 1), end)
        yield cur, nxt
        cur = nxt + timedelta(days=1)


def fetch_actuals(start: date = DELIVERY_START, end: date = DELIVERY_END) -> pd.DataFrame:
    rows: list[dict] = []
    with httpx.Client() as client:
        for d0, d1 in _chunks(start, end, 10):
            params = {
                "settlementDateFrom": d0.isoformat(),
                "settlementDateTo": d1.isoformat(),
                "fuelType": "WIND",
            }
            rows += _get(client, "datasets/FUELHH/stream", params)
    df = pd.DataFrame(rows)
    if df.empty:
        raise RuntimeError("FUELHH returned no rows")
    df = df[df["fuelType"] == "WIND"].copy()
    df["startTime"] = pd.to_datetime(df["startTime"], utc=True)
    df["generation"] = pd.to_numeric(df["generation"], errors="coerce")
    df = df.dropna(subset=["generation"]).drop_duplicates("startTime")
    return df[["startTime", "generation"]].sort_values("startTime").reset_index(drop=True)


def fetch_forecasts(start: date = DELIVERY_START, end: date = DELIVERY_END) -> pd.DataFrame:
    """All forecasts published from a few days before `start` up to the last
    decision cutoff, so every delivery day has candidates before its cutoff."""
    first = datetime.combine(start - timedelta(days=3), datetime.min.time(), tzinfo=timezone.utc)
    last = datetime.combine(end, datetime.min.time(), tzinfo=timezone.utc)
    fmt = "%Y-%m-%dT%H:%MZ"
    rows: list[dict] = []
    with httpx.Client() as client:
        cur = first
        while cur < last:
            nxt = min(cur + timedelta(days=2), last)
            params = {
                "publishDateTimeFrom": cur.strftime(fmt),
                "publishDateTimeTo": nxt.strftime(fmt),
            }
            rows += _get(client, "datasets/WINDFOR/stream", params)
            cur = nxt
    df = pd.DataFrame(rows)
    if df.empty:
        raise RuntimeError("WINDFOR returned no rows")
    df["startTime"] = pd.to_datetime(df["startTime"], utc=True)
    df["publishTime"] = pd.to_datetime(df["publishTime"], utc=True)
    df["generation"] = pd.to_numeric(df["generation"], errors="coerce")
    df = df.dropna(subset=["generation"]).drop_duplicates(["publishTime", "startTime"])
    return df[["publishTime", "startTime", "generation"]].sort_values(
        ["publishTime", "startTime"]
    ).reset_index(drop=True)
