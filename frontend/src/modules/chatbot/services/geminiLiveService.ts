// ============================================================================
// SERVICIO GEMINI LIVE CON FUNCTION CALLING
// ============================================================================

import axios from 'axios'

const GEMINI_API_KEY = import.meta.env.VITE_GEMINI_API_KEY
const GEMINI_API_URL = 'https://generativelanguage.googleapis.com/v1beta'

// Definición de funciones disponibles para el asistente
export const AVAILABLE_FUNCTIONS = {
  get_todays_appointments: {
    name: 'get_todays_appointments',
    description: 'Obtiene las citas programadas para el día de hoy',
    parameters: {
      type: 'object',
      properties: {},
      required: []
    }
  },
  create_patient: {
    name: 'create_patient',
    description: 'Crea un nuevo paciente en el sistema',
    parameters: {
      type: 'object',
      properties: {
        nombres: { type: 'string', description: 'Nombres del paciente' },
        apellidos: { type: 'string', description: 'Apellidos del paciente' },
        telefono: { type: 'string', description: 'Número de teléfono' },
        email: { type: 'string', description: 'Correo electrónico (opcional)' }
      },
      required: ['nombres', 'apellidos', 'telefono']
    }
  },
  search_patient: {
    name: 'search_patient',
    description: 'Busca pacientes por nombre, apellido o teléfono',
    parameters: {
      type: 'object',
      properties: {
        query: { type: 'string', description: 'Término de búsqueda' }
      },
      required: ['query']
    }
  },
  get_active_treatments: {
    name: 'get_active_treatments',
    description: 'Obtiene la lista de tratamientos activos',
    parameters: {
      type: 'object',
      properties: {},
      required: []
    }
  },
  schedule_appointment: {
    name: 'schedule_appointment',
    description: 'Agenda una nueva cita',
    parameters: {
      type: 'object',
      properties: {
        paciente_id: { type: 'number', description: 'ID del paciente' },
        podologo_id: { type: 'number', description: 'ID del podólogo' },
        fecha_hora: { type: 'string', description: 'Fecha y hora en formato ISO' },
        motivo: { type: 'string', description: 'Motivo de la consulta' }
      },
      required: ['paciente_id', 'podologo_id', 'fecha_hora']
    }
  },
  
  // ========== FUNCIONES DE NAVEGACIÓN ==========
  navigate_to_page: {
    name: 'navigate_to_page',
    description: 'Navega a una página específica del sistema. Usa esto cuando el usuario pida ir a alguna sección como "llévame a...", "abre...", "ir a..."',
    parameters: {
      type: 'object',
      properties: {
        page: {
          type: 'string',
          enum: ['dashboard', 'inicio', 'pacientes', 'historial', 'citas', 'agenda', 'tratamientos', 'servicios', 'reportes', 'settings', 'configuracion', 'ajustes'],
          description: 'Nombre de la página destino en español o inglés'
        },
        params: {
          type: 'object',
          description: 'Parámetros opcionales como ID de recurso',
          properties: {
            id: { type: 'number' }
          }
        }
      },
      required: ['page']
    }
  },
  
  open_modal: {
    name: 'open_modal',
    description: 'Abre un formulario modal para crear pacientes, citas, tratamientos, etc. Usa esto cuando el usuario pida "crear", "nuevo", "agregar"',
    parameters: {
      type: 'object',
      properties: {
        modal: {
          type: 'string',
          enum: ['crear_paciente', 'crear_cita', 'crear_tratamiento', 'create_patient', 'create_appointment', 'create_treatment'],
          description: 'Tipo de formulario a abrir'
        },
        prefill: {
          type: 'object',
          description: 'Datos para pre-llenar el formulario'
        }
      },
      required: ['modal']
    }
  },
  
  show_notification: {
    name: 'show_notification',
    description: 'Muestra una notificación al usuario con información importante',
    parameters: {
      type: 'object',
      properties: {
        message: {
          type: 'string',
          description: 'Mensaje a mostrar'
        },
        type: {
          type: 'string',
          enum: ['success', 'error', 'warning', 'info'],
          description: 'Tipo de notificación'
        }
      },
      required: ['message']
    }
  }
}

export interface GeminiMessage {
  role: 'user' | 'model'
  parts: Array<{
    text?: string
    inline_data?: {
      mime_type: string
      data: string
    }
  }>
}

export interface GeminiResponse {
  candidates: Array<{
    content: {
      parts: Array<{
        text?: string
        functionCall?: {
          name: string
          args: Record<string, any>
        }
      }>
      role: string
    }
    finishReason: string
  }>
}

export class GeminiLiveService {
  private conversationHistory: GeminiMessage[] = []
  private systemPrompt = `Eres un asistente virtual para el sistema PodoSkin de gestión de clínica podológica.
Tu objetivo es ayudar al personal de la clínica con consultas sobre pacientes, citas, tratamientos y gestión general.

Capacidades:
- Buscar y consultar información de pacientes
- Ayudar a programar citas
- Consultar tratamientos activos
- Proporcionar información sobre el sistema

Siempre responde de manera profesional, concisa y útil. Si necesitas realizar una acción en el sistema, utiliza las funciones disponibles.`

  /**
   * Enviar mensaje de texto a Gemini Live
   */
  async sendTextMessage(message: string): Promise<string> {
    try {
      if (!GEMINI_API_KEY) {
        throw new Error('GEMINI_API_KEY no está configurada')
      }

      // Agregar mensaje del usuario al historial
      this.conversationHistory.push({
        role: 'user',
        parts: [{ text: message }]
      })

      const response = await axios.post<GeminiResponse>(
        `${GEMINI_API_URL}/models/gemini-2.0-flash-exp:generateContent?key=${GEMINI_API_KEY}`,
        {
          contents: [
            {
              role: 'user',
              parts: [{ text: this.systemPrompt }]
            },
            ...this.conversationHistory
          ],
          tools: [{
            function_declarations: Object.values(AVAILABLE_FUNCTIONS)
          }],
          generationConfig: {
            temperature: 0.7,
            topK: 40,
            topP: 0.95,
            maxOutputTokens: 1024,
          }
        }
      )

      const candidate = response.data.candidates[0]
      const part = candidate.content.parts[0]

      // Agregar respuesta al historial
      this.conversationHistory.push({
        role: 'model',
        parts: candidate.content.parts
      })

      // Si es un function call, retornar indicación
      if (part.functionCall) {
        return `[FUNCTION_CALL]${JSON.stringify(part.functionCall)}`
      }

      return part.text || 'Lo siento, no pude generar una respuesta.'
    } catch (error) {
      console.error('Error in Gemini Live:', error)
      throw error
    }
  }

  /**
   * Enviar audio a Gemini Live para transcripción y procesamiento
   */
  async sendAudioMessage(audioBase64: string, mimeType: string = 'audio/webm'): Promise<string> {
    try {
      if (!GEMINI_API_KEY) {
        throw new Error('GEMINI_API_KEY no está configurada')
      }

      // Agregar audio del usuario al historial
      this.conversationHistory.push({
        role: 'user',
        parts: [{
          inline_data: {
            mime_type: mimeType,
            data: audioBase64
          }
        }]
      })

      const response = await axios.post<GeminiResponse>(
        `${GEMINI_API_URL}/models/gemini-2.0-flash-exp:generateContent?key=${GEMINI_API_KEY}`,
        {
          contents: [
            {
              role: 'user',
              parts: [{ text: this.systemPrompt }]
            },
            ...this.conversationHistory
          ],
          tools: [{
            function_declarations: Object.values(AVAILABLE_FUNCTIONS)
          }],
          generationConfig: {
            temperature: 0.7,
            topK: 40,
            topP: 0.95,
            maxOutputTokens: 1024,
          }
        }
      )

      const candidate = response.data.candidates[0]
      const part = candidate.content.parts[0]

      // Agregar respuesta al historial
      this.conversationHistory.push({
        role: 'model',
        parts: candidate.content.parts
      })

      // Si es un function call, retornar indicación
      if (part.functionCall) {
        return `[FUNCTION_CALL]${JSON.stringify(part.functionCall)}`
      }

      return part.text || 'Lo siento, no pude procesar el audio.'
    } catch (error) {
      console.error('Error processing audio with Gemini:', error)
      throw error
    }
  }

  /**
   * Enviar resultado de function call de vuelta a Gemini
   */
  async sendFunctionResult(functionName: string, functionResult: any): Promise<string> {
    try {
      // Agregar resultado de la función al historial
      this.conversationHistory.push({
        role: 'user',
        parts: [{
          text: `Resultado de ${functionName}: ${JSON.stringify(functionResult)}`
        }]
      })

      const response = await axios.post<GeminiResponse>(
        `${GEMINI_API_URL}/models/gemini-2.0-flash-exp:generateContent?key=${GEMINI_API_KEY}`,
        {
          contents: [
            {
              role: 'user',
              parts: [{ text: this.systemPrompt }]
            },
            ...this.conversationHistory
          ],
          generationConfig: {
            temperature: 0.7,
            topK: 40,
            topP: 0.95,
            maxOutputTokens: 1024,
          }
        }
      )

      const candidate = response.data.candidates[0]
      const part = candidate.content.parts[0]

      // Agregar respuesta al historial
      this.conversationHistory.push({
        role: 'model',
        parts: candidate.content.parts
      })

      return part.text || 'Operación completada.'
    } catch (error) {
      console.error('Error sending function result to Gemini:', error)
      throw error
    }
  }

  /**
   * Limpiar historial de conversación
   */
  clearHistory(): void {
    this.conversationHistory = []
  }

  /**
   * Obtener historial actual
   */
  getHistory(): GeminiMessage[] {
    return this.conversationHistory
  }
}

export const geminiLiveService = new GeminiLiveService()
