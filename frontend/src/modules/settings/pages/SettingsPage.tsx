// ============================================================================
// PÁGINA DE CONFIGURACIÓN DEL SISTEMA
// ============================================================================
// Página principal de configuración donde se agrupan todos los ajustes
// del sistema, incluyendo la configuración de API Keys de Gemini
// ============================================================================

import { Gear, UserCircle, Bell, Shield, Key } from '@phosphor-icons/react'
import { GeminiKeySettings } from '../components/GeminiKeySettings'
import { useAuthStore } from '../../auth/stores/authStore'

export const SettingsPage = () => {
  const { user } = useAuthStore()

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
            <Gear size={32} weight="duotone" className="text-blue-600" />
            Configuración
          </h1>
          <p className="text-gray-600 mt-1">
            Administra las preferencias y configuración del sistema
          </p>
        </div>
      </div>

      {/* Grid de secciones */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Sidebar con navegación */}
        <div className="lg:col-span-1">
          <div className="bg-white rounded-lg shadow-sm p-4 space-y-2">
            <h3 className="text-sm font-semibold text-gray-500 uppercase px-3 mb-3">
              Secciones
            </h3>
            
            <button className="w-full flex items-center gap-3 px-3 py-2 text-left rounded-lg bg-blue-50 text-blue-700 font-medium">
              <Key size={20} />
              <span>API Keys</span>
            </button>

            <button className="w-full flex items-center gap-3 px-3 py-2 text-left rounded-lg hover:bg-gray-50 text-gray-700">
              <UserCircle size={20} />
              <span>Perfil</span>
            </button>

            <button className="w-full flex items-center gap-3 px-3 py-2 text-left rounded-lg hover:bg-gray-50 text-gray-700">
              <Bell size={20} />
              <span>Notificaciones</span>
            </button>

            <button className="w-full flex items-center gap-3 px-3 py-2 text-left rounded-lg hover:bg-gray-50 text-gray-700">
              <Shield size={20} />
              <span>Seguridad</span>
            </button>
          </div>

          {/* Info del usuario */}
          <div className="bg-white rounded-lg shadow-sm p-4 mt-4">
            <h4 className="text-sm font-semibold text-gray-700 mb-2">
              Usuario actual
            </h4>
            <div className="space-y-1 text-sm text-gray-600">
              <p><span className="font-medium">Nombre:</span> {user?.nombre_usuario}</p>
              <p><span className="font-medium">Rol:</span> {user?.rol}</p>
              <p><span className="font-medium">Email:</span> {user?.email}</p>
            </div>
          </div>
        </div>

        {/* Contenido principal */}
        <div className="lg:col-span-2 space-y-6">
          {/* Sección de API Keys de Gemini */}
          <GeminiKeySettings />

          {/* Placeholder para otras configuraciones futuras */}
          <div className="bg-white rounded-lg shadow-sm p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-3">
              Otras configuraciones
            </h3>
            <p className="text-sm text-gray-500">
              Más opciones de configuración estarán disponibles próximamente.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
