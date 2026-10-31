import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { camerasApi, recordingsApi } from "../api";
import { errorMessage } from "../api/client";
import ClipPlayer from "../components/ClipPlayer";
import { Card, EmptyState, ErrorAlert, PageHeader, Pagination, Spinner } from "../components/ui";
import usePolling from "../hooks/usePolling";
import { dayRangeISO, formatBytes, formatDuration, formatTime, todayISO, zonedToUtcISO } from "../utils/format";

const LIMIT = 24;

export default function RecordingsPage() {
  // Filters live in the URL so other pages can link here, e.g. History -> "Video" (?at=...)
  const [params, setParams] = useSearchParams();
  const cameraId = params.get("camera") || "";
  const date = params.get("date") || todayISO();
  const fromTime = params.get("time") || "";
  const minPeople = params.get("min") || "";
  const personId = params.get("person") || "";
  const at = params.get("at");
  const [skip, setSkip] = useState(0);
  const [player, setPlayer] = useState(null); // { clip, startAt, index }
  const [error, setError] = useState(null);

  const setParam = (key, value) => {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    next.delete("at");
    setParams(next, { replace: true });
    setSkip(0);
  };

  const cameras = usePolling(camerasApi.list, 0);
  const cameraNames = Object.fromEntries((cameras.data || []).map((c) => [c.id, c.name]));

  const query = () => {
    const range = dayRangeISO(date);
    return recordingsApi.list({
      camera_id: cameraId || undefined,
      start: fromTime ? zonedToUtcISO(date, fromTime) : range.start,
      end: range.end,
      min_people: minPeople || undefined,
      person_id: personId || undefined,
      order: fromTime ? "oldest" : "newest", // "from 10:30" reads forwards in time
      skip,
      limit: LIMIT,
    });
  };
  // Refresh while looking at today (new clips appear); pause while a clip is playing
  const live = date === todayISO() && !fromTime && player === null;
  const result = usePolling(query, live ? 8000 : 0, [cameraId, date, fromTime, minPeople, personId, skip]);
  const items = result.data?.items || [];

  // Deep link: ?at=<ISO> opens the clip covering that moment, already seeked to it
  useEffect(() => {
    if (!at) return;
    recordingsApi
      .at({ at, camera_id: cameraId || undefined })
      .then(({ recording, offset_seconds }) => setPlayer({ clip: recording, startAt: offset_seconds, index: -1 }))
      .catch((err) => setError(err.response?.status === 404 ? "No video was recorded around that moment (recordings exist only while a camera is running)." : errorMessage(err)));
  }, [at, cameraId]);

  const open = (index) => setPlayer({ clip: items[index], startAt: 0, index });
  const close = () => {
    setPlayer(null);
    if (at) setParam("at", "");
  };
  const remove = async () => {
    try {
      await recordingsApi.remove(player.clip.id);
      setPlayer(null);
      result.refresh();
    } catch (err) {
      setError(errorMessage(err));
    }
  };

  return (
    <>
      <PageHeader title="Recordings" subtitle="Video is recorded automatically while people are in view, from 2 s before they appear until 5 s after the last one leaves" />

      <div className="row" style={{ marginBottom: 16 }}>
        <select value={cameraId} onChange={(e) => setParam("camera", e.target.value)} aria-label="Camera">
          <option value="">All cameras</option>
          {(cameras.data || []).map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
        </select>
        <input type="date" value={date} max={todayISO()} onChange={(e) => setParam("date", e.target.value)} aria-label="Day" />
        <label className="row" style={{ gap: 6 }}>
          <span className="secondary">From</span>
          <input type="time" value={fromTime} onChange={(e) => setParam("time", e.target.value)} aria-label="From time" />
        </label>
        <select value={minPeople} onChange={(e) => setParam("min", e.target.value)} aria-label="Minimum people">
          <option value="">Any number of people</option>
          {[2, 3, 4, 5].map((n) => <option key={n} value={n}>{n}+ people at once</option>)}
        </select>
        {personId && (
          <button className="badge badge-idle" style={{ border: 0, cursor: "pointer" }} onClick={() => setParam("person", "")} title="Clear person filter">
            Person {personId} ✕
          </button>
        )}
      </div>

      {(error || result.error) && <div style={{ marginBottom: 16 }}><ErrorAlert error={error || errorMessage(result.error)} /></div>}

      <Card flush>
        {result.loading && !result.data ? (
          <div className="center"><Spinner /></div>
        ) : items.length === 0 ? (
          <EmptyState title="No recordings">
            Clips are recorded while a camera is running and people are in view. Try another day or remove filters.
          </EmptyState>
        ) : (
          <div className="frame-grid">
            {items.map((r, i) => {
              const recording = r.status === "recording";
              return (
                <button key={r.id} className="frame-card" onClick={() => !recording && open(i)} disabled={recording}>
                  <div className="clip-thumb">
                    {recording ? (
                      <div className="clip-recording"><span className="rec-dot" /> Recording…</div>
                    ) : (
                      <>
                        <img src={recordingsApi.posterUrl(r.id)} alt={`Recording at ${formatTime(r.start_time)}`} loading="lazy" />
                        <span className="clip-play" aria-hidden="true">▶</span>
                        <span className="clip-duration">{formatDuration(r.duration_seconds)}</span>
                      </>
                    )}
                  </div>
                  <div className="frame-info">
                    <span className="mono">{formatTime(r.start_time)}</span>
                    <span className="frame-count">up to {r.max_people} {r.max_people === 1 ? "person" : "people"}</span>
                  </div>
                  <div className="frame-sub">
                    <span>{r.entries} in · {r.exits} out{recording ? "" : ` · ${formatBytes(r.size_bytes)}`}</span>
                    {!cameraId && <span>{cameraNames[r.camera_id]}</span>}
                  </div>
                </button>
              );
            })}
          </div>
        )}
        {result.data && result.data.total > 0 && <Pagination skip={skip} limit={LIMIT} total={result.data.total} onChange={setSkip} />}
      </Card>

      {player && (
        <ClipPlayer
          clip={player.clip}
          startAt={player.startAt}
          cameraName={cameraNames[player.clip.camera_id]}
          onClose={close}
          onDelete={remove}
          onPrev={player.index > 0 ? () => open(player.index - 1) : null}
          onNext={player.index >= 0 && player.index < items.length - 1 && items[player.index + 1].status === "complete" ? () => open(player.index + 1) : null}
        />
      )}
    </>
  );
}
