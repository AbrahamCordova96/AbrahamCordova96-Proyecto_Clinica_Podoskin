import axios from 'axios'
import { 
  Paciente, 
  PacienteCreateInput, 
  PacienteUpdateInput, 
  PacienteFilters,
  PacienteHistorial,
  Tratamiento,
  TratamientoCreateInput,
  TratamientoUpdateInput,
  Evolucion,
  EvolucionCreateInput,
  Podologo
} from '../types/pacientes.types'
import { pacientesServiceMock } from './pacientesService.mock'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

// Toggle between mock and real API
export const USE_MOCK = false

const pacientesServiceReal = {
  // Get all pacientes with filters
  getPacientes: async (filters?: PacienteFilters): Promise<Paciente[]> => {
    const params = new URLSearchParams()
    
    if (filters?.search) params.append('search', filters.search)
    if (filters?.activo !== undefined) params.append('activo', filters.activo.toString())
    if (filters?.page) params.append('page', filters.page.toString())
    if (filters?.per_page) params.append('per_page', filters.per_page.toString())
    
    const response = await axios.get<Paciente[]>(`${API_URL}/pacientes?${params.toString()}`)
    return response.data
  },

  // Get single paciente
  getPaciente: async (id: number): Promise<Paciente | null> => {
    try {
      const response = await axios.get<Paciente>(`${API_URL}/pacientes/${id}`)
      return response.data
    } catch (error) {
      if (axios.isAxiosError(error) && error.response?.status === 404) {
        return null
      }
      throw error
    }
  },

  // Create paciente
  createPaciente: async (data: PacienteCreateInput): Promise<Paciente> => {
    const response = await axios.post<Paciente>(`${API_URL}/pacientes`, data)
    return response.data
  },

  // Update paciente
  updatePaciente: async (id: number, data: PacienteUpdateInput): Promise<Paciente | null> => {
    try {
      const response = await axios.patch<Paciente>(`${API_URL}/pacientes/${id}`, data)
      return response.data
    } catch (error) {
      if (axios.isAxiosError(error) && error.response?.status === 404) {
        return null
      }
      throw error
    }
  },

  // Delete paciente (soft delete)
  deletePaciente: async (id: number): Promise<boolean> => {
    try {
      await axios.delete(`${API_URL}/pacientes/${id}`)
      return true
    } catch (error) {
      if (axios.isAxiosError(error) && error.response?.status === 404) {
        return false
      }
      throw error
    }
  },

  // Get paciente historial (tratamientos + citas)
  getPacienteHistorial: async (id: number): Promise<PacienteHistorial | null> => {
    try {
      const response = await axios.get<PacienteHistorial>(`${API_URL}/pacientes/${id}/historial`)
      return response.data
    } catch (error) {
      if (axios.isAxiosError(error) && error.response?.status === 404) {
        return null
      }
      throw error
    }
  },

  // Get tratamientos for paciente
  getTratamientosByPaciente: async (pacienteId: number): Promise<Tratamiento[]> => {
    const response = await axios.get<Tratamiento[]>(`${API_URL}/pacientes/${pacienteId}/tratamientos`)
    return response.data
  },

  // Create tratamiento
  createTratamiento: async (data: TratamientoCreateInput): Promise<Tratamiento> => {
    const response = await axios.post<Tratamiento>(`${API_URL}/tratamientos`, data)
    return response.data
  },

  // Update tratamiento
  updateTratamiento: async (id: number, data: TratamientoUpdateInput): Promise<Tratamiento | null> => {
    try {
      const response = await axios.patch<Tratamiento>(`${API_URL}/tratamientos/${id}`, data)
      return response.data
    } catch (error) {
      if (axios.isAxiosError(error) && error.response?.status === 404) {
        return null
      }
      throw error
    }
  },

  // Get evoluciones for tratamiento
  getEvolucionesByTratamiento: async (tratamientoId: number): Promise<Evolucion[]> => {
    const response = await axios.get<Evolucion[]>(`${API_URL}/evoluciones`, {
      params: { tratamiento_id: tratamientoId }
    })
    return response.data
  },

  // Create evolucion
  createEvolucion: async (data: EvolucionCreateInput): Promise<Evolucion> => {
    const response = await axios.post<Evolucion>(`${API_URL}/evoluciones`, data)
    return response.data
  },

  // Get podologos
  getPodologos: async (): Promise<Podologo[]> => {
    const response = await axios.get<Podologo[]>(`${API_URL}/podologos`, {
      params: { activo: true }
    })
    return response.data
  }
}

// Export the selected service implementation
export const pacientesService = USE_MOCK ? pacientesServiceMock : pacientesServiceReal
