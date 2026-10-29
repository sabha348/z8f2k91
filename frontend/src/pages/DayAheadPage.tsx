import { useMemo, useState } from "react";
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api, type DayAhead, type Meta } from "../api";
import { Card, StatTile, Status, TableView, TooltipBox, type TooltipRow } from "../components/ui";
import { addDays, fmtDateTime, fmtGw, fmtLongDay, fmtMw, fmtSignedMw, fmtTime } from "../format";
import { useFetch } from "../useFetch";

interface Props {
  meta: Meta;
  decisionTime: string;
  deliveryDate: string;
  onDeliveryDateChange: (day: string) => void;
}

export function DayAheadPage({ meta, decisionTime, deliveryDate, onDeliveryDateChange }: Props) {
  const state = useFetch(() => api.dayAhead(deliveryDate, decisionTime), [deliveryDate, decisionTime]);
  const [showFinal, setShowFinal] = useState(false);

  const canPrev = deliveryDate > meta.deliveryDateFrom;
  const canNext = deliveryDate < meta.deliveryDateTo;

  return (
    <>
      <div className="controls" style={{ marginBottom: 16 }}>
        <label className="field">
          Delivery day (D)
          <div className="stepper">
            <button aria-label="Previous day" disabled={!canPrev} onClick={() => onDeliveryDateChange(addDays(deliveryDate, -1))}>
              ‹
            </button>
            <input
              type="date"
              value={deliveryDate}
              min={meta.deliveryDateFrom}
              max={meta.deliveryDateTo}
              onChange={(e) => e.target.value && onDeliveryDateChange(e.target.value)}
            />
            <button aria-label="Next day" disabled={!canNext} onClick={() => onDeliveryDateChange(addDays(deliveryDate, 1))}>
              ›
            </button>
          </div>
        </label>
      </div>

      {state.status === "loading" && <Status>Loading forecast…</Status>}
      {state.status === "error" && <Status error>Could not load the forecast: {state.message}</Status>}
      {state.status === "ready" && <DayAheadView data={state.data} showFinal={showFinal} onShowFinal={setShowFinal} />}
    </>
  );
}

function DayAheadView({
  data,
  showFinal,
  onShowFinal,
}: {
  data: DayAhead;
  showFinal: boolean;
  onShowFinal: (v: boolean) => void;
}) {
  const rows = useMemo(
    () =>
      data.points.map((p) => ({
        ...p,
        band: p.bandLow !== null && p.bandHigh !== null ? [p.bandLow, p.bandHigh] : null,
      })),
    [data.points],
  );
  const leads = data.points.map((p) => p.leadHours).filter((h): h is number => h !== null);
  const s = data.forecastSummary;
  const acc = data.accuracy;
  const decisionDay = addDays(data.deliveryDate, -1);

  return (
    <>
      <div className="banner">
        Decision at <strong>{data.decisionTime}</strong> on {fmtLongDay(decisionDay)} for delivery on{" "}
        <strong>{fmtLongDay(data.deliveryDate)}</strong>.{" "}
        {data.forecastPublishTime ? (
          <>
            Latest forecast available then: run published <strong>{fmtDateTime(data.forecastPublishTime)}</strong>
            {leads.length > 0 && (
              <> ({Math.round(Math.min(...leads))}–{Math.round(Math.max(...leads))} h ahead of delivery periods)</>
            )}
            .
          </>
        ) : (
          <>No forecast had been published by then.</>
        )}
      </div>

      <div className="tiles">
        <StatTile label="Expected wind (mean)" value={s ? fmtGw(s.meanMw) : "–"} sub={s ? `range ${fmtGw(s.minMw)} – ${fmtGw(s.maxMw)}` : undefined} />
        <StatTile
          label="Wind you can count on (P10)"
          value={s?.firmMeanMw != null ? fmtGw(s.firmMeanMw) : "–"}
          sub="exceeded in 9 of 10 periods historically"
        />
        <StatTile
          label="Outturn vs forecast (MAE)"
          value={acc ? fmtMw(acc.mae) : "–"}
          sub={acc ? `worst period ${fmtMw(acc.maxAbsError)}` : "no outturn yet"}
        />
        <StatTile
          label="Forecast bias this day"
          value={acc ? fmtSignedMw(acc.bias) : "–"}
          sub={acc && acc.bias !== null ? (acc.bias > 0 ? "over-forecast: wind short" : "under-forecast: wind surplus") : undefined}
        />
      </div>

      <Card
        title="Wind generation: forecast at decision time vs outturn"
        subtitle="MW, half-hourly outturn vs hourly forecast. Shaded band: 80% range of outturn given the forecast, from the decision-time errors observed over the whole period. All times UK."
      >
        <div className="legend">
          <span><i className="key-line" style={{ borderColor: "var(--series-forecast)" }} /> Forecast at decision</span>
          <span><i className="key-area" /> 80% range (P10–P90)</span>
          <span><i className="key-line" style={{ borderColor: "var(--series-actual)" }} /> Actual outturn</span>
          <label>
            <input type="checkbox" checked={showFinal} onChange={(e) => onShowFinal(e.target.checked)} />
            <i className="key-line dashed" style={{ borderColor: "var(--series-final)" }} /> Final forecast before delivery
            {data.finalForecastPublishTime && ` (${fmtDateTime(data.finalForecastPublishTime)})`}
          </label>
        </div>
        <div style={{ width: "100%", height: 380 }}>
          <ResponsiveContainer>
            <ComposedChart data={rows} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
              <CartesianGrid vertical={false} />
              <XAxis dataKey="startTime" tickFormatter={fmtTime} minTickGap={32} stroke="var(--axis)" tickLine={false} />
              <YAxis
                tickFormatter={(v: number) => v.toLocaleString("en-GB")}
                stroke="var(--axis)"
                tickLine={false}
                axisLine={false}
                width={56}
              />
              <Tooltip
                cursor={{ stroke: "var(--axis)" }}
                content={({ active, label, payload }) => {
                  if (!active || !payload?.length) return null;
                  const p = payload[0].payload as (typeof rows)[number];
                  const tr: TooltipRow[] = [];
                  if (p.forecast !== null) tr.push({ name: "forecast", value: fmtMw(p.forecast), color: "var(--series-forecast)" });
                  if (p.bandLow !== null && p.bandHigh !== null)
                    tr.push({ name: "80% range", value: `${fmtMw(p.bandLow)} – ${fmtMw(p.bandHigh)}` });
                  if (p.actual !== null) tr.push({ name: "actual", value: fmtMw(p.actual), color: "var(--series-actual)" });
                  if (showFinal && p.finalForecast !== null)
                    tr.push({ name: "final forecast", value: fmtMw(p.finalForecast), color: "var(--series-final)", dashed: true });
                  return <TooltipBox title={fmtTime(String(label))} rows={tr} />;
                }}
              />
              <Area dataKey="band" stroke="none" fill="var(--band)" connectNulls isAnimationActive={false} activeDot={false} />
              <Line dataKey="forecast" stroke="var(--series-forecast)" strokeWidth={2} dot={false} connectNulls isAnimationActive={false} />
              {showFinal && (
                <Line
                  dataKey="finalForecast"
                  stroke="var(--series-final)"
                  strokeWidth={2}
                  strokeDasharray="5 4"
                  dot={false}
                  connectNulls
                  isAnimationActive={false}
                />
              )}
              <Line dataKey="actual" stroke="var(--series-actual)" strokeWidth={2} dot={false} isAnimationActive={false} />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
        <TableView
          headers={["Time (UK)", "Forecast", "P10", "P90", "Actual", "Error", "Lead (h)"]}
          rows={data.points.map((p) => [
            fmtTime(p.startTime),
            fmtMw(p.forecast),
            fmtMw(p.bandLow),
            fmtMw(p.bandHigh),
            fmtMw(p.actual),
            p.forecast !== null && p.actual !== null ? fmtSignedMw(p.forecast - p.actual) : "–",
            p.leadHours !== null ? p.leadHours.toFixed(1) : "–",
          ])}
        />
      </Card>
    </>
  );
}
