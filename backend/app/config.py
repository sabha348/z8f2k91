"""Runtime configuration, overridable through environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import date, time
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent


def _date(name: str, default: str) -> date:
    return date.fromisoformat(os.getenv(name, default))


@dataclass(frozen=True)
class Settings:
    elexon_base_url: str = field(
        default_factory=lambda: os.getenv(
            "ELEXON_BASE_URL", "https://data.elexon.co.uk/bmrs/api/v1"
        )
    )
    # Purchase decisions made on D-1 between these dates (inclusive) are in scope.
    # Decisions in January 2026 => delivery days 2 Jan .. 1 Feb 2026.
    decision_date_from: date = field(
        default_factory=lambda: _date("DECISION_DATE_FROM", "2026-01-01")
    )
    decision_date_to: date = field(default_factory=lambda: _date("DECISION_DATE_TO", "2026-01-31"))
    # Default decision time (UK local) on D-1; adjustable per request.
    default_decision_time: time = field(
        default_factory=lambda: time.fromisoformat(os.getenv("DEFAULT_DECISION_TIME", "09:00"))
    )
    # Longest forecast horizon analysed (WINDFOR covers roughly two days ahead).
    max_horizon_hours: int = field(
        default_factory=lambda: int(os.getenv("MAX_HORIZON_HOURS", "48"))
    )
    data_dir: Path = field(
        default_factory=lambda: Path(os.getenv("DATA_DIR", str(BACKEND_DIR / "data")))
    )
    static_dir: Path = field(
        default_factory=lambda: Path(os.getenv("STATIC_DIR", str(BACKEND_DIR / "static")))
    )
    request_timeout_s: float = field(
        default_factory=lambda: float(os.getenv("ELEXON_TIMEOUT_S", "60"))
    )


settings = Settings()
