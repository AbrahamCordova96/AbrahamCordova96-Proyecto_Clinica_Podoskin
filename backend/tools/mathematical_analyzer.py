"""
Herramientas de Análisis Matemático y Estadístico
===============================================

Herramientas especializadas para cálculos matemáticos, estadísticas 
y análisis de datos clínicos para el agente PodoSkin.
"""

import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, date, timedelta
from decimal import Decimal
import statistics
import numpy as np
from sqlalchemy import text, func
from sqlalchemy.orm import Session

from backend.api.deps.database import get_core_db, get_ops_db

logger = logging.getLogger(__name__)


class MathematicalAnalyzer:
    """
    Clase para realizar análisis matemáticos y estadísticos
    sobre los datos clínicos.
    """
    
    def __init__(self):
        self.core_db_gen = get_core_db()
        self.ops_db_gen = get_ops_db()
    
    def _get_core_session(self) -> Session:
        """Obtiene una sesión de la BD core."""
        return next(self.core_db_gen)
    
    def _get_ops_session(self) -> Session:
        """Obtiene una sesión de la BD ops.""" 
        return next(self.ops_db_gen)

    def calculate_patient_age_statistics(self) -> Dict[str, Any]:
        """
        Calcula estadísticas de edad de los pacientes.
        
        Returns:
            Diccionario con estadísticas de edad
        """
        try:
            db = self._get_core_session()
            
            # Query para obtener edades actuales
            query = text("""
                SELECT 
                    EXTRACT(YEAR FROM AGE(CURRENT_DATE, fecha_nacimiento)) as edad
                FROM clinic.pacientes 
                WHERE deleted_at IS NULL 
                    AND fecha_nacimiento IS NOT NULL
            """)
            
            result = db.execute(query)
            edades = [row[0] for row in result.fetchall()]
            
            if not edades:
                return {"error": "No se encontraron datos de edad"}
            
            # Calcular estadísticas
            stats = {
                "total_pacientes": len(edades),
                "edad_promedio": round(statistics.mean(edades), 1),
                "edad_mediana": statistics.median(edades),
                "edad_minima": min(edades),
                "edad_maxima": max(edades),
                "desviacion_estandar": round(statistics.stdev(edades) if len(edades) > 1 else 0, 1),
                "distribucion_por_decadas": self._calculate_age_distribution(edades)
            }
            
            db.close()
            return stats
            
        except Exception as e:
            logger.error(f"Error calculando estadísticas de edad: {e}")
            return {"error": str(e)}

    def _calculate_age_distribution(self, edades: List[float]) -> Dict[str, int]:
        """
        Calcula la distribución de pacientes por décadas.
        """
        distribution = {
            "0-10": 0, "11-20": 0, "21-30": 0, "31-40": 0, "41-50": 0,
            "51-60": 0, "61-70": 0, "71-80": 0, "81-90": 0, "90+": 0
        }
        
        for edad in edades:
            if edad <= 10:
                distribution["0-10"] += 1
            elif edad <= 20:
                distribution["11-20"] += 1
            elif edad <= 30:
                distribution["21-30"] += 1
            elif edad <= 40:
                distribution["31-40"] += 1
            elif edad <= 50:
                distribution["41-50"] += 1
            elif edad <= 60:
                distribution["51-60"] += 1
            elif edad <= 70:
                distribution["61-70"] += 1
            elif edad <= 80:
                distribution["71-80"] += 1
            elif edad <= 90:
                distribution["81-90"] += 1
            else:
                distribution["90+"] += 1
        
        return distribution

    def calculate_gender_distribution(self) -> Dict[str, Any]:
        """
        Calcula la distribución por género de los pacientes.
        """
        try:
            db = self._get_core_session()
            
            query = text("""
                SELECT 
                    sexo,
                    COUNT(*) as cantidad,
                    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) as porcentaje
                FROM clinic.pacientes 
                WHERE deleted_at IS NULL 
                    AND sexo IS NOT NULL
                GROUP BY sexo
                ORDER BY cantidad DESC
            """)
            
            result = db.execute(query)
            rows = result.fetchall()
            
            total = sum(row[1] for row in rows)
            
            distribution = {
                "total_pacientes": total,
                "por_genero": {
                    row[0]: {
                        "cantidad": row[1],
                        "porcentaje": float(row[2])
                    }
                    for row in rows
                }
            }
            
            db.close()
            return distribution
            
        except Exception as e:
            logger.error(f"Error calculando distribución por género: {e}")
            return {"error": str(e)}

    def calculate_treatment_duration_statistics(self) -> Dict[str, Any]:
        """
        Calcula estadísticas de duración de tratamientos.
        """
        try:
            db = self._get_core_session()
            
            query = text("""
                SELECT 
                    fecha_inicio,
                    CASE 
                        WHEN estado_tratamiento = 'Alta' AND fecha_cierre IS NOT NULL 
                        THEN fecha_cierre
                        ELSE CURRENT_DATE
                    END as fecha_fin,
                    estado_tratamiento
                FROM clinic.tratamientos 
                WHERE deleted_at IS NULL 
                    AND fecha_inicio IS NOT NULL
            """)
            
            result = db.execute(query)
            rows = result.fetchall()
            
            if not rows:
                return {"error": "No se encontraron datos de tratamientos"}
            
            duraciones = []
            completados = []
            activos = []
            
            for row in rows:
                fecha_inicio = row[0]
                fecha_fin = row[1]
                estado = row[2]
                
                if isinstance(fecha_inicio, str):
                    fecha_inicio = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
                if isinstance(fecha_fin, str):
                    fecha_fin = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
                elif isinstance(fecha_fin, datetime):
                    fecha_fin = fecha_fin.date()
                
                duracion_dias = (fecha_fin - fecha_inicio).days
                duraciones.append(duracion_dias)
                
                if estado == 'Alta':
                    completados.append(duracion_dias)
                else:
                    activos.append(duracion_dias)
            
            stats = {
                "total_tratamientos": len(duraciones),
                "duracion_promedio_dias": round(statistics.mean(duraciones), 1),
                "duracion_mediana_dias": statistics.median(duraciones),
                "duracion_minima_dias": min(duraciones),
                "duracion_maxima_dias": max(duraciones),
                "tratamientos_completados": {
                    "cantidad": len(completados),
                    "duracion_promedio": round(statistics.mean(completados), 1) if completados else 0
                },
                "tratamientos_activos": {
                    "cantidad": len(activos),
                    "tiempo_transcurrido_promedio": round(statistics.mean(activos), 1) if activos else 0
                }
            }
            
            db.close()
            return stats
            
        except Exception as e:
            logger.error(f"Error calculando estadísticas de tratamientos: {e}")
            return {"error": str(e)}

    def calculate_appointment_efficiency_metrics(self) -> Dict[str, Any]:
        """
        Calcula métricas de eficiencia de citas.
        """
        try:
            db = self._get_ops_session()
            
            # Análisis de ausentismo
            ausentismo_query = text("""
                SELECT 
                    status,
                    COUNT(*) as cantidad,
                    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) as porcentaje
                FROM ops.citas 
                WHERE deleted_at IS NULL 
                    AND fecha_cita >= CURRENT_DATE - INTERVAL '30 days'
                GROUP BY status
                ORDER BY cantidad DESC
            """)
            
            ausentismo_result = db.execute(ausentismo_query)
            ausentismo_data = {
                row[0]: {"cantidad": row[1], "porcentaje": float(row[2])}
                for row in ausentismo_result.fetchall()
            }
            
            # Análisis de productividad por podólogo
            productividad_query = text("""
                SELECT 
                    p.nombre_completo,
                    COUNT(c.id_cita) as total_citas,
                    COUNT(CASE WHEN c.status = 'Realizada' THEN 1 END) as citas_realizadas,
                    ROUND(
                        COUNT(CASE WHEN c.status = 'Realizada' THEN 1 END) * 100.0 / 
                        NULLIF(COUNT(c.id_cita), 0), 2
                    ) as eficiencia_porcentaje
                FROM ops.podologos p
                LEFT JOIN ops.citas c ON p.id_podologo = c.podologo_id 
                    AND c.deleted_at IS NULL 
                    AND c.fecha_cita >= CURRENT_DATE - INTERVAL '30 days'
                WHERE p.deleted_at IS NULL AND p.activo = true
                GROUP BY p.id_podologo, p.nombre_completo
                ORDER BY citas_realizadas DESC
            """)
            
            productividad_result = db.execute(productividad_query)
            productividad_data = [
                {
                    "podologo": row[0],
                    "total_citas": row[1],
                    "citas_realizadas": row[2],
                    "eficiencia_porcentaje": float(row[3]) if row[3] else 0
                }
                for row in productividad_result.fetchall()
            ]
            
            # Análisis de horarios más solicitados
            horarios_query = text("""
                SELECT 
                    EXTRACT(HOUR FROM hora_inicio) as hora,
                    COUNT(*) as cantidad_citas
                FROM ops.citas 
                WHERE deleted_at IS NULL 
                    AND fecha_cita >= CURRENT_DATE - INTERVAL '30 days'
                    AND hora_inicio IS NOT NULL
                GROUP BY EXTRACT(HOUR FROM hora_inicio)
                ORDER BY cantidad_citas DESC
                LIMIT 5
            """)
            
            horarios_result = db.execute(horarios_query)
            horarios_populares = [
                {"hora": f"{int(row[0])}:00", "cantidad": row[1]}
                for row in horarios_result.fetchall()
            ]
            
            metrics = {
                "ausentismo_por_status": ausentismo_data,
                "productividad_por_podologo": productividad_data,
                "horarios_mas_populares": horarios_populares,
                "periodo_analisis": "Últimos 30 días"
            }
            
            db.close()
            return metrics
            
        except Exception as e:
            logger.error(f"Error calculando métricas de citas: {e}")
            return {"error": str(e)}

    def calculate_service_profitability(self) -> Dict[str, Any]:
        """
        Calcula análisis de rentabilidad por servicio.
        """
        try:
            db = self._get_ops_session()
            
            query = text("""
                SELECT 
                    cs.nombre_servicio,
                    cs.precio_base,
                    COUNT(c.id_cita) as veces_solicitado,
                    cs.precio_base * COUNT(c.id_cita) as ingreso_potencial,
                    cs.duracion_minutos,
                    ROUND(
                        cs.precio_base / NULLIF(cs.duracion_minutos, 0), 2
                    ) as precio_por_minuto
                FROM ops.catalogo_servicios cs
                LEFT JOIN ops.citas c ON cs.id_servicio = c.servicio_id 
                    AND c.deleted_at IS NULL 
                    AND c.status = 'Realizada'
                    AND c.fecha_cita >= CURRENT_DATE - INTERVAL '30 days'
                WHERE cs.activo = true
                GROUP BY cs.id_servicio, cs.nombre_servicio, cs.precio_base, cs.duracion_minutos
                ORDER BY ingreso_potencial DESC
            """)
            
            result = db.execute(query)
            servicios = [
                {
                    "servicio": row[0],
                    "precio_base": float(row[1]) if row[1] else 0,
                    "veces_solicitado": row[2],
                    "ingreso_potencial": float(row[3]) if row[3] else 0,
                    "duracion_minutos": row[4] if row[4] else 0,
                    "precio_por_minuto": float(row[5]) if row[5] else 0
                }
                for row in result.fetchall()
            ]
            
            total_ingresos = sum(s["ingreso_potencial"] for s in servicios)
            
            # Agregar porcentaje de contribución
            for servicio in servicios:
                servicio["porcentaje_ingresos"] = round(
                    (servicio["ingreso_potencial"] / total_ingresos * 100) if total_ingresos > 0 else 0, 
                    2
                )
            
            analysis = {
                "servicios": servicios,
                "total_ingresos_potenciales": total_ingresos,
                "servicio_mas_rentable": servicios[0] if servicios else None,
                "periodo_analisis": "Últimos 30 días"
            }
            
            db.close()
            return analysis
            
        except Exception as e:
            logger.error(f"Error calculando rentabilidad de servicios: {e}")
            return {"error": str(e)}

    def calculate_diagnosis_frequency_analysis(self) -> Dict[str, Any]:
        """
        Analiza la frecuencia de diagnósticos por rango de edad.
        """
        try:
            db = self._get_core_session()
            
            query = text("""
                SELECT 
                    t.diagnostico_inicial,
                    COUNT(*) as frecuencia,
                    ROUND(AVG(EXTRACT(YEAR FROM AGE(t.fecha_inicio, p.fecha_nacimiento))), 1) as edad_promedio,
                    MIN(EXTRACT(YEAR FROM AGE(t.fecha_inicio, p.fecha_nacimiento))) as edad_minima,
                    MAX(EXTRACT(YEAR FROM AGE(t.fecha_inicio, p.fecha_nacimiento))) as edad_maxima
                FROM clinic.tratamientos t
                JOIN clinic.pacientes p ON t.paciente_id = p.id_paciente
                WHERE t.deleted_at IS NULL 
                    AND p.deleted_at IS NULL
                    AND t.diagnostico_inicial IS NOT NULL
                    AND p.fecha_nacimiento IS NOT NULL
                GROUP BY t.diagnostico_inicial
                HAVING COUNT(*) >= 2  -- Solo diagnósticos con al menos 2 casos
                ORDER BY frecuencia DESC
                LIMIT 10
            """)
            
            result = db.execute(query)
            diagnosticos = [
                {
                    "diagnostico": row[0],
                    "frecuencia": row[1],
                    "edad_promedio": float(row[2]) if row[2] else 0,
                    "rango_edad_minima": int(row[3]) if row[3] else 0,
                    "rango_edad_maxima": int(row[4]) if row[4] else 0
                }
                for row in result.fetchall()
            ]
            
            total_casos = sum(d["frecuencia"] for d in diagnosticos)
            
            # Agregar porcentajes
            for diagnostico in diagnosticos:
                diagnostico["porcentaje"] = round(
                    (diagnostico["frecuencia"] / total_casos * 100) if total_casos > 0 else 0,
                    2
                )
            
            analysis = {
                "diagnosticos_mas_frecuentes": diagnosticos,
                "total_casos_analizados": total_casos,
                "diagnostico_mas_comun": diagnosticos[0] if diagnosticos else None
            }
            
            db.close()
            return analysis
            
        except Exception as e:
            logger.error(f"Error analizando frecuencia de diagnósticos: {e}")
            return {"error": str(e)}


# =============================================================================
# FUNCIONES UTILITARIAS PARA EL AGENTE
# =============================================================================

def execute_mathematical_analysis(analysis_type: str, **kwargs) -> Dict[str, Any]:
    """
    Ejecuta un análisis matemático específico.
    
    Args:
        analysis_type: Tipo de análisis a ejecutar
        **kwargs: Parámetros adicionales
        
    Returns:
        Resultado del análisis
    """
    analyzer = MathematicalAnalyzer()
    
    analyses = {
        "edad_pacientes": analyzer.calculate_patient_age_statistics,
        "distribucion_genero": analyzer.calculate_gender_distribution,
        "duracion_tratamientos": analyzer.calculate_treatment_duration_statistics,
        "eficiencia_citas": analyzer.calculate_appointment_efficiency_metrics,
        "rentabilidad_servicios": analyzer.calculate_service_profitability,
        "frecuencia_diagnosticos": analyzer.calculate_diagnosis_frequency_analysis
    }
    
    if analysis_type not in analyses:
        return {"error": f"Tipo de análisis '{analysis_type}' no disponible"}
    
    try:
        return analyses[analysis_type]()
    except Exception as e:
        logger.error(f"Error ejecutando análisis {analysis_type}: {e}")
        return {"error": str(e)}


def calculate_custom_statistics(data: List[Union[int, float]]) -> Dict[str, Any]:
    """
    Calcula estadísticas descriptivas para una lista de números.
    
    Args:
        data: Lista de números
        
    Returns:
        Diccionario con estadísticas
    """
    try:
        if not data:
            return {"error": "No hay datos para analizar"}
        
        # Filtrar valores no numéricos
        numeric_data = [x for x in data if isinstance(x, (int, float)) and not np.isnan(x)]
        
        if not numeric_data:
            return {"error": "No hay datos numéricos válidos"}
        
        stats = {
            "cantidad": len(numeric_data),
            "suma": sum(numeric_data),
            "promedio": statistics.mean(numeric_data),
            "mediana": statistics.median(numeric_data),
            "moda": statistics.mode(numeric_data) if len(set(numeric_data)) < len(numeric_data) else None,
            "minimo": min(numeric_data),
            "maximo": max(numeric_data),
            "rango": max(numeric_data) - min(numeric_data),
            "desviacion_estandar": statistics.stdev(numeric_data) if len(numeric_data) > 1 else 0,
            "varianza": statistics.variance(numeric_data) if len(numeric_data) > 1 else 0
        }
        
        # Percentiles usando numpy
        if len(numeric_data) >= 4:
            stats["percentil_25"] = np.percentile(numeric_data, 25)
            stats["percentil_75"] = np.percentile(numeric_data, 75)
            stats["rango_intercuartilico"] = stats["percentil_75"] - stats["percentil_25"]
        
        return stats
        
    except Exception as e:
        return {"error": f"Error calculando estadísticas: {str(e)}"}


# =============================================================================
# FUNCIONES PARA INTEGRATION CON EL AGENTE
# =============================================================================

# Mapa de análisis disponibles para el agente
AVAILABLE_ANALYSES = {
    "edad": "edad_pacientes",
    "edades": "edad_pacientes", 
    "género": "distribucion_genero",
    "genero": "distribucion_genero",
    "sexo": "distribucion_genero",
    "tratamientos": "duracion_tratamientos",
    "tratamiento": "duracion_tratamientos",
    "citas": "eficiencia_citas",
    "agenda": "eficiencia_citas",
    "servicios": "rentabilidad_servicios",
    "rentabilidad": "rentabilidad_servicios",
    "diagnósticos": "frecuencia_diagnosticos",
    "diagnosticos": "frecuencia_diagnosticos",
    "patologías": "frecuencia_diagnosticos",
    "patologias": "frecuencia_diagnosticos"
}


def get_analysis_for_query(query: str) -> Optional[str]:
    """
    Determina qué análisis ejecutar basado en la consulta.
    
    Args:
        query: Consulta del usuario
        
    Returns:
        Tipo de análisis a ejecutar o None
    """
    query_lower = query.lower()
    
    for keyword, analysis_type in AVAILABLE_ANALYSES.items():
        if keyword in query_lower:
            return analysis_type
    
    return None