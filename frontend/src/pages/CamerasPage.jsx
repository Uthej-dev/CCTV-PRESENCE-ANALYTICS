import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { camerasApi } from "../api";
import { errorMessage } from "../api/client";
import CameraForm from "../components/CameraForm";
import { PlayIcon, PlusIcon, StopIcon } from "../components/Icons";
import { Card, EmptyState, ErrorAlert, PageHeader, Spinner, StatusBadge } from "../components/ui";
import usePolling from "../hooks/usePolling";
import { cameraStatus } from "../utils/format";

const SOURCE_LABEL = { file: "Video file", webcam: "Webcam", rtsp: "RTSP" };

export default function CamerasPage() {
  const { data: cameras, loading, refresh } = usePolling(camerasApi.list, 4000);
  const [adding, setAdding] = useState(false);
  const [busy, setBusy] = useState(null);
  const [confirmDelete, setConfirmDelete] = useState(null);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  const act = async (id, fn) => {
    setBusy(id);
    setError(null);
    try {
      await fn();
      await refresh();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(null);
      setConfirmDelete(null);
    }
  };

  const create = async (body) => {
    const cam = await camerasApi.create(body);
    setAdding(false);
    navigate(`/cameras/${cam.id}`);
  };

  return (
    <>
      <PageHeader title="Cameras" subtitle="Configure sources and start or stop detection">
        {!adding && <button className="btn btn-primary" onClick={() => setAdding(true)}><PlusIcon width="16" height="16" /> Add camera</button>}
      </PageHeader>

      {adding && (
        <Card title="New camera" subtitle="You can place the entry/exit line after saving" className="" >
          <CameraForm onSubmit={create} onCancel={() => setAdding(false)} submitLabel="Create camera" />
        </Card>
      )}
      {adding && <div style={{ height: 16 }} />}
      {error && <div style={{ marginBottom: 16 }}><ErrorAlert error={error} /></div>}

      <Card flush>
        {loading && !cameras ? (
          <div className="center"><Spinner /></div>
        ) : !cameras?.length ? (
          <EmptyState title="No cameras yet" action={!adding && <button className="btn btn-primary" onClick={() => setAdding(true)}>Add your first camera</button>}>
            Add a camera with a video file, webcam or RTSP source.
          </EmptyState>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr><th>Camera</th><th>Source</th><th>Status</th><th className="num">Actions</th></tr>
              </thead>
              <tbody>
                {cameras.map((c) => {
                  const status = cameraStatus(c);
                  const running = c.status === "running";
                  return (
                    <tr key={c.id}>
                      <td>
                        <Link to={`/cameras/${c.id}`}><strong>{c.name}</strong></Link>
                        <div className="muted" style={{ fontSize: "0.82rem" }}>{c.location || "—"}</div>
                      </td>
                      <td>
                        {SOURCE_LABEL[c.source_type]}
                        <div className="muted mono" style={{ fontSize: "0.8rem", maxWidth: 260, overflow: "hidden", textOverflow: "ellipsis" }}>{c.source}</div>
                      </td>
                      <td>
                        <StatusBadge status={status} />
                        {c.status === "error" && c.last_error && <div className="muted" style={{ fontSize: "0.8rem", maxWidth: 260, whiteSpace: "normal" }}>{c.last_error}</div>}
                      </td>
                      <td className="num">
                        <div className="row" style={{ justifyContent: "flex-end", flexWrap: "nowrap" }}>
                          {confirmDelete === c.id ? (
                            <>
                              <span className="muted">Delete camera and its data?</span>
                              <button className="btn btn-sm btn-danger-solid" disabled={busy === c.id} onClick={() => act(c.id, () => camerasApi.remove(c.id))}>Delete</button>
                              <button className="btn btn-sm" onClick={() => setConfirmDelete(null)}>Cancel</button>
                            </>
                          ) : (
                            <>
                              {running ? (
                                <button className="btn btn-sm" disabled={busy === c.id} onClick={() => act(c.id, () => camerasApi.stop(c.id))}><StopIcon width="14" height="14" /> Stop</button>
                              ) : (
                                <button className="btn btn-sm" disabled={busy === c.id || !c.is_active} title={c.is_active ? "" : "Activate the camera first"} onClick={() => act(c.id, () => camerasApi.start(c.id))}><PlayIcon width="14" height="14" /> Start</button>
                              )}
                              <Link className="btn btn-sm" to={`/cameras/${c.id}`}>Open</Link>
                              <button className="btn btn-sm btn-danger" onClick={() => setConfirmDelete(c.id)}>Delete</button>
                            </>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </>
  );
}
