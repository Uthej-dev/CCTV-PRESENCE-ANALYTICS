import { beforeEach, describe, expect, it } from "vitest";
import { addSeconds, cameraStatus, formatClock, dayRangeISO, formatDuration, formatHour, formatMinutes, localDateISO, setTimezone, zonedToUtcISO } from "../format";

describe("formatDuration", () => {
  it("formats seconds, minutes and hours", () => {
    expect(formatDuration(12)).toBe("12s");
    expect(formatDuration(75)).toBe("1m 15s");
    expect(formatDuration(3725)).toBe("1h 2m");
    expect(formatDuration(null)).toBe("—");
  });
});

describe("formatMinutes / formatHour", () => {
  it("formats KPI values", () => {
    expect(formatMinutes(0)).toBe("0 min");
    expect(formatMinutes(45)).toBe("45 s");
    expect(formatMinutes(90)).toBe("1.5 min");
    expect(formatMinutes(753)).toBe("13 min");
    expect(formatHour(9)).toBe("09:00");
    expect(formatHour(null)).toBe("—");
  });
});

describe("dayRangeISO", () => {
  beforeEach(() => localStorage.clear());

  it("returns UTC bounds of a local day in the chosen timezone", () => {
    setTimezone("Asia/Kolkata"); // UTC+5:30
    expect(dayRangeISO("2026-03-10")).toEqual({
      start: "2026-03-09T18:30:00.000Z",
      end: "2026-03-10T18:30:00.000Z",
    });
  });

  it("converts a local date + time to UTC", () => {
    setTimezone("Asia/Kolkata");
    expect(zonedToUtcISO("2026-03-10", "14:30")).toBe("2026-03-10T09:00:00.000Z");
  });

  it("gives the local calendar date of an instant", () => {
    setTimezone("Asia/Kolkata");
    expect(localDateISO("2026-03-09T19:00:00Z")).toBe("2026-03-10"); // 00:30 IST next day
  });

  it("handles DST days (23h long)", () => {
    setTimezone("America/New_York"); // DST starts 2026-03-08
    const { start, end } = dayRangeISO("2026-03-08");
    expect(start).toBe("2026-03-08T05:00:00.000Z");
    expect(end).toBe("2026-03-09T04:00:00.000Z");
  });
});

describe("cameraStatus", () => {
  it("shows inactive cameras as inactive unless running", () => {
    expect(cameraStatus({ is_active: false, status: "idle" })).toBe("inactive");
    expect(cameraStatus({ is_active: false, status: "running" })).toBe("running");
    expect(cameraStatus({ is_active: true, status: "error" })).toBe("error");
  });
});

describe("clip helpers", () => {
  it("formats player time and offsets", () => {
    expect(formatClock(0)).toBe("0:00");
    expect(formatClock(75.4)).toBe("1:15");
    expect(formatClock(3725)).toBe("1:02:05");
    expect(addSeconds("2026-03-10T10:00:00.000Z", 90.5)).toBe("2026-03-10T10:01:30.500Z");
  });
});
