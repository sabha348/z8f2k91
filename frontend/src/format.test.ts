import { describe, expect, it } from "vitest";
import { addDays, fmtMw, fmtSignedMw, fmtTime, timeOptions } from "./format";

describe("format", () => {
  it("adds days across month boundaries", () => {
    expect(addDays("2026-01-31", 1)).toBe("2026-02-01");
    expect(addDays("2026-01-02", -1)).toBe("2026-01-01");
  });

  it("formats MW values and missing values", () => {
    expect(fmtMw(1234.4)).toBe("1,234 MW");
    expect(fmtMw(null)).toBe("–");
    expect(fmtSignedMw(-500)).toBe("−500 MW");
    expect(fmtSignedMw(250)).toBe("+250 MW");
  });

  it("shows times in UK local time", () => {
    expect(fmtTime("2026-01-15T09:00:00Z")).toBe("09:00");
    expect(fmtTime("2026-07-15T09:00:00Z")).toBe("10:00"); // BST
  });

  it("builds half-hourly decision time options", () => {
    expect(timeOptions("09:00", "10:00")).toEqual(["09:00", "09:30", "10:00"]);
  });
});
