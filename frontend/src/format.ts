// Display helpers. All times are shown in UK local time, as traders work in it.

const UK = "Europe/London";

const timeFmt = new Intl.DateTimeFormat("en-GB", { timeZone: UK, hour: "2-digit", minute: "2-digit" });
const dateTimeFmt = new Intl.DateTimeFormat("en-GB", {
  timeZone: UK,
  weekday: "short",
  day: "numeric",
  month: "short",
  hour: "2-digit",
  minute: "2-digit",
});
const dayFmt = new Intl.DateTimeFormat("en-GB", {
  timeZone: UK,
  weekday: "short",
  day: "numeric",
  month: "short",
});
const longDayFmt = new Intl.DateTimeFormat("en-GB", {
  timeZone: UK,
  weekday: "long",
  day: "numeric",
  month: "long",
  year: "numeric",
});

export const fmtTime = (iso: string) => timeFmt.format(new Date(iso));
export const fmtDateTime = (iso: string) => dateTimeFmt.format(new Date(iso));

/** A calendar date ("YYYY-MM-DD") rendered without shifting across time zones. */
export const fmtDay = (day: string) => dayFmt.format(new Date(`${day}T12:00:00Z`));
export const fmtLongDay = (day: string) => longDayFmt.format(new Date(`${day}T12:00:00Z`));

export function fmtMw(value: number | null | undefined, digits = 0): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "–";
  return `${value.toLocaleString("en-GB", { maximumFractionDigits: digits, minimumFractionDigits: digits })} MW`;
}

export function fmtSignedMw(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "–";
  const sign = value > 0 ? "+" : value < 0 ? "−" : "±";
  return `${sign}${Math.abs(value).toLocaleString("en-GB", { maximumFractionDigits: 0 })} MW`;
}

export function fmtPct(value: number | null | undefined, digits = 1): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "–";
  return `${(value * 100).toFixed(digits)}%`;
}

export const fmtGw = (mw: number) => `${(mw / 1000).toLocaleString("en-GB", { maximumFractionDigits: 1 })} GW`;

/** Add whole days to a "YYYY-MM-DD" date string. */
export function addDays(day: string, delta: number): string {
  const d = new Date(`${day}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + delta);
  return d.toISOString().slice(0, 10);
}

/** Half-hourly HH:MM options between two times, inclusive. */
export function timeOptions(from = "05:00", to = "16:00", stepMinutes = 30): string[] {
  const toMin = (t: string) => Number(t.slice(0, 2)) * 60 + Number(t.slice(3, 5));
  const out: string[] = [];
  for (let m = toMin(from); m <= toMin(to); m += stepMinutes) {
    out.push(`${String(Math.floor(m / 60)).padStart(2, "0")}:${String(m % 60).padStart(2, "0")}`);
  }
  return out;
}
