import { useState } from "react";
import { camerasApi } from "../api";

/** MJPEG stream rendered by a plain <img>; the browser keeps the connection open. */
export default function LiveStream({ cameraId, running, label = "LIVE" }) {
  const [failed, setFailed] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const [prevRunning, setPrevRunning] = useState(running);
  if (prevRunning !== running) {
    setPrevRunning(running);
    setFailed(false);
    setAttempt((a) => a + 1);
  }

  if (!running) {
    return (
      <div className="video-frame">
        <div className="overlay-msg">Camera is not running. Start it to see the live feed.</div>
      </div>
    );
  }
  return (
    <div className="video-frame">
      {failed ? (
        <div className="overlay-msg">
          Stream unavailable.
          <div><button className="btn btn-sm" style={{ marginTop: 10 }} onClick={() => { setFailed(false); setAttempt((a) => a + 1); }}>Retry</button></div>
        </div>
      ) : (
        <>
          <img key={attempt} src={`${camerasApi.streamUrl(cameraId)}&a=${attempt}`} alt="Live camera feed with detections" onError={() => setFailed(true)} />
          <span className="live-pill"><span className="live-dot" /> {label}</span>
        </>
      )}
    </div>
  );
}
