import { useState } from "react";
import { analyticsApi, camerasApi } from "../api";
import { errorMessage } from "../api/client";
import BarsChart from "../components/charts/BarsChart";
import TimeSeriesChart from "../components/charts/TimeSeriesChart";
import TrendLineChart from "../components/charts/TrendLineChart";
import { Card, EmptyState, ErrorAlert, PageHeader, StatCard } from "../components/ui";
import usePolling from "../hooks/usePolling";
import { dayRangeISO, formatDay, formatDuration, formatHour, formatMinutes, formatNumber, formatShortTime, todayISO } from "../utils/format";

const ENTRY_EXIT = [
  { key: "entries", label: "Entries", color: "var(--series-1)" },
  { key: "exits", label: "Exits", color: "var(--series-2)" },
];

export default function AnalyticsPage() {
  const [date, setDate] = useState(todayISO());
  const [days, setDays] = useState(7);
  const [cameraId, setCameraId] = useState("");
  const cam = cameraId || undefined;

  const cameras = usePolling(camerasApi.list, 0);
  const daily = usePolling(() => analyticsApi.daily({ date, camera_id: cam }), 60000, [date, cam]);
  const weekly = usePolling(() => analyticsApi.weekly({ end_date: date, days, camera_id: cam }), 60000, [date, days, cam]);
  const occupancy = usePolling(() => {
    const { start, end } = dayRangeISO(date);
    return analyticsApi.occupancy({ start, end, interval_minutes: 10, camera_id: cam });
  }, 60000, [date, cam]);

  const d = daily.data;
  const w = weekly.data;
  const occPoints = (occupancy.data?.points || []).map((p) => ({ t: new Date(p.timestamp).getTime(), occupancy: p.occupancy }));
  const avgByDay = (w?.days || []).map((x) => ({ ...x, avg_minutes: +(x.avg_duration_seconds / 60).toFixed(1) }));
  const byHour = (w?.visitors_by_hour || []).map((v, hour) => ({ hour, visitors: v }));
  const error = daily.error || weekly.error || occupancy.error;

  return (
    <>
      <PageHeader title="Analytics" subtitle="Visitors, presence duration and occupancy trends">
        <select value={cameraId} onChange={(e) => setCameraId(e.target.value)} aria-label="Camera">
          <option value="">All cameras</option>
          {(cameras.data || []).map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
        </select>
        <input type="date" value={date} max={todayISO()} onChange={(e) => e.target.value && setDate(e.target.value)} aria-label="Day" />
        <div className="tabs" role="tablist" aria-label="Period">
          {[7, 14, 30].map((n) => (
            <button key={n} className={days === n ? "active" : ""} onClick={() => setDays(n)}>{n}d</button>
          ))}
        </div>
      </PageHeader>
      {error && <div style={{ marginBottom: 16 }}><ErrorAlert error={errorMessage(error)} /></div>}

      <h2 style={{ margin: "4px 0 12px" }}>{date === todayISO() ? "Today" : formatDay(date)}</h2>
      <div className="grid grid-4" style={{ marginBottom: 16 }}>
        <StatCard label="Visitors" value={d ? formatNumber(d.visitors) : "—"} sub={d ? `${d.entries} entries · ${d.exits} exits` : " "} />
        <StatCard label="Avg presence" value={d ? formatMinutes(d.avg_duration_seconds) : "—"} sub={d ? `Longest ${formatDuration(d.max_duration_seconds)}` : " "} />
        <StatCard label="Peak occupancy" value={d ? formatNumber(d.peak_occupancy) : "—"} sub={d?.peak_occupancy_time ? `at ${formatShortTime(d.peak_occupancy_time)}` : "No samples"} />
        <StatCard label="Peak hour" value={d ? formatHour(d.peak_hour) : "—"} sub={d?.peak_hour != null ? `${d.hourly[d.peak_hour].visitors} visitors` : "No visitors"} />
      </div>

      <div className="grid grid-2" style={{ marginBottom: 16 }}>
        <Card title="Entries and exits by hour">
          <BarsChart data={d?.hourly || []} xKey="hour" series={ENTRY_EXIT} xFormatter={formatHour} />
        </Card>
        <Card title="Occupancy" subtitle="People in view, 10-minute peaks">
          {occPoints.length ? (
            <TimeSeriesChart data={occPoints} yKey="occupancy" label="People" xFormatter={(t) => formatShortTime(t)} />
          ) : (
            <EmptyState title="No occupancy samples for this day" />
          )}
        </Card>
      </div>

      <h2 style={{ margin: "24px 0 12px" }}>Last {days} days</h2>
      <div className="grid grid-4" style={{ marginBottom: 16 }}>
        <StatCard label="Total visitors" value={w ? formatNumber(w.total_visitors) : "—"} sub={w ? `${formatNumber(Math.round(w.total_visitors / days))} per day on average` : " "} />
        <StatCard label="Avg presence" value={w ? formatMinutes(w.avg_duration_seconds) : "—"} />
        <StatCard label="Busiest day" value={w?.busiest_day ? formatDay(w.busiest_day) : "—"} />
        <StatCard label="Peak hour" value={w ? formatHour(w.peak_hour) : "—"} sub="Most arrivals across the period" />
      </div>

      <div className="grid grid-2" style={{ marginBottom: 16 }}>
        <Card title="Visitors per day">
          <BarsChart data={w?.days || []} xKey="date" series={[{ key: "visitors", label: "Visitors", color: "var(--series-1)" }]} xFormatter={formatDay} />
        </Card>
        <Card title="Average presence per day" subtitle="Minutes">
          <TrendLineChart data={avgByDay} xKey="date" yKey="avg_minutes" label="Avg minutes" xFormatter={formatDay} valueFormatter={(v) => `${v} min`} height={260} />
        </Card>
      </div>

      <div className="grid grid-2">
        <Card title="Peak hours" subtitle={`Arrivals by hour of day, last ${days} days`}>
          <BarsChart data={byHour} xKey="hour" series={[{ key: "visitors", label: "Visitors", color: "var(--series-1)" }]} xFormatter={formatHour} />
        </Card>
        <Card title="Daily breakdown" flush>
          <div className="table-wrap" style={{ maxHeight: 300, overflowY: "auto" }}>
            <table>
              <thead><tr><th>Day</th><th className="num">Visitors</th><th className="num">Entries</th><th className="num">Exits</th><th className="num">Avg presence</th><th className="num">Peak</th></tr></thead>
              <tbody>
                {[...(w?.days || [])].reverse().map((x) => (
                  <tr key={x.date}>
                    <td>{formatDay(x.date)}</td>
                    <td className="num">{x.visitors}</td>
                    <td className="num">{x.entries}</td>
                    <td className="num">{x.exits}</td>
                    <td className="num">{formatDuration(x.avg_duration_seconds)}</td>
                    <td className="num">{x.peak_occupancy}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      </div>
    </>
  );
}
