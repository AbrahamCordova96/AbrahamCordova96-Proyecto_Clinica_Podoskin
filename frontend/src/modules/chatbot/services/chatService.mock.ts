// ============================================================================
// SERVICIO MOCK DEL CHATBOT
// ============================================================================

const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms))

const MOCK_RESPONSES = [
  '¡Hola! Soy el asistente virtual de PodoSkin. ¿En qué puedo ayudarte hoy?',
  'Encontré la información que buscabas. ¿Necesitas algo más?',
  'Procesando tu solicitud...',
  'Aquí está el resumen de las citas de hoy.',
  'He actualizado los datos correctamente.',
]

export const chatServiceMock = {
  sendMessage: async (message: string): Promise<string> => {
    await delay(1000)
    return MOCK_RESPONSES[Math.floor(Math.random() * MOCK_RESPONSES.length)]
  },

  sendVoiceMessage: async (audioBlob: Blob): Promise<string> => {
    await delay(1500)
    return '🎤 Mensaje de voz procesado (mock)'
  },

  executeFunctionCall: async (functionName: string, args: Record<string, any>): Promise<any> => {
    await delay(500)
    return { success: true, message: `Función ${functionName} ejecutada (mock)`, data: args }
  },

  textToSpeech: async (text: string, lang: string = 'es-ES'): Promise<void> => {
    console.log(`[MOCK] Text-to-speech: ${text}`)
    await delay(500)
  },

  clearHistory: (): void => {
    console.log('[MOCK] Historial limpiado')
  }
}
