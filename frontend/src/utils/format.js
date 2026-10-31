const TZ_KEY = "cctv_timezone";

export const browserTimezone = () => Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
export const getTimezone = () => localStorage.getItem(TZ_KEY) || browserTimezone();
export const setTimezone = (tz) => (tz ? localStorage.setItem(TZ_KEY, tz) : localStorage.removeItem(TZ_KEY));

const fmt = (opts) => new Intl.DateTimeFormat(undefined, { timeZone: getTimezone(), ...opts });

export const formatTime = (iso) => (iso ? fmt({ hour: "2-digit", minute: "2-digit", second: "2-digit" }).format(new Date(iso)) : "—");
export const formatShortTime = (iso) => (iso ? fmt({ hour: "2-digit", minute: "2-digit" }).format(new Date(iso)) : "—");
export const formatDateTime = (iso) =>
  iso ? fmt({ month: "short", day: "numeric", hour: "2-digit", minute: "2-digit", second: "2-digit" }).format(new Date(iso)) : "—";
export const formatDay = (isoDate) =>
  new Intl.DateTimeFormat(undefined, { weekday: "short", day: "numeric", month: "short", timeZone: "UTC" }).format(
    new Date(`${isoDate}T00:00:00Z`),
  );

/** 75 -> "1m 15s", 3725 -> "1h 2m", 12 -> "12s" */
export function formatDuration(seconds) {
  if (seconds == null || Number.isNaN(seconds)) return "—";
  const s = Math.round(seconds);
  if (s < 60) return `${s}s`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m ${s % 60}s`;
  return `${Math.floor(m / 60)}h ${m % 60}m`;
}

/** Shorter form for KPI tiles: 753 -> "12.6 min" */
export function formatMinutes(seconds) {
  if (!seconds) return "0 min";
  if (seconds < 60) return `${Math.round(seconds)} s`;
  return `${(seconds / 60).toFixed(seconds < 600 ? 1 : 0)} min`;
}

export const formatHour = (h) => (h == null ? "—" : `${String(h).padStart(2, "0")}:00`);
export const formatNumber = (n) => (n == null ? "—" : new Intl.NumberFormat().format(n));

export function formatBytes(b) {
  if (b < 1024 * 1024) return `${(b / 1024).toFixed(0)} KB`;
  return `${(b / 1024 / 1024).toFixed(1)} MB`;
}

/** Calendar date (YYYY-MM-DD) of an instant in the selected timezone */
export const localDateISO = (iso) => new Intl.DateTimeFormat("en-CA", { timeZone: getTimezone() }).format(new Date(iso));

/** Today's date (YYYY-MM-DD) in the selected timezone */
export function todayISO() {
  const parts = new Intl.DateTimeFormat("en-CA", { timeZone: getTimezone() }).format(new Date());
  return parts; // en-CA formats as YYYY-MM-DD
}

// Offset (ms) of the selected timezone from UTC at a given instant
const offsetAt = (date) => {
  const local = new Date(date.toLocaleString("en-US", { timeZone: getTimezone() }));
  const utc = new Date(date.toLocaleString("en-US", { timeZone: "UTC" }));
  return local - utc;
};

/** "2026-03-10" + "14:30" in the selected timezone -> UTC ISO string */
export function zonedToUtcISO(isoDate, hhmm = "00:00") {
  const guess = new Date(`${isoDate}T${hhmm}:00Z`);
  return new Date(guess.getTime() - offsetAt(guess)).toISOString();
}

/** UTC ISO bounds of a local calendar day in the selected timezone (for /tracking & /events filters) */
export function dayRangeISO(isoDate) {
  const next = new Date(new Date(`${isoDate}T00:00:00Z`).getTime() + 86400000).toISOString().slice(0, 10);
  return { start: zonedToUtcISO(isoDate), end: zonedToUtcISO(next) };
}

/** Effective display status of a camera document */
export const cameraStatus = (cam) => (!cam.is_active && cam.status !== "running" ? "inactive" : cam.status);

/** ISO time + seconds -> ISO time */
export const addSeconds = (iso, seconds) => new Date(new Date(iso).getTime() + seconds * 1000).toISOString();

/** 75.4 -> "1:15" (video player style) */
export function formatClock(seconds) {
  const s = Math.max(0, Math.floor(seconds));
  const m = Math.floor(s / 60);
  return m >= 60 ? `${Math.floor(m / 60)}:${String(m % 60).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}` : `${m}:${String(s % 60).padStart(2, "0")}`;
}
