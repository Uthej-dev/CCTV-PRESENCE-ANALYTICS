import { useState } from "react";
import { errorMessage } from "../api/client";
import VideoPicker from "./VideoPicker";

const EMPTY = { name: "", location: "", source_type: "file", source: "", is_active: true, entry_direction: "down" };

/** Create / edit a camera. The entry line itself is placed on the camera details page. */
export default function CameraForm({ initial, onSubmit, onCancel, submitLabel = "Save" }) {
  const [form, setForm] = useState({ ...EMPTY, ...initial });
  const [error, setError] = useState(null);
  const [saving, setSaving] = useState(false);
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e?.target ? (e.target.type === "checkbox" ? e.target.checked : e.target.value) : e }));

  const changeType = (e) => {
    const t = e.target.value;
    setForm((f) => ({ ...f, source_type: t, source: t === "webcam" ? "0" : t === "rtsp" ? "rtsp://" : "" }));
  };

  const submit = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const { name, location, source_type, source, is_active, entry_direction } = form;
      await onSubmit({ name, location, source_type, source, is_active, entry_direction });
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <form onSubmit={submit} className="stack">
      <div className="form-grid">
        <label className="field">Camera name
          <input value={form.name} onChange={set("name")} placeholder="Main Entrance" required maxLength={100} />
        </label>
        <label className="field">Location
          <input value={form.location} onChange={set("location")} placeholder="Ground floor, lobby" maxLength={200} />
        </label>
        <label className="field">Source type
          <select value={form.source_type} onChange={changeType}>
            <option value="file">Video file</option>
            <option value="webcam">Webcam</option>
            <option value="rtsp">RTSP stream</option>
          </select>
        </label>
        <label className="field">Entry direction
          <select value={form.entry_direction} onChange={set("entry_direction")}>
            <option value="down">Moving down the frame</option>
            <option value="up">Moving up the frame</option>
            <option value="left">Moving left</option>
            <option value="right">Moving right</option>
          </select>
        </label>
        <div className="field full">
          <span>Source</span>
          {form.source_type === "file" && <VideoPicker value={form.source} onChange={set("source")} />}
          {form.source_type === "webcam" && (
            <>
              <input type="number" min="0" value={form.source} onChange={set("source")} required />
              <span className="hint">Device index; 0 is the default webcam of the machine running the backend.</span>
            </>
          )}
          {form.source_type === "rtsp" && (
            <>
              <input value={form.source} onChange={set("source")} placeholder="rtsp://user:pass@192.168.1.20:554/stream1" required />
              <span className="hint">The backend must be able to reach this address.</span>
            </>
          )}
        </div>
        <label className="checkbox full">
          <input type="checkbox" checked={form.is_active} onChange={set("is_active")} /> Active (can be started)
        </label>
      </div>
      {error && <div className="alert alert-error">{error}</div>}
      <div className="row">
        <button className="btn btn-primary" disabled={saving}>{saving ? "Saving…" : submitLabel}</button>
        {onCancel && <button type="button" className="btn" onClick={onCancel}>Cancel</button>}
      </div>
    </form>
  );
}
