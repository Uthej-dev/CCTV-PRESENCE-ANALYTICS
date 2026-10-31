import { useEffect, useMemo, useRef, useState } from "react";
import { recordingsApi } from "../api";
import { addSeconds, formatClock, formatDuration, formatTime } from "../utils/format";

/** Moments worth jumping to: line crossings and changes in how many people are in view. */
function moments(clip) {
  const list = clip.events.map((e) => ({
    offset: e.offset,
    kind: e.type,
    label: `${e.person_id} ${e.type === "entry" ? "entered" : "exited"}`,
  }));
  clip.marks.forEach((m, i) => {
    if (i === 0 && m.in_view === 0) return; // pre-roll start
    list.push({ offset: m.offset, kind: "count", label: m.in_view === 0 ? "Everyone left" : `${m.in_view} ${m.in_view === 1 ? "person" : "people"} in view` });
  });
  return list.sort((a, b) => a.offset - b.offset);
}

/** Modal video player for a recording, with a clickable timeline of moments. */
export default function ClipPlayer({ clip, startAt = 0, cameraName, onClose, onPrev, onNext, onDelete }) {
  const video = useRef(null);
  const [time, setTime] = useState(startAt);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const items = useMemo(() => moments(clip), [clip]);
  const duration = clip.duration_seconds || 1;

  useEffect(() => {
    const onKey = (e) => {
      if (e.key === "Escape") onClose();
      if (e.key === "ArrowLeft" && e.shiftKey && onPrev) onPrev();
      if (e.key === "ArrowRight" && e.shiftKey && onNext) onNext();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose, onPrev, onNext]);

  const seek = (offset) => {
    if (!video.current) return;
    video.current.currentTime = Math.max(0, offset - 1); // start 1 s before the moment
    video.current.play().catch(() => {});
  };

  return (
    <div className="viewer" role="dialog" aria-modal="true" aria-label="Recording" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="viewer-inner">
        <div className="viewer-bar">
          <div>
            <strong>{formatTime(clip.start_time)} – {formatTime(clip.end_time)}</strong>
            <span className="viewer-meta">
              {cameraName && <>{cameraName} · </>}{formatDuration(clip.duration_seconds)} · up to {clip.max_people} {clip.max_people === 1 ? "person" : "people"}
            </span>
          </div>
          <div className="row">
            {onPrev && <button className="btn btn-sm" onClick={onPrev} title="Shift + ←">‹ Newer</button>}
            {onNext && <button className="btn btn-sm" onClick={onNext} title="Shift + →">Older ›</button>}
            <button className="btn btn-sm" onClick={onClose} aria-label="Close">Close ✕</button>
          </div>
        </div>

        <video
          key={clip.id}
          ref={video}
          className="viewer-video"
          src={recordingsApi.videoUrl(clip.id)}
          poster={recordingsApi.posterUrl(clip.id)}
          controls
          autoPlay
          muted
          playsInline
          onLoadedMetadata={(e) => { if (startAt) e.currentTarget.currentTime = startAt; }}
          onTimeUpdate={(e) => setTime(e.currentTarget.currentTime)}
        />

        {/* timeline: event ticks + playhead; click anywhere to seek */}
        <div
          className="clip-track"
          onClick={(e) => {
            const r = e.currentTarget.getBoundingClientRect();
            seek(((e.clientX - r.left) / r.width) * duration + 1);
          }}
          title="Click to seek"
        >
          {items.filter((m) => m.kind !== "count").map((m, i) => (
            <span key={i} className={`clip-tick ${m.kind}`} style={{ left: `${(m.offset / duration) * 100}%` }} />
          ))}
          <span className="clip-playhead" style={{ left: `${Math.min(100, (time / duration) * 100)}%` }} />
        </div>

        <div className="viewer-bar">
          <span className="viewer-meta">
            Showing <strong style={{ color: "#fff" }}>{formatTime(addSeconds(clip.start_time, time))}</strong> · {formatClock(time)} / {formatClock(duration)}
          </span>
          <span className="viewer-meta">
            {confirmDelete ? (
              <>Delete this recording? <button className="btn btn-sm btn-danger-solid" onClick={onDelete}>Delete</button>{" "}
                <button className="btn btn-sm" onClick={() => setConfirmDelete(false)}>Cancel</button></>
            ) : (
              onDelete && <button className="btn btn-sm btn-ghost" style={{ color: "#c9c9c9" }} onClick={() => setConfirmDelete(true)}>Delete recording</button>
            )}
          </span>
        </div>

        {items.length > 0 && (
          <div className="moments" aria-label="Jump to moment">
            {items.map((m, i) => (
              <button key={i} className={`moment ${m.kind}`} onClick={() => seek(m.offset)}>
                <span className="mono">{formatTime(addSeconds(clip.start_time, m.offset))}</span> {m.label}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
