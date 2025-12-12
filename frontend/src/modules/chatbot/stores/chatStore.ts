// ============================================================================
// STORE DEL CHATBOT CON SOPORTE DE VOZ Y BACKEND REAL
// ============================================================================

import { create } from 'zustand'
import { ChatMessage, ChatState } from '../types/chat.types'
import { chatService } from '../services/chatService'
import { voiceService } from '../services/voiceService'
import { useAuthStore } from '../../auth/stores/authStore'
import { backendIntegration } from '../services/backendIntegration'

interface ChatActions {
  initializeChat: () => void
  toggleChat: () => void
  sendMessage: (content: string) => Promise<void>
  sendVoiceMessage: (audioBlob: Blob) => Promise<void>
  startRecording: () => Promise<void>
  stopRecording: () => Promise<void>
  addMessage: (message: Omit<ChatMessage, 'id' | 'timestamp'>) => void
  clearMessages: () => void
  toggleVoiceOutput: () => void
}

type ChatStore = ChatState & ChatActions & { voiceOutputEnabled: boolean }

export const useChatStore = create<ChatStore>((set, get) => ({
  messages: [],
  isOpen: false,
  isTyping: false,
  isRecording: false,
  isSpeaking: false,
  voiceOutputEnabled: true,
  
  /**
   * Inicializar el chat con token y thread_id
   * Se llama automáticamente al abrir el chatbot
   */
  initializeChat: () => {
    const authStore = useAuthStore.getState()
    const user = authStore.user
    const token = authStore.token
    
    if (user && token) {
      // Configurar token para autenticación con backend
      backendIntegration.setToken(token)
      
      // Generar y configurar thread_id único para esta sesión
      const threadId = backendIntegration.generateThreadId(user.id_usuario)
      backendIntegration.setThreadId(threadId)
      
      console.log('Chat inicializado con thread_id:', threadId)
    } else {
      console.warn('No se pudo inicializar el chat: usuario o token no disponible')
    }
  },
  
  toggleChat: () => set(state => {
    // Si se está abriendo el chat, inicializar
    if (!state.isOpen) {
      get().initializeChat()
    }
    return { isOpen: !state.isOpen }
  }),
  
  toggleVoiceOutput: () => set(state => ({ voiceOutputEnabled: !state.voiceOutputEnabled })),
  
  sendMessage: async (content: string) => {
    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content,
      timestamp: new Date(),
    }
    
    set(state => ({
      messages: [...state.messages, userMessage],
      isTyping: true
    }))
    
    try {
      const response = await chatService.sendMessage(content)
      
      // Verificar si es un function call
      if (response.startsWith('[FUNCTION_CALL]')) {
        const functionCallData = JSON.parse(response.replace('[FUNCTION_CALL]', ''))
        
        // Ejecutar la función
        const functionResult = await chatService.executeFunctionCall(
          functionCallData.name,
          functionCallData.args
        )
        
        // Crear mensaje de asistente con el resultado
        const assistantMessage: ChatMessage = {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: `He ejecutado la acción: ${functionCallData.name}. ${JSON.stringify(functionResult)}`,
          timestamp: new Date(),
          functionCall: {
            name: functionCallData.name,
            arguments: functionCallData.args,
            result: functionResult
          }
        }
        
        set(state => ({
          messages: [...state.messages, assistantMessage],
          isTyping: false
        }))
      } else {
        const assistantMessage: ChatMessage = {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: response,
          timestamp: new Date(),
        }
        
        set(state => ({
          messages: [...state.messages, assistantMessage],
          isTyping: false
        }))
        
        // Si está habilitado, reproducir respuesta
        if (get().voiceOutputEnabled && response) {
          set({ isSpeaking: true })
          try {
            await chatService.textToSpeech(response)
          } catch (error) {
            console.error('Error in text-to-speech:', error)
          } finally {
            set({ isSpeaking: false })
          }
        }
      }
    } catch (error) {
      console.error('Error sending message:', error)
      
      const errorMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: 'Lo siento, hubo un error al procesar tu mensaje. Por favor intenta de nuevo.',
        timestamp: new Date(),
      }
      
      set(state => ({
        messages: [...state.messages, errorMessage],
        isTyping: false
      }))
    }
  },
  
  sendVoiceMessage: async (audioBlob: Blob) => {
    // Crear mensaje de usuario con indicador de voz
    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: '🎤 Mensaje de voz',
      timestamp: new Date(),
      isVoice: true,
      audioUrl: URL.createObjectURL(audioBlob)
    }
    
    set(state => ({
      messages: [...state.messages, userMessage],
      isTyping: true
    }))
    
    try {
      const response = await chatService.sendVoiceMessage(audioBlob)
      
      // Similar al sendMessage, manejar function calls
      if (response.startsWith('[FUNCTION_CALL]')) {
        const functionCallData = JSON.parse(response.replace('[FUNCTION_CALL]', ''))
        
        const functionResult = await chatService.executeFunctionCall(
          functionCallData.name,
          functionCallData.args
        )
        
        const assistantMessage: ChatMessage = {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: `He ejecutado la acción: ${functionCallData.name}. ${JSON.stringify(functionResult)}`,
          timestamp: new Date(),
          functionCall: {
            name: functionCallData.name,
            arguments: functionCallData.args,
            result: functionResult
          }
        }
        
        set(state => ({
          messages: [...state.messages, assistantMessage],
          isTyping: false
        }))
      } else {
        const assistantMessage: ChatMessage = {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: response,
          timestamp: new Date(),
        }
        
        set(state => ({
          messages: [...state.messages, assistantMessage],
          isTyping: false
        }))
        
        // Reproducir respuesta si está habilitado
        if (get().voiceOutputEnabled && response) {
          set({ isSpeaking: true })
          try {
            await chatService.textToSpeech(response)
          } catch (error) {
            console.error('Error in text-to-speech:', error)
          } finally {
            set({ isSpeaking: false })
          }
        }
      }
    } catch (error) {
      console.error('Error sending voice message:', error)
      
      const errorMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: 'Lo siento, hubo un error al procesar tu mensaje de voz. Por favor intenta de nuevo.',
        timestamp: new Date(),
      }
      
      set(state => ({
        messages: [...state.messages, errorMessage],
        isTyping: false
      }))
    }
  },
  
  startRecording: async () => {
    try {
      await voiceService.startRecording()
      set({ isRecording: true })
    } catch (error) {
      console.error('Error starting recording:', error)
      throw error
    }
  },
  
  stopRecording: async () => {
    try {
      const audioBlob = await voiceService.stopRecording()
      set({ isRecording: false })
      
      // Enviar el mensaje de voz
      await get().sendVoiceMessage(audioBlob)
    } catch (error) {
      console.error('Error stopping recording:', error)
      set({ isRecording: false })
      throw error
    }
  },
  
  addMessage: (message) => {
    const newMessage: ChatMessage = {
      ...message,
      id: Date.now().toString(),
      timestamp: new Date(),
    }
    
    set(state => ({
      messages: [...state.messages, newMessage]
    }))
  },
  
  clearMessages: () => {
    chatService.clearHistory()
    set({ messages: [] })
  }
}))
