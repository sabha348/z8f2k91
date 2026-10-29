"""Domain records shared by the data layer and the analysis core."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class ActualPoint:
    start_time: datetime  # UTC, start of the 30-minute settlement period
    generation: float  # MW
    publish_time: datetime | None = None


@dataclass(frozen=True, slots=True)
class ForecastPoint:
    publish_time: datetime  # UTC, when the forecast was created
    start_time: datetime  # UTC, target time
    generation: float  # MW
