import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { LoginForm } from '../modules/auth/components/LoginForm'
import { ProtectedRoute } from './ProtectedRoute'
import { MainLayout } from '../modules/layout/components/MainLayout'
import { DashboardView } from '../modules/dashboard/components/DashboardView'
import { AgendaView } from '../modules/agenda/components/AgendaView'
import { HistorialPacientesView } from '../modules/pacientes/components/HistorialPacientesView'
import { ConfiguracionesView } from '../components/ConfiguracionesView'
import { SettingsPage } from '../modules/settings'
import { AuditPage } from '../modules/audit/pages/AuditPage'

const UnauthorizedPage = () => (
  <div className="min-h-screen flex items-center justify-center bg-gray-50">
    <div className="text-center">
      <h1 className="text-4xl font-bold text-gray-900 mb-4">403</h1>
      <p className="text-xl text-gray-600 mb-8">No tienes permiso para acceder a esta página</p>
      <a href="/dashboard" className="text-blue-600 hover:underline">Volver al Dashboard</a>
    </div>
  </div>
)

export const AppRoutes = () => (
  <BrowserRouter>
    <Routes>
      <Route path="/login" element={<LoginForm />} />
      
      <Route element={<ProtectedRoute />}>
        <Route element={<MainLayout />}>
          <Route path="/dashboard" element={<DashboardView />} />
          <Route path="/agenda" element={<AgendaView />} />
          <Route path="/settings" element={<SettingsPage />} />
          
          <Route element={<ProtectedRoute allowedRoles={['Admin', 'Podologo']} />}>
            <Route path="/historial-pacientes" element={<HistorialPacientesView />} />
            <Route path="/auditoria" element={<AuditPage />} />
          </Route>
          
          <Route element={<ProtectedRoute allowedRoles={['Admin']} />}>
            <Route path="/configuraciones" element={<ConfiguracionesView />} />
          </Route>
        </Route>
      </Route>
      
      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="/unauthorized" element={<UnauthorizedPage />} />
    </Routes>
  </BrowserRouter>
)
