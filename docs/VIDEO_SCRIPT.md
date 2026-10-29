# Demo video script (≤ 10 minutes)

Record the screen with your voice over it (e.g. OBS, Loom or QuickTime), upload to YouTube as
**Unlisted**. Fill each `[…]` from the live app on real data. The figures come straight from
the KPI tiles and the "Key takeaways" card, so read them off the screen instead of guessing.

Target length: Part 1 ≈ 4:30, Part 2 ≈ 4:30.

---

## Part 1: Customer pitch (≤ 5 min)

Audience: the day-ahead trading team. Goal: show the pilot answers their two questions.

| Time | On screen | Say |
|---|---|---|
| 0:00 | App home | "Every morning your team buys tomorrow's power before the day-ahead auction closes. The gap you buy is demand minus what wind will deliver, so the quality of the wind forecast drives the cost. In this pilot we answered two questions: what did the latest forecast say when you had to decide, and how far can you trust it?" |
| 0:30 | Decision-time dropdown (09:00) | "You set when your team makes the decision, 09:00 the day before by default. Everything shown uses only forecasts that were published by then, so it's exactly what you would have seen, with no hindsight." |
| 0:50 | Day-ahead view, pick a calm day `[date]` | "Blue is the forecast at decision time, the shaded band is the range the actual wind fell in 8 times out of 10, and orange is what actually happened. The banner names the exact forecast run used and how far ahead it was." |
| 1:30 | Tiles | "For planning: expected wind `[x] GW`, and 'wind you can count on' `[y] GW`, the level beaten in 9 of 10 periods historically. Buying against that level, not the central forecast, is a simple way to manage shortfall risk." |
| 2:00 | Step to a bad day `[date]`, tick "Final forecast before delivery" | "On days like this the forecast moved a lot after the decision. The dashed line is the last forecast before delivery. It shows the risk you are carrying from the morning decision." |
| 2:40 | Forecast accuracy tab, KPIs | "Over January the 09:00 forecast missed by `[MAE]` on average, which is `[nMAE]` of output. 9 in 10 periods were within `[P90]`. Bias was `[bias]`, so forecasts ran `[high/low]`." |
| 3:20 | Horizon chart | "Error grows with lead time, from `[x]` on the freshest forecast to `[y]` two days out. This puts a number on the value of deciding later or of trading again intraday." |
| 3:50 | Hour-of-day + daily charts | "The largest errors fall around `[hour]`, and these days stand out: `[dates]`. That is where a risk buffer matters most." |
| 4:15 | Back to top | "Next steps: add demand to show the residual you need to buy directly, condition the band on lead time and weather, and roll it out to live data. Thank you." |

---

## Part 2: Tech-lead review (≤ 5 min)

| Time | On screen | Say |
|---|---|---|
| 0:00 | README layout | "React + TypeScript frontend, FastAPI backend, one Docker image. It's deployed on Vercel: the static build plus FastAPI as a Python function. Heroku runs the same Dockerfile." |
| 0:30 | `backend/app/elexon.py` | "The Elexon client calls the FUELHH stream, filtered to WIND, and the WINDFOR stream by publish time, in 7-day chunks. It dedupes re-published rows and parses everything to UTC." |
| 1:00 | `repository.py`, `scripts/fetch_data.py` | "The data is historical, so it's loaded once: a committed JSON snapshot first, otherwise Elexon, then cached. Load failures return a 503 with a clear message instead of crashing." |
| 1:30 | `analysis.py`: `decision_cutoff`, `ForecastIndex.latest_as_of` | "The core has no I/O. Decision cutoff is D-1 at the decision time in Europe/London, converted to UTC. ForecastIndex keeps the runs for each target sorted by publish time, so 'latest as of the cutoff' is a binary search. That's the no-look-ahead guarantee." |
| 2:15 | `error_stats`, `horizon_pairs`, `error_band` | "Error is forecast minus actual. Stats are MAE, RMSE, bias, nMAE and percentiles. The band inverts the P10/P90 of the error. The horizon curve scores each period against the latest forecast at least h hours old." |
| 2:50 | `service.py`, `schemas.py`, `/docs` | "The service layer composes the core into responses, memoised per parameter set. Pydantic schemas give camelCase JSON and OpenAPI docs." |
| 3:20 | `frontend/src` | "The frontend has a typed API client that mirrors the schemas, two pages, small shared UI components, and takeaways computed from the stats, not hard-coded. Times are shown in UK local time." |
| 3:50 | `tests/`, CI workflow | "pytest covers timezone and BST edges, the no-look-ahead rule, the stats maths, the client with mocked HTTP, and the API. vitest covers formatting and takeaways. CI runs ruff, tests, the build and the Docker build." |
| 4:20 | README assumptions | "Assumptions: January decisions mean delivery 2 Jan – 1 Feb. Hourly forecasts are scored against half-hourly actuals on the hour. The band is in-sample. Next, I'd make the band out-of-sample and conditioned on lead time." |
