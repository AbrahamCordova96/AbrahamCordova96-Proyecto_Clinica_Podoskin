// ============================================================================
// SERVICIO DE INTEGRACIÓN CON EL BACKEND - CHATBOT
// ============================================================================
// Este servicio maneja toda la comunicación entre el chatbot del frontend
// y el endpoint de chat del backend (/api/v1/chat)
// ============================================================================

import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

/**
 * Interfaz para la solicitud al backend
 */
export interface BackendChatRequest {
  message: string
  thread_id?: string
}

/**
 * Interfaz para la respuesta del backend
 */
export interface BackendChatResponse {
  success: boolean
  message: string
  data?: any
  intent?: string
  session_id: string
  thread_id?: string
  processing_time_ms: number
}

/**
 * Clase que maneja la integración con el backend del chatbot
 * Gestiona tokens JWT, thread_ids y llamadas a funciones
 */
export class BackendIntegration {
  private token: string | null = null
  private currentThreadId: string | null = null

  /**
   * Configura el token JWT para autenticación
   */
  setToken(token: string) {
    this.token = token
  }

  /**
   * Configura el thread_id actual para mantener contexto
   */
  setThreadId(threadId: string) {
    this.currentThreadId = threadId
  }

  /**
   * Genera un thread_id único basado en el ID del usuario
   * Formato: {userId}_webapp_{timestamp}
   */
  generateThreadId(userId: number): string {
    return `${userId}_webapp_${Date.now()}`
  }

  /**
   * Envía un mensaje al endpoint de chat del backend
   * @param message - Mensaje del usuario
   * @returns Respuesta del backend con la información procesada
   */
  async sendMessageToBackend(message: string): Promise<BackendChatResponse> {
    if (!this.token) {
      throw new Error('No hay token de autenticación. Inicia sesión primero.')
    }

    try {
      const response = await axios.post<BackendChatResponse>(
        `${API_URL}/chat`,
        {
          message,
          thread_id: this.currentThreadId
        },
        {
          headers: {
            'Authorization': `Bearer ${this.token}`,
            'Content-Type': 'application/json'
          },
          timeout: 30000 // 30 segundos para dar tiempo al backend de procesar
        }
      )

      // Guardar thread_id devuelto por el backend para mantener contexto
      if (response.data.thread_id) {
        this.currentThreadId = response.data.thread_id
      }

      return response.data
    } catch (error: any) {
      console.error('Error calling backend chat:', error)
      
      // Manejo de errores específicos
      if (error.response?.status === 401) {
        throw new Error('Sesión expirada. Por favor inicia sesión nuevamente.')
      }
      
      if (error.response?.status === 429) {
        throw new Error('Demasiadas solicitudes. Espera un momento e intenta de nuevo.')
      }

      if (error.code === 'ECONNABORTED') {
        throw new Error('El servidor tardó demasiado en responder. Intenta de nuevo.')
      }
      
      throw new Error(error.response?.data?.detail || 'Error al comunicarse con el servidor. Intenta de nuevo.')
    }
  }

  /**
   * Ejecuta una función específica llamando al endpoint correspondiente del backend
   * Mapea function calls de Gemini a endpoints REST del backend
   * @param functionName - Nombre de la función a ejecutar
   * @param args - Argumentos para la función
   * @returns Resultado de la ejecución
   */
  async executeFunctionCall(functionName: string, args: Record<string, any>): Promise<any> {
    // Mapeo de funciones a endpoints del backend
    const functionMap: Record<string, { method: string, endpoint: string, buildUrl?: (args: any) => string }> = {
      'get_todays_appointments': {
        method: 'GET',
        endpoint: '/citas',
        buildUrl: () => {
          const today = new Date().toISOString().split('T')[0]
          return `/citas?fecha_inicio=${today}&fecha_fin=${today}`
        }
      },
      'search_patient': {
        method: 'GET',
        endpoint: '/pacientes',
        buildUrl: (args) => `/pacientes?busqueda=${encodeURIComponent(args.query)}`
      },
      'get_active_treatments': {
        method: 'GET',
        endpoint: '/tratamientos',
        buildUrl: () => '/tratamientos?estado=activo'
      },
      'create_patient': {
        method: 'POST',
        endpoint: '/pacientes'
      },
      'schedule_appointment': {
        method: 'POST',
        endpoint: '/citas'
      }
    }

    const mapping = functionMap[functionName]
    
    if (!mapping) {
      console.warn(`Función ${functionName} no mapeada. Usando backend chat.`)
      // Fallback: enviar al backend como mensaje de texto
      return await this.sendMessageToBackend(`Ejecuta: ${functionName} con ${JSON.stringify(args)}`)
    }

    try {
      const url = mapping.buildUrl ? mapping.buildUrl(args) : mapping.endpoint

      if (mapping.method === 'GET') {
        const response = await axios.get(`${API_URL}${url}`, {
          headers: {
            'Authorization': `Bearer ${this.token}`
          }
        })
        return response.data
      } else {
        // POST/PUT
        const response = await axios.post(`${API_URL}${mapping.endpoint}`, args, {
          headers: {
            'Authorization': `Bearer ${this.token}`,
            'Content-Type': 'application/json'
          }
        })
        return response.data
      }
    } catch (error: any) {
      console.error(`Error executing function ${functionName}:`, error)
      return {
        error: true,
        message: error.response?.data?.detail || 'Error al ejecutar la acción'
      }
    }
  }
}

// Exportar instancia única del servicio (singleton)
export const backendIntegration = new BackendIntegration()
