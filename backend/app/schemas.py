"""API response models (serialised as camelCase JSON)."""

from __future__ import annotations

import math
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, field_validator
from pydantic.alias_generators import to_camel

from .analysis import ErrorStats


class ApiModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    @field_validator("*", mode="before")
    @classmethod
    def _nan_to_none(cls, value):
        # NaN is not valid JSON; surface "not computable" as null instead.
        if isinstance(value, float) and math.isnan(value):
            return None
        return value


class Stats(ApiModel):
    count: int
    mean_actual: float | None
    mean_forecast: float | None
    mae: float | None
    rmse: float | None
    bias: float | None
    nmae: float | None
    p50_abs_error: float | None
    p90_abs_error: float | None
    max_abs_error: float | None
    error_p10: float | None
    error_p90: float | None

    @classmethod
    def of(cls, stats: ErrorStats | None) -> Stats | None:
        return None if stats is None else cls(**stats.__dict__)


class Meta(ApiModel):
    timezone: str
    decision_date_from: date
    decision_date_to: date
    delivery_date_from: date
    delivery_date_to: date
    default_decision_time: str
    max_horizon_hours: int
    data_source: str
    data_loaded_at: datetime
    actual_points: int
    forecast_points: int
    forecast_runs: int


class DayAheadPoint(ApiModel):
    start_time: datetime
    actual: float | None
    forecast: float | None
    forecast_publish_time: datetime | None
    lead_hours: float | None
    band_low: float | None
    band_high: float | None
    final_forecast: float | None  # latest forecast published by the start of delivery


class ForecastSummary(ApiModel):
    points: int
    mean_mw: float
    min_mw: float
    max_mw: float
    firm_mean_mw: float | None  # mean of the P10 ("90% likely to be exceeded") level


class DayAhead(ApiModel):
    delivery_date: date
    decision_time: str
    decision_cutoff: datetime
    forecast_publish_time: datetime | None
    final_forecast_publish_time: datetime | None
    points: list[DayAheadPoint]
    forecast_summary: ForecastSummary | None
    accuracy: Stats | None  # this day's error, at decision time
    band_basis: Stats | None  # error distribution the band is built from


class HourStats(ApiModel):
    hour: int
    count: int
    mae: float
    bias: float
    error_p10: float
    error_p90: float


class DayStats(ApiModel):
    delivery_date: date
    count: int
    mean_actual: float
    mean_forecast: float
    mae: float
    bias: float


class HistogramBin(ApiModel):
    lower: float
    upper: float
    count: int


class HorizonStats(ApiModel):
    horizon_hours: int
    count: int
    mean_lead_hours: float
    mae: float
    rmse: float
    bias: float
    p90_abs_error: float


class ScatterPoint(ApiModel):
    forecast: float
    actual: float


class Accuracy(ApiModel):
    decision_time: str
    delivery_date_from: date
    delivery_date_to: date
    overall: Stats | None
    mean_lead_hours: float | None
    by_hour: list[HourStats]
    by_day: list[DayStats]
    error_histogram: list[HistogramBin]
    by_horizon: list[HorizonStats]
    scatter: list[ScatterPoint]
