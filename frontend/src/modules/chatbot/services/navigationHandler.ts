// ============================================================================
// MANEJADOR DE NAVEGACIÓN POR VOZ
// ============================================================================
// Este servicio permite al chatbot navegar por la aplicación mediante
// comandos de voz o texto. Traduce comandos en español a rutas de React Router.
// ============================================================================

import { NavigateFunction } from 'react-router-dom'
import { toast } from 'sonner'

/**
 * Interfaz para comandos de navegación
 */
export interface NavigationCommand {
  page: string
  params?: Record<string, any>
}

/**
 * Interfaz para comandos de apertura de modales
 */
export interface ModalCommand {
  modal: string
  prefill?: Record<string, any>
}

/**
 * Clase que maneja la navegación por voz
 * Traduce comandos en lenguaje natural a acciones de navegación
 */
export class NavigationHandler {
  private navigate: NavigateFunction | null = null

  /**
   * Configura la función navigate de React Router
   * Debe ser llamado al inicializar el chatbot
   */
  setNavigate(navigate: NavigateFunction) {
    this.navigate = navigate
  }

  /**
   * Navega a una página específica del sistema
   * Soporta comandos en español e inglés
   * @param command - Comando de navegación con página y parámetros opcionales
   * @returns Resultado de la navegación
   */
  async navigateToPage(command: NavigationCommand): Promise<any> {
    if (!this.navigate) {
      throw new Error('Navigate function not initialized')
    }

    // Mapeo de nombres de páginas a rutas
    const routes: Record<string, string> = {
      // Dashboard
      'dashboard': '/dashboard',
      'home': '/dashboard',
      'inicio': '/dashboard',
      'principal': '/dashboard',
      
      // Pacientes
      'patients': '/historial-pacientes',
      'pacientes': '/historial-pacientes',
      'historial': '/historial-pacientes',
      
      // Citas/Agenda
      'appointments': '/agenda',
      'citas': '/agenda',
      'agenda': '/agenda',
      'calendario': '/agenda',
      
      // Tratamientos (si existe)
      'treatments': '/tratamientos',
      'tratamientos': '/tratamientos',
      
      // Servicios (si existe)
      'services': '/servicios',
      'servicios': '/servicios',
      
      // Reportes (si existe)
      'reports': '/reportes',
      'reportes': '/reportes',
      
      // Configuración
      'settings': '/settings',
      'configuracion': '/settings',
      'ajustes': '/settings',
      'config': '/settings',
      
      // Configuraciones antiguas (solo Admin)
      'configuraciones': '/configuraciones',
      'admin': '/configuraciones'
    }

    const page = command.page.toLowerCase()
    const path = routes[page]

    if (!path) {
      toast.error(`No se encontró la página: ${command.page}`)
      return { success: false, error: 'Página no encontrada' }
    }

    // Construir ruta con parámetros si existen
    let fullPath = path
    if (command.params?.id) {
      fullPath += `/${command.params.id}`
    }

    // Navegar usando React Router
    this.navigate(fullPath)
    toast.success(`Navegando a ${command.page}`)

    return {
      success: true,
      page: command.page,
      path: fullPath
    }
  }

  /**
   * Abre un modal o formulario específico
   * Nota: Requiere integración con un sistema de modales (ej: Zustand store)
   * @param command - Comando de modal con nombre y datos opcionales para pre-llenar
   * @returns Resultado de la apertura del modal
   */
  async openModal(command: ModalCommand): Promise<any> {
    // Mapeo de nombres de modales
    const modals: Record<string, string> = {
      'create_patient': 'createPatient',
      'crear_paciente': 'createPatient',
      'new_patient': 'createPatient',
      'nuevo_paciente': 'createPatient',
      
      'create_appointment': 'createAppointment',
      'crear_cita': 'createAppointment',
      'agendar_cita': 'createAppointment',
      'nueva_cita': 'createAppointment',
      
      'create_treatment': 'createTreatment',
      'crear_tratamiento': 'createTreatment',
      'nuevo_tratamiento': 'createTreatment'
    }

    const modalKey = command.modal.toLowerCase()
    const modalName = modals[modalKey]

    if (!modalName) {
      toast.error(`No se encontró el modal: ${command.modal}`)
      return { success: false, error: 'Modal no encontrado' }
    }

    // TODO: Integrar con sistema de modales
    // Ejemplo con Zustand: useModalStore.getState().openModal(modalName, command.prefill)
    
    toast.info(`Abriendo formulario: ${command.modal}`)

    return {
      success: true,
      modal: command.modal,
      prefill: command.prefill,
      note: 'Integración con sistema de modales pendiente'
    }
  }

  /**
   * Muestra una notificación toast al usuario
   * @param message - Mensaje a mostrar
   * @param type - Tipo de notificación (success, error, warning, info)
   * @returns Resultado de la notificación
   */
  async showNotification(
    message: string, 
    type: 'success' | 'error' | 'warning' | 'info' = 'info'
  ): Promise<any> {
    switch (type) {
      case 'success':
        toast.success(message)
        break
      case 'error':
        toast.error(message)
        break
      case 'warning':
        toast.warning(message)
        break
      default:
        toast.info(message)
    }

    return { success: true, message, type }
  }
}

// Exportar instancia única del manejador (singleton)
export const navigationHandler = new NavigationHandler()
