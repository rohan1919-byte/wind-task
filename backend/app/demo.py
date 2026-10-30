"""Synthetic stand-in data, used ONLY when the Elexon API cannot be reached.

It mimics the shape of FUELHH/WINDFOR (30-min actuals, forecasts with a
publishTime and an error that grows with horizon) so the UI can be explored
offline. The API flags it as source="demo" and the UI shows a banner.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .config import DELIVERY_END, DELIVERY_START


def generate() -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(2026)
    start = pd.Timestamp(DELIVERY_START, tz="UTC") - pd.Timedelta(days=4)
    end = pd.Timestamp(DELIVERY_END, tz="UTC") + pd.Timedelta(days=1)
    idx = pd.date_range(start, end, freq="30min", inclusive="left")

    # Slowly varying "weather" signal -> wind output between ~0.4 and ~16 GW.
    z = np.zeros(len(idx))
    for i in range(1, len(idx)):
        z[i] = 0.995 * z[i - 1] + rng.normal(0, 0.11)
    z = (z - z.mean()) / z.std()
    truth = np.clip(8500 + 4800 * z, 400, 16500)

    actual = pd.DataFrame({"startTime": idx, "generation": np.round(truth + rng.normal(0, 60, len(idx)))})
    actual = actual[actual["startTime"] >= pd.Timestamp(DELIVERY_START, tz="UTC")]

    truth_s = pd.Series(truth, index=idx)
    pub_times = pd.date_range(start, end - pd.Timedelta(hours=1), freq="3h")
    rows = []
    for p in pub_times:
        targets = pd.date_range(p + pd.Timedelta(hours=1), p + pd.Timedelta(hours=60), freq="1h")
        targets = targets[targets.isin(idx)]
        horizon = (targets - p) / pd.Timedelta(hours=1)
        sd = 250 + 85 * horizon.to_numpy()
        gen = truth_s.loc[targets].to_numpy() * 1.02 + rng.normal(0, sd)
        rows.append(pd.DataFrame({"publishTime": p, "startTime": targets, "generation": np.round(np.clip(gen, 0, None))}))
    forecast = pd.concat(rows, ignore_index=True)
    return actual.reset_index(drop=True), forecast
