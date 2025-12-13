/**
 * NOM-024 Catalogos - Mexican States and other required catalogs
 * These are simplified catalogs for the frontend.
 * Full official catalogs should be managed in the backend.
 */

export const ESTADOS_MEXICO = [
  { codigo: 'AGU', nombre: 'Aguascalientes' },
  { codigo: 'BCN', nombre: 'Baja California' },
  { codigo: 'BCS', nombre: 'Baja California Sur' },
  { codigo: 'CAM', nombre: 'Campeche' },
  { codigo: 'CHP', nombre: 'Chiapas' },
  { codigo: 'CHH', nombre: 'Chihuahua' },
  { codigo: 'CMX', nombre: 'Ciudad de México' },
  { codigo: 'COA', nombre: 'Coahuila' },
  { codigo: 'COL', nombre: 'Colima' },
  { codigo: 'DUR', nombre: 'Durango' },
  { codigo: 'GUA', nombre: 'Guanajuato' },
  { codigo: 'GRO', nombre: 'Guerrero' },
  { codigo: 'HID', nombre: 'Hidalgo' },
  { codigo: 'JAL', nombre: 'Jalisco' },
  { codigo: 'MEX', nombre: 'Estado de México' },
  { codigo: 'MIC', nombre: 'Michoacán' },
  { codigo: 'MOR', nombre: 'Morelos' },
  { codigo: 'NAY', nombre: 'Nayarit' },
  { codigo: 'NLE', nombre: 'Nuevo León' },
  { codigo: 'OAX', nombre: 'Oaxaca' },
  { codigo: 'PUE', nombre: 'Puebla' },
  { codigo: 'QUE', nombre: 'Querétaro' },
  { codigo: 'ROO', nombre: 'Quintana Roo' },
  { codigo: 'SLP', nombre: 'San Luis Potosí' },
  { codigo: 'SIN', nombre: 'Sinaloa' },
  { codigo: 'SON', nombre: 'Sonora' },
  { codigo: 'TAB', nombre: 'Tabasco' },
  { codigo: 'TAM', nombre: 'Tamaulipas' },
  { codigo: 'TLA', nombre: 'Tlaxcala' },
  { codigo: 'VER', nombre: 'Veracruz' },
  { codigo: 'YUC', nombre: 'Yucatán' },
  { codigo: 'ZAC', nombre: 'Zacatecas' },
]

/**
 * Validates CURP format (basic validation)
 * Full format: 4 letters + 6 digits + 1 letter (H/M) + 2 letters + 3 letters/digits + 2 digits
 * Example: HEGG560427MVZRRL04
 */
export const validateCURP = (curp: string): boolean => {
  if (!curp || curp.length !== 18) return false
  const curpRegex = /^[A-Z]{4}\d{6}[HM][A-Z]{5}[0-9A-Z]\d$/
  return curpRegex.test(curp)
}

/**
 * Validates CURP and returns error message if invalid
 */
export const getCURPValidationMessage = (curp: string): string | null => {
  if (!curp) return null // Empty is valid (optional field)
  if (curp.length !== 18) return 'CURP debe tener 18 caracteres'
  if (!validateCURP(curp)) return 'Formato de CURP inválido'
  return null
}
