"""Use cases behind the API: compose the analysis core over the loaded dataset."""

from __future__ import annotations

from datetime import date, time, timedelta
from functools import lru_cache

from . import analysis as an
from .config import Settings
from .repository import Dataset, data_window
from .schemas import (
    Accuracy,
    DayAhead,
    DayAheadPoint,
    DayStats,
    ForecastSummary,
    HistogramBin,
    HorizonStats,
    HourStats,
    Meta,
    ScatterPoint,
    Stats,
)

HISTOGRAM_BIN_MW = 250.0


def _hhmm(t: time) -> str:
    return t.strftime("%H:%M")


class WindService:
    def __init__(self, settings: Settings, dataset: Dataset):
        self.settings = settings
        self.data = dataset
        self.window = data_window(settings)
        # Results depend only on (immutable) data + parameters, so memoise per instance.
        self.day_ahead = lru_cache(maxsize=256)(self._day_ahead)
        self.accuracy = lru_cache(maxsize=64)(self._accuracy)

    @property
    def delivery_days(self) -> list[date]:
        return an.days_between(self.window.delivery_from, self.window.delivery_to)

    def meta(self) -> Meta:
        s, w = self.settings, self.window
        return Meta(
            timezone="Europe/London",
            decision_date_from=s.decision_date_from,
            decision_date_to=s.decision_date_to,
            delivery_date_from=w.delivery_from,
            delivery_date_to=w.delivery_to,
            default_decision_time=_hhmm(s.default_decision_time),
            max_horizon_hours=s.max_horizon_hours,
            data_source=self.data.source,
            data_loaded_at=self.data.fetched_at,
            actual_points=len(self.data.actuals),
            forecast_points=len(self.data.forecasts),
            forecast_runs=len(self.data.forecasts.publish_times),
        )

    def _decision_stats(self, decision_time: time) -> an.ErrorStats | None:
        pairs = an.decision_pairs(
            self.data.actuals, self.data.forecasts, self.delivery_days, decision_time
        )
        return an.error_stats(pairs)

    def _day_ahead(self, delivery_date: date, decision_time: time) -> DayAhead:
        actuals, fc = self.data.actuals, self.data.forecasts
        cutoff = an.decision_cutoff(delivery_date, decision_time)
        day_start = an.local_midnight(delivery_date)
        band_basis = self._decision_stats(decision_time)

        targets = sorted(
            {t for t in actuals if an.in_delivery_day(t, delivery_date)}
            | {t for t in fc.targets if an.in_delivery_day(t, delivery_date)}
        )
        points: list[DayAheadPoint] = []
        scored: list[an.Pair] = []
        forecast_values: list[float] = []
        firm_values: list[float] = []
        publish_used = None
        for t in targets:
            hit = fc.latest_as_of(t, cutoff)
            final = fc.latest_as_of(t, day_start)
            actual = actuals.get(t)
            band = an.error_band(hit[1], band_basis) if hit else None
            if hit:
                publish_used = max(publish_used or hit[0], hit[0])
                forecast_values.append(hit[1])
                if band:
                    firm_values.append(band[0])
                if actual is not None:
                    scored.append(an.Pair(t, hit[0], hit[1], actual))
            points.append(
                DayAheadPoint(
                    start_time=t,
                    actual=actual,
                    forecast=hit[1] if hit else None,
                    forecast_publish_time=hit[0] if hit else None,
                    lead_hours=(t - hit[0]).total_seconds() / 3600 if hit else None,
                    band_low=band[0] if band else None,
                    band_high=band[1] if band else None,
                    final_forecast=final[1] if final else None,
                )
            )

        summary = None
        if forecast_values:
            summary = ForecastSummary(
                points=len(forecast_values),
                mean_mw=sum(forecast_values) / len(forecast_values),
                min_mw=min(forecast_values),
                max_mw=max(forecast_values),
                firm_mean_mw=sum(firm_values) / len(firm_values) if firm_values else None,
            )
        return DayAhead(
            delivery_date=delivery_date,
            decision_time=_hhmm(decision_time),
            decision_cutoff=cutoff,
            forecast_publish_time=publish_used,
            final_forecast_publish_time=fc.latest_publish_as_of(day_start),
            points=points,
            forecast_summary=summary,
            accuracy=Stats.of(an.error_stats(scored)),
            band_basis=Stats.of(band_basis),
        )

    def _accuracy(self, decision_time: time) -> Accuracy:
        actuals, fc = self.data.actuals, self.data.forecasts
        pairs = an.decision_pairs(actuals, fc, self.delivery_days, decision_time)

        by_hour = []
        for hour, group in an.by_local_hour(pairs).items():
            st = an.error_stats(group)
            by_hour.append(
                HourStats(
                    hour=hour,
                    count=st.count,
                    mae=st.mae,
                    bias=st.bias,
                    error_p10=st.error_p10,
                    error_p90=st.error_p90,
                )
            )
        by_day = []
        for day, group in an.by_delivery_day(pairs).items():
            st = an.error_stats(group)
            by_day.append(
                DayStats(
                    delivery_date=day,
                    count=st.count,
                    mean_actual=st.mean_actual,
                    mean_forecast=st.mean_forecast,
                    mae=st.mae,
                    bias=st.bias,
                )
            )

        histogram = [
            HistogramBin(lower=lo, upper=lo + HISTOGRAM_BIN_MW, count=n)
            for lo, n in an.histogram([p.error for p in pairs], HISTOGRAM_BIN_MW)
        ]

        # Horizon curve: independent of decision time, over all delivery periods in scope.
        start = an.local_midnight(self.window.delivery_from)
        end = an.local_midnight(self.window.delivery_to + timedelta(days=1))
        targets = [t for t in fc.targets if start <= t < end]
        by_horizon = []
        for h in range(0, self.settings.max_horizon_hours + 1):
            hp = an.horizon_pairs(actuals, fc, targets, h)
            st = an.error_stats(hp)
            if st is None:
                continue
            by_horizon.append(
                HorizonStats(
                    horizon_hours=h,
                    count=st.count,
                    mean_lead_hours=sum(p.lead_hours for p in hp) / len(hp),
                    mae=st.mae,
                    rmse=st.rmse,
                    bias=st.bias,
                    p90_abs_error=st.p90_abs_error,
                )
            )

        return Accuracy(
            decision_time=_hhmm(decision_time),
            delivery_date_from=self.window.delivery_from,
            delivery_date_to=self.window.delivery_to,
            overall=Stats.of(an.error_stats(pairs)),
            mean_lead_hours=sum(p.lead_hours for p in pairs) / len(pairs) if pairs else None,
            by_hour=by_hour,
            by_day=by_day,
            error_histogram=histogram,
            by_horizon=by_horizon,
            scatter=[ScatterPoint(forecast=p.forecast, actual=p.actual) for p in pairs],
        )
