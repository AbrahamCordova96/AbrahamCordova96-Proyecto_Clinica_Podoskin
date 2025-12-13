// ============================================================================
// COMPONENTE DE CONFIGURACIÓN PROFESIONAL - NOM-024
// ============================================================================
// Permite a los podólogos configurar sus datos profesionales (cédula, 
// especialidad, institución) requeridos por la norma NOM-024
// ============================================================================

import { useState, useEffect } from 'react'
import { GraduationCap, IdentificationCard, Buildings, Check, Info } from '@phosphor-icons/react'
import { toast } from 'sonner'
import { useAuthStore } from '../../auth/stores/authStore'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

interface ProfessionalData {
  cedula_profesional?: string
  especialidad?: string
  institucion_emisora?: string
}

export const ProfessionalDataSettings = () => {
  const { user, token } = useAuthStore()
  const [isLoading, setIsLoading] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [hasData, setHasData] = useState(false)
  
  const [formData, setFormData] = useState<ProfessionalData>({
    cedula_profesional: '',
    especialidad: '',
    institucion_emisora: ''
  })

  // Only show for Podologo role
  const isPodologo = user?.rol === 'Podologo' || user?.rol === 'Admin'
  
  useEffect(() => {
    if (isPodologo) {
      loadProfessionalData()
    }
  }, [isPodologo, user])

  /**
   * Load current professional data from backend
   */
  const loadProfessionalData = async () => {
    if (!user?.id_usuario) return
    
    setIsLoading(true)
    try {
      // Attempt to fetch podologo data linked to this user
      const response = await axios.get(
        `${API_URL}/podologos/by-user/${user.id_usuario}`,
        {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        }
      )

      if (response.data) {
        setFormData({
          cedula_profesional: response.data.cedula_profesional || '',
          especialidad: response.data.especialidad || '',
          institucion_emisora: response.data.institucion_emisora || ''
        })
        setHasData(!!(response.data.cedula_profesional || response.data.especialidad))
      }
    } catch (error: any) {
      // If 404, user doesn't have podologo profile yet - that's okay
      if (error.response?.status !== 404) {
        console.error('Error loading professional data:', error)
      }
    } finally {
      setIsLoading(false)
    }
  }

  /**
   * Save professional data to backend
   */
  const handleSave = async () => {
    if (!user?.id_usuario) return

    // Validate at least one field is filled
    if (!formData.cedula_profesional && !formData.especialidad && !formData.institucion_emisora) {
      toast.error('Completa al menos un campo')
      return
    }

    setIsSaving(true)
    try {
      await axios.put(
        `${API_URL}/podologos/professional-data`,
        formData,
        {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        }
      )

      toast.success('Datos profesionales actualizados')
      setHasData(true)
      loadProfessionalData() // Reload to get updated data
    } catch (error: any) {
      console.error('Error saving professional data:', error)
      
      if (error.response?.status === 404) {
        toast.warning('Endpoint no disponible. El backend necesita implementar este endpoint.')
      } else {
        toast.error('Error al guardar datos profesionales')
      }
    } finally {
      setIsSaving(false)
    }
  }

  // Don't show for non-clinical staff
  if (!isPodologo) {
    return null
  }

  if (isLoading) {
    return (
      <div className="bg-white rounded-lg shadow-sm p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-6 bg-gray-200 rounded w-1/3"></div>
          <div className="h-4 bg-gray-200 rounded w-2/3"></div>
          <div className="h-10 bg-gray-200 rounded"></div>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-lg shadow-sm p-6 space-y-4">
      {/* Header */}
      <div className="flex items-start gap-3">
        <GraduationCap size={24} className="text-blue-500 flex-shrink-0 mt-1" weight="duotone" />
        <div>
          <h3 className="text-lg font-semibold text-gray-900">Datos Profesionales (NOM-024)</h3>
          <p className="text-sm text-gray-600 mt-1">
            Información profesional requerida para cumplimiento normativo. Estos datos aparecerán en reportes oficiales y expedientes.
          </p>
        </div>
      </div>

      {/* Status indicator */}
      {hasData && (
        <div className="p-3 rounded-lg flex items-center gap-2 bg-green-50 text-green-700">
          <Check size={20} weight="bold" />
          <span className="text-sm font-medium">Datos profesionales configurados</span>
        </div>
      )}

      {/* Form fields */}
      <div className="space-y-4">
        <div>
          <Label htmlFor="cedula_profesional" className="flex items-center gap-2">
            <IdentificationCard size={16} />
            Cédula Profesional
          </Label>
          <Input
            id="cedula_profesional"
            value={formData.cedula_profesional}
            onChange={(e) => setFormData({ ...formData, cedula_profesional: e.target.value })}
            placeholder="Número de cédula profesional"
            className="mt-1"
          />
          <p className="text-xs text-muted-foreground mt-1">
            Cédula profesional emitida por la SEP
          </p>
        </div>

        <div>
          <Label htmlFor="especialidad" className="flex items-center gap-2">
            <GraduationCap size={16} />
            Especialidad
          </Label>
          <Input
            id="especialidad"
            value={formData.especialidad}
            onChange={(e) => setFormData({ ...formData, especialidad: e.target.value })}
            placeholder="Ej: Podología Clínica, Podología Deportiva"
            className="mt-1"
          />
          <p className="text-xs text-muted-foreground mt-1">
            Especialidad o área de práctica principal
          </p>
        </div>

        <div>
          <Label htmlFor="institucion_emisora" className="flex items-center gap-2">
            <Buildings size={16} />
            Institución que Otorgó el Título
          </Label>
          <Input
            id="institucion_emisora"
            value={formData.institucion_emisora}
            onChange={(e) => setFormData({ ...formData, institucion_emisora: e.target.value })}
            placeholder="Ej: Universidad Nacional Autónoma de México"
            className="mt-1"
          />
          <p className="text-xs text-muted-foreground mt-1">
            Universidad o institución educativa
          </p>
        </div>
      </div>

      {/* Action button */}
      <div className="pt-2">
        <Button
          onClick={handleSave}
          disabled={isSaving}
          className="w-full sm:w-auto"
        >
          {isSaving ? (
            <>
              <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2" />
              Guardando...
            </>
          ) : (
            'Guardar Datos Profesionales'
          )}
        </Button>
      </div>

      {/* Info box */}
      <div className="bg-blue-50 p-3 rounded-lg flex items-start gap-2">
        <Info size={20} className="text-blue-600 flex-shrink-0 mt-0.5" />
        <div className="text-xs text-blue-900 space-y-1">
          <p className="font-medium">¿Por qué se solicita esta información?</p>
          <ul className="list-disc list-inside space-y-0.5 ml-1">
            <li>La NOM-024 requiere identificación completa del profesional</li>
            <li>Aparecerá en reportes y expedientes oficiales</li>
            <li>Es opcional ahora, pero será obligatorio para certificación oficial</li>
          </ul>
        </div>
      </div>
    </div>
  )
}
