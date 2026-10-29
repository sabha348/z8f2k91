"""Loads the wind dataset once (local JSON snapshot, else the Elexon API) and keeps it in memory."""

from __future__ import annotations

import json
import logging
import threading
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from .analysis import ForecastIndex, local_midnight
from .config import Settings
from .elexon import ElexonClient, parse_time
from .models import ActualPoint, ForecastPoint

log = logging.getLogger(__name__)

ACTUALS_FILE = "wind_actuals.json"
FORECASTS_FILE = "wind_forecasts.json"


@dataclass(frozen=True)
class Dataset:
    actuals: dict[datetime, float]  # start_time -> MW
    forecasts: ForecastIndex
    fetched_at: datetime
    source: str  # "snapshot" or "elexon-api"


@dataclass(frozen=True)
class DataWindow:
    delivery_from: date
    delivery_to: date
    actuals_from: date
    actuals_to: date
    forecasts_publish_from: datetime
    forecasts_publish_to: datetime


def data_window(settings: Settings) -> DataWindow:
    """Data needed to evaluate decisions made on D-1 for every delivery day D in scope."""
    delivery_from = settings.decision_date_from + timedelta(days=1)
    delivery_to = settings.decision_date_to + timedelta(days=1)
    # Horizon analysis looks up to max_horizon_hours before the first delivery period.
    lookback = timedelta(hours=settings.max_horizon_hours) + timedelta(days=1)
    return DataWindow(
        delivery_from=delivery_from,
        delivery_to=delivery_to,
        actuals_from=delivery_from,
        actuals_to=delivery_to,
        forecasts_publish_from=local_midnight(delivery_from) - lookback,
        forecasts_publish_to=local_midnight(delivery_to + timedelta(days=1)),
    )


def _dump(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(rows))
    tmp.replace(path)


def save_snapshot(
    data_dir: Path, actuals: list[ActualPoint], forecasts: list[ForecastPoint]
) -> None:
    _dump(
        data_dir / ACTUALS_FILE,
        [{"startTime": a.start_time.isoformat(), "generation": a.generation} for a in actuals],
    )
    _dump(
        data_dir / FORECASTS_FILE,
        [
            {
                "publishTime": f.publish_time.isoformat(),
                "startTime": f.start_time.isoformat(),
                "generation": f.generation,
            }
            for f in forecasts
        ],
    )


def load_snapshot(data_dir: Path) -> tuple[list[ActualPoint], list[ForecastPoint]] | None:
    actuals_path, forecasts_path = data_dir / ACTUALS_FILE, data_dir / FORECASTS_FILE
    if not (actuals_path.exists() and forecasts_path.exists()):
        return None
    actuals = [
        ActualPoint(start_time=parse_time(r["startTime"]), generation=float(r["generation"]))
        for r in json.loads(actuals_path.read_text())
    ]
    forecasts = [
        ForecastPoint(
            publish_time=parse_time(r["publishTime"]),
            start_time=parse_time(r["startTime"]),
            generation=float(r["generation"]),
        )
        for r in json.loads(forecasts_path.read_text())
    ]
    return actuals, forecasts


def fetch_from_elexon(
    settings: Settings, client: ElexonClient | None = None
) -> tuple[list[ActualPoint], list[ForecastPoint]]:
    client = client or ElexonClient(settings.elexon_base_url, settings.request_timeout_s)
    window = data_window(settings)
    actuals = client.fetch_wind_actuals(window.actuals_from, window.actuals_to)
    forecasts = client.fetch_wind_forecasts(
        window.forecasts_publish_from, window.forecasts_publish_to
    )
    log.info("Fetched %d actuals and %d forecast points", len(actuals), len(forecasts))
    return actuals, forecasts


def build_dataset(
    actuals: list[ActualPoint], forecasts: list[ForecastPoint], source: str
) -> Dataset:
    return Dataset(
        actuals={a.start_time: a.generation for a in actuals},
        forecasts=ForecastIndex(forecasts),
        fetched_at=datetime.now(UTC),
        source=source,
    )


class Repository:
    """Lazily loads the dataset once; thread-safe so concurrent first requests fetch only once."""

    def __init__(self, settings: Settings, client: ElexonClient | None = None):
        self._settings = settings
        self._client = client
        self._lock = threading.Lock()
        self._dataset: Dataset | None = None

    @property
    def loaded(self) -> bool:
        return self._dataset is not None

    def get(self) -> Dataset:
        if self._dataset is None:
            with self._lock:
                if self._dataset is None:
                    self._dataset = self._load()
        return self._dataset

    def _load(self) -> Dataset:
        snapshot = load_snapshot(self._settings.data_dir)
        if snapshot is not None:
            log.info("Loaded wind data snapshot from %s", self._settings.data_dir)
            return build_dataset(*snapshot, source="snapshot")
        actuals, forecasts = fetch_from_elexon(self._settings, self._client)
        try:
            save_snapshot(self._settings.data_dir, actuals, forecasts)
        except OSError:  # read-only filesystem: keep serving from memory
            log.warning("Could not write snapshot to %s", self._settings.data_dir, exc_info=True)
        return build_dataset(actuals, forecasts, source="elexon-api")
