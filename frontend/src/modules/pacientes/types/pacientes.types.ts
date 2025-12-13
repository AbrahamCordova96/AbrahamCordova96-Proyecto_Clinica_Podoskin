export interface Paciente {
  id_paciente: number
  nombres: string
  apellidos: string
  fecha_nacimiento: string
  sexo: string
  telefono: string
  email?: string
  domicilio?: string
  documento_id?: string
  activo: boolean
  created_at: string
  updated_at: string
  // NOM-024 optional fields
  curp?: string
  estado_nacimiento?: string
  nacionalidad?: string
  estado_residencia?: string
  municipio_residencia?: string
  localidad_residencia?: string
}

export interface PacienteCreateInput {
  nombres: string
  apellidos: string
  fecha_nacimiento: string
  sexo: string
  telefono: string
  email?: string
  domicilio?: string
  documento_id?: string
  // NOM-024 optional fields
  curp?: string
  estado_nacimiento?: string
  nacionalidad?: string
  estado_residencia?: string
  municipio_residencia?: string
  localidad_residencia?: string
}

export interface PacienteUpdateInput {
  nombres?: string
  apellidos?: string
  fecha_nacimiento?: string
  sexo?: string
  telefono?: string
  email?: string
  domicilio?: string
  documento_id?: string
  activo?: boolean
  // NOM-024 optional fields
  curp?: string
  estado_nacimiento?: string
  nacionalidad?: string
  estado_residencia?: string
  municipio_residencia?: string
  localidad_residencia?: string
}

export interface PacienteFilters {
  search?: string
  activo?: boolean
  page?: number
  per_page?: number
}

export interface PacienteHistorial {
  paciente: Paciente
  tratamientos: Tratamiento[]
  citas: Cita[]
}

export type TratamientoEstado = 'activo' | 'completado'

export interface Tratamiento {
  id_tratamiento: number
  paciente_id: number
  paciente?: Paciente
  problema: string
  fecha_inicio: string
  fecha_fin?: string
  estado: TratamientoEstado
  notas_adicionales?: string
  activo: boolean
  evoluciones?: Evolucion[]
  evidencias?: Evidencia[]
}

export interface TratamientoCreateInput {
  paciente_id: number
  problema: string
  fecha_inicio: string
  fecha_fin?: string
  estado?: TratamientoEstado
  notas_adicionales?: string
}

export interface TratamientoUpdateInput {
  problema?: string
  fecha_inicio?: string
  fecha_fin?: string
  estado?: TratamientoEstado
  notas_adicionales?: string
  activo?: boolean
}

export interface Evolucion {
  id_evolucion: number
  tratamiento_id: number
  podologo_id: number
  podologo?: Podologo
  fecha_visita: string
  nota: string
  tipo_visita?: string
  signos_vitales?: Record<string, any>
  created_at: string
  // NOM-024 optional fields
  diagnostico_codigo_cie10?: string
  procedimiento_codigo?: string
}

export interface EvolucionCreateInput {
  tratamiento_id: number
  podologo_id: number
  fecha_visita: string
  nota: string
  tipo_visita?: string
  signos_vitales?: Record<string, any>
  // NOM-024 optional fields
  diagnostico_codigo_cie10?: string
  procedimiento_codigo?: string
}

export interface EvolucionUpdateInput {
  fecha_visita?: string
  nota?: string
  tipo_visita?: string
  signos_vitales?: Record<string, any>
  // NOM-024 optional fields
  diagnostico_codigo_cie10?: string
  procedimiento_codigo?: string
}

export type EvidenciaTipo = 'foto' | 'radiografia'

export interface Evidencia {
  id_evidencia: number
  tratamiento_id: number
  evolucion_id?: number
  archivo_url: string
  thumbnail_url?: string
  tipo: EvidenciaTipo
  metadata?: Record<string, any>
  created_at: string
}

export interface Podologo {
  id_podologo: number
  nombres: string
  apellidos: string
  especialidad?: string
  disponibilidad?: Record<string, any>
  contacto?: string
  activo: boolean
  // NOM-024 professional data
  cedula_profesional?: string
  institucion_emisora?: string
}

export interface Cita {
  id_cita: number
  paciente_id: number
  podologo_id: number
  podologo?: Podologo
  servicio_id?: number
  servicio?: Servicio
  fecha_hora: string
  duracion_minutos: number
  estado: string
  motivo?: string
  sala?: string
  created_by: number
  created_at: string
}

export interface Servicio {
  id_servicio: number
  nombre: string
  descripcion?: string
  duracion_minutos: number
  precio: number
  activo: boolean
}
