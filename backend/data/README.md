Local snapshot of the Elexon wind data (`wind_actuals.json`, `wind_forecasts.json`).

Create it with `cd backend && python -m scripts.fetch_data`. When the files are present the app
loads them at start-up; otherwise it downloads from the Elexon API on first start and writes them here.
