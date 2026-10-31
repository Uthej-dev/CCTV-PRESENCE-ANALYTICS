import { useEffect, useRef, useState } from "react";
import { systemApi } from "../api";
import { errorMessage } from "../api/client";
import { formatBytes } from "../utils/format";

/** Select a video from the server library, or upload a new one. */
export default function VideoPicker({ value, onChange }) {
  const [videos, setVideos] = useState([]);
  const [progress, setProgress] = useState(null);
  const [error, setError] = useState(null);
  const fileRef = useRef(null);

  const load = () => systemApi.videos().then(setVideos).catch((e) => setError(errorMessage(e)));
  useEffect(() => { load(); }, []);

  const upload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setError(null);
    setProgress(0);
    try {
      const v = await systemApi.uploadVideo(file, setProgress);
      await load();
      onChange(v.name);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setProgress(null);
      e.target.value = "";
    }
  };

  return (
    <div className="stack" style={{ gap: 8 }}>
      <div className="row" style={{ flexWrap: "nowrap" }}>
        <select value={value} onChange={(e) => onChange(e.target.value)} style={{ flex: 1 }} required>
          <option value="" disabled>Select a video…</option>
          {videos.map((v) => (
            <option key={v.name} value={v.name}>{v.name} ({formatBytes(v.size_bytes)})</option>
          ))}
          {value && !videos.some((v) => v.name === value) && <option value={value}>{value} (missing)</option>}
        </select>
        <button type="button" className="btn" onClick={() => fileRef.current?.click()} disabled={progress !== null}>Upload…</button>
        <input ref={fileRef} type="file" accept="video/*" hidden onChange={upload} />
      </div>
      {progress !== null && <div className="progress" aria-label="Upload progress"><div style={{ width: `${progress}%` }} /></div>}
      {error && <div className="alert alert-error">{error}</div>}
    </div>
  );
}
