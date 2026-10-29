# Demo video script

You record yourself (camera + voice) reading this script. A screen recording of the live app
(https://z8f2k91.vercel.app) is then made to match your timing, with you shown in a corner, so it
looks as if you are walking through the app.

## How to record

1. **Two recordings, one per part:** `part1.mp4` (client) and `part2.mp4` (tech lead).
   Landscape (16:9), 720p or 1080p, phone or laptop camera. Quiet room, face well lit, look at
   the camera.
2. **Read the segments in order.** Don't read the numbers or the *[Screen]* lines aloud.
3. **After each segment, stay silent for 3 full seconds** (count "one-thousand, two-thousand,
   three-thousand" in your head). This is how your video is lined up with the screen, and the
   long pauses are trimmed out afterwards. Keep natural pauses inside a segment short (under 1 s).
4. **If you stumble,** stay silent for 3 seconds and restart *that segment* from its beginning.
   Then say which segment number was repeated when you send the files.
5. Speak a little slower than normal. Each part should come out at about 4 minutes, and must be
   under 5.
6. Before you start speaking, stay silent for 2 seconds after pressing record. Do the same at the
   very end, before you stop.

All figures below are from the live app (real Elexon data, decision time 09:00 unless stated).

---

## Part 1: Client presentation (about 4 minutes)

**1.** *[Screen: title card]*
> Hello everyone. Over the past few weeks we ran a pilot for your day-ahead trading team. I'd like to show you what we built, and what it tells us about wind forecasts.

**2.** *[Screen: the app opens]*
> Every morning your team buys tomorrow's power on the day-ahead market. What you need to buy is your demand, minus whatever wind will deliver. So the wind forecast you see at that moment decides how much you buy, and how much risk you carry.

**3.** *[Screen: the two tabs]*
> The portal answers two questions. First, what did the latest forecast say when you had to decide? Second, how far can you trust it?

**4.** *[Screen: decision time dropdown]*
> Everything starts from your decision time. By default that's nine a.m. the day before delivery. The portal only uses forecasts published by then, so you see exactly what your traders saw. No hindsight.

**5.** *[Screen: delivery day set to 19 January; banner]*
> Let's take the nineteenth of January. The banner shows exactly which forecast run was used. Here it's the run published at seven thirty that morning, between seventeen and forty hours ahead of delivery.

**6.** *[Screen: cursor runs along the chart]*
> The blue line is the forecast at decision time. The shaded band is the range the actual wind landed in eight times out of ten. The orange line is what actually happened. On this day the forecast was close: it missed by under seven hundred megawatts on average.

**7.** *[Screen: the four tiles]*
> The tiles give you the planning numbers. Expected wind of about five point eight gigawatts. And "wind you can count on", the level beaten in nine periods out of ten, of about one point six gigawatts. Buying against that firm level is a simple way to protect yourself against a shortfall.

**8.** *[Screen: jump to 28 January]*
> Now a very different day: the twenty-eighth of January. The forecast at nine a.m. expected about eleven gigawatts. Only about five point eight arrived. That's a miss of over five gigawatts, all day long, so a large volume had to be bought at short notice.

**9.** *[Screen: "final forecast before delivery" switched on]*
> Turning on the final forecast before delivery shows that later forecasts did come down, but only part of the way. Even the cautious "count on" level was too high on this day. That's exactly the kind of day a risk buffer is for.

**10.** *[Screen: data table opens]*
> Every chart also has a data table behind it, for anyone who wants the detail.

**11.** *[Screen: Forecast accuracy tab]*
> The second question: how far can you trust the forecast? This tab backtests every delivery day in January. At a nine a.m. decision, the forecast missed by about two thousand megawatts on average. That's eighteen percent of average wind output.

**12.** *[Screen: bias tile, then key takeaways]*
> The most important finding is the bias. Forecasts ran high by about one point seven gigawatts on average, and the gap gets bigger when more wind is forecast. In other words, the forecast systematically promised more wind than arrived. That's worth investigating with the forecast provider, and in the meantime building into your buying.

**13.** *[Screen: horizon chart]*
> This chart shows how error grows with lead time. On the freshest forecast it's about one point seven gigawatts. Two days ahead it's about two point three. So a fresher forecast helps, but it doesn't remove the bias.

**14.** *[Screen: time of day and daily charts]*
> Errors also vary by time of day. They're largest in the early morning, around five a.m. And the daily chart picks out the difficult days: the eleventh, twelfth, twenty-first and twenty-eighth of January.

**15.** *[Screen: decision time changed to 14:00]*
> You can test your own process too. Moving the decision from nine a.m. to two p.m. cuts the average error from about two thousand and twenty to about eighteen ninety megawatts. It's a modest gain, and the portal lets you weigh it against your trading timetable.

**16.** *[Screen: closing card]*
> As next steps, we suggest adding your demand forecast to show the exact volume to buy, correcting for the forecast bias, and making the uncertainty band depend on lead time and weather. Thank you.

---

## Part 2: Technical review (about 4 minutes)

**1.** *[Screen: title card]*
> Now the technical walkthrough. I'll cover the architecture, data handling, the core analysis, the API, the frontend, and how it's tested and deployed.

**2.** *[Screen: README]*
> The README is the entry point. It explains the method and the assumptions, lists every file and directory, and covers how to run and deploy the app.

**3.** *[Screen: architecture diagram]*
> The architecture is deliberately simple. A Python FastAPI backend fetches from the Elexon API. A pure analysis core does the maths. A React and TypeScript frontend shows the results. It runs as one Docker image, and on Vercel as a static site plus a Python function.

**4.** *[Screen: elexon.py]*
> The Elexon client calls the FUELHH stream, filtered to wind, for actuals, and the WINDFOR stream for forecasts, in seven-day chunks. Timestamps are parsed to UTC, and if a period was published twice, the latest version wins.

**5.** *[Screen: repository.py]*
> The data is historical, so it's loaded once. A JSON snapshot is committed with the code, and if it's missing the app fetches from Elexon and caches it. A lock makes sure concurrent first requests fetch only once.

**6.** *[Screen: analysis.py: decision cutoff and ForecastIndex]*
> The heart of the app is the analysis module, which does no input or output. The decision cutoff is the day before delivery, at the decision time in UK local time, converted to UTC. ForecastIndex keeps every forecast run for each target time, sorted by publish time, so finding the latest forecast as of the cutoff is a binary search. That's what guarantees no look-ahead.

**7.** *[Screen: error stats and error band]*
> Error is forecast minus actual, so a positive number means a shortfall. The statistics are mean absolute error, root mean square error, bias, normalised error and percentiles. The uncertainty band comes from the tenth and ninetieth percentiles of the error.

**8.** *[Screen: decision pairs and horizon pairs]*
> Decision pairs match every delivery period with the forecast known at the cutoff. Horizon pairs use the latest forecast published at least h hours earlier, which drives the horizon chart.

**9.** *[Screen: service.py]*
> The service layer combines these functions into API responses. The data never changes, so results are memoised per set of parameters.

**10.** *[Screen: main.py]*
> FastAPI exposes three typed endpoints: meta, day-ahead and accuracy. Inputs are validated, and if data isn't ready the API returns a clear 503. The same app can also serve the React build, so it deploys as a single service.

**11.** *[Screen: raw JSON response from the live API]*
> This is a raw response from the live API. Pydantic schemas produce camelCase JSON, and FastAPI generates OpenAPI documentation automatically.

**12.** *[Screen: frontend api.ts and insights.ts]*
> On the frontend, a typed API client mirrors the backend schemas. The takeaways are computed from the statistics, not hard-coded. All times are shown in UK local time.

**13.** *[Screen: tests]*
> For testing, pytest covers timezone edge cases including British summer time, the no-look-ahead rule, the statistics, the Elexon client with mocked HTTP, and the API end to end. Vitest covers formatting and the takeaways.

**14.** *[Screen: CI, Dockerfile, vercel.json]*
> Continuous integration runs linting, both test suites, the frontend build and the Docker build. The Dockerfile is multi-stage: Node builds the React app, and a slim Python image serves everything. vercel.json configures the Vercel deployment.

**15.** *[Screen: README assumptions]*
> Finally, the key assumptions. Decisions made in January mean delivery days from the second of January to the first of February. Hourly forecasts are scored against actuals on the hour. The band is estimated in-sample. Next, I'd make it out-of-sample and dependent on lead time.

**16.** *[Screen: closing card]*
> Thanks for reviewing. I'm happy to take any questions.
