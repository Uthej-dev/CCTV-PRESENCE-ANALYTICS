import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { analyticsApi, camerasApi, presenceApi } from "../api";
import { errorMessage } from "../api/client";
import CameraForm from "../components/CameraForm";
import { PlayIcon, StopIcon } from "../components/Icons";
import LineEditor from "../components/LineEditor";
import LiveStream from "../components/LiveStream";
import SessionsTable from "../components/SessionsTable";
import { Card, EmptyState, ErrorAlert, PageHeader, Spinner, StatusBadge } from "../components/ui";
import usePolling from "../hooks/usePolling";
import { cameraStatus, formatDuration, formatMinutes, formatNumber } from "../utils/format";
import { LiveStatsPanel } from "./LiveMonitorPage";

const DIRS = { down: [0, 1], up: [0, -1], left: [-1, 0], right: [1, 0] };

/** True when the entry direction is (nearly) parallel to the line, which makes entry/exit ambiguous. */
function directionAlongLine({ line, entry_direction }) {
  const lx = line.x2 - line.x1;
  const ly = line.y2 - line.y1;
  const [dx, dy] = DIRS[entry_direction];
  const len = Math.hypot(lx, ly) || 1;
  return Math.abs((lx * dx + ly * dy) / len) > 0.85;
}

export default function CameraDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const camera = usePolling(() => camerasApi.get(id), 3000, [id]);
  const cam = camera.data;
  const running = cam?.status === "running";
  const live = usePolling(() => (running ? camerasApi.live(id) : Promise.resolve(null)), running ? 1000 : 0, [id, running]);
  const daily = usePolling(() => analyticsApi.daily({ camera_id: id }), 30000, [id]);
  const sessions = usePolling(() => presenceApi.sessions({ camera_id: id, limit: 10 }), 5000, [id]);

  const [lineDraft, setLineDraft] = useState(null);
  const [editing, setEditing] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [frameKey, setFrameKey] = useState(0);
  const [confirmDelete, setConfirmDelete] = useState(false);

  useEffect(() => {
    if (cam && !lineDraft) setLineDraft({ line: cam.line, entry_direction: cam.entry_direction });
  }, [cam, lineDraft]);

  if (camera.error?.response?.status === 404) {
    return <EmptyState title="Camera not found" action={<Link className="btn" to="/cameras">Back to cameras</Link>} />;
  }
  if (!cam) return <div className="center"><Spinner /></div>;

  const run = async (fn) => {
    setBusy(true);
    setError(null);
    try {
      await fn();
      await camera.refresh();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  const parallel = lineDraft && directionAlongLine(lineDraft);
  const lineDirty = lineDraft && (JSON.stringify(lineDraft.line) !== JSON.stringify(cam.line) || lineDraft.entry_direction !== cam.entry_direction);
  const d = daily.data;

  return (
    <>
      <PageHeader title={cam.name} subtitle={cam.location || "No location set"}>
        <StatusBadge status={live.data?.state === "starting" ? "starting" : cameraStatus(cam)} />
        {running ? (
          <button className="btn" disabled={busy} onClick={() => run(() => camerasApi.stop(id))}><StopIcon width="15" height="15" /> Stop</button>
        ) : (
          <button className="btn btn-primary" disabled={busy || !cam.is_active} onClick={() => run(() => camerasApi.start(id))}><PlayIcon width="15" height="15" /> Start detection</button>
        )}
      </PageHeader>

      {error && <div style={{ marginBottom: 16 }}><ErrorAlert error={error} /></div>}
      {cam.status === "error" && <div className="alert alert-error" style={{ marginBottom: 16 }}>Last run failed: {cam.last_error}</div>}
      {!cam.is_active && <div className="alert alert-warn" style={{ marginBottom: 16 }}>This camera is deactivated. Edit it and tick “Active” to start detection.</div>}

      <div className="grid grid-3-1" style={{ marginBottom: 16 }}>
        <Card title="Live view">
          <LiveStream cameraId={id} running={running} />
        </Card>
        <Card title="Live stats" subtitle={running ? "Updated every second" : "Available while running"}>
          {running && live.data ? <LiveStatsPanel status={live.data} /> : <p className="muted">Start detection to see live counts.</p>}
        </Card>
      </div>

      <div className="grid grid-4" style={{ marginBottom: 16 }}>
        <div className="card"><div className="stat-label">Visitors today</div><div className="stat-value">{d ? formatNumber(d.visitors) : "—"}</div></div>
        <div className="card"><div className="stat-label">Entries / exits</div><div className="stat-value">{d ? `${d.entries} / ${d.exits}` : "—"}</div></div>
        <div className="card"><div className="stat-label">Avg presence</div><div className="stat-value">{d ? formatMinutes(d.avg_duration_seconds) : "—"}</div></div>
        <div className="card"><div className="stat-label">Peak occupancy</div><div className="stat-value">{d ? formatNumber(d.peak_occupancy) : "—"}</div></div>
      </div>

      <div className="grid grid-2" style={{ marginBottom: 16 }}>
        <Card
          title="Entry / exit line"
          subtitle={running ? "Saving restarts detection with the new line" : "Crossing in the arrow's direction counts as an entry"}
          actions={<button className="btn btn-sm" onClick={() => setFrameKey((k) => k + 1)}>Refresh frame</button>}
        >
          {lineDraft && (
            <div className="stack">
              <LineEditor cameraId={id} value={lineDraft} onChange={setLineDraft} refreshKey={frameKey} />
              {parallel && (
                <div className="alert alert-warn">
                  The entry direction runs along the line, so crossings can't be told apart. For a mostly
                  {Math.abs(lineDraft.line.x2 - lineDraft.line.x1) > Math.abs(lineDraft.line.y2 - lineDraft.line.y1) ? " horizontal line choose Up or Down." : " vertical line choose Left or Right."}
                </div>
              )}
              <div className="row">
                <label className="field" style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>Entry direction
                  <select value={lineDraft.entry_direction} onChange={(e) => setLineDraft({ ...lineDraft, entry_direction: e.target.value })}>
                    <option value="down">Down</option><option value="up">Up</option><option value="left">Left</option><option value="right">Right</option>
                  </select>
                </label>
                <span className="spacer" />
                <button className="btn" disabled={!lineDirty} onClick={() => setLineDraft({ line: cam.line, entry_direction: cam.entry_direction })}>Reset</button>
                <button className="btn btn-primary" disabled={!lineDirty || busy} onClick={() => run(async () => {
                  const updated = await camerasApi.update(id, lineDraft);
                  setLineDraft({ line: updated.line, entry_direction: updated.entry_direction });
                })}>Save line</button>
              </div>
            </div>
          )}
        </Card>

        <Card title="Camera settings" actions={!editing && <button className="btn btn-sm" onClick={() => setEditing(true)}>Edit</button>}>
          {editing ? (
            <CameraForm
              initial={cam}
              onCancel={() => setEditing(false)}
              onSubmit={async (body) => { await camerasApi.update(id, body); setEditing(false); setFrameKey((k) => k + 1); await camera.refresh(); }}
            />
          ) : (
            <>
              <dl className="kv">
                <dt>Source type</dt><dd>{cam.source_type}</dd>
                <dt>Source</dt><dd className="mono">{cam.source}</dd>
                <dt>Entry direction</dt><dd>{cam.entry_direction}</dd>
                <dt>Line</dt><dd className="mono">({cam.line.x1}, {cam.line.y1}) → ({cam.line.x2}, {cam.line.y2})</dd>
                <dt>Active</dt><dd>{cam.is_active ? "Yes" : "No"}</dd>
                <dt>Created</dt><dd>{new Date(cam.created_at).toLocaleString()}</dd>
              </dl>
              <div className="row" style={{ marginTop: 18 }}>
                {confirmDelete ? (
                  <>
                    <span className="muted">This deletes the camera and all its recorded data.</span>
                    <button className="btn btn-danger-solid btn-sm" onClick={() => run(async () => { await camerasApi.remove(id); navigate("/cameras"); })}>Delete</button>
                    <button className="btn btn-sm" onClick={() => setConfirmDelete(false)}>Cancel</button>
                  </>
                ) : (
                  <button className="btn btn-danger btn-sm" onClick={() => setConfirmDelete(true)}>Delete camera</button>
                )}
              </div>
            </>
          )}
        </Card>
      </div>

      <Card title="Recent people" subtitle="Latest presence sessions on this camera" flush>
        {sessions.data?.items?.length ? (
          <SessionsTable sessions={sessions.data.items} />
        ) : (
          <EmptyState title="No sessions yet">Tracked people will appear here once detection runs.</EmptyState>
        )}
        {d && d.visitors > 0 && <div className="pagination"><span>Longest visit today: {formatDuration(d.max_duration_seconds)}</span></div>}
      </Card>
    </>
  );
}
