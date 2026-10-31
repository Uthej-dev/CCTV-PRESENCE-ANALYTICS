import axios from "axios";

export const API_URL = (import.meta.env.VITE_API_URL || "http://localhost:8000").replace(/\/$/, "");
const TOKEN_KEY = "cctv_token";

export const tokenStore = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (t) => localStorage.setItem(TOKEN_KEY, t),
  clear: () => localStorage.removeItem(TOKEN_KEY),
};

const api = axios.create({ baseURL: API_URL, timeout: 20000 });

// Attach the JWT to every request
api.interceptors.request.use((config) => {
  const token = tokenStore.get();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// A 401 anywhere means the token is missing/expired: tell the app to log out
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401 && tokenStore.get()) {
      tokenStore.clear();
      window.dispatchEvent(new Event("auth:expired"));
    }
    return Promise.reject(err);
  },
);

/** Human-readable message from an API error (FastAPI `detail` can be a string or a list). */
export function errorMessage(err) {
  const detail = err?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail.length) {
    return detail.map((d) => `${d.loc?.slice(1).join(".") || "field"}: ${d.msg}`).join("; ");
  }
  if (err?.code === "ERR_NETWORK") return "Cannot reach the server";
  return err?.message || "Something went wrong";
}

export default api;
