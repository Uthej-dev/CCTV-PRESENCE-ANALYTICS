import { Link } from "react-router-dom";
import { formatDuration, formatTime, localDateISO } from "../utils/format";

/** Open the recording at the moment this person crossed the line (or was first seen). */
const videoLink = (s) => `/recordings?camera=${s.camera_id}&date=${localDateISO(s.first_seen)}&at=${encodeURIComponent(s.entry_time || s.exit_time || s.first_seen)}`;

/** Person presence sessions: ID, entry, exit, duration. */
export default function SessionsTable({ sessions, cameraNames = {}, showDate = false, formatter }) {
  const fmt = formatter || formatTime;
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Person</th>
            {Object.keys(cameraNames).length > 1 && <th>Camera</th>}
            <th>{showDate ? "First seen" : "Seen"}</th>
            <th>Entry</th>
            <th>Exit</th>
            <th className="num">Duration</th>
            <th>Status</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {sessions.map((s) => (
            <tr key={s.id}>
              <td className="mono">{s.person_id}</td>
              {Object.keys(cameraNames).length > 1 && <td>{cameraNames[s.camera_id] || "—"}</td>}
              <td className="mono">{fmt(s.first_seen)}</td>
              <td className="mono">{s.entry_time ? fmt(s.entry_time) : "—"}</td>
              <td className="mono">{s.exit_time ? fmt(s.exit_time) : "—"}</td>
              <td className="num">{formatDuration(s.duration_seconds)}</td>
              <td>{s.status === "active" ? <span className="badge badge-running">In view</span> : <span className="muted">Left</span>}</td>
              <td className="num"><Link className="btn btn-sm" to={videoLink(s)}>▶ Video</Link></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
