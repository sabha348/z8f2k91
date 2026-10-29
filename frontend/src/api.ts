// Typed client for the FastAPI backend. Shapes mirror backend/app/schemas.py.

export interface Stats {
  count: number;
  meanActual: number | null;
  meanForecast: number | null;
  mae: number | null;
  rmse: number | null;
  bias: number | null;
  nmae: number | null;
  p50AbsError: number | null;
  p90AbsError: number | null;
  maxAbsError: number | null;
  errorP10: number | null;
  errorP90: number | null;
}

export interface Meta {
  timezone: string;
  decisionDateFrom: string;
  decisionDateTo: string;
  deliveryDateFrom: string;
  deliveryDateTo: string;
  defaultDecisionTime: string;
  maxHorizonHours: number;
  dataSource: string;
  dataLoadedAt: string;
  actualPoints: number;
  forecastPoints: number;
  forecastRuns: number;
}

export interface DayAheadPoint {
  startTime: string;
  actual: number | null;
  forecast: number | null;
  forecastPublishTime: string | null;
  leadHours: number | null;
  bandLow: number | null;
  bandHigh: number | null;
  finalForecast: number | null;
}

export interface DayAhead {
  deliveryDate: string;
  decisionTime: string;
  decisionCutoff: string;
  forecastPublishTime: string | null;
  finalForecastPublishTime: string | null;
  points: DayAheadPoint[];
  forecastSummary: {
    points: number;
    meanMw: number;
    minMw: number;
    maxMw: number;
    firmMeanMw: number | null;
  } | null;
  accuracy: Stats | null;
  bandBasis: Stats | null;
}

export interface HourStats {
  hour: number;
  count: number;
  mae: number;
  bias: number;
  errorP10: number;
  errorP90: number;
}

export interface DayStats {
  deliveryDate: string;
  count: number;
  meanActual: number;
  meanForecast: number;
  mae: number;
  bias: number;
}

export interface HorizonStats {
  horizonHours: number;
  count: number;
  meanLeadHours: number;
  mae: number;
  rmse: number;
  bias: number;
  p90AbsError: number;
}

export interface Accuracy {
  decisionTime: string;
  deliveryDateFrom: string;
  deliveryDateTo: string;
  overall: Stats | null;
  meanLeadHours: number | null;
  byHour: HourStats[];
  byDay: DayStats[];
  errorHistogram: { lower: number; upper: number; count: number }[];
  byHorizon: HorizonStats[];
  scatter: { forecast: number; actual: number }[];
}

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
  }
}

const BASE = import.meta.env.VITE_API_BASE ?? "";

async function get<T>(path: string, params: Record<string, string> = {}): Promise<T> {
  const query = new URLSearchParams(params).toString();
  const res = await fetch(`${BASE}${path}${query ? `?${query}` : ""}`);
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      if (typeof body?.detail === "string") detail = body.detail;
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(detail, res.status);
  }
  return res.json() as Promise<T>;
}

export const api = {
  meta: () => get<Meta>("/api/meta"),
  dayAhead: (deliveryDate: string, decisionTime: string) =>
    get<DayAhead>("/api/day-ahead", { delivery_date: deliveryDate, decision_time: decisionTime }),
  accuracy: (decisionTime: string) =>
    get<Accuracy>("/api/accuracy", { decision_time: decisionTime }),
};
