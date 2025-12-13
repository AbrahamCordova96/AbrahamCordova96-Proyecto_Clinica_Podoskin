// ============================================================================
// SERVICIO REAL DEL DASHBOARD
// ============================================================================

import axios from 'axios'
import { DashboardKPIs } from '../types/dashboard.types'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

export const dashboardServiceReal = {
  getKPIs: async (): Promise<DashboardKPIs> => {
    const response = await axios.get(`${API_BASE_URL}/statistics/dashboard-kpis`)
    return response.data
  }
}

import { dashboardServiceMock } from './dashboardService.mock'

export const USE_MOCK = false

export const dashboardService = USE_MOCK ? dashboardServiceMock : dashboardServiceReal
