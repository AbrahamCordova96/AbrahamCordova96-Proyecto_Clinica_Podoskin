"""
Herramientas de Gestión de Citas - Agente PodoSkin
================================================

Funciones para crear, modificar, consultar y gestionar citas
a través del agente conversacional.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, date, time, timedelta
from sqlalchemy import text, and_, or_, func
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from backend.api.deps.database import get_ops_db, get_core_db
from backend.schemas.ops.models import Cita, Podologo, CatalogoServicio
from backend.schemas.core.models import Paciente

logger = logging.getLogger(__name__)


class AppointmentManager:
    """
    Gestor de citas con capacidades avanzadas de búsqueda,
    creación y modificación a través del agente.
    """
    
    def __init__(self):
        self.ops_db_gen = get_ops_db()
        self.core_db_gen = get_core_db()
    
    def _get_ops_session(self) -> Session:
        """Obtiene sesión de la BD ops."""
        return next(self.ops_db_gen)
    
    def _get_core_session(self) -> Session:
        """Obtiene sesión de la BD core."""
        return next(self.core_db_gen)

    def search_available_slots(self, 
                             fecha: date, 
                             podologo_id: Optional[int] = None,
                             servicio_id: Optional[int] = None,
                             hora_inicio: Optional[time] = None,
                             hora_fin: Optional[time] = None) -> Dict[str, Any]:
        """
        Busca horarios disponibles para agendar citas.
        
        Args:
            fecha: Fecha para buscar disponibilidad
            podologo_id: ID específico del podólogo (opcional)
            servicio_id: ID del servicio (para calcular duración)
            hora_inicio: Hora de inicio del rango de búsqueda
            hora_fin: Hora de fin del rango de búsqueda
            
        Returns:
            Diccionario con horarios disponibles
        """
        try:
            ops_db = self._get_ops_session()
            
            # Obtener información del servicio si se especifica
            duracion_servicio = 60  # Default 60 minutos
            if servicio_id:
                servicio = ops_db.query(CatalogoServicio).filter(
                    CatalogoServicio.id_servicio == servicio_id
                ).first()
                if servicio and servicio.duracion_minutos:
                    duracion_servicio = servicio.duracion_minutos
            
            # Query para obtener citas existentes
            query = text("""
                SELECT 
                    c.podologo_id,
                    p.nombre_completo as podologo,
                    c.hora_inicio,
                    c.hora_fin,
                    c.status,
                    s.nombre_servicio
                FROM ops.citas c
                JOIN ops.podologos p ON c.podologo_id = p.id_podologo
                LEFT JOIN ops.catalogo_servicios s ON c.servicio_id = s.id_servicio
                WHERE c.fecha_cita = :fecha
                    AND c.deleted_at IS NULL
                    AND c.status NOT IN ('Cancelada', 'No Asistió')
                    AND (:podologo_id IS NULL OR c.podologo_id = :podologo_id)
                ORDER BY c.podologo_id, c.hora_inicio
            """)
            
            params = {
                "fecha": fecha,
                "podologo_id": podologo_id
            }
            
            result = ops_db.execute(query, params)
            citas_existentes = result.fetchall()
            
            # Agrupar por podólogo
            citas_por_podologo = {}
            for cita in citas_existentes:
                pid = cita[0]
                if pid not in citas_por_podologo:
                    citas_por_podologo[pid] = {
                        "podologo": cita[1],
                        "citas": []
                    }
                citas_por_podologo[pid]["citas"].append({
                    "hora_inicio": cita[2],
                    "hora_fin": cita[3],
                    "status": cita[4],
                    "servicio": cita[5]
                })
            
            # Generar horarios disponibles
            horarios_disponibles = self._generate_available_slots(
                citas_por_podologo,
                duracion_servicio,
                hora_inicio or time(8, 0),   # 8:00 AM por defecto
                hora_fin or time(18, 0)      # 6:00 PM por defecto
            )
            
            ops_db.close()
            
            return {
                "fecha": fecha.isoformat(),
                "duracion_servicio_minutos": duracion_servicio,
                "horarios_disponibles": horarios_disponibles,
                "citas_existentes": len(citas_existentes)
            }
            
        except Exception as e:
            logger.error(f"Error buscando horarios disponibles: {e}")
            return {"error": str(e)}

    def _generate_available_slots(self, 
                                citas_por_podologo: Dict[int, Dict],
                                duracion_minutos: int,
                                hora_inicio: time,
                                hora_fin: time) -> List[Dict[str, Any]]:
        """
        Genera lista de horarios disponibles basado en citas existentes.
        """
        slots_disponibles = []
        
        # Si no hay podólogos específicos, buscar todos los activos
        if not citas_por_podologo:
            try:
                ops_db = self._get_ops_session()
                podologos_query = text("""
                    SELECT id_podologo, nombre_completo 
                    FROM ops.podologos 
                    WHERE activo = true AND deleted_at IS NULL
                """)
                podologos_result = ops_db.execute(podologos_query)
                
                for podologo_row in podologos_result.fetchall():
                    pid = podologo_row[0]
                    citas_por_podologo[pid] = {
                        "podologo": podologo_row[1],
                        "citas": []
                    }
                ops_db.close()
            except Exception as e:
                logger.error(f"Error obteniendo podólogos: {e}")
                return []
        
        # Generar slots para cada podólogo
        for podologo_id, data in citas_por_podologo.items():
            podologo_nombre = data["podologo"]
            citas = sorted(data["citas"], key=lambda x: x["hora_inicio"])
            
            # Convertir a minutos para facilitar cálculos
            inicio_minutos = hora_inicio.hour * 60 + hora_inicio.minute
            fin_minutos = hora_fin.hour * 60 + hora_fin.minute
            
            # Buscar espacios libres
            tiempo_actual = inicio_minutos
            
            for cita in citas:
                cita_inicio = cita["hora_inicio"]
                cita_fin = cita["hora_fin"]
                
                # Convertir a minutos
                cita_inicio_min = cita_inicio.hour * 60 + cita_inicio.minute
                cita_fin_min = cita_fin.hour * 60 + cita_fin.minute
                
                # Si hay espacio antes de esta cita
                if tiempo_actual + duracion_minutos <= cita_inicio_min:
                    while tiempo_actual + duracion_minutos <= cita_inicio_min:
                        hora_slot = time(tiempo_actual // 60, tiempo_actual % 60)
                        hora_fin_slot = time((tiempo_actual + duracion_minutos) // 60, 
                                           (tiempo_actual + duracion_minutos) % 60)
                        
                        slots_disponibles.append({
                            "podologo_id": podologo_id,
                            "podologo": podologo_nombre,
                            "hora_inicio": hora_slot.strftime("%H:%M"),
                            "hora_fin": hora_fin_slot.strftime("%H:%M"),
                            "disponible": True
                        })
                        
                        tiempo_actual += 30  # Slots de 30 minutos
                
                # Avanzar tiempo actual después de la cita
                tiempo_actual = max(tiempo_actual, cita_fin_min)
            
            # Espacios libres después de la última cita
            while tiempo_actual + duracion_minutos <= fin_minutos:
                hora_slot = time(tiempo_actual // 60, tiempo_actual % 60)
                hora_fin_slot = time((tiempo_actual + duracion_minutos) // 60, 
                                   (tiempo_actual + duracion_minutos) % 60)
                
                slots_disponibles.append({
                    "podologo_id": podologo_id,
                    "podologo": podologo_nombre,
                    "hora_inicio": hora_slot.strftime("%H:%M"),
                    "hora_fin": hora_fin_slot.strftime("%H:%M"),
                    "disponible": True
                })
                
                tiempo_actual += 30
        
        return sorted(slots_disponibles, key=lambda x: (x["podologo"], x["hora_inicio"]))

    def create_appointment(self,
                         paciente_id: int,
                         podologo_id: int,
                         servicio_id: int,
                         fecha_cita: date,
                         hora_inicio: time,
                         notas: Optional[str] = None,
                         creado_por: int = 1) -> Dict[str, Any]:
        """
        Crea una nueva cita.
        
        Args:
            paciente_id: ID del paciente
            podologo_id: ID del podólogo
            servicio_id: ID del servicio
            fecha_cita: Fecha de la cita
            hora_inicio: Hora de inicio
            notas: Notas adicionales
            creado_por: ID del usuario que crea la cita
            
        Returns:
            Resultado de la operación
        """
        try:
            ops_db = self._get_ops_session()
            core_db = self._get_core_session()
            
            # Validar que el paciente existe
            paciente = core_db.query(Paciente).filter(
                Paciente.id_paciente == paciente_id,
                Paciente.deleted_at.is_(None)
            ).first()
            
            if not paciente:
                return {"error": f"Paciente con ID {paciente_id} no encontrado"}
            
            # Validar que el podólogo existe y está activo
            podologo = ops_db.query(Podologo).filter(
                Podologo.id_podologo == podologo_id,
                Podologo.activo == True,
                Podologo.deleted_at.is_(None)
            ).first()
            
            if not podologo:
                return {"error": f"Podólogo con ID {podologo_id} no encontrado o inactivo"}
            
            # Validar que el servicio existe
            servicio = ops_db.query(CatalogoServicio).filter(
                CatalogoServicio.id_servicio == servicio_id,
                CatalogoServicio.activo == True
            ).first()
            
            if not servicio:
                return {"error": f"Servicio con ID {servicio_id} no encontrado"}
            
            # Calcular hora de fin
            duracion = servicio.duracion_minutos or 60
            hora_fin = (datetime.combine(date.today(), hora_inicio) + 
                       timedelta(minutes=duracion)).time()
            
            # Verificar disponibilidad del horario
            conflicto = ops_db.query(Cita).filter(
                Cita.podologo_id == podologo_id,
                Cita.fecha_cita == fecha_cita,
                Cita.deleted_at.is_(None),
                Cita.status.in_(['Pendiente', 'Confirmada', 'En Sala']),
                or_(
                    and_(Cita.hora_inicio <= hora_inicio, Cita.hora_fin > hora_inicio),
                    and_(Cita.hora_inicio < hora_fin, Cita.hora_fin >= hora_fin),
                    and_(Cita.hora_inicio >= hora_inicio, Cita.hora_fin <= hora_fin)
                )
            ).first()
            
            if conflicto:
                return {
                    "error": f"Conflicto de horario. Ya existe cita de {conflicto.hora_inicio} a {conflicto.hora_fin}"
                }
            
            # Crear la nueva cita
            nueva_cita = Cita(
                paciente_id=paciente_id,
                podologo_id=podologo_id,
                servicio_id=servicio_id,
                fecha_cita=fecha_cita,
                hora_inicio=hora_inicio,
                hora_fin=hora_fin,
                status='Pendiente',
                notas_agendamiento=notas,
                created_by=creado_por
            )
            
            ops_db.add(nueva_cita)
            ops_db.commit()
            ops_db.refresh(nueva_cita)
            
            result = {
                "success": True,
                "cita_id": nueva_cita.id_cita,
                "mensaje": "Cita creada exitosamente",
                "detalles": {
                    "paciente": f"{paciente.nombres} {paciente.apellidos}",
                    "podologo": podologo.nombre_completo,
                    "servicio": servicio.nombre_servicio,
                    "fecha": fecha_cita.isoformat(),
                    "hora_inicio": hora_inicio.strftime("%H:%M"),
                    "hora_fin": hora_fin.strftime("%H:%M"),
                    "status": "Pendiente"
                }
            }
            
            ops_db.close()
            core_db.close()
            
            return result
            
        except SQLAlchemyError as e:
            logger.error(f"Error de BD creando cita: {e}")
            return {"error": "Error de base de datos al crear la cita"}
        except Exception as e:
            logger.error(f"Error creando cita: {e}")
            return {"error": str(e)}

    def search_appointments(self,
                          fecha_inicio: Optional[date] = None,
                          fecha_fin: Optional[date] = None,
                          paciente_id: Optional[int] = None,
                          podologo_id: Optional[int] = None,
                          status: Optional[str] = None,
                          limit: int = 50) -> Dict[str, Any]:
        """
        Busca citas según criterios especificados.
        
        Args:
            fecha_inicio: Fecha de inicio del rango de búsqueda
            fecha_fin: Fecha de fin del rango de búsqueda
            paciente_id: ID del paciente específico
            podologo_id: ID del podólogo específico
            status: Status específico de la cita
            limit: Límite de resultados
            
        Returns:
            Lista de citas encontradas
        """
        try:
            ops_db = self._get_ops_session()
            core_db = self._get_core_session()
            
            # Si no se especifican fechas, usar hoy como fecha de inicio
            if not fecha_inicio:
                fecha_inicio = date.today()
            
            # Si no se especifica fecha fin, usar una semana después del inicio
            if not fecha_fin:
                fecha_fin = fecha_inicio + timedelta(days=7)
            
            # =========================================================================
            # QUERY PASO 1: Obtener citas (ops.citas) con JOINs dentro de la misma BD
            # =========================================================================
            # No podemos hacer JOIN entre ops.citas y clinic.pacientes porque están 
            # en bases de datos diferentes. Hacemos queries separadas.
            
            query_citas = text("""
                SELECT 
                    c.id_cita,
                    c.fecha_cita,
                    c.hora_inicio,
                    c.hora_fin,
                    c.status,
                    c.notas_agendamiento,
                    c.paciente_id,
                    c.podologo_id,
                    c.servicio_id,
                    c.created_at,
                    pod.nombre_completo as podologo_nombre,
                    s.nombre_servicio,
                    s.precio_base
                FROM ops.citas c
                JOIN ops.podologos pod ON c.podologo_id = pod.id_podologo
                LEFT JOIN ops.catalogo_servicios s ON c.servicio_id = s.id_servicio
                WHERE c.deleted_at IS NULL
                    AND pod.deleted_at IS NULL
                    AND c.fecha_cita BETWEEN :fecha_inicio AND :fecha_fin
                    AND (:paciente_id IS NULL OR c.paciente_id = :paciente_id)
                    AND (:podologo_id IS NULL OR c.podologo_id = :podologo_id)
                    AND (:status IS NULL OR c.status = :status)
                ORDER BY c.fecha_cita, c.hora_inicio
                LIMIT :limit
            """)
            
            params = {
                "fecha_inicio": fecha_inicio,
                "fecha_fin": fecha_fin,
                "paciente_id": paciente_id,
                "podologo_id": podologo_id,
                "status": status,
                "limit": limit
            }
            
            result_citas = ops_db.execute(query_citas, params)
            citas_raw = result_citas.fetchall()
            
            # =========================================================================
            # QUERY PASO 2: Obtener datos de pacientes desde clinic.pacientes
            # =========================================================================
            # Extraer los IDs de pacientes que necesitamos
            paciente_ids = list(set([row[6] for row in citas_raw]))  # row[6] es paciente_id
            
            pacientes_dict = {}
            if paciente_ids:
                # Query a clinic.pacientes para obtener nombres y teléfonos
                query_pacientes = text("""
                    SELECT 
                        id_paciente,
                        nombres || ' ' || apellidos as nombre_completo,
                        telefono
                    FROM clinic.pacientes
                    WHERE id_paciente = ANY(:paciente_ids)
                        AND deleted_at IS NULL
                """)
                
                result_pacientes = core_db.execute(query_pacientes, {"paciente_ids": paciente_ids})
                
                for pac_row in result_pacientes.fetchall():
                    pacientes_dict[pac_row[0]] = {
                        "id": pac_row[0],
                        "nombre": pac_row[1],
                        "telefono": pac_row[2]
                    }
            
            # =========================================================================
            # PASO 3: Fusionar datos en memoria (application-level JOIN)
            # =========================================================================
            citas = []
            
            for row in citas_raw:
                paciente_id = row[6]
                paciente_data = pacientes_dict.get(paciente_id, {
                    "id": paciente_id,
                    "nombre": "Paciente no encontrado",
                    "telefono": "N/A"
                })
                
                cita = {
                    "id_cita": row[0],
                    "fecha_cita": row[1].isoformat() if row[1] else None,
                    "hora_inicio": row[2].strftime("%H:%M") if row[2] else None,
                    "hora_fin": row[3].strftime("%H:%M") if row[3] else None,
                    "status": row[4],
                    "notas": row[5],
                    "paciente": paciente_data,
                    "podologo": {
                        "id": row[7],
                        "nombre": row[10]
                    },
                    "servicio": {
                        "id": row[8],
                        "nombre": row[11],
                        "precio": float(row[12]) if row[12] else 0
                    },
                    "creada_en": row[9].isoformat() if row[9] else None
                }
                citas.append(cita)
            
            # Estadísticas rápidas
            stats = {
                "total_encontradas": len(citas),
                "por_status": {},
                "periodo": f"{fecha_inicio.isoformat()} a {fecha_fin.isoformat()}"
            }
            
            for cita in citas:
                status = cita["status"]
                stats["por_status"][status] = stats["por_status"].get(status, 0) + 1
            
            ops_db.close()
            core_db.close()
            
            return {
                "citas": citas,
                "estadisticas": stats,
                "filtros_aplicados": {
                    "fecha_inicio": fecha_inicio.isoformat() if fecha_inicio else None,
                    "fecha_fin": fecha_fin.isoformat() if fecha_fin else None,
                    "paciente_id": paciente_id,
                    "podologo_id": podologo_id,
                    "status": status
                }
            }
            
        except Exception as e:
            logger.error(f"Error buscando citas: {e}")
            return {"error": str(e)}

    def update_appointment_status(self,
                                cita_id: int,
                                nuevo_status: str,
                                notas: Optional[str] = None,
                                modificado_por: int = 1) -> Dict[str, Any]:
        """
        Actualiza el status de una cita.
        
        Args:
            cita_id: ID de la cita
            nuevo_status: Nuevo status
            notas: Notas adicionales
            modificado_por: ID del usuario que modifica
            
        Returns:
            Resultado de la operación
        """
        try:
            ops_db = self._get_ops_session()
            
            # Obtener la cita
            cita = ops_db.query(Cita).filter(
                Cita.id_cita == cita_id,
                Cita.deleted_at.is_(None)
            ).first()
            
            if not cita:
                return {"error": f"Cita con ID {cita_id} no encontrada"}
            
            # Validar nuevo status
            status_validos = ['Pendiente', 'Confirmada', 'En Sala', 'Realizada', 'Cancelada', 'No Asistió']
            if nuevo_status not in status_validos:
                return {"error": f"Status '{nuevo_status}' no válido. Opciones: {', '.join(status_validos)}"}
            
            # Actualizar
            status_anterior = cita.status
            cita.status = nuevo_status
            cita.updated_by = modificado_por
            
            if notas:
                cita.notas_agendamiento = (cita.notas_agendamiento or "") + f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M')}] {notas}"
            
            ops_db.commit()
            
            result = {
                "success": True,
                "mensaje": f"Status actualizado de '{status_anterior}' a '{nuevo_status}'",
                "cita_id": cita_id,
                "status_anterior": status_anterior,
                "status_nuevo": nuevo_status
            }
            
            ops_db.close()
            return result
            
        except Exception as e:
            logger.error(f"Error actualizando status de cita: {e}")
            return {"error": str(e)}


# =============================================================================
# FUNCIONES DE INTEGRACIÓN CON EL AGENTE
# =============================================================================

def process_appointment_request(query: str, user_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Procesa solicitudes relacionadas con citas desde el agente.
    
    Args:
        query: Consulta del usuario
        user_data: Datos del usuario autenticado
        
    Returns:
        Respuesta procesada
    """
    manager = AppointmentManager()
    query_lower = query.lower()
    
    # Detectar tipo de solicitud
    if any(keyword in query_lower for keyword in ['disponible', 'horario libre', 'agenda']):
        # Búsqueda de disponibilidad
        return manager.search_available_slots(date.today())
    
    elif any(keyword in query_lower for keyword in ['citas hoy', 'agenda hoy', 'programadas hoy']):
        # Citas del día
        return manager.search_appointments(fecha_inicio=date.today(), fecha_fin=date.today())
    
    elif any(keyword in query_lower for keyword in ['próximas citas', 'siguiente', 'esta semana']):
        # Próximas citas
        return manager.search_appointments(fecha_inicio=date.today())
    
    elif 'cancelar' in query_lower or 'cambiar status' in query_lower:
        # Cambio de status (requeriría parsing más específico)
        return {"mensaje": "Para cambiar status de citas, especifique el ID de la cita y el nuevo status"}
    
    else:
        # Búsqueda general
        return manager.search_appointments()


# =============================================================================
# KEYWORDS PARA EL AGENTE
# =============================================================================

APPOINTMENT_KEYWORDS = {
    "consulta": ["cita", "citas", "agenda", "agendar", "programar", "horario"],
    "disponibilidad": ["disponible", "libre", "horarios", "espacio"],
    "modificacion": ["cancelar", "cambiar", "mover", "reprogramar"],
    "busqueda": ["buscar", "encontrar", "mostrar", "listar"]
}


def is_appointment_query(query: str) -> bool:
    """
    Determina si una consulta está relacionada con citas.
    
    Args:
        query: Consulta del usuario
        
    Returns:
        True si es relacionada con citas
    """
    query_lower = query.lower()
    
    for category, keywords in APPOINTMENT_KEYWORDS.items():
        if any(keyword in query_lower for keyword in keywords):
            return True
    
    return False