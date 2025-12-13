import axios from 'axios'
import { Cita, CitaCreateInput, CitaUpdateInput, CitaFilters } from '../types/agenda.types'
import { Paciente, Podologo, Servicio } from '@/lib/types'
import { agendaServiceMock } from './agendaService.mock'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

// Toggle between mock and real API
export const USE_MOCK = false

const agendaServiceReal = {
  // Get all citas with filters
  getCitas: async (filters?: CitaFilters): Promise<Cita[]> => {
    const params = new URLSearchParams()
    
    if (filters?.fecha_inicio) params.append('fecha_inicio', filters.fecha_inicio)
    if (filters?.fecha_fin) params.append('fecha_fin', filters.fecha_fin)
    if (filters?.podologo_id) params.append('podologo_id', filters.podologo_id.toString())
    if (filters?.paciente_id) params.append('paciente_id', filters.paciente_id.toString())
    if (filters?.estado) params.append('estado', filters.estado)
    if (filters?.page) params.append('page', filters.page.toString())
    if (filters?.per_page) params.append('per_page', filters.per_page.toString())
    
    const response = await axios.get<Cita[]>(`${API_URL}/citas?${params.toString()}`)
    return response.data
  },

  // Get calendar view
  getCalendarView: async (startDate: string, endDate: string, view: 'week' | 'day' | 'month' = 'week'): Promise<Cita[]> => {
    const response = await axios.get<Cita[]>(`${API_URL}/citas/calendar`, {
      params: { fecha_inicio: startDate, fecha_fin: endDate, vista: view }
    })
    return response.data
  },

  // Get single cita
  getCita: async (id: number): Promise<Cita | null> => {
    try {
      const response = await axios.get<Cita>(`${API_URL}/citas/${id}`)
      return response.data
    } catch (error) {
      if (axios.isAxiosError(error) && error.response?.status === 404) {
        return null
      }
      throw error
    }
  },

  // Create cita
  createCita: async (data: CitaCreateInput): Promise<Cita> => {
    const response = await axios.post<Cita>(`${API_URL}/citas`, data)
    return response.data
  },

  // Update cita
  updateCita: async (id: number, data: CitaUpdateInput): Promise<Cita | null> => {
    try {
      const response = await axios.patch<Cita>(`${API_URL}/citas/${id}`, data)
      return response.data
    } catch (error) {
      if (axios.isAxiosError(error) && error.response?.status === 404) {
        return null
      }
      throw error
    }
  },

  // Delete/Cancel cita
  deleteCita: async (id: number): Promise<boolean> => {
    try {
      await axios.delete(`${API_URL}/citas/${id}`)
      return true
    } catch (error) {
      if (axios.isAxiosError(error) && error.response?.status === 404) {
        return false
      }
      throw error
    }
  },

  // Reschedule cita
  rescheduleCita: async (id: number, newDateTime: string): Promise<Cita | null> => {
    try {
      const response = await axios.post<Cita>(`${API_URL}/citas/${id}/reschedule`, {
        nueva_fecha_hora: newDateTime
      })
      return response.data
    } catch (error) {
      if (axios.isAxiosError(error) && error.response?.status === 404) {
        return null
      }
      throw error
    }
  },

  // Get pacientes for dropdown
  getPacientes: async (): Promise<Paciente[]> => {
    const response = await axios.get<Paciente[]>(`${API_URL}/pacientes`, {
      params: { activo: true, per_page: 1000 }
    })
    return response.data
  },

  // Get podologos for dropdown
  getPodologos: async (): Promise<Podologo[]> => {
    const response = await axios.get<Podologo[]>(`${API_URL}/podologos`, {
      params: { activo: true }
    })
    return response.data
  },

  // Get servicios for dropdown
  getServicios: async (): Promise<Servicio[]> => {
    const response = await axios.get<Servicio[]>(`${API_URL}/servicios`, {
      params: { activo: true }
    })
    return response.data
  }
}

// Export the selected service implementation
export const agendaService = USE_MOCK ? agendaServiceMock : agendaServiceReal
