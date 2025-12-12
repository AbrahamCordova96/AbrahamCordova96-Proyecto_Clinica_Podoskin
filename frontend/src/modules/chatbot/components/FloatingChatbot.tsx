// ============================================================================
// CHATBOT FLOTANTE PERSISTENTE CON VOZ Y NAVEGACIÓN
// ============================================================================

import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { ChatCircleDots, X, Minus, PaperPlaneRight, Microphone, MicrophoneSlash, SpeakerHigh, SpeakerSlash, Trash, CalendarCheck, UserPlus, Notebook, Camera, Question, Lightbulb } from '@phosphor-icons/react'
import { useChatStore } from '../stores/chatStore'
import { useAuthStore } from '../../auth/stores/authStore'
import { ChatMessage } from './ChatMessage'
import { toast } from 'sonner'
import { navigationHandler } from '../services/navigationHandler'

const QUICK_COMMANDS = [
  { id: 'help', label: 'Ayuda general', icon: Question, category: 'Ayuda' },
  { id: 'appointments', label: 'Ver citas de hoy', icon: CalendarCheck, category: 'Información' },
  { id: 'new-patient', label: 'Crear paciente', icon: UserPlus, category: 'Información' },
  { id: 'treatments', label: 'Tratamientos activos', icon: Notebook, category: 'Información' },
  { id: 'photos', label: 'Subir evidencias', icon: Camera, category: 'Información' },
  { id: 'tips', label: 'Consejos de uso', icon: Lightbulb, category: 'Ayuda' },
]

export const FloatingChatbot = () => {
  const navigate = useNavigate()
  const { user } = useAuthStore()
  const { 
    messages, 
    isOpen, 
    isTyping, 
    isRecording, 
    isSpeaking,
    voiceOutputEnabled,
    toggleChat, 
    sendMessage, 
    startRecording,
    stopRecording,
    addMessage, 
    clearMessages,
    toggleVoiceOutput
  } = useChatStore()
  
  const [inputValue, setInputValue] = useState('')
  const messagesEndRef = useRef<HTMLDivElement>(null)
  
  // Inicializar navigationHandler con la función navigate
  useEffect(() => {
    navigationHandler.setNavigate(navigate)
  }, [navigate])
  
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])
  
  useEffect(() => {
    if (messages.length === 0 && user) {
      addMessage({
        role: 'assistant',
        content: `¡Hola ${user.nombre_usuario}! Soy tu asistente virtual. ¿En qué puedo ayudarte hoy?`
      })
    }
  }, [user, messages.length, addMessage])
  
  const handleSend = async () => {
    if (!inputValue.trim()) return
    
    await sendMessage(inputValue)
    setInputValue('')
  }
  
  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }
  
  const handleQuickCommand = (commandId: string) => {
    const command = QUICK_COMMANDS.find(c => c.id === commandId)
    if (command) {
      sendMessage(command.label)
    }
  }
  
  const handleMicrophoneClick = async () => {
    if (isRecording) {
      try {
        await stopRecording()
      } catch (error) {
        toast.error('Error al detener la grabación')
      }
    } else {
      try {
        await startRecording()
        toast.success('Grabando... Haz clic nuevamente para enviar')
      } catch (error) {
        toast.error('No se pudo acceder al micrófono. Verifica los permisos.')
      }
    }
  }
  
  return (
    <div className="fixed bottom-6 right-6 z-50">
      {!isOpen && (
        <button
          onClick={toggleChat}
          className="w-16 h-16 bg-gradient-to-br from-blue-600 to-blue-700 text-white rounded-full shadow-2xl hover:shadow-blue-500/50 hover:scale-110 transition-all flex items-center justify-center group"
        >
          <ChatCircleDots size={28} weight="duotone" className="group-hover:scale-110 transition-transform" />
          <span className="absolute -top-1 -right-1 w-5 h-5 bg-red-500 text-white text-xs font-bold rounded-full flex items-center justify-center animate-pulse">
            1
          </span>
        </button>
      )}
      
      {isOpen && (
        <div className="w-96 h-[600px] bg-white rounded-2xl shadow-2xl flex flex-col overflow-hidden border border-gray-200">
          
          <div className="bg-gradient-to-r from-blue-600 to-blue-700 text-white p-4 flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-white bg-opacity-20 rounded-full flex items-center justify-center backdrop-blur-sm">
                <ChatCircleDots size={20} weight="duotone" />
              </div>
              <div>
                <h3 className="font-semibold text-lg">Asistente PodoSkin</h3>
                <p className="text-xs text-blue-100">
                  {isTyping ? 'Escribiendo...' : 'En línea'}
                </p>
              </div>
            </div>
            
            <div className="flex items-center space-x-2">
              <button
                onClick={toggleVoiceOutput}
                className="p-2 hover:bg-white hover:bg-opacity-20 rounded-lg transition"
                title={voiceOutputEnabled ? 'Desactivar voz' : 'Activar voz'}
              >
                {voiceOutputEnabled ? <SpeakerHigh size={16} /> : <SpeakerSlash size={16} />}
              </button>
              <button
                onClick={clearMessages}
                className="p-2 hover:bg-white hover:bg-opacity-20 rounded-lg transition"
                title="Limpiar chat"
              >
                <Trash size={16} />
              </button>
              <button
                onClick={toggleChat}
                className="p-2 hover:bg-white hover:bg-opacity-20 rounded-lg transition"
              >
                <Minus size={16} />
              </button>
              <button
                onClick={toggleChat}
                className="p-2 hover:bg-white hover:bg-opacity-20 rounded-lg transition"
              >
                <X size={16} />
              </button>
            </div>
          </div>
          
          {messages.length === 1 && (
            <div className="p-4 bg-gradient-to-r from-blue-50 to-purple-50 border-b border-gray-200">
              <div className="bg-gradient-to-r from-blue-600 via-purple-600 to-blue-600 bg-clip-text text-transparent animate-gradient font-semibold text-sm leading-relaxed">
                Bienvenido al sistema de gestión clínica PodoSkin.
                Estoy aquí para ayudarte con cualquier consulta.
                Selecciona un comando rápido o escribe tu pregunta.
              </div>
            </div>
          )}
          
          <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-gray-50">
            {messages.map((message) => (
              <ChatMessage key={message.id} message={message} />
            ))}
            
            {isTyping && (
              <div className="flex items-center space-x-2 text-gray-500 text-sm">
                <div className="flex space-x-1">
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                </div>
                <span>Escribiendo...</span>
              </div>
            )}
            
            {isSpeaking && (
              <div className="flex items-center space-x-2 text-blue-500 text-sm">
                <SpeakerHigh size={16} className="animate-pulse" />
                <span>Reproduciendo respuesta...</span>
              </div>
            )}
            
            <div ref={messagesEndRef} />
          </div>
          
          {messages.length === 1 && (
            <div className="p-3 border-t border-gray-200 bg-white">
              <p className="text-xs font-semibold text-gray-500 mb-2">Comandos rápidos:</p>
              <div className="grid grid-cols-2 gap-2">
                {QUICK_COMMANDS.slice(0, 4).map((cmd) => {
                  const Icon = cmd.icon
                  return (
                    <button
                      key={cmd.id}
                      onClick={() => handleQuickCommand(cmd.id)}
                      className="flex items-center space-x-2 px-3 py-2 bg-gray-50 hover:bg-blue-50 rounded-lg text-xs text-gray-700 hover:text-blue-600 transition"
                    >
                      <Icon size={14} />
                      <span className="truncate">{cmd.label}</span>
                    </button>
                  )
                })}
              </div>
            </div>
          )}
          
          <div className="p-4 bg-white border-t border-gray-200">
            <div className="flex items-end space-x-2">
              <textarea
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Escribe tu mensaje..."
                className="flex-1 px-4 py-3 border border-gray-300 rounded-xl resize-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition"
                rows={1}
                disabled={isTyping}
              />
              
              <button 
                onClick={handleMicrophoneClick}
                disabled={isTyping || isSpeaking}
                className={`p-3 rounded-xl transition disabled:opacity-50 disabled:cursor-not-allowed ${
                  isRecording 
                    ? 'bg-red-500 text-white animate-pulse' 
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
                title={isRecording ? 'Detener grabación' : 'Grabar mensaje de voz'}
              >
                {isRecording ? <MicrophoneSlash size={20} /> : <Microphone size={20} />}
              </button>
              
              <button
                onClick={handleSend}
                disabled={!inputValue.trim() || isTyping || isRecording}
                className="p-3 bg-blue-600 text-white rounded-xl hover:bg-blue-700 transition disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <PaperPlaneRight size={20} />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
