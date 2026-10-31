import { Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import ProtectedRoute from "./components/ProtectedRoute";
import AnalyticsPage from "./pages/AnalyticsPage";
import CameraDetailPage from "./pages/CameraDetailPage";
import CamerasPage from "./pages/CamerasPage";
import DashboardPage from "./pages/DashboardPage";
import HistoryPage from "./pages/HistoryPage";
import LiveMonitorPage from "./pages/LiveMonitorPage";
import LoginPage from "./pages/LoginPage";
import NotFoundPage from "./pages/NotFoundPage";
import RecordingsPage from "./pages/RecordingsPage";
import RegisterPage from "./pages/RegisterPage";
import SettingsPage from "./pages/SettingsPage";

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route element={<ProtectedRoute><Layout /></ProtectedRoute>}>
        <Route index element={<DashboardPage />} />
        <Route path="live" element={<LiveMonitorPage />} />
        <Route path="recordings" element={<RecordingsPage />} />
        <Route path="cameras" element={<CamerasPage />} />
        <Route path="cameras/:id" element={<CameraDetailPage />} />
        <Route path="analytics" element={<AnalyticsPage />} />
        <Route path="history" element={<HistoryPage />} />
        <Route path="settings" element={<SettingsPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}
