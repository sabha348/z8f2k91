"""Thin client for the Elexon BMRS Insights API (FUELHH and WINDFOR stream endpoints)."""

from __future__ import annotations

import logging
from collections.abc import Iterator
from datetime import UTC, date, datetime, timedelta
from typing import Any

import httpx

from .models import ActualPoint, ForecastPoint

log = logging.getLogger(__name__)

CHUNK_DAYS = 7


def parse_time(value: str) -> datetime:
    """Parse an Elexon ISO-8601 timestamp into an aware UTC datetime."""
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _rows(payload: Any) -> list[dict[str, Any]]:
    # Stream endpoints return a bare JSON array; non-stream ones wrap it in {"data": [...]}.
    if isinstance(payload, dict):
        payload = payload.get("data", [])
    if not isinstance(payload, list):
        raise ValueError(f"Unexpected Elexon payload type: {type(payload).__name__}")
    return payload


def _date_chunks(start: date, end: date) -> Iterator[tuple[date, date]]:
    """Split [start, end] (inclusive) into consecutive chunks of at most CHUNK_DAYS days."""
    cursor = start
    while cursor <= end:
        chunk_end = min(cursor + timedelta(days=CHUNK_DAYS - 1), end)
        yield cursor, chunk_end
        cursor = chunk_end + timedelta(days=1)


def _iso(dt: datetime) -> str:
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


class ElexonClient:
    def __init__(self, base_url: str, timeout_s: float = 60.0, http: httpx.Client | None = None):
        self._base_url = base_url.rstrip("/")
        self._http = http or httpx.Client(timeout=timeout_s, headers={"Accept": "application/json"})

    def _get(self, path: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        url = f"{self._base_url}{path}"
        log.info("GET %s %s", url, params)
        response = self._http.get(url, params=params)
        response.raise_for_status()
        return _rows(response.json())

    def fetch_wind_actuals(self, settlement_from: date, settlement_to: date) -> list[ActualPoint]:
        """Half-hourly outturn wind generation (FUELHH, fuelType=WIND) for settlement dates."""
        points: dict[datetime, ActualPoint] = {}
        for lo, hi in _date_chunks(settlement_from, settlement_to):
            rows = self._get(
                "/datasets/FUELHH/stream",
                {
                    "settlementDateFrom": lo.isoformat(),
                    "settlementDateTo": hi.isoformat(),
                    "fuelType": "WIND",
                },
            )
            for row in rows:
                if row.get("fuelType") != "WIND" or row.get("generation") is None:
                    continue
                point = ActualPoint(
                    start_time=parse_time(row["startTime"]),
                    generation=float(row["generation"]),
                    publish_time=parse_time(row["publishTime"]) if row.get("publishTime") else None,
                )
                # If a period was re-published, keep the most recent value.
                existing = points.get(point.start_time)
                if existing is None or _newer(point.publish_time, existing.publish_time):
                    points[point.start_time] = point
        return sorted(points.values(), key=lambda p: p.start_time)

    def fetch_wind_forecasts(
        self, publish_from: datetime, publish_to: datetime
    ) -> list[ForecastPoint]:
        """Every WINDFOR forecast published in [publish_from, publish_to)."""
        points: dict[tuple[datetime, datetime], ForecastPoint] = {}
        for lo, hi in _date_chunks(publish_from.date(), (publish_to - timedelta(seconds=1)).date()):
            lo_dt = max(publish_from, datetime.combine(lo, datetime.min.time(), UTC))
            hi_dt = min(
                publish_to, datetime.combine(hi + timedelta(days=1), datetime.min.time(), UTC)
            )
            rows = self._get(
                "/datasets/WINDFOR/stream",
                {"publishDateTimeFrom": _iso(lo_dt), "publishDateTimeTo": _iso(hi_dt)},
            )
            for row in rows:
                if row.get("generation") is None:
                    continue
                point = ForecastPoint(
                    publish_time=parse_time(row["publishTime"]),
                    start_time=parse_time(row["startTime"]),
                    generation=float(row["generation"]),
                )
                if publish_from <= point.publish_time < publish_to:
                    points[(point.publish_time, point.start_time)] = point
        return sorted(points.values(), key=lambda p: (p.publish_time, p.start_time))


def _newer(candidate: datetime | None, current: datetime | None) -> bool:
    if candidate is None:
        return False
    return current is None or candidate > current
