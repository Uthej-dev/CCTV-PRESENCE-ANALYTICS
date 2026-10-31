import { useState } from "react";
import { Link } from "react-router-dom";
import { camerasApi, presenceApi } from "../api";
import { errorMessage } from "../api/client";
import SessionsTable from "../components/SessionsTable";
import { Card, EmptyState, ErrorAlert, PageHeader, Pagination, Spinner } from "../components/ui";
import usePolling from "../hooks/usePolling";
import { dayRangeISO, formatDateTime, localDateISO, todayISO } from "../utils/format";

const LIMIT = 25;

export default function HistoryPage() {
  const [tab, setTab] = useState("sessions");
  const [cameraId, setCameraId] = useState("");
  const [date, setDate] = useState(todayISO());
  const [type, setType] = useState("");
  const [skip, setSkip] = useState(0);

  const cameras = usePolling(camerasApi.list, 0);
  const cameraNames = Object.fromEntries((cameras.data || []).map((c) => [c.id, c.name]));
  const range = date ? dayRangeISO(date) : {};
  const params = { camera_id: cameraId || undefined, start: range.start, end: range.end, skip, limit: LIMIT };

  const result = usePolling(
    () => (tab === "sessions" ? presenceApi.sessions(params) : presenceApi.events({ ...params, type: type || undefined })),
    10000,
    [tab, cameraId, date, type, skip],
  );
  const resetPage = (fn) => (e) => { fn(e.target.value); setSkip(0); };
  const items = result.data?.items || [];

  return (
    <>
      <PageHeader title="Entry / exit history" subtitle="Every tracked visit and line crossing">
        <div className="tabs" role="tablist">
          <button className={tab === "sessions" ? "active" : ""} onClick={() => { setTab("sessions"); setSkip(0); }}>Visits</button>
          <button className={tab === "events" ? "active" : ""} onClick={() => { setTab("events"); setSkip(0); }}>Line crossings</button>
        </div>
      </PageHeader>

      <div className="row" style={{ marginBottom: 16 }}>
        <select value={cameraId} onChange={resetPage(setCameraId)} aria-label="Camera">
          <option value="">All cameras</option>
          {(cameras.data || []).map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
        </select>
        <input type="date" value={date} max={todayISO()} onChange={resetPage(setDate)} aria-label="Day" />
        {date && <button className="btn btn-sm btn-ghost" onClick={() => { setDate(""); setSkip(0); }}>All dates</button>}
        {tab === "events" && (
          <select value={type} onChange={resetPage(setType)} aria-label="Event type">
            <option value="">Entries and exits</option>
            <option value="entry">Entries only</option>
            <option value="exit">Exits only</option>
          </select>
        )}
      </div>

      {result.error && <div style={{ marginBottom: 16 }}><ErrorAlert error={errorMessage(result.error)} /></div>}

      <Card flush>
        {result.loading && !result.data ? (
          <div className="center"><Spinner /></div>
        ) : items.length === 0 ? (
          <EmptyState title="Nothing recorded">No {tab === "sessions" ? "visits" : "line crossings"} match these filters.</EmptyState>
        ) : tab === "sessions" ? (
          <SessionsTable sessions={items} cameraNames={cameraNames} showDate formatter={formatDateTime} />
        ) : (
          <div className="table-wrap">
            <table>
              <thead><tr><th>Time</th><th>Person</th><th>Camera</th><th>Event</th><th /></tr></thead>
              <tbody>
                {items.map((e) => (
                  <tr key={e.id}>
                    <td className="mono">{formatDateTime(e.timestamp)}</td>
                    <td className="mono">{e.person_id}</td>
                    <td>{cameraNames[e.camera_id] || "—"}</td>
                    <td>
                      <span className="tag">
                        <span className="swatch" style={{ background: e.type === "entry" ? "var(--series-1)" : "var(--series-2)" }} />
                        {e.type === "entry" ? "Entry" : "Exit"}
                      </span>
                    </td>
                    <td className="num">
                      <Link className="btn btn-sm" to={`/recordings?camera=${e.camera_id}&date=${localDateISO(e.timestamp)}&at=${encodeURIComponent(e.timestamp)}`}>▶ Video</Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {result.data && result.data.total > 0 && <Pagination skip={skip} limit={LIMIT} total={result.data.total} onChange={setSkip} />}
      </Card>
    </>
  );
}
