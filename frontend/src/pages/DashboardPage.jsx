import { Link } from "react-router-dom";
import { analyticsApi, camerasApi, presenceApi } from "../api";
import { errorMessage } from "../api/client";
import BarsChart from "../components/charts/BarsChart";
import TimeSeriesChart from "../components/charts/TimeSeriesChart";
import SessionsTable from "../components/SessionsTable";
import { Card, EmptyState, ErrorAlert, PageHeader, StatCard } from "../components/ui";
import usePolling from "../hooks/usePolling";
import { formatDay, formatDuration, formatHour, formatMinutes, formatNumber, formatShortTime } from "../utils/format";

export default function DashboardPage() {
  const presence = usePolling(presenceApi.current, 3000);
  const daily = usePolling(() => analyticsApi.daily(), 30000);
  const occupancy = usePolling(() => analyticsApi.occupancy({ interval_minutes: 5 }), 30000);
  const weekly = usePolling(() => analyticsApi.weekly({ days: 7 }), 60000);
  const sessions = usePolling(() => presenceApi.sessions({ limit: 8 }), 5000);
  const cameras = usePolling(camerasApi.list, 0);

  const p = presence.data;
  const d = daily.data;
  const cameraNames = Object.fromEntries((cameras.data || []).map((c) => [c.id, c.name]));
  const occPoints = (occupancy.data?.points || []).map((pt) => ({ t: new Date(pt.timestamp).getTime(), occupancy: pt.occupancy }));
  const error = presence.error || daily.error;

  return (
    <>
      <PageHeader title="Dashboard" subtitle="Live occupancy and today's presence analytics" />
      {error && <div style={{ marginBottom: 16 }}><ErrorAlert error={errorMessage(error)} /></div>}

      <div className="grid grid-4" style={{ marginBottom: 16 }}>
        <StatCard
          live={p?.running_cameras > 0}
          label="Current people"
          value={p ? formatNumber(p.in_view) : "—"}
          sub={p ? (p.running_cameras ? `${p.running_cameras} camera${p.running_cameras > 1 ? "s" : ""} running` : "No cameras running") : " "}
        />
        <StatCard label="Today's visitors" value={d ? formatNumber(d.visitors) : "—"} sub={d ? `${formatNumber(d.entries)} entries · ${formatNumber(d.exits)} exits` : " "} />
        <StatCard label="Avg presence" value={d ? formatMinutes(d.avg_duration_seconds) : "—"} sub={d ? `Longest ${formatDuration(d.max_duration_seconds)}` : " "} />
        <StatCard
          label="Peak occupancy"
          value={d ? formatNumber(d.peak_occupancy) : "—"}
          sub={d?.peak_occupancy_time ? `at ${formatShortTime(d.peak_occupancy_time)} · busiest hour ${formatHour(d.peak_hour)}` : "No data yet today"}
        />
      </div>

      <div className="grid grid-3-1" style={{ marginBottom: 16 }}>
        <Card title="Occupancy over time" subtitle="People in view today, 5-minute peaks">
          {occPoints.length ? (
            <TimeSeriesChart data={occPoints} yKey="occupancy" label="People" xFormatter={(t) => formatShortTime(t)} />
          ) : (
            <EmptyState title="No occupancy data today">Start a camera to begin collecting data.</EmptyState>
          )}
        </Card>
        <Card title="Live now" subtitle="Running cameras" actions={<Link to="/live" className="btn btn-sm">Open live view</Link>}>
          {p?.cameras?.length ? (
            <div className="stack" style={{ gap: 8 }}>
              {p.cameras.map((c) => (
                <Link key={c.camera_id} to={`/cameras/${c.camera_id}`} className="person-row" style={{ color: "inherit", textDecoration: "none" }}>
                  <span><span className="live-dot" style={{ display: "inline-block", marginRight: 8 }} />{c.camera_name}</span>
                  <strong>{c.in_view} in view</strong>
                </Link>
              ))}
              <div className="stat-sub">{p.entries} entries · {p.exits} exits since started</div>
            </div>
          ) : (
            <EmptyState title="No cameras running" action={<Link to="/cameras" className="btn btn-sm">Manage cameras</Link>} />
          )}
        </Card>
      </div>

      <div className="grid grid-2" style={{ marginBottom: 16 }}>
        <Card title="Visitors by hour" subtitle="Today">
          <BarsChart
            data={d?.hourly || []}
            xKey="hour"
            series={[{ key: "visitors", label: "Visitors", color: "var(--series-1)" }]}
            xFormatter={formatHour}
           
          />
        </Card>
        <Card title="Visitors per day" subtitle="Last 7 days">
          <BarsChart
            data={weekly.data?.days || []}
            xKey="date"
            series={[{ key: "visitors", label: "Visitors", color: "var(--series-1)" }]}
            xFormatter={formatDay}
           
          />
        </Card>
      </div>

      <Card title="Recent entry / exit activity" subtitle="Latest tracked people" flush actions={<Link to="/history" className="btn btn-sm" style={{ marginRight: 0 }}>View history</Link>}>
        {sessions.data?.items?.length ? (
          <SessionsTable sessions={sessions.data.items} cameraNames={cameraNames} />
        ) : (
          <EmptyState title="No activity yet">People detected by your cameras will appear here.</EmptyState>
        )}
      </Card>
    </>
  );
}
