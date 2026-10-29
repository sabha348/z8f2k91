from __future__ import annotations

import math
from datetime import date, time

import pytest

from app import analysis as an
from app.models import ForecastPoint

from .conftest import utc


def test_decision_cutoff_is_previous_day_uk_local():
    assert an.decision_cutoff(date(2026, 1, 15), time(9)) == utc(2026, 1, 14, 9)
    # In summer UK local time is BST (UTC+1).
    assert an.decision_cutoff(date(2026, 7, 2), time(9)) == utc(2026, 7, 1, 8)


def test_in_delivery_day_uses_uk_local_midnight():
    assert an.in_delivery_day(utc(2026, 7, 1, 23, 30), date(2026, 7, 2))  # 00:30 BST
    assert not an.in_delivery_day(utc(2026, 7, 2, 23), date(2026, 7, 2))


def test_latest_as_of_picks_most_recent_vintage_published_by_cutoff():
    target = utc(2026, 1, 10, 12)
    idx = an.ForecastIndex(
        [
            ForecastPoint(utc(2026, 1, 9, 0), target, 100),
            ForecastPoint(utc(2026, 1, 9, 6), target, 200),
            ForecastPoint(utc(2026, 1, 9, 12), target, 300),
        ]
    )
    assert idx.latest_as_of(target, utc(2026, 1, 8)) is None
    assert idx.latest_as_of(target, utc(2026, 1, 9, 6)) == (utc(2026, 1, 9, 6), 200)
    assert idx.latest_as_of(target, utc(2026, 1, 9, 11)) == (utc(2026, 1, 9, 6), 200)
    assert idx.latest_as_of(utc(2026, 1, 11), utc(2026, 1, 12)) is None
    assert idx.latest_publish_as_of(utc(2026, 1, 9, 13)) == utc(2026, 1, 9, 12)


def test_duplicate_vintage_keeps_last_value():
    target = utc(2026, 1, 10)
    idx = an.ForecastIndex(
        [ForecastPoint(utc(2026, 1, 9), target, 1), ForecastPoint(utc(2026, 1, 9), target, 2)]
    )
    assert len(idx) == 1
    assert idx.latest_as_of(target, utc(2026, 1, 9)) == (utc(2026, 1, 9), 2)


def test_decision_pairs_never_use_forecasts_published_after_cutoff(synthetic_points):
    actuals, forecasts = synthetic_points
    idx = an.ForecastIndex(forecasts)
    actual_map = {a.start_time: a.generation for a in actuals}
    pairs = an.decision_pairs(actual_map, idx, [date(2026, 1, 3)], time(9))
    cutoff = utc(2026, 1, 2, 9)
    assert pairs, "expected scored periods"
    assert all(p.publish_time <= cutoff for p in pairs)
    # Latest run before 09:00 is 06:00; 48h runs cover delivery day up to 06:00 on D+1.
    assert {p.publish_time for p in pairs} == {utc(2026, 1, 2, 6)}
    assert all(an.in_delivery_day(p.target, date(2026, 1, 3)) for p in pairs)
    assert len(pairs) == 24  # hourly forecast targets matched to half-hourly actuals


def test_error_stats_known_values():
    pairs = [
        an.Pair(utc(2026, 1, 1, h), utc(2026, 1, 1), f, a)
        for h, (f, a) in enumerate([(110, 100), (90, 100), (130, 100), (100, 100)])
    ]
    st = an.error_stats(pairs)
    assert st.count == 4
    assert st.mae == pytest.approx(12.5)
    assert st.bias == pytest.approx(7.5)
    assert st.rmse == pytest.approx(math.sqrt((100 + 100 + 900 + 0) / 4))
    assert st.nmae == pytest.approx(0.125)
    assert st.max_abs_error == 30
    assert an.error_stats([]) is None


def test_percentile_interpolates():
    assert an.percentile([0, 10], 50) == 5
    assert an.percentile([1, 2, 3, 4, 5], 90) == pytest.approx(4.6)
    assert math.isnan(an.percentile([], 50))


def test_error_band_inverts_error_quantiles_and_floors_at_zero():
    pairs = [an.Pair(utc(2026, 1, 1), utc(2026, 1, 1), 100 + e, 100) for e in range(-50, 51)]
    st = an.error_stats(pairs)
    low, high = an.error_band(1000, st)
    assert low == pytest.approx(1000 - st.error_p90)
    assert high == pytest.approx(1000 - st.error_p10)
    assert an.error_band(10, st)[0] == 0.0


def test_horizon_pairs_error_grows_with_lead(synthetic_points):
    actuals, forecasts = synthetic_points
    idx = an.ForecastIndex(forecasts)
    actual_map = {a.start_time: a.generation for a in actuals}
    targets = [t for t in idx.targets if t in actual_map]
    short = an.error_stats(an.horizon_pairs(actual_map, idx, targets, 1))
    long = an.error_stats(an.horizon_pairs(actual_map, idx, targets, 24))
    assert all(p.lead_hours >= 24 for p in an.horizon_pairs(actual_map, idx, targets, 24))
    assert short.mae < long.mae


def test_histogram_fills_gaps():
    assert an.histogram([0, 10, 260, 760], 250) == [(0, 2), (250, 1), (500, 0), (750, 1)]
    assert an.histogram([], 250) == []
