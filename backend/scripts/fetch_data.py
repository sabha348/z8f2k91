"""Download the in-scope Elexon wind data into a local snapshot (backend/data/*.json).

Usage (from backend/):  python -m scripts.fetch_data
The app loads this snapshot on start-up instead of calling Elexon, which keeps the deployed
app fast and independent of Elexon availability. Without it, the app fetches on first start.
"""

from __future__ import annotations

import logging

from app.config import settings
from app.repository import data_window, fetch_from_elexon, save_snapshot


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    window = data_window(settings)
    logging.info("Data window: %s", window)
    actuals, forecasts = fetch_from_elexon(settings)
    save_snapshot(settings.data_dir, actuals, forecasts)
    logging.info(
        "Saved %d actuals and %d forecasts to %s", len(actuals), len(forecasts), settings.data_dir
    )


if __name__ == "__main__":
    main()
