// ============================================================================
// SERVICIO DEL CHATBOT CON BACKEND REAL Y GEMINI LIVE
// ============================================================================

import { chatServiceMock } from './chatService.mock'
import { geminiLiveService } from './geminiLiveService'
import { voiceService } from './voiceService'
import { backendIntegration } from './backendIntegration'

export const chatServiceReal = {
  /**
   * Enviar mensaje de texto
   * PRIORIDAD: Usa el backend real para procesamiento de mensajes
   * El backend maneja Gemini internamente con las API Keys del usuario
   */
  sendMessage: async (message: string): Promise<string> => {
    try {
      // OPCIÓN A: Usar solo backend (IMPLEMENTADO - RECOMENDADO)
      const response = await backendIntegration.sendMessageToBackend(message)
      return response.message

      // OPCIÓN B: Usar Gemini directo + ejecutar function calls contra backend
      // (Descomentado si se prefiere usar Gemini desde frontend)
      /*
      const response = await geminiLiveService.sendTextMessage(message)
      
      // Si Gemini devuelve un function call, ejecutarlo contra el backend
      if (response.startsWith('[FUNCTION_CALL]')) {
        const functionCallData = JSON.parse(response.replace('[FUNCTION_CALL]', ''))
        const result = await backendIntegration.executeFunctionCall(
          functionCallData.name,
          functionCallData.args
        )
        
        // Enviar resultado a Gemini para que lo formatee en lenguaje natural
        return await geminiLiveService.sendFunctionResult(functionCallData.name, result)
      }
      
      return response
      */
    } catch (error) {
      console.error('Error calling chat service:', error)
      throw error
    }
  },

  /**
   * Enviar mensaje de voz (audio)
   */
  sendVoiceMessage: async (audioBlob: Blob): Promise<string> => {
    try {
      // Convertir audio a base64
      const audioBase64 = await voiceService.audioToBase64(audioBlob)
      
      // Enviar a Gemini Live para procesamiento
      const response = await geminiLiveService.sendAudioMessage(audioBase64, audioBlob.type)
      
      return response
    } catch (error) {
      console.error('Error processing voice message:', error)
      throw error
    }
  },

  /**
   * Ejecutar una función llamada por Gemini o el backend
   * Ahora usa el backend real en lugar de datos mock
   */
  executeFunctionCall: async (functionName: string, args: Record<string, any>): Promise<any> => {
    console.log(`Ejecutando función: ${functionName}`, args)
    
    // Usar backend real para ejecutar las funciones
    return await backendIntegration.executeFunctionCall(functionName, args)
  },

  /**
   * Sintetizar texto a voz
   */
  textToSpeech: async (text: string, lang: string = 'es-ES'): Promise<void> => {
    try {
      await voiceService.textToSpeech(text, lang)
    } catch (error) {
      console.error('Error in text-to-speech:', error)
      throw error
    }
  },

  /**
   * Limpiar historial de conversación
   */
  clearHistory: (): void => {
    geminiLiveService.clearHistory()
  }
}

export const USE_MOCK = false

export const chatService = USE_MOCK ? chatServiceMock : chatServiceReal
