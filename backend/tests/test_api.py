from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.repository import Repository, save_snapshot


@pytest.fixture
def client(small_settings, synthetic_points):
    save_snapshot(small_settings.data_dir, *synthetic_points)
    app = create_app(small_settings, Repository(small_settings))
    with TestClient(app) as c:
        yield c


def test_health(client):
    assert client.get("/api/health").json()["status"] == "ok"


def test_meta(client):
    body = client.get("/api/meta").json()
    assert body["deliveryDateFrom"] == "2026-01-02"
    assert body["deliveryDateTo"] == "2026-01-03"
    assert body["defaultDecisionTime"] == "09:00"
    assert body["dataSource"] == "snapshot"


def test_day_ahead_uses_forecast_available_at_decision_time(client):
    body = client.get("/api/day-ahead", params={"delivery_date": "2026-01-03"}).json()
    assert body["decisionCutoff"] == "2026-01-02T09:00:00Z"
    assert body["forecastPublishTime"] == "2026-01-02T06:00:00Z"
    assert len(body["points"]) == 48  # half-hourly actuals, hourly forecasts
    scored = [p for p in body["points"] if p["forecast"] is not None]
    assert all(p["bandLow"] <= p["bandHigh"] for p in scored)
    # Synthetic forecasts always over-predict, so the empirical band sits below the forecast.
    assert all(p["bandHigh"] < p["forecast"] for p in scored)
    assert body["accuracy"]["bias"] > 0  # synthetic forecasts over-predict
    # The final run at or before the start of delivery (00:00 UK) is also tracked.
    assert body["finalForecastPublishTime"] == "2026-01-03T00:00:00Z"


def test_later_decision_time_uses_newer_run(client):
    early = client.get(
        "/api/day-ahead", params={"delivery_date": "2026-01-03", "decision_time": "07:00"}
    ).json()
    late = client.get(
        "/api/day-ahead", params={"delivery_date": "2026-01-03", "decision_time": "13:00"}
    ).json()
    assert early["forecastPublishTime"] < late["forecastPublishTime"]
    assert late["accuracy"]["mae"] < early["accuracy"]["mae"]


def test_day_ahead_validates_inputs(client):
    assert client.get("/api/day-ahead", params={"delivery_date": "2026-03-01"}).status_code == 422
    r = client.get("/api/day-ahead", params={"delivery_date": "2026-01-03", "decision_time": "9am"})
    assert r.status_code == 422


def test_accuracy(client):
    body = client.get("/api/accuracy").json()
    assert body["overall"]["count"] > 0
    assert [d["deliveryDate"] for d in body["byDay"]] == ["2026-01-02", "2026-01-03"]
    assert sum(b["count"] for b in body["errorHistogram"]) == body["overall"]["count"]
    maes = [h["mae"] for h in body["byHorizon"]]
    assert maes == sorted(maes)  # synthetic error grows with lead time
    assert body["byHorizon"][0]["horizonHours"] == 0
