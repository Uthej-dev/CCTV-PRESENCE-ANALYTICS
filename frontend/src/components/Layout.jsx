import { useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { CameraIcon, ChartIcon, DashboardIcon, HistoryIcon, LiveIcon, MenuIcon, RecordingsIcon, SettingsIcon } from "./Icons";

const NAV = [
  { to: "/", label: "Dashboard", icon: DashboardIcon, end: true },
  { to: "/live", label: "Live monitoring", icon: LiveIcon },
  { to: "/recordings", label: "Recordings", icon: RecordingsIcon },
  { to: "/cameras", label: "Cameras", icon: CameraIcon },
  { to: "/analytics", label: "Analytics", icon: ChartIcon },
  { to: "/history", label: "Entry / exit history", icon: HistoryIcon },
  { to: "/settings", label: "Settings", icon: SettingsIcon },
];

function Brand() {
  return (
    <div className="brand">
      <div className="brand-mark"><CameraIcon width="18" height="18" /></div>
      <div>CCTV Analytics<small>Human detection & presence</small></div>
    </div>
  );
}

export default function Layout() {
  const { user, logout } = useAuth();
  const [open, setOpen] = useState(false);
  const location = useLocation();
  const [lastPath, setLastPath] = useState(location.pathname);
  if (lastPath !== location.pathname) {
    // close the mobile menu after navigating
    setLastPath(location.pathname);
    setOpen(false);
  }

  return (
    <div className="app">
      <header className="topbar">
        <button onClick={() => setOpen(true)} aria-label="Open menu"><MenuIcon width="22" height="22" /></button>
        <strong>CCTV Analytics</strong>
      </header>
      <aside className={`sidebar ${open ? "open" : ""}`} onClick={(e) => e.target === e.currentTarget && setOpen(false)}>
        <Brand />
        <nav className="nav">
          {NAV.map((item) => (
            <NavLink key={item.to} to={item.to} end={item.end}>
              <item.icon /> {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-footer">
          <div className="user">{user?.full_name}</div>
          <div className="muted" style={{ overflow: "hidden", textOverflow: "ellipsis" }}>{user?.email}</div>
          <button className="btn btn-ghost btn-sm" onClick={logout}>Log out</button>
        </div>
      </aside>
      <main className="main">
        <Outlet />
      </main>
    </div>
  );
}
