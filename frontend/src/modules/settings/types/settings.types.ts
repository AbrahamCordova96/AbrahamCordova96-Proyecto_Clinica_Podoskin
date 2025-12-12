// ============================================================================
// TIPOS DEL MÓDULO DE CONFIGURACIÓN
// ============================================================================

import { User } from '../../auth/types/auth.types'

/**
 * Usuario extendido con campos opcionales de configuración
 * Estos campos deberían ser agregados al modelo User en el backend
 */
export interface UserWithSettings extends User {
  has_gemini_key?: boolean
  gemini_key_status?: 'valid' | 'invalid' | null
}
