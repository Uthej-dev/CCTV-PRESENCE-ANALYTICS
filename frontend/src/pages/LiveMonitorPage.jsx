import { useState } from "react";
import { Link } from "react-router-dom";
import { camerasApi, presenceApi } from "../api";
import { errorMessage } from "../api/client";
import { PlayIcon } from "../components/Icons";
import LiveStream from "../components/LiveStream";
import { Card, EmptyState, ErrorAlert, PageHeader, Spinner } from "../components/ui";
import usePolling from "../hooks/usePolling";
import { formatDuration, formatTime } from "../utils/format";

export function LiveStatsPanel({ status }) {
  return (
    <div className="stack" style={{ gap: 14 }}>
      <div className="grid" style={{ gridTemplateColumns: "repeat(2, minmax(0,1fr))", gap: 10 }}>
        <Metric label="In view" value={status.in_view} big />
        <Metric label="Inside (net)" value={status.inside} big />
        <Metric label="Entries" value={status.entries} />
        <Metric label="Exits" value={status.exits} />
      </div>
      <div className="row muted" style={{ fontSize: "0.82rem", justifyContent: "space-between" }}>
        <span>
          Detection: <strong className="secondary">{status.state}</strong>
          {status.recording && <span className="rec-badge"><span className="rec-dot" /> REC</span>}
        </span>
        <span>{status.fps} fps · {status.frame_width}×{status.frame_height}</span>
      </div>
      <div>
        <h3 style={{ marginBottom: 8 }}>People in view</h3>
        {status.people.length ? (
          <div className="people-list">
            {status.people.map((p) => (
              <div className="person-row" key={p.person_id}>
                <span className="mono">{p.person_id}</span>
                <span className="muted">since {formatTime(p.first_seen)}</span>
                <strong>{formatDuration(p.duration_seconds)}</strong>
              </div>
            ))}
          </div>
        ) : (
          <p className="muted" style={{ margin: 0 }}>Nobody in view.</p>
        )}
      </div>
    </div>
  );
}

function Metric({ label, value, big }) {
  return (
    <div style={{ background: "var(--surface-2)", borderRadius: 8, padding: "10px 12px" }}>
      <div className="stat-label">{label}</div>
      <div style={{ fontSize: big ? "1.7rem" : "1.2rem", fontWeight: 600 }}>{value}</div>
    </div>
  );
}

export default function LiveMonitorPage() {
  const presence = usePolling(presenceApi.current, 1000);
  const cameras = usePolling(camerasApi.list, 5000);
  const [starting, setStarting] = useState(null);
  const [error, setError] = useState(null);

  const running = presence.data?.cameras || [];
  const idle = (cameras.data || []).filter((c) => c.is_active && c.status !== "running");

  const start = async (id) => {
    setStarting(id);
    setError(null);
    try {
      await camerasApi.start(id);
      await Promise.all([presence.refresh(), cameras.refresh()]);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setStarting(null);
    }
  };

  return (
    <>
      <PageHeader title="Live monitoring" subtitle="Detections, tracking IDs and the entry line, in real time">
        {presence.data && <span className="badge badge-running">{presence.data.in_view} people in view</span>}
      </PageHeader>
      {error && <div style={{ marginBottom: 16 }}><ErrorAlert error={error} /></div>}

      {presence.loading && !presence.data ? (
        <div className="center"><Spinner /></div>
      ) : running.length === 0 ? (
        <Card>
          <EmptyState title="No cameras are running">
            {idle.length ? "Start a camera to watch it live." : <>Add or activate a camera on the <Link to="/cameras">Cameras</Link> page.</>}
          </EmptyState>
          {idle.length > 0 && (
            <div className="stack" style={{ gap: 8, maxWidth: 520, margin: "0 auto 12px" }}>
              {idle.map((c) => (
                <div className="person-row" key={c.id} style={{ alignItems: "center" }}>
                  <span><strong>{c.name}</strong> <span className="muted">· {c.location || c.source}</span></span>
                  <button className="btn btn-sm btn-primary" disabled={starting === c.id} onClick={() => start(c.id)}>
                    <PlayIcon width="13" height="13" /> {starting === c.id ? "Starting…" : "Start"}
                  </button>
                </div>
              ))}
            </div>
          )}
        </Card>
      ) : (
        <div className="stack">
          {running.map((status) => (
            <div className="grid grid-3-1" key={status.camera_id}>
              <Card title={status.camera_name} actions={<Link className="btn btn-sm" to={`/cameras/${status.camera_id}`}>Camera details</Link>}>
                <LiveStream cameraId={status.camera_id} running={status.state === "running" || status.state === "starting"} />
              </Card>
              <Card title="Live stats">
                {status.state === "starting" ? <p className="muted">Loading model and opening source…</p> : <LiveStatsPanel status={status} />}
              </Card>
            </div>
          ))}
        </div>
      )}
    </>
  );
}
