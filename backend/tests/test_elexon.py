from __future__ import annotations

from datetime import date

import httpx

from app.elexon import ElexonClient, _date_chunks, parse_time

from .conftest import utc


def test_parse_time_handles_z_suffix():
    assert parse_time("2026-01-01T00:30:00Z") == utc(2026, 1, 1, 0, 30)


def test_date_chunks_cover_range_without_overlap():
    chunks = list(_date_chunks(date(2026, 1, 1), date(2026, 1, 16)))
    assert chunks[0] == (date(2026, 1, 1), date(2026, 1, 7))
    assert chunks[-1] == (date(2026, 1, 15), date(2026, 1, 16))


def _client(handler) -> tuple[ElexonClient, list[httpx.Request]]:
    seen: list[httpx.Request] = []

    def wrapped(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return handler(request)

    http = httpx.Client(transport=httpx.MockTransport(wrapped))
    return ElexonClient("https://example.test/api", http=http), seen


def test_fetch_wind_actuals_filters_and_dedupes():
    rows = [
        {
            "fuelType": "WIND",
            "startTime": "2026-01-02T00:00:00Z",
            "generation": 100,
            "publishTime": "2026-01-02T00:30:00Z",
        },
        {
            "fuelType": "WIND",
            "startTime": "2026-01-02T00:00:00Z",
            "generation": 120,
            "publishTime": "2026-01-02T01:00:00Z",
        },
        {
            "fuelType": "CCGT",
            "startTime": "2026-01-02T00:00:00Z",
            "generation": 9999,
            "publishTime": "2026-01-02T00:30:00Z",
        },
    ]
    client, seen = _client(lambda r: httpx.Response(200, json=rows))
    actuals = client.fetch_wind_actuals(date(2026, 1, 2), date(2026, 1, 2))
    assert [(a.start_time, a.generation) for a in actuals] == [(utc(2026, 1, 2), 120.0)]
    assert seen[0].url.path == "/api/datasets/FUELHH/stream"
    assert seen[0].url.params["fuelType"] == "WIND"


def test_fetch_wind_forecasts_chunks_requests_and_clips_publish_window():
    rows = [
        {
            "publishTime": "2026-01-01T03:00:00Z",
            "startTime": "2026-01-01T12:00:00Z",
            "generation": 7000,
        },
        {
            "publishTime": "2025-12-31T23:00:00Z",
            "startTime": "2026-01-01T12:00:00Z",
            "generation": 6000,
        },
    ]
    client, seen = _client(lambda r: httpx.Response(200, json={"data": rows}))
    forecasts = client.fetch_wind_forecasts(utc(2026, 1, 1), utc(2026, 1, 10))
    assert len(seen) == 2  # 9 days => two 7-day chunks
    assert seen[0].url.params["publishDateTimeFrom"] == "2026-01-01T00:00:00Z"
    assert seen[-1].url.params["publishDateTimeTo"] == "2026-01-10T00:00:00Z"
    assert [f.generation for f in forecasts] == [7000.0]
