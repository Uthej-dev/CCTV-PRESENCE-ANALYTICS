import { useState } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";
import { errorMessage } from "../api/client";
import { useAuth } from "../context/AuthContext";

export default function LoginPage() {
  const { user, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  if (user) return <Navigate to={location.state?.from || "/"} replace />;

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await login(email, password);
      navigate(location.state?.from || "/", { replace: true });
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="card auth-card">
        <h1>Sign in</h1>
        <p className="secondary" style={{ margin: 0 }}>CCTV Human Detection & Presence Analytics</p>
        <form onSubmit={submit}>
          <label className="field">Email
            <input type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
          </label>
          <label className="field">Password
            <input type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} required />
          </label>
          {error && <div className="alert alert-error" role="alert">{error}</div>}
          <button className="btn btn-primary" disabled={busy}>{busy ? "Signing in…" : "Sign in"}</button>
        </form>
        <p className="secondary" style={{ marginBottom: 0 }}>No account? <Link to="/register">Create one</Link></p>
      </div>
    </div>
  );
}
