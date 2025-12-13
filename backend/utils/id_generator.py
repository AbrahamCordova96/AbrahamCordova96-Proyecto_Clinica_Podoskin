# backend/utils/id_generator.py
"""
Generador de IDs estructurados para el sistema.

Formato: ASGO-1212-00001
- 2 letras del primer apellido (uppercase)
- 2 letras del primer nombre (uppercase)
- Guion
- Mes-Día del registro (MMDD)
- Guion
- Contador secuencial con padding de 5 dígitos (00001)

Ejemplos:
- Santiago de Jesus Ornelas Reynoso → RENO-1213-00001
- Maria Lopez Garcia → LOMA-0315-00023
- Juan Carlos Perez → PEJU-0801-00150
"""

from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func
import re


def limpiar_nombre(nombre: str) -> str:
    """
    Limpia un nombre removiendo acentos y caracteres especiales.
    
    Args:
        nombre: Nombre a limpiar
        
    Returns:
        Nombre limpio sin acentos ni caracteres especiales
    """
    # Mapeo de caracteres con acento a sin acento
    acentos = {
        'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u',
        'Á': 'A', 'É': 'E', 'Í': 'I', 'Ó': 'O', 'Ú': 'U',
        'ñ': 'n', 'Ñ': 'N', 'ü': 'u', 'Ü': 'U'
    }
    
    resultado = nombre
    for con_acento, sin_acento in acentos.items():
        resultado = resultado.replace(con_acento, sin_acento)
    
    # Remover cualquier otro carácter que no sea letra o espacio
    resultado = re.sub(r'[^a-zA-Z\s]', '', resultado)
    
    return resultado.strip()


def extraer_iniciales(nombre_completo: str, es_apellido: bool = False) -> str:
    """
    Extrae las ÚLTIMAS 2 letras de un nombre o apellido.
    
    Args:
        nombre_completo: Nombre o apellido completo (puede tener múltiples palabras)
        es_apellido: True si es apellido, False si es nombre
        
    Returns:
        2 letras en mayúsculas (ÚLTIMAS 2 del primer elemento)
        
    Ejemplos:
        - "Ornelas Reynoso" → "AS" (últimas 2 de Ornelas)
        - "Santiago de Jesus" → "GO" (últimas 2 de Santiago)
        - "Maria" → "IA"
    """
    # Limpiar acentos y caracteres especiales
    limpio = limpiar_nombre(nombre_completo)
    
    # Separar palabras
    palabras = [p for p in limpio.split() if len(p) > 1]  # Ignorar "de", "la", etc.
    
    if not palabras:
        return "XX"  # Fallback si no hay palabras válidas
    
    # Tomar el primer elemento válido
    primer_elemento = palabras[0].upper()
    
    # Si la palabra tiene al menos 2 letras, tomar las ÚLTIMAS 2
    if len(primer_elemento) >= 2:
        return primer_elemento[-2:]
    
    # Si solo tiene 1 letra, completar con la última letra de la siguiente palabra
    if len(palabras) > 1:
        return (primer_elemento + palabras[1][-1]).upper()
    
    # Fallback: duplicar la única letra
    return (primer_elemento + primer_elemento).upper()


def generar_codigo_interno(
    apellido_paterno: str,
    nombre: str,
    fecha_registro: datetime,
    model_class,
    db: Session
) -> str:
    """
    Genera un código interno estructurado para usuarios, pacientes, etc.
    
    Formato: ASGO-1212-00001
    
    Args:
        apellido_paterno: Primer apellido (ej: "Ornelas Reynoso")
        nombre: Primer nombre (ej: "Santiago de Jesus")
        fecha_registro: Fecha de registro del usuario/paciente
        model_class: Clase del modelo (SysUsuario, Paciente, etc.)
        db: Sesión de base de datos
        
    Returns:
        Código interno único
        
    Ejemplo:
        generar_codigo_interno("Ornelas Reynoso", "Santiago", datetime.now(), SysUsuario, db)
        → "RENO-1213-00001"
    """
    # 1. Extraer iniciales (2 letras de apellido + 2 de nombre)
    iniciales_apellido = extraer_iniciales(apellido_paterno, es_apellido=True)
    iniciales_nombre = extraer_iniciales(nombre, es_apellido=False)
    
    prefijo = f"{iniciales_apellido}{iniciales_nombre}"
    
    # 2. Fecha en formato MMDD
    mes_dia = fecha_registro.strftime("%m%d")
    
    # 3. Obtener el contador actual para este prefijo y fecha
    # Buscar el último código generado que comience con este prefijo-fecha
    patron_busqueda = f"{prefijo}-{mes_dia}-%"
    
    # Query para obtener el último número
    ultimo_codigo = db.query(
        func.max(model_class.codigo_interno)
    ).filter(
        model_class.codigo_interno.like(patron_busqueda)
    ).scalar()
    
    # 4. Incrementar el contador
    if ultimo_codigo:
        # Extraer el número del último código (formato: XXXX-MMDD-NNNNN)
        partes = ultimo_codigo.split('-')
        if len(partes) == 3:
            ultimo_numero = int(partes[2])
            nuevo_numero = ultimo_numero + 1
        else:
            nuevo_numero = 1
    else:
        # Primer registro con este prefijo-fecha
        nuevo_numero = 1
    
    # 5. Formatear con padding de 5 dígitos
    numero_formateado = str(nuevo_numero).zfill(5)
    
    # 6. Construir el código completo
    codigo_completo = f"{prefijo}-{mes_dia}-{numero_formateado}"
    
    return codigo_completo


def generar_codigo_clinica(nombre_clinica: str, fecha_registro: datetime, db: Session) -> str:
    """
    Genera un código interno para clínicas.
    
    Formato: POLI-1213-00001
    
    Args:
        nombre_clinica: Nombre de la clínica (ej: "Podoskin Libertad")
        fecha_registro: Fecha de registro
        db: Sesión de base de datos
        
    Returns:
        Código interno único
        
    Ejemplo:
        "Podoskin Libertad" → "POLI-1213-00001"
    """
    from backend.schemas.auth.models import Clinica
    
    # Tomar las primeras 4 letras del primer palabra del nombre
    palabras = limpiar_nombre(nombre_clinica).split()
    if palabras:
        prefijo = palabras[0][:4].upper()
    else:
        prefijo = "CLIN"  # Fallback
    
    # Asegurar que tenga exactamente 4 caracteres
    if len(prefijo) < 4:
        prefijo = prefijo.ljust(4, 'X')
    
    # Fecha en formato MMDD
    mes_dia = fecha_registro.strftime("%m%d")
    
    # Obtener contador
    patron_busqueda = f"{prefijo}-{mes_dia}-%"
    ultimo_codigo = db.query(
        func.max(Clinica.codigo_interno)
    ).filter(
        Clinica.codigo_interno.like(patron_busqueda)
    ).scalar()
    
    if ultimo_codigo:
        partes = ultimo_codigo.split('-')
        if len(partes) == 3:
            nuevo_numero = int(partes[2]) + 1
        else:
            nuevo_numero = 1
    else:
        nuevo_numero = 1
    
    numero_formateado = str(nuevo_numero).zfill(5)
    
    return f"{prefijo}-{mes_dia}-{numero_formateado}"
