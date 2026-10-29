import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api, type Accuracy } from "../api";
import { Card, StatTile, Status, TableView, TooltipBox } from "../components/ui";
import { fmtDay, fmtMw, fmtPct, fmtSignedMw } from "../format";
import { accuracyInsights } from "../insights";
import { useFetch } from "../useFetch";

const AXIS = { stroke: "var(--axis)", tickLine: false } as const;
const mw = (v: number) => v.toLocaleString("en-GB");

export function AccuracyPage({ decisionTime }: { decisionTime: string }) {
  const state = useFetch(() => api.accuracy(decisionTime), [decisionTime]);
  if (state.status === "loading") return <Status>Crunching a month of forecasts…</Status>;
  if (state.status === "error") return <Status error>Could not load accuracy: {state.message}</Status>;
  return <AccuracyView acc={state.data} />;
}

function AccuracyView({ acc }: { acc: Accuracy }) {
  const o = acc.overall;
  const insights = accuracyInsights(acc);
  const histogram = acc.errorHistogram.map((b) => ({ ...b, mid: (b.lower + b.upper) / 2 }));
  const maxMw = Math.ceil(Math.max(1, ...acc.scatter.flatMap((p) => [p.forecast, p.actual])) / 5000) * 5000;

  return (
    <>
      <div className="banner">
        Backtest of every delivery day from <strong>{fmtDay(acc.deliveryDateFrom)}</strong> to{" "}
        <strong>{fmtDay(acc.deliveryDateTo)}</strong>, using only the forecast that was available at{" "}
        <strong>{acc.decisionTime}</strong> UK time the day before
        {acc.meanLeadHours !== null && <> (on average {acc.meanLeadHours.toFixed(0)} h ahead)</>}. Error = forecast − actual.
      </div>

      <div className="tiles">
        <StatTile label="Mean absolute error" value={fmtMw(o?.mae)} sub={`${fmtPct(o?.nmae)} of mean output`} />
        <StatTile label="Root mean square error" value={fmtMw(o?.rmse)} sub="penalises large misses" />
        <StatTile label="Bias" value={fmtSignedMw(o?.bias)} sub={o?.bias != null && o.bias > 0 ? "forecasts ran high" : "forecasts ran low"} />
        <StatTile label="90th percentile |error|" value={fmtMw(o?.p90AbsError)} sub={`worst ${fmtMw(o?.maxAbsError)}`} />
        <StatTile label="Periods evaluated" value={o?.count.toLocaleString("en-GB") ?? "0"} sub="hourly forecast points" />
      </div>

      {insights.length > 0 && (
        <Card title="Key takeaways">
          <ul className="insights">
            {insights.map((t) => (
              <li key={t}>{t}</li>
            ))}
          </ul>
        </Card>
      )}

      <Card
        title="How error grows with forecast horizon"
        subtitle="Error in MW. For each horizon h, every period is scored against the latest forecast published at least h hours earlier. This does not depend on the decision time."
      >
        <div className="legend">
          <span><i className="key-line" style={{ borderColor: "var(--series-forecast)" }} /> Mean absolute error</span>
          <span><i className="key-line" style={{ borderColor: "var(--series-actual)" }} /> 90th percentile |error|</span>
        </div>
        <div style={{ height: 300 }}>
          <ResponsiveContainer>
            <LineChart data={acc.byHorizon} margin={{ top: 8, right: 8, bottom: 16, left: 0 }}>
              <CartesianGrid vertical={false} />
              <XAxis dataKey="horizonHours" {...AXIS} label={{ value: "Horizon (hours ahead)", position: "insideBottom", dy: 14 }} />
              <YAxis {...AXIS} axisLine={false} width={56} tickFormatter={mw} />
              <Tooltip
                cursor={{ stroke: "var(--axis)" }}
                content={({ active, payload }) => {
                  if (!active || !payload?.length) return null;
                  const h = payload[0].payload as Accuracy["byHorizon"][number];
                  return (
                    <TooltipBox
                      title={`≥ ${h.horizonHours} h ahead (avg lead ${h.meanLeadHours.toFixed(1)} h)`}
                      rows={[
                        { name: "MAE", value: fmtMw(h.mae), color: "var(--series-forecast)" },
                        { name: "P90 |error|", value: fmtMw(h.p90AbsError), color: "var(--series-actual)" },
                        { name: "bias", value: fmtSignedMw(h.bias) },
                      ]}
                    />
                  );
                }}
              />
              <Line dataKey="mae" stroke="var(--series-forecast)" strokeWidth={2} dot={false} isAnimationActive={false} />
              <Line dataKey="p90AbsError" stroke="var(--series-actual)" strokeWidth={2} dot={false} isAnimationActive={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
        <TableView
          headers={["Horizon (h)", "Avg lead (h)", "MAE", "RMSE", "Bias", "P90 |error|", "Periods"]}
          rows={acc.byHorizon.map((h) => [
            h.horizonHours,
            h.meanLeadHours.toFixed(1),
            fmtMw(h.mae),
            fmtMw(h.rmse),
            fmtSignedMw(h.bias),
            fmtMw(h.p90AbsError),
            h.count,
          ])}
        />
      </Card>

      <div className="grid-2">
        <Card title="Error by time of day" subtitle="Mean absolute error (MW) of the decision-time forecast, by delivery hour (UK).">
          <div style={{ height: 260 }}>
            <ResponsiveContainer>
              <BarChart data={acc.byHour} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
                <CartesianGrid vertical={false} />
                <XAxis dataKey="hour" {...AXIS} tickFormatter={(h: number) => `${String(h).padStart(2, "0")}`} interval={2} />
                <YAxis {...AXIS} axisLine={false} width={56} tickFormatter={mw} />
                <Tooltip
                  cursor={{ fill: "var(--grid)" }}
                  content={({ active, payload }) => {
                    if (!active || !payload?.length) return null;
                    const h = payload[0].payload as Accuracy["byHour"][number];
                    return (
                      <TooltipBox
                        title={`${String(h.hour).padStart(2, "0")}:00 – ${String(h.hour).padStart(2, "0")}:59`}
                        rows={[
                          { name: "MAE", value: fmtMw(h.mae) },
                          { name: "bias", value: fmtSignedMw(h.bias) },
                          { name: "80% error range", value: `${fmtSignedMw(h.errorP10)} to ${fmtSignedMw(h.errorP90)}` },
                        ]}
                      />
                    );
                  }}
                />
                <Bar dataKey="mae" fill="var(--series-forecast)" radius={[4, 4, 0, 0]} isAnimationActive={false} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>

        <Card title="Distribution of errors" subtitle="Number of periods per 250 MW error bin. Right of zero = over-forecast.">
          <div style={{ height: 260 }}>
            <ResponsiveContainer>
              <BarChart data={histogram} margin={{ top: 8, right: 8, bottom: 0, left: 0 }} barCategoryGap={1}>
                <CartesianGrid vertical={false} />
                <XAxis type="number" dataKey="mid" {...AXIS} tickFormatter={mw} domain={["dataMin - 125", "dataMax + 125"]} />
                <YAxis {...AXIS} axisLine={false} width={40} allowDecimals={false} />
                <Tooltip
                  cursor={{ fill: "var(--grid)" }}
                  content={({ active, payload }) => {
                    if (!active || !payload?.length) return null;
                    const b = payload[0].payload as Accuracy["errorHistogram"][number];
                    return (
                      <TooltipBox
                        title={`${fmtSignedMw(b.lower)} to ${fmtSignedMw(b.upper)}`}
                        rows={[{ name: "periods", value: String(b.count) }]}
                      />
                    );
                  }}
                />
                <ReferenceLine x={0} stroke="var(--text-muted)" />
                <Bar dataKey="count" fill="var(--series-forecast)" radius={[4, 4, 0, 0]} isAnimationActive={false} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>

        <Card title="Forecast vs actual" subtitle="Each dot is one period (actual MW on the vertical axis). Dots on the diagonal are perfect forecasts; below it = over-forecast.">
          <div style={{ height: 300 }}>
            <ResponsiveContainer>
              <ScatterChart margin={{ top: 8, right: 8, bottom: 16, left: 0 }}>
                <CartesianGrid />
                <XAxis type="number" dataKey="forecast" {...AXIS} tickFormatter={mw} domain={[0, maxMw]} label={{ value: "Forecast (MW)", position: "insideBottom", dy: 14 }} />
                <YAxis type="number" dataKey="actual" {...AXIS} axisLine={false} width={56} tickFormatter={mw} domain={[0, maxMw]} />
                <ReferenceLine segment={[{ x: 0, y: 0 }, { x: maxMw, y: maxMw }]} stroke="var(--text-muted)" strokeDasharray="4 4" />
                <Tooltip
                  content={({ active, payload }) => {
                    if (!active || !payload?.length) return null;
                    const p = payload[0].payload as Accuracy["scatter"][number];
                    return (
                      <TooltipBox
                        title="Period"
                        rows={[
                          { name: "forecast", value: fmtMw(p.forecast) },
                          { name: "actual", value: fmtMw(p.actual) },
                          { name: "error", value: fmtSignedMw(p.forecast - p.actual) },
                        ]}
                      />
                    );
                  }}
                />
                <Scatter data={acc.scatter} fill="var(--series-forecast)" fillOpacity={0.45} isAnimationActive={false} />
              </ScatterChart>
            </ResponsiveContainer>
          </div>
        </Card>

        <Card title="Error by delivery day" subtitle="Daily mean absolute error (MW) at decision time. Spikes flag days where buying on the forecast alone was risky.">
          <div style={{ height: 300 }}>
            <ResponsiveContainer>
              <BarChart data={acc.byDay} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
                <CartesianGrid vertical={false} />
                <XAxis dataKey="deliveryDate" {...AXIS} tickFormatter={(d: string) => d.slice(8, 10)} minTickGap={8} />
                <YAxis {...AXIS} axisLine={false} width={56} tickFormatter={mw} />
                <Tooltip
                  cursor={{ fill: "var(--grid)" }}
                  content={({ active, payload }) => {
                    if (!active || !payload?.length) return null;
                    const d = payload[0].payload as Accuracy["byDay"][number];
                    return (
                      <TooltipBox
                        title={fmtDay(d.deliveryDate)}
                        rows={[
                          { name: "MAE", value: fmtMw(d.mae) },
                          { name: "bias", value: fmtSignedMw(d.bias) },
                          { name: "mean forecast", value: fmtMw(d.meanForecast) },
                          { name: "mean actual", value: fmtMw(d.meanActual) },
                        ]}
                      />
                    );
                  }}
                />
                <Bar dataKey="mae" fill="var(--series-forecast)" radius={[4, 4, 0, 0]} isAnimationActive={false} />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <TableView
            headers={["Delivery day", "Mean forecast", "Mean actual", "MAE", "Bias"]}
            rows={acc.byDay.map((d) => [fmtDay(d.deliveryDate), fmtMw(d.meanForecast), fmtMw(d.meanActual), fmtMw(d.mae), fmtSignedMw(d.bias)])}
          />
        </Card>
      </div>
    </>
  );
}
