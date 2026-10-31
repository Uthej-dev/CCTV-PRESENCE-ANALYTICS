import api, { API_URL, tokenStore } from "./client";
import { getTimezone } from "../utils/format";

const tz = () => getTimezone();
const data = (p) => p.then((r) => r.data);

// Auth
export const authApi = {
  register: (body) => data(api.post("/auth/register", body)),
  login: (body) => data(api.post("/auth/login", body)),
  me: () => data(api.get("/auth/me")),
  logout: () => api.post("/auth/logout").catch(() => {}),
};

// Cameras
export const camerasApi = {
  list: () => data(api.get("/cameras")),
  get: (id) => data(api.get(`/cameras/${id}`)),
  create: (body) => data(api.post("/cameras", body)),
  update: (id, body) => data(api.put(`/cameras/${id}`, body)),
  remove: (id) => api.delete(`/cameras/${id}`),
  start: (id) => data(api.post(`/cameras/${id}/start`)),
  stop: (id) => api.post(`/cameras/${id}/stop`),
  live: (id) => data(api.get(`/cameras/${id}/live`)),
  // <img> tags can't send headers, so these URLs carry the token as a query param
  streamUrl: (id) => `${API_URL}/cameras/${id}/stream?token=${tokenStore.get()}`,
  snapshotUrl: (id) => `${API_URL}/cameras/${id}/snapshot?token=${tokenStore.get()}&t=${Date.now()}`,
};

// Presence / tracking / events
export const presenceApi = {
  current: () => data(api.get("/presence/current")),
  detections: (camera_id) => data(api.get("/detections", { params: { camera_id } })),
  sessions: (params) => data(api.get("/tracking", { params })),
  events: (params) => data(api.get("/events", { params })),
};

// Video recordings
export const recordingsApi = {
  list: (params) => data(api.get("/recordings", { params })),
  at: (params) => data(api.get("/recordings/at", { params })),
  remove: (id) => api.delete(`/recordings/${id}`),
  // <video>/<img> can't send headers, so the token goes in the URL
  videoUrl: (id) => `${API_URL}/recordings/${id}/video?token=${tokenStore.get()}`,
  posterUrl: (id) => `${API_URL}/recordings/${id}/poster?token=${tokenStore.get()}`,
};

// Analytics (always sent with the user's timezone)
export const analyticsApi = {
  daily: (params = {}) => data(api.get("/analytics/daily", { params: { tz: tz(), ...params } })),
  weekly: (params = {}) => data(api.get("/analytics/weekly", { params: { tz: tz(), ...params } })),
  occupancy: (params = {}) => data(api.get("/analytics/occupancy", { params: { tz: tz(), ...params } })),
};

// System / videos
export const systemApi = {
  health: () => data(api.get("/health")),
  info: () => data(api.get("/system/info")),
  videos: () => data(api.get("/videos")),
  uploadVideo: (file, onProgress) => {
    const form = new FormData();
    form.append("file", file);
    return data(
      api.post("/videos", form, {
        timeout: 0,
        onUploadProgress: (e) => e.total && onProgress?.(Math.round((e.loaded / e.total) * 100)),
      }),
    );
  },
};
