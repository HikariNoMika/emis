import { BrowserRouter, Route, Routes } from 'react-router-dom'
import MainLayout from './components/layout/MainLayout'
import AccomplishmentPage from './pages/AccomplishmentPage'
import AlertsPage from './pages/AlertsPage'
import AnalyticsPage from './pages/AnalyticsPage'
import AuditLogsPage from './pages/AuditLogsPage'
import DataQualityPage from './pages/DataQualityPage'
import ComparisonPage from './pages/ComparisonPage'
import DashboardPage from './pages/DashboardPage'
import DataManagementPage from './pages/DataManagementPage'
import LatestMonitoringPage from './pages/LatestMonitoringPage'
import LoginPage from './pages/LoginPage'
import MaintenancePage from './pages/MaintenancePage'
import NotFoundPage from './pages/NotFoundPage'
import ProfilePage from './pages/ProfilePage'
import ReportsPage from './pages/ReportsPage'
import SensorDetailPage from './pages/SensorDetailPage'
import StationHealthPage from './pages/StationHealthPage'
import SystemSettingsPage from './pages/SystemSettingsPage'
import SensorsPage from './pages/SensorsPage'
import StationDetailPage from './pages/StationDetailPage'
import StationMapPage from './pages/StationMapPage'
import StationsPage from './pages/StationsPage'
import StationAnalyticsPage from './pages/StationAnalyticsPage'
import UsersPage from './pages/UsersPage'
import ProtectedRoute from './routes/ProtectedRoute'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />

        {/* Every page below requires a valid administrator session. */}
        <Route
          element={
            <ProtectedRoute>
              <MainLayout />
            </ProtectedRoute>
          }
        >
          <Route index element={<DashboardPage />} />
          <Route path="map" element={<StationMapPage />} />
          <Route path="stations" element={<StationsPage />} />
          <Route path="stations/:id" element={<StationDetailPage />} />
          <Route path="stations/:id/analytics" element={<StationAnalyticsPage />} />
          <Route path="sensors" element={<SensorsPage />} />
          <Route path="sensors/:id" element={<SensorDetailPage />} />
          <Route path="data-management" element={<DataManagementPage />} />
          <Route path="analytics" element={<AnalyticsPage />} />
          <Route path="latest" element={<LatestMonitoringPage />} />
          <Route path="comparison" element={<ComparisonPage />} />
          <Route path="health" element={<StationHealthPage />} />
          <Route path="data-quality" element={<DataQualityPage />} />
          <Route path="alerts" element={<AlertsPage />} />
          <Route path="reports" element={<ReportsPage />} />
          <Route path="maintenance" element={<MaintenancePage />} />
          <Route path="settings" element={<SystemSettingsPage />} />
          <Route path="users" element={<UsersPage />} />
          <Route path="profile" element={<ProfilePage />} />
          <Route path="accomplishment" element={<AccomplishmentPage section="dashboard" />} />
          <Route path="accomplishment/indicators" element={<AccomplishmentPage section="indicators" />} />
          <Route path="accomplishment/targets" element={<AccomplishmentPage section="targets" />} />
          <Route path="accomplishment/actuals" element={<AccomplishmentPage section="actuals" />} />
          <Route path="accomplishment/weights" element={<AccomplishmentPage section="weights" />} />
          <Route path="accomplishment/annual" element={<AccomplishmentPage section="annual" />} />
          <Route path="accomplishment/reports" element={<AccomplishmentPage section="reports" />} />
          <Route path="audit-logs" element={<AuditLogsPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
