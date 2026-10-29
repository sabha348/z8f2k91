// Plain-language takeaways derived from the accuracy statistics (no hard-coded findings).

import type { Accuracy } from "./api";
import { fmtMw, fmtPct, fmtSignedMw } from "./format";

export function accuracyInsights(acc: Accuracy): string[] {
  const o = acc.overall;
  if (!o || o.mae === null) return [];
  const out: string[] = [];

  out.push(
    `At a ${acc.decisionTime} decision, the forecast was off by ${fmtMw(o.mae)} on average ` +
      `(${fmtPct(o.nmae)} of mean wind output of ${fmtMw(o.meanActual)}).`,
  );

  if (o.errorP10 !== null && o.errorP90 !== null) {
    out.push(
      `In 80% of periods the outturn landed between ${fmtSignedMw(-o.errorP90)} and ` +
        `${fmtSignedMw(-o.errorP10)} of the forecast. Planning on forecast ${fmtSignedMw(-o.errorP90)} ` +
        `would have covered 9 in 10 periods.`,
    );
  }

  if (o.bias !== null && o.mae > 0 && Math.abs(o.bias) > 0.2 * o.mae) {
    out.push(
      o.bias > 0
        ? `Forecasts ran high: on average ${fmtMw(o.bias)} more wind was expected than arrived, ` +
            `which leaves a shortfall to cover in the market.`
        : `Forecasts ran low: on average ${fmtMw(-o.bias)} less wind was expected than arrived, ` +
            `which leads to over-procurement.`,
    );
  }

  const worstHour = [...acc.byHour].sort((a, b) => b.mae - a.mae)[0];
  if (worstHour) {
    out.push(
      `The largest errors fall around ${String(worstHour.hour).padStart(2, "0")}:00 UK time ` +
        `(average ${fmtMw(worstHour.mae)}).`,
    );
  }

  const h0 = acc.byHorizon[0];
  const hLast = acc.byHorizon[acc.byHorizon.length - 1];
  if (h0 && hLast && hLast.horizonHours > h0.horizonHours && hLast.mae > h0.mae) {
    out.push(
      `Average error grows from ${fmtMw(h0.mae)} on the latest forecast to ${fmtMw(hLast.mae)} ` +
        `${hLast.horizonHours} hours ahead: deciding later, on a fresher forecast, cuts the error.`,
    );
  }
  return out;
}
