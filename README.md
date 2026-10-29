# Wind Forecast Monitor

A web app for a UK energy supplier's day-ahead trading team. It answers two questions:

1. **What does the latest wind forecast say at the moment we have to buy?** For a chosen delivery
   day *D* and decision time on *D-1*, it shows the most recent national wind forecast that had
   been published by then, an empirical uncertainty band, and (after the fact) the actual outturn.
2. **How much can we trust that forecast?** It backtests every day in scope and quantifies the
   error: overall, by time of day, by delivery day, by forecast horizon, and as a distribution.

Data: Elexon BMRS national wind **outturn** ([FUELHH], `fuelType = WIND`, half-hourly) and wind
**forecasts** ([WINDFOR], hourly, with `publishTime`). No other data is used.

**Live app:** https://z8f2k91.vercel.app/ (API docs: https://z8f2k91.vercel.app/docs)

[FUELHH]: https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/FUELHH/stream
[WINDFOR]: https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/WINDFOR/stream

---

## How it works

### Which forecast the trader would have seen

For delivery day *D* (a UK calendar day, 00:00–24:00 Europe/London) and decision time *T*
(UK local time on *D-1*, 09:00 by default and adjustable in the UI):

```
cutoff = (D - 1 day) at T, Europe/London -> UTC
for each target period t in D:
    forecast(t) = the WINDFOR value for t with the latest publishTime <= cutoff
```

Only data published by the cutoff is used, so the view is exactly what a trader could have
seen, with no look-ahead. The view also shows the **final forecast before delivery** (latest
publish at or before 00:00 on *D*) to show how the forecast moved after the decision.

### Accuracy metrics

`error = forecast − actual` (MW). Positive means over-forecast: less wind arrived than
expected, so the shortfall had to be bought elsewhere.

| Metric | Meaning |
|---|---|
| MAE | Mean absolute error, the typical miss in MW |
| nMAE | MAE ÷ mean actual output |
| RMSE | Penalises large misses more heavily |
| Bias | Mean signed error: systematic over- or under-forecasting |
| P90 \|error\| | 9 in 10 periods missed by less than this |
| P10 / P90 of error | Basis of the 80% band; *forecast − P90* is the "wind you can count on" level |

Forecasts are hourly and actuals half-hourly, so periods are scored where both exist (on the
hour). The band uses the empirical error distribution over the whole backtest period (an
in-sample pilot estimate; see [Limitations](#assumptions-and-limitations)).

**Error against horizon:** independent of the decision time. For each horizon *h* = 0…48 h, every
period is scored against the latest forecast published at least *h* hours before it. This
shows how much accuracy is gained by deciding later.

### Assumptions and limitations

- **Scope = purchase decisions made in January 2026.** Decisions are made on *D-1*, so decision
  days 1–31 Jan 2026 mean **delivery days 2 Jan – 1 Feb 2026**. Configurable through
  `DECISION_DATE_FROM` / `DECISION_DATE_TO`.
- **Decision time** defaults to 09:00 UK on *D-1*, ahead of the morning GB day-ahead auction
  gate closures. It is adjustable from 05:00 to 16:00 in the UI.
- Timestamps from Elexon are treated as UTC; delivery days and charts use Europe/London time.
- If a FUELHH period is re-published, the latest value is kept. Duplicate WINDFOR
  (publishTime, startTime) rows keep the last value.
- The uncertainty band comes from one month of history and is not conditioned on lead time or
  weather regime. A production version would condition it on both and use a rolling,
  out-of-sample window.

---

## Repository layout

```
.
├── backend/                    Python 3.12 · FastAPI
│   ├── app/
│   │   ├── main.py             App factory, routes (/api/*), serves the built React app
│   │   ├── config.py           Settings (env-overridable): date scope, decision time, paths
│   │   ├── elexon.py           Elexon BMRS client: FUELHH + WINDFOR stream, chunked, deduped
│   │   ├── models.py           Domain records (ActualPoint, ForecastPoint)
│   │   ├── repository.py       Loads data once: local snapshot first, else Elexon (then caches)
│   │   ├── analysis.py         Pure analysis core: forecast selection, pairing, error stats
│   │   ├── service.py          Use cases composing the analysis into API responses (memoised)
│   │   └── schemas.py          Pydantic response models (camelCase JSON, OpenAPI at /docs)
│   ├── scripts/fetch_data.py   Downloads the in-scope data into backend/data/ (snapshot)
│   ├── data/                   Snapshot location (wind_actuals.json, wind_forecasts.json)
│   ├── tests/                  pytest: analysis, Elexon client (mocked HTTP), API
│   ├── requirements*.txt
│   └── pyproject.toml          pytest + ruff config
├── frontend/                   React 19 · TypeScript · Vite · Recharts
│   ├── src/
│   │   ├── App.tsx             Shell: header, decision-time control, tabs
│   │   ├── pages/DayAheadPage.tsx   Forecast at decision time vs outturn, band, KPIs
│   │   ├── pages/AccuracyPage.tsx   Backtest: KPIs, takeaways, horizon/hour/day/histogram/scatter
│   │   ├── api.ts              Typed API client (mirrors backend schemas)
│   │   ├── insights.ts         Plain-language takeaways computed from the stats
│   │   ├── format.ts           UK-time and MW formatting helpers
│   │   ├── components/ui.tsx   Tile, card, tooltip and table-view components
│   │   └── *.test.ts           vitest unit tests
│   └── vite.config.ts          Dev server proxies /api to :8000
├── Dockerfile                  Multi-stage: build React, then a slim Python runtime serving both
├── docker-compose.yml          Local run of the production image (persists the data snapshot)
├── heroku.yml                  Heroku container-stack build
├── vercel.json, api/index.py   Vercel: static React build + FastAPI as a Python function
├── requirements.txt            Python deps for the Vercel function (points at backend/)
├── Makefile                    Common dev commands
└── .github/workflows/ci.yml    Lint, tests, frontend build, Docker build
```

### Design notes

- **One deployable.** FastAPI serves `/api/*` and the static React build on all other paths,
  so a single container runs on Heroku with no CORS or second service. On Vercel the same
  app runs as a serverless function behind the static build.
- **Pure core, thin edges.** `analysis.py` has no I/O and works on plain datetimes and floats,
  so it is unit-tested directly. `ForecastIndex` stores the vintages for each target, sorted by
  publish time, so "latest forecast as of *x*" is a binary search.
- **Data loading.** The data is historical, so it is fetched once. The app loads
  `backend/data/*.json` if present, otherwise it calls Elexon in 7-day chunks at start-up (in a
  background thread) and writes the snapshot. Until data is loaded the API returns `503` with a
  clear message, and the UI shows it.
- **Memoised results.** Day-ahead and accuracy responses depend only on the immutable dataset
  and the parameters, so they are cached per (date, decision time).

---

## Running it

### With Docker (recommended)

```bash
docker compose up --build
# open http://localhost:8000      (API docs: http://localhost:8000/docs)
```

On first start the container downloads the January 2026 data from Elexon and keeps it in the
`wind-data` volume.

### Local development

Requires Python 3.12+ and Node 22+.

```bash
make install        # backend venv + npm ci
make data           # optional: pre-download the Elexon snapshot into backend/data/
make dev-api        # FastAPI on http://localhost:8000 (auto-reload)
make dev-ui         # Vite on http://localhost:5173 (proxies /api to :8000)
make test           # pytest + vitest
make lint           # ruff + tsc
```

### Configuration (environment variables)

| Variable | Default | Purpose |
|---|---|---|
| `DECISION_DATE_FROM` / `DECISION_DATE_TO` | `2026-01-01` / `2026-01-31` | Decision days in scope |
| `DEFAULT_DECISION_TIME` | `09:00` | Default decision time on D-1 (UK) |
| `MAX_HORIZON_HOURS` | `48` | Longest horizon in the horizon analysis |
| `ELEXON_BASE_URL` | `https://data.elexon.co.uk/bmrs/api/v1` | Elexon Insights API |
| `DATA_DIR` | `backend/data` | Snapshot location |
| `PORT` | `8000` | HTTP port (set by Heroku) |

### API

| Endpoint | Description |
|---|---|
| `GET /api/health` | Liveness and whether data is loaded |
| `GET /api/meta` | Scope, defaults, data source and counts |
| `GET /api/day-ahead?delivery_date=2026-01-15&decision_time=09:00` | Decision-time forecast vs actual for one day |
| `GET /api/accuracy?decision_time=09:00` | Backtest statistics for the whole period |

Interactive OpenAPI docs are at `/docs`.

---

## Deploy

### Step 0: bundle the data snapshot (required for Vercel, recommended for Heroku)

Serverless functions have a read-only filesystem and short time limits, so commit the data
instead of fetching it on every cold start:

```bash
make install && make data      # writes backend/data/wind_actuals.json + wind_forecasts.json
git add backend/data/*.json && git commit -m "Add Jan 2026 wind data snapshot" && git push
```

### Vercel

`vercel.json` builds the React app as static files and runs FastAPI as a Python function
(`api/index.py`). `/api/*`, `/docs` and `/openapi.json` go to the function; every other path
serves the React app.

- **Dashboard:** vercel.com → *Add New… → Project* → import this GitHub repo → *Deploy*. No
  settings to change, because `vercel.json` sets everything.
- **CLI:** `npm i -g vercel && vercel --prod` from the repo root.

### Heroku (Docker)

```bash
heroku create <app-name>
heroku stack:set container -a <app-name>
git push heroku <branch>:main
heroku open -a <app-name>
```

`heroku.yml` builds the root `Dockerfile`, and the app listens on `$PORT`.

---

## Use of AI tools

This project was built with **Claude Code** (Anthropic), an AI coding assistant. It was used for
design, implementation of the backend, frontend, tests and Docker setup, and for drafting this
README.
