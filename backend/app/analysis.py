"""Pure analysis core: selecting the forecast available at decision time and scoring it.

Conventions
-----------
* All datetimes are timezone-aware UTC; delivery days are UK local calendar days.
* error = forecast - actual (MW). Positive error = over-forecast, i.e. less wind turned
  up than expected, so more power had to be bought elsewhere.
"""

from __future__ import annotations

import math
from bisect import bisect_right
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from .models import ForecastPoint

UK = ZoneInfo("Europe/London")


def local_midnight(day: date) -> datetime:
    """UTC instant of 00:00 UK local time on `day`."""
    return datetime.combine(day, time(0), UK).astimezone(UTC)


def decision_cutoff(delivery_day: date, decision_time: time) -> datetime:
    """UTC instant of the purchase decision: `decision_time` UK local on the day before delivery."""
    return datetime.combine(delivery_day - timedelta(days=1), decision_time, UK).astimezone(UTC)


def days_between(start: date, end: date) -> list[date]:
    return [start + timedelta(days=i) for i in range((end - start).days + 1)]


def in_delivery_day(ts: datetime, day: date) -> bool:
    return local_midnight(day) <= ts < local_midnight(day + timedelta(days=1))


class ForecastIndex:
    """All forecast vintages, indexed by target time for fast "latest as of" lookups."""

    def __init__(self, points: Iterable[ForecastPoint]):
        by_target: dict[datetime, dict[datetime, float]] = defaultdict(dict)
        for p in points:
            by_target[p.start_time][p.publish_time] = p.generation
        self._publish: dict[datetime, list[datetime]] = {}
        self._values: dict[datetime, list[float]] = {}
        for target, vintages in by_target.items():
            ordered = sorted(vintages.items())
            self._publish[target] = [pt for pt, _ in ordered]
            self._values[target] = [v for _, v in ordered]
        self.publish_times: list[datetime] = sorted(
            {pt for pts in self._publish.values() for pt in pts}
        )

    def __len__(self) -> int:
        return sum(len(v) for v in self._publish.values())

    @property
    def targets(self) -> list[datetime]:
        return sorted(self._publish)

    def latest_as_of(self, target: datetime, as_of: datetime) -> tuple[datetime, float] | None:
        """Most recent forecast for `target` published at or before `as_of`."""
        publish = self._publish.get(target)
        if not publish:
            return None
        i = bisect_right(publish, as_of)
        if i == 0:
            return None
        return publish[i - 1], self._values[target][i - 1]

    def latest_publish_as_of(self, as_of: datetime) -> datetime | None:
        i = bisect_right(self.publish_times, as_of)
        return self.publish_times[i - 1] if i else None

    def vintage(self, publish_time: datetime, targets: Iterable[datetime]) -> dict[datetime, float]:
        """Values of one specific forecast run for the given targets (where it covers them)."""
        out: dict[datetime, float] = {}
        for t in targets:
            publish = self._publish.get(t)
            if not publish:
                continue
            i = bisect_right(publish, publish_time)
            if i and publish[i - 1] == publish_time:
                out[t] = self._values[t][i - 1]
        return out


@dataclass(frozen=True, slots=True)
class Pair:
    target: datetime
    publish_time: datetime
    forecast: float
    actual: float

    @property
    def error(self) -> float:
        return self.forecast - self.actual

    @property
    def lead_hours(self) -> float:
        return (self.target - self.publish_time).total_seconds() / 3600


def percentile(sorted_values: Sequence[float], q: float) -> float:
    """Linear-interpolated percentile (q in [0, 100]) of an already sorted sequence."""
    if not sorted_values:
        return math.nan
    pos = (len(sorted_values) - 1) * q / 100
    lo, hi = math.floor(pos), math.ceil(pos)
    return sorted_values[lo] + (sorted_values[hi] - sorted_values[lo]) * (pos - lo)


@dataclass(frozen=True)
class ErrorStats:
    count: int
    mean_actual: float
    mean_forecast: float
    mae: float
    rmse: float
    bias: float  # mean(forecast - actual)
    nmae: float  # MAE / mean actual
    p50_abs_error: float
    p90_abs_error: float
    max_abs_error: float
    error_p10: float  # 10th percentile of signed error
    error_p90: float  # 90th percentile of signed error


def error_stats(pairs: Sequence[Pair]) -> ErrorStats | None:
    if not pairs:
        return None
    n = len(pairs)
    errors = sorted(p.error for p in pairs)
    abs_errors = sorted(abs(e) for e in errors)
    mean_actual = sum(p.actual for p in pairs) / n
    mae = sum(abs_errors) / n
    return ErrorStats(
        count=n,
        mean_actual=mean_actual,
        mean_forecast=sum(p.forecast for p in pairs) / n,
        mae=mae,
        rmse=math.sqrt(sum(e * e for e in errors) / n),
        bias=sum(errors) / n,
        nmae=mae / mean_actual if mean_actual else math.nan,
        p50_abs_error=percentile(abs_errors, 50),
        p90_abs_error=percentile(abs_errors, 90),
        max_abs_error=abs_errors[-1],
        error_p10=percentile(errors, 10),
        error_p90=percentile(errors, 90),
    )


def decision_pairs(
    actuals: Mapping[datetime, float],
    forecasts: ForecastIndex,
    delivery_days: Iterable[date],
    decision_time: time,
) -> list[Pair]:
    """For each delivery day, pair every forecast target with the forecast known at decision time.

    Only targets that have both an actual and a forecast published by the cutoff are scored.
    """
    pairs: list[Pair] = []
    targets = forecasts.targets
    for day in delivery_days:
        cutoff = decision_cutoff(day, decision_time)
        for t in targets:
            if not in_delivery_day(t, day) or t not in actuals:
                continue
            hit = forecasts.latest_as_of(t, cutoff)
            if hit is not None:
                pairs.append(Pair(t, hit[0], hit[1], actuals[t]))
    return pairs


def horizon_pairs(
    actuals: Mapping[datetime, float],
    forecasts: ForecastIndex,
    targets: Iterable[datetime],
    horizon_hours: float,
) -> list[Pair]:
    """Pair each target with the latest forecast published at least `horizon_hours` before it."""
    lead = timedelta(hours=horizon_hours)
    pairs: list[Pair] = []
    for t in targets:
        if t not in actuals:
            continue
        hit = forecasts.latest_as_of(t, t - lead)
        if hit is not None:
            pairs.append(Pair(t, hit[0], hit[1], actuals[t]))
    return pairs


def error_band(forecast: float, stats: ErrorStats | None) -> tuple[float, float] | None:
    """80% empirical range for the actual given a forecast (P10..P90), floored at zero MW."""
    if stats is None:
        return None
    return max(0.0, forecast - stats.error_p90), max(0.0, forecast - stats.error_p10)


def by_local_hour(pairs: Iterable[Pair]) -> dict[int, list[Pair]]:
    groups: dict[int, list[Pair]] = defaultdict(list)
    for p in pairs:
        groups[p.target.astimezone(UK).hour].append(p)
    return dict(sorted(groups.items()))


def by_delivery_day(pairs: Iterable[Pair]) -> dict[date, list[Pair]]:
    groups: dict[date, list[Pair]] = defaultdict(list)
    for p in pairs:
        groups[p.target.astimezone(UK).date()].append(p)
    return dict(sorted(groups.items()))


def histogram(values: Sequence[float], bin_width: float) -> list[tuple[float, int]]:
    """Counts per bin, keyed by each bin's lower edge; empty bins inside the range are included."""
    if not values:
        return []
    counts: dict[int, int] = defaultdict(int)
    for v in values:
        counts[math.floor(v / bin_width)] += 1
    lo, hi = min(counts), max(counts)
    return [(k * bin_width, counts.get(k, 0)) for k in range(lo, hi + 1)]
