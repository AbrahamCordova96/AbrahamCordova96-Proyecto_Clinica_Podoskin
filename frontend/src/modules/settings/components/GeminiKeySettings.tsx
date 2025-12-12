// ============================================================================
// COMPONENTE DE CONFIGURACIÓN DE API KEY DE GEMINI
// ============================================================================
// Permite a los usuarios configurar su API Key personal de Google Gemini
// para habilitar el chatbot con voz. La API Key se almacena encriptada en el backend.
// ============================================================================

import { useState, useEffect } from 'react'
import { Eye, EyeSlash, Check, X, Info } from '@phosphor-icons/react'
import { toast } from 'sonner'
import { useAuthStore } from '../../auth/stores/authStore'
import { UserWithSettings } from '../types/settings.types'
import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

// Constantes de validación
const MIN_API_KEY_LENGTH = 20

export const GeminiKeySettings = () => {
  const { user, token } = useAuthStore()
  const [apiKey, setApiKey] = useState('')
  const [showApiKey, setShowApiKey] = useState(false)
  const [isValidating, setIsValidating] = useState(false)
  const [hasKey, setHasKey] = useState(false)
  const [keyStatus, setKeyStatus] = useState<'valid' | 'invalid' | null>(null)

  useEffect(() => {
    // Verificar si el usuario tiene API Key configurada
    // Usando type assertion segura con tipo extendido
    if (user) {
      const userWithSettings = user as UserWithSettings
      setHasKey(userWithSettings.has_gemini_key || false)
      setKeyStatus(userWithSettings.gemini_key_status || null)
    }
  }, [user])

  /**
   * Guarda la API Key en el backend
   * El backend se encarga de validarla y encriptarla
   */
  const handleSaveKey = async () => {
    if (!apiKey.trim()) {
      toast.error('Ingresa una API Key válida')
      return
    }

    if (apiKey.length < MIN_API_KEY_LENGTH) {
      toast.error(`La API Key debe tener al menos ${MIN_API_KEY_LENGTH} caracteres`)
      return
    }

    setIsValidating(true)

    try {
      const response = await axios.put(
        `${API_URL}/usuarios/${user?.id_usuario}/gemini-key`,
        { api_key: apiKey },
        {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        }
      )

      if (response.status === 200) {
        toast.success('API Key guardada exitosamente')
        setHasKey(true)
        setKeyStatus('valid')
        setApiKey('') // Limpiar input por seguridad
      }
    } catch (error: any) {
      console.error('Error saving API key:', error)
      
      if (error.response?.status === 400) {
        toast.error('API Key inválida. Verifica que sea correcta.')
        setKeyStatus('invalid')
      } else if (error.response?.status === 404) {
        toast.warning('Endpoint no disponible aún. El backend necesita implementar este endpoint.')
      } else {
        toast.error('Error al guardar la API Key. Intenta de nuevo.')
      }
    } finally {
      setIsValidating(false)
    }
  }

  /**
   * Elimina la API Key del backend
   */
  const handleDeleteKey = async () => {
    if (!confirm('¿Estás seguro de eliminar tu API Key de Gemini?')) {
      return
    }

    try {
      await axios.delete(
        `${API_URL}/usuarios/${user?.id_usuario}/gemini-key`,
        {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        }
      )

      toast.success('API Key eliminada')
      setHasKey(false)
      setKeyStatus(null)
    } catch (error: any) {
      if (error.response?.status === 404) {
        toast.warning('Endpoint no disponible aún. El backend necesita implementar este endpoint.')
      } else {
        toast.error('Error al eliminar la API Key')
      }
    }
  }

  return (
    <div className="bg-white rounded-lg shadow-sm p-6 space-y-4">
      {/* Header con información */}
      <div className="flex items-start gap-3">
        <Info size={24} className="text-blue-500 flex-shrink-0 mt-1" />
        <div>
          <h3 className="text-lg font-semibold text-gray-900">Configuración de Gemini Live</h3>
          <p className="text-sm text-gray-600 mt-1">
            Configura tu API Key personal de Google Gemini para habilitar el chatbot con voz.
            Tu API Key será encriptada y almacenada de forma segura.
          </p>
        </div>
      </div>

      {/* Estado actual de la API Key */}
      {hasKey && (
        <div className={`p-3 rounded-lg flex items-center gap-2 ${
          keyStatus === 'valid' ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'
        }`}>
          {keyStatus === 'valid' ? (
            <>
              <Check size={20} weight="bold" />
              <span className="text-sm font-medium">API Key configurada y válida</span>
            </>
          ) : (
            <>
              <X size={20} weight="bold" />
              <span className="text-sm font-medium">API Key inválida o expirada</span>
            </>
          )}
        </div>
      )}

      {/* Input para API Key */}
      <div className="space-y-2">
        <label className="block text-sm font-medium text-gray-700">
          API Key de Gemini
        </label>
        <div className="relative">
          <input
            type={showApiKey ? 'text' : 'password'}
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            placeholder="Ingresa tu API Key de Gemini"
            className="w-full px-4 py-2 pr-12 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
          <button
            type="button"
            onClick={() => setShowApiKey(!showApiKey)}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-700"
          >
            {showApiKey ? <EyeSlash size={20} /> : <Eye size={20} />}
          </button>
        </div>
        <p className="text-xs text-gray-500">
          Obtén tu API Key en:{' '}
          <a
            href="https://aistudio.google.com/app/apikey"
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-600 hover:underline"
          >
            https://aistudio.google.com/app/apikey
          </a>
        </p>
      </div>

      {/* Botones de acción */}
      <div className="flex gap-3">
        <button
          onClick={handleSaveKey}
          disabled={isValidating || !apiKey.trim()}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed flex items-center gap-2"
        >
          {isValidating ? (
            <>
              <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
              Validando...
            </>
          ) : (
            'Guardar API Key'
          )}
        </button>

        {hasKey && (
          <button
            onClick={handleDeleteKey}
            className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
          >
            Eliminar API Key
          </button>
        )}
      </div>

      {/* Información de seguridad */}
      <div className="bg-gray-50 p-3 rounded-lg">
        <h4 className="text-sm font-semibold text-gray-900 mb-2">🔒 Seguridad</h4>
        <ul className="text-xs text-gray-600 space-y-1">
          <li>• Tu API Key será encriptada antes de almacenarse</li>
          <li>• Solo tú puedes ver o modificar tu API Key</li>
          <li>• La API Key se valida al iniciar sesión</li>
          <li>• Puedes eliminarla en cualquier momento</li>
        </ul>
      </div>
    </div>
  )
}
