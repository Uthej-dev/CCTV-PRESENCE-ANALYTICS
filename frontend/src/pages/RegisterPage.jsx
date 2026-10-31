import { useRef, useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { errorMessage } from "../api/client";
import { useAuth } from "../context/AuthContext";

export default function RegisterPage() {
  const { user, register } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ full_name: "", email: "", password: "" });
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));
  const justRegistered = useRef(false);

  // Already logged in when arriving here -> dashboard. After registering, new users go to Cameras.
  if (user) return <Navigate to={justRegistered.current ? "/cameras" : "/"} replace />;

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      justRegistered.current = true;
      await register(form);
      navigate("/cameras", { replace: true });
    } catch (err) {
      justRegistered.current = false;
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="card auth-card">
        <h1>Create account</h1>
        <p className="secondary" style={{ margin: 0 }}>Start monitoring your cameras</p>
        <form onSubmit={submit}>
          <label className="field">Full name
            <input autoComplete="name" value={form.full_name} onChange={set("full_name")} required maxLength={100} />
          </label>
          <label className="field">Email
            <input type="email" autoComplete="email" value={form.email} onChange={set("email")} required />
          </label>
          <label className="field">Password
            <input type="password" autoComplete="new-password" value={form.password} onChange={set("password")} required minLength={8} maxLength={72} />
            <span className="hint">At least 8 characters</span>
          </label>
          {error && <div className="alert alert-error" role="alert">{error}</div>}
          <button className="btn btn-primary" disabled={busy}>{busy ? "Creating…" : "Create account"}</button>
        </form>
        <p className="secondary" style={{ marginBottom: 0 }}>Already registered? <Link to="/login">Sign in</Link></p>
      </div>
    </div>
  );
}
