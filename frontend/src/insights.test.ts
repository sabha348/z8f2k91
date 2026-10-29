import { describe, expect, it } from "vitest";
import type { Accuracy } from "./api";
import { accuracyInsights } from "./insights";

const base: Accuracy = {
  decisionTime: "09:00",
  deliveryDateFrom: "2026-01-02",
  deliveryDateTo: "2026-02-01",
  overall: {
    count: 10, meanActual: 10000, meanForecast: 10500, mae: 1000, rmse: 1300, bias: 500, nmae: 0.1,
    p50AbsError: 800, p90AbsError: 2000, maxAbsError: 3000, errorP10: -1000, errorP90: 2000,
  },
  meanLeadHours: 27,
  byHour: [
    { hour: 3, count: 5, mae: 800, bias: 0, errorP10: -1, errorP90: 1 },
    { hour: 20, count: 5, mae: 1200, bias: 0, errorP10: -1, errorP90: 1 },
  ],
  byDay: [],
  errorHistogram: [],
  byHorizon: [
    { horizonHours: 0, count: 1, meanLeadHours: 1, mae: 300, rmse: 1, bias: 0, p90AbsError: 1 },
    { horizonHours: 48, count: 1, meanLeadHours: 49, mae: 1500, rmse: 1, bias: 0, p90AbsError: 1 },
  ],
  scatter: [],
};

describe("accuracyInsights", () => {
  it("derives takeaways from the statistics", () => {
    const text = accuracyInsights(base).join("\n");
    expect(text).toContain("1,000 MW on average");
    expect(text).toContain("between −2,000 MW and +1,000 MW");
    expect(text).toContain("Forecasts ran high");
    expect(text).toContain("around 20:00");
    expect(text).toContain("from 300 MW on the latest forecast to 1,500 MW");
  });

  it("returns nothing without data", () => {
    expect(accuracyInsights({ ...base, overall: null })).toEqual([]);
  });
});
