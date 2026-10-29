import { useEffect, useState } from "react";
import { api } from "./api";
import { Status } from "./components/ui";
import { fmtDateTime, timeOptions } from "./format";
import { AccuracyPage } from "./pages/AccuracyPage";
import { DayAheadPage } from "./pages/DayAheadPage";
import { useFetch } from "./useFetch";

type Tab = "day-ahead" | "accuracy";

export default function App() {
  const meta = useFetch(() => api.meta(), []);
  const [tab, setTab] = useState<Tab>("day-ahead");
  const [decisionTime, setDecisionTime] = useState<string | null>(null);
  const [deliveryDate, setDeliveryDate] = useState<string | null>(null);

  useEffect(() => {
    if (meta.status === "ready") {
      setDecisionTime((t) => t ?? meta.data.defaultDecisionTime);
      setDeliveryDate((d) => d ?? meta.data.deliveryDateFrom);
    }
  }, [meta]);

  return (
    <div className="app">
      <header className="header">
        <div className="brand">
          <img src="/favicon.svg" alt="" />
          <div>
            <h1>Wind Forecast Monitor</h1>
            <p>GB national wind generation, for day-ahead purchasing decisions</p>
          </div>
        </div>
        {decisionTime && (
          <div className="controls">
            <label className="field">
              Decision time on D-1 (UK)
              <select value={decisionTime} onChange={(e) => setDecisionTime(e.target.value)}>
                {timeOptions().map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>
            </label>
          </div>
        )}
      </header>

      <nav className="tabs" role="tablist">
        <button className="tab" role="tab" aria-selected={tab === "day-ahead"} onClick={() => setTab("day-ahead")}>
          Day-ahead view
        </button>
        <button className="tab" role="tab" aria-selected={tab === "accuracy"} onClick={() => setTab("accuracy")}>
          Forecast accuracy
        </button>
      </nav>

      {meta.status === "loading" && <Status>Loading wind data from Elexon…</Status>}
      {meta.status === "error" && <Status error>Could not reach the data service: {meta.message}</Status>}
      {meta.status === "ready" && decisionTime && deliveryDate && (
        <main>
          {tab === "day-ahead" ? (
            <DayAheadPage
              meta={meta.data}
              decisionTime={decisionTime}
              deliveryDate={deliveryDate}
              onDeliveryDateChange={setDeliveryDate}
            />
          ) : (
            <AccuracyPage decisionTime={decisionTime} />
          )}
          <footer className="footer">
            Data: Elexon BMRS, FUELHH (wind outturn, half-hourly) and WINDFOR (wind forecasts, hourly), covering
            purchase decisions from {meta.data.decisionDateFrom} to {meta.data.decisionDateTo}.{" "}
            {meta.data.forecastRuns.toLocaleString("en-GB")} forecast runs, {meta.data.actualPoints.toLocaleString("en-GB")}{" "}
            outturn periods. Loaded {fmtDateTime(meta.data.dataLoadedAt)} ({meta.data.dataSource}).{" "}
            <a href="/docs">API docs</a>
          </footer>
        </main>
      )}
    </div>
  );
}
