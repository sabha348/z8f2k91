from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest

from app.config import Settings
from app.models import ActualPoint, ForecastPoint


def utc(*args: int) -> datetime:
    return datetime(*args, tzinfo=UTC)


@pytest.fixture
def small_settings(tmp_path) -> Settings:
    # Decisions on 1-2 Jan => delivery days 2-3 Jan 2026.
    return Settings(
        decision_date_from=date(2026, 1, 1),
        decision_date_to=date(2026, 1, 2),
        max_horizon_hours=6,
        data_dir=tmp_path / "data",
        static_dir=tmp_path / "static",
    )


@pytest.fixture
def synthetic_points() -> tuple[list[ActualPoint], list[ForecastPoint]]:
    """Deterministic test data: actuals are a flat 5000 MW, half-hourly, on 2-3 Jan 2026.

    Forecast runs are published every 6 h from 30 Dec, each covering the next 48 h hourly, with
    forecast = 5000 + 10 * lead_hours, so the error grows by 10 MW per hour of lead time.
    """
    start, end = utc(2026, 1, 2), utc(2026, 1, 4)
    actuals = []
    t = start
    while t < end:
        actuals.append(ActualPoint(start_time=t, generation=5000.0))
        t += timedelta(minutes=30)
    forecasts = []
    publish = utc(2025, 12, 30)
    while publish < end:
        for h in range(1, 49):
            target = publish + timedelta(hours=h)
            forecasts.append(ForecastPoint(publish, target, 5000.0 + 10.0 * h))
        publish += timedelta(hours=6)
    return actuals, forecasts
