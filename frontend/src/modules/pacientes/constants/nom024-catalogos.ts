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
 * Full format breakdown:
 * - Position 1-4: First 4 letters (2 from last name, 2 from first name)
 * - Position 5-10: Birth date YYMMDD
 * - Position 11: Sex (H=Male, M=Female)
 * - Position 12-13: State of birth code (2 letters)
 * - Position 14-16: First internal consonants of names (3 letters)
 * - Position 17: Homonym differentiator (0-9 or A-Z)
 * - Position 18: Check digit (0-9)
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
