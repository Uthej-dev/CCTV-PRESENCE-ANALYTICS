import { useState } from "react";
import { camerasApi } from "../api";

const ARROWS = { down: [0, 1], up: [0, -1], left: [-1, 0], right: [1, 0] };

/**
 * Shows a frame from the camera and lets the user click two points to place the entry line.
 * value = { line: {x1,y1,x2,y2} (0..1), entry_direction }
 */
export default function LineEditor({ cameraId, value, onChange, refreshKey }) {
  const [pending, setPending] = useState(null); // first clicked point
  const [imgError, setImgError] = useState(false);
  const [size, setSize] = useState({ w: 16, h: 9 });
  const { line, entry_direction: dir } = value;

  const onClick = (e) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const p = {
      x: Math.min(1, Math.max(0, (e.clientX - rect.left) / rect.width)),
      y: Math.min(1, Math.max(0, (e.clientY - rect.top) / rect.height)),
    };
    if (!pending) return setPending(p);
    if (Math.hypot(p.x - pending.x, p.y - pending.y) < 0.02) return; // ignore a double click on the same spot
    onChange({ ...value, line: { x1: +pending.x.toFixed(3), y1: +pending.y.toFixed(3), x2: +p.x.toFixed(3), y2: +p.y.toFixed(3) } });
    setPending(null);
  };

  const mx = (line.x1 + line.x2) / 2;
  const my = (line.y1 + line.y2) / 2;
  const [ax, ay] = ARROWS[dir];
  // arrow length in normalised units, corrected for aspect ratio so it looks the same length both ways
  const len = 0.08;
  const ex = mx + ax * len * (size.h / size.w);
  const ey = my + ay * len;

  return (
    <div className="stack" style={{ gap: 10 }}>
      <div className="line-editor" onClick={onClick} style={{ background: "#000", borderRadius: 8, overflow: "hidden" }}>
        {imgError ? (
          <div className="video-frame"><div className="overlay-msg">Could not load a frame from this source.</div></div>
        ) : (
          <img
            src={camerasApi.snapshotUrl(cameraId) + `&k=${refreshKey}`}
            alt="Camera frame for placing the entry line"
            style={{ display: "block", width: "100%" }}
            onLoad={(e) => setSize({ w: e.target.naturalWidth, h: e.target.naturalHeight })}
            onError={() => setImgError(true)}
            draggable={false}
          />
        )}
        <svg viewBox="0 0 1 1" preserveAspectRatio="none">
          <defs>
            <marker id="arrowhead" markerWidth="6" markerHeight="6" refX="3" refY="3" orient="auto" markerUnits="strokeWidth">
              <path d="M0,0 L6,3 L0,6 z" fill="#ffc400" />
            </marker>
          </defs>
          <line x1={line.x1} y1={line.y1} x2={line.x2} y2={line.y2} stroke="#ffc400" strokeWidth="3" vectorEffect="non-scaling-stroke" />
          <line x1={mx} y1={my} x2={ex} y2={ey} stroke="#ffc400" strokeWidth="2.5" vectorEffect="non-scaling-stroke" markerEnd="url(#arrowhead)" />
          {pending && <circle cx={pending.x} cy={pending.y} r="0.012" fill="#ffc400" />}
        </svg>
      </div>
      <div className="muted" style={{ fontSize: "0.85rem" }}>
        {pending ? "Now click the second point of the line." : "Click two points on the frame to draw the entry/exit line. The arrow shows the entry direction."}
      </div>
    </div>
  );
}
