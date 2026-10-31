import { useMemo, useState } from "react";
import { systemApi } from "../api";
import { API_URL } from "../api/client";
import VideoPicker from "../components/VideoPicker";
import { Card, PageHeader } from "../components/ui";
import { useAuth } from "../context/AuthContext";
import usePolling from "../hooks/usePolling";
import { browserTimezone, getTimezone, setTimezone } from "../utils/format";

export default function SettingsPage() {
  const { user, logout } = useAuth();
  const info = usePolling(systemApi.info, 0);
  const health = usePolling(systemApi.health, 10000);
  const [tz, setTz] = useState(localStorage.getItem("cctv_timezone") || "");
  const [saved, setSaved] = useState(false);
  const [video, setVideo] = useState("");
  const zones = useMemo(() => (Intl.supportedValuesOf ? Intl.supportedValuesOf("timeZone") : [browserTimezone()]), []);

  const saveTz = (value) => {
    setTz(value);
    setTimezone(value);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };
  const i = info.data;
  const h = health.data;

  return (
    <>
      <PageHeader title="Settings" subtitle="Account, preferences and system information" />
      <div className="grid grid-2">
        <Card title="Account">
          <dl className="kv">
            <dt>Name</dt><dd>{user.full_name}</dd>
            <dt>Email</dt><dd>{user.email}</dd>
            <dt>Member since</dt><dd>{new Date(user.created_at).toLocaleDateString()}</dd>
          </dl>
          <button className="btn" style={{ marginTop: 18 }} onClick={logout}>Log out</button>
        </Card>

        <Card title="Timezone" subtitle="Used for “today”, hourly charts and all displayed times">
          <label className="field">
            Display timezone
            <select value={tz} onChange={(e) => saveTz(e.target.value)}>
              <option value="">Browser default ({browserTimezone()})</option>
              {zones.map((z) => <option key={z} value={z}>{z}</option>)}
            </select>
          </label>
          <p className="muted" style={{ marginBottom: 0 }}>Currently using <strong className="secondary">{getTimezone()}</strong>{saved && " — saved"}</p>
        </Card>

        <Card title="System">
          <dl className="kv">
            <dt>API</dt><dd>{h ? <span className={`badge ${h.status === "ok" ? "badge-running" : "badge-error"}`}>{h.status}</span> : "…"}</dd>
            <dt>Database</dt><dd>{h?.database || "…"}</dd>
            <dt>API URL</dt><dd className="mono">{API_URL}</dd>
            <dt>Environment</dt><dd>{i?.environment || "…"}</dd>
            <dt>Model</dt><dd className="mono">{i?.yolo_model || "…"}</dd>
            <dt>Inference device</dt><dd>{i?.yolo_device || "…"}</dd>
            <dt>Processing rate</dt><dd>{i ? `${i.process_fps} fps per camera` : "…"}</dd>
            <dt>Running cameras</dt><dd>{i ? `${i.running_cameras} of ${i.max_running_cameras} max` : "…"}</dd>
            <dt>Visit threshold</dt><dd>{i ? `${i.min_visit_seconds}s minimum presence` : "…"}</dd>
          </dl>
          <a className="btn btn-sm" style={{ marginTop: 18 }} href={`${API_URL}/docs`} target="_blank" rel="noreferrer">Open API docs</a>
        </Card>

        <Card title="Video library" subtitle={`Files available as camera sources${i ? ` · max ${i.max_upload_mb} MB per upload` : ""}`}>
          <VideoPicker value={video} onChange={setVideo} />
          <p className="muted" style={{ marginBottom: 0, fontSize: "0.85rem" }}>
            Uploaded videos are stored on the server and play in a loop like a live camera.
          </p>
        </Card>
      </div>
    </>
  );
}
