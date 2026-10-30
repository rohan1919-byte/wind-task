import sys
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import analysis  # noqa: E402


def ts(s):
    return pd.Timestamp(s, tz="UTC")


@pytest.fixture
def frames():
    target = ts("2026-01-10 12:00")
    actuals = pd.DataFrame({"startTime": [target], "generation": [1000.0]})
    forecasts = pd.DataFrame(
        {
            "publishTime": [ts("2026-01-08 12:00"), ts("2026-01-09 08:00"), ts("2026-01-09 10:00")],
            "startTime": [target] * 3,
            "generation": [500.0, 1200.0, 9999.0],
        }
    )
    return actuals, forecasts


def test_cutoff_is_london_time_day_before():
    assert analysis.cutoff_for(date(2026, 1, 10), 9, 0) == ts("2026-01-09 09:00")
    # BST (summer): 09:00 London == 08:00 UTC
    assert analysis.cutoff_for(date(2026, 7, 10), 9, 0) == ts("2026-07-09 08:00")


def test_uses_latest_forecast_before_cutoff_and_ignores_later_ones(frames):
    actuals, forecasts = frames
    d = analysis.decision_forecasts(actuals, forecasts, 9, 0)
    assert len(d) == 1
    row = d.iloc[0]
    assert row["forecast"] == 1200.0  # 08:00 publish, NOT the 10:00 one (after cutoff)
    assert row["publishTime"] == ts("2026-01-09 08:00")
    assert row["error"] == 200.0


def test_metrics_values():
    df = pd.DataFrame({"forecast": [110.0, 90.0, 130.0], "actual": [100.0, 100.0, 100.0]})
    df["error"] = df["forecast"] - df["actual"]
    m = analysis.metrics(df)
    assert m["n"] == 3
    assert m["mae"] == pytest.approx(16.67, abs=0.01)
    assert m["bias"] == pytest.approx(10.0)
    assert m["rmse"] == pytest.approx(((100 + 100 + 900) / 3) ** 0.5, abs=0.01)
    assert m["wmape"] == pytest.approx(50 / 300 * 100, abs=0.01)


def test_metrics_empty():
    assert analysis.metrics(pd.DataFrame({"forecast": [], "actual": [], "error": []})) == {"n": 0}
