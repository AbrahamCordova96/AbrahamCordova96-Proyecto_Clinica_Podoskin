# =============================================================================
# backend/api/routes/pacientes.py
# CRUD de Pacientes con control de acceso por rol
# =============================================================================
# Este archivo implementa los endpoints de pacientes:
#   - GET /pacientes → Listar pacientes
#   - GET /pacientes/buscar → Búsqueda fuzzy
#   - GET /pacientes/{id} → Detalle de paciente
#   - POST /pacientes → Crear paciente
#   - PUT /pacientes/{id} → Editar paciente
#   - DELETE /pacientes/{id} → Soft delete
#   - DELETE /pacientes/{id}/purge → Hard delete (solo Admin)
#
# PERMISOS:
#   - Admin: Todo
#   - Podologo: Todo excepto purge
#   - Recepcion: Solo campos básicos (sin historial médico)
# =============================================================================

from typing import List, Optional
from datetime import date, datetime
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from pydantic import BaseModel, Field, EmailStr

from backend.api.deps.database import get_core_db, get_ops_db
from backend.api.deps.permissions import (
    require_role, 
    ALL_ROLES, 
    CLINICAL_ROLES,
    ROLE_ADMIN,
    is_recepcion,
    filter_paciente_for_recepcion
)
from backend.schemas.auth.models import SysUsuario
from backend.schemas.core.models import Paciente, HistorialMedicoGeneral, HistorialGineco, Tratamiento, EvolucionClinica
from backend.api.utils.pdf_export import generate_patient_pdf

# Logger para operaciones importantes
logger = logging.getLogger(__name__)


# =============================================================================
# ROUTER
# =============================================================================
router = APIRouter(prefix="/pacientes", tags=["Pacientes"])


# =============================================================================
# SCHEMAS
# =============================================================================

class PacienteBase(BaseModel):
    """Campos base de paciente"""
    nombres: str = Field(..., min_length=2, max_length=100)
    apellidos: str = Field(..., min_length=2, max_length=100)
    fecha_nacimiento: date
    sexo: Optional[str] = Field(None, pattern="^[MF]$")
    estado_civil: Optional[str] = None
    ocupacion: Optional[str] = None
    escolaridad: Optional[str] = None
    religion: Optional[str] = None
    domicilio: Optional[str] = None
    como_supo_de_nosotros: Optional[str] = None
    telefono: str = Field(..., min_length=10)
    email: Optional[EmailStr] = None


class PacienteCreate(PacienteBase):
    """Request para crear paciente"""
    pass


class PacienteUpdate(BaseModel):
    """Request para actualizar paciente (todos opcionales)"""
    nombres: Optional[str] = Field(None, min_length=2, max_length=100)
    apellidos: Optional[str] = Field(None, min_length=2, max_length=100)
    fecha_nacimiento: Optional[date] = None
    sexo: Optional[str] = Field(None, pattern="^[MF]$")
    estado_civil: Optional[str] = None
    ocupacion: Optional[str] = None
    escolaridad: Optional[str] = None
    religion: Optional[str] = None
    domicilio: Optional[str] = None
    como_supo_de_nosotros: Optional[str] = None
    telefono: Optional[str] = Field(None, min_length=10)
    email: Optional[EmailStr] = None


class PacienteResponse(PacienteBase):
    """Response de paciente (todos los campos)"""
    id_paciente: int
    id_clinica: int
    codigo_interno: Optional[str] = None  # ID estructurado
    fecha_registro: Optional[datetime] = None
    created_by: Optional[int] = None
    
    class Config:
        from_attributes = True


class PacienteBasicResponse(BaseModel):
    """Response limitado para Recepción"""
    id_paciente: int
    nombres: str
    apellidos: str
    fecha_nacimiento: date
    sexo: Optional[str] = None
    telefono: str
    email: Optional[str] = None
    domicilio: Optional[str] = None
    
    class Config:
        from_attributes = True


class PacienteListResponse(BaseModel):
    """Response de lista paginada"""
    total: int
    pacientes: List[PacienteResponse]


# =============================================================================
# ENDPOINT: GET /pacientes
# =============================================================================

@router.get("", response_model=PacienteListResponse)
async def list_pacientes(
    skip: int = Query(0, ge=0, description="Registros a saltar"),
    limit: int = Query(50, ge=1, le=100, description="Máximo de registros"),
    current_user: SysUsuario = Depends(require_role(ALL_ROLES)),
    db: Session = Depends(get_core_db)
):
    """
    Lista todos los pacientes activos.
    
    **Permisos:**
    - Admin, Podologo: Todos los campos
    - Recepcion: Solo campos básicos
    
    **Parámetros:**
    - skip: Cuántos registros saltar (paginación)
    - limit: Máximo de registros a retornar (1-100)
    """
    # Query base: solo pacientes no eliminados
    query = db.query(Paciente).filter(Paciente.deleted_at.is_(None))
    
    # Filtrar por clínica del usuario
    if current_user.clinica_id:
        query = query.filter(Paciente.id_clinica == current_user.clinica_id)
    
    # Contar total
    total = query.count()
    
    # Paginar
    pacientes = query.offset(skip).limit(limit).all()
    
    # Si es Recepción, filtrar campos
    if is_recepcion(current_user):
        pacientes_response = [
            PacienteBasicResponse.model_validate(p) for p in pacientes
        ]
    else:
        pacientes_response = [
            PacienteResponse.model_validate(p) for p in pacientes
        ]
    
    return {"total": total, "pacientes": pacientes_response}


# =============================================================================
# ENDPOINT: GET /pacientes/buscar
# =============================================================================

@router.get("/buscar")
async def search_pacientes(
    q: str = Query(..., min_length=2, description="Término de búsqueda"),
    limit: int = Query(20, ge=1, le=50),
    current_user: SysUsuario = Depends(require_role(ALL_ROLES)),
    db: Session = Depends(get_core_db)
):
    """
    Búsqueda de pacientes por nombre, apellido o teléfono.
    
    **Permisos:** Todos los roles
    
    **Parámetros:**
    - q: Término a buscar (mínimo 2 caracteres)
    - limit: Máximo de resultados
    
    **Nota:** Búsqueda case-insensitive
    """
    search_term = f"%{q.lower()}%"
    
    query = db.query(Paciente).filter(
        Paciente.deleted_at.is_(None),
        or_(
            func.lower(Paciente.nombres).like(search_term),
            func.lower(Paciente.apellidos).like(search_term),
            Paciente.telefono.like(search_term)
        )
    )
    
    # Filtrar por clínica
    if current_user.clinica_id:
        query = query.filter(Paciente.id_clinica == current_user.clinica_id)
    
    pacientes = query.limit(limit).all()
    
    # Filtrar campos para Recepción
    if is_recepcion(current_user):
        return [PacienteBasicResponse.model_validate(p) for p in pacientes]
    
    return [PacienteResponse.model_validate(p) for p in pacientes]


# =============================================================================
# ENDPOINT: GET /pacientes/{id}
# =============================================================================

@router.get("/{paciente_id}")
async def get_paciente(
    paciente_id: int,
    current_user: SysUsuario = Depends(require_role(ALL_ROLES)),
    db: Session = Depends(get_core_db)
):
    """
    Obtiene detalle de un paciente.
    
    **Permisos:**
    - Admin, Podologo: Todos los campos + historial médico
    - Recepcion: Solo campos básicos
    """
    paciente = db.query(Paciente).filter(
        Paciente.id_paciente == paciente_id,
        Paciente.deleted_at.is_(None)
    ).first()
    
    if not paciente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paciente no encontrado"
        )
    
    # Verificar que pertenece a la clínica del usuario
    if current_user.clinica_id and paciente.id_clinica != current_user.clinica_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes acceso a este paciente"
        )
    
    # Recepción solo ve campos básicos
    if is_recepcion(current_user):
        return PacienteBasicResponse.model_validate(paciente)
    
    # Admin/Podologo ven todo incluyendo historial
    response = PacienteResponse.model_validate(paciente)
    
    # Agregar historial médico si existe
    historial = db.query(HistorialMedicoGeneral).filter(
        HistorialMedicoGeneral.paciente_id == paciente_id
    ).first()
    
    historial_gineco = db.query(HistorialGineco).filter(
        HistorialGineco.paciente_id == paciente_id
    ).first()
    
    result = response.model_dump()
    result["historial_medico"] = historial.__dict__ if historial else None
    result["historial_gineco"] = historial_gineco.__dict__ if historial_gineco else None
    
    return result


# =============================================================================
# ENDPOINT: POST /pacientes
# =============================================================================

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_paciente(
    data: PacienteCreate,
    current_user: SysUsuario = Depends(require_role(ALL_ROLES)),
    db: Session = Depends(get_core_db)
):
    """
    Crea un nuevo paciente.
    
    **Permisos:** Todos los roles
    
    **Campos requeridos:**
    - nombres, apellidos, fecha_nacimiento, telefono
    
    **Sistema de IDs estructurados:**
    - Se genera automáticamente un codigo_interno único
    - Formato: [2 letras apellido][2 letras nombre]-[MMDD]-[contador]
    - Ejemplo: "RENO-1213-00001" para "Ornelas Reynoso, Santiago"
    """
    from backend.utils.id_generator import generar_codigo_interno
    from datetime import datetime
    
    # Crear paciente
    paciente = Paciente(
        **data.model_dump(),
        id_clinica=current_user.clinica_id or 1,
        created_by=current_user.id_usuario
    )
    
    # Agregar a la sesión para obtener el ID antes de generar el código
    db.add(paciente)
    db.flush()  # Obtiene el ID sin hacer commit
    
    # Generar código interno estructurado
    try:
        codigo = generar_codigo_interno(
            apellido_paterno=paciente.apellidos,
            nombre=paciente.nombres,
            fecha_registro=datetime.now(),
            model_class=Paciente,
            db=db
        )
        paciente.codigo_interno = codigo
    except Exception as e:
        # Si falla la generación del código, continuar sin él (no es crítico)
        logger.warning(f"No se pudo generar codigo_interno para paciente: {e}")
    
    db.commit()
    db.refresh(paciente)
    
    return PacienteResponse.model_validate(paciente)


# =============================================================================
# ENDPOINT: PUT /pacientes/{id}
# =============================================================================

@router.put("/{paciente_id}")
async def update_paciente(
    paciente_id: int,
    data: PacienteUpdate,
    current_user: SysUsuario = Depends(require_role(ALL_ROLES)),
    db: Session = Depends(get_core_db)
):
    """
    Actualiza un paciente existente.
    
    **Permisos:**
    - Admin, Podologo: Todos los campos
    - Recepcion: Solo campos básicos
    """
    paciente = db.query(Paciente).filter(
        Paciente.id_paciente == paciente_id,
        Paciente.deleted_at.is_(None)
    ).first()
    
    if not paciente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paciente no encontrado"
        )
    
    # Verificar clínica
    if current_user.clinica_id and paciente.id_clinica != current_user.clinica_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes acceso a este paciente"
        )
    
    # Actualizar solo campos proporcionados
    update_data = data.model_dump(exclude_unset=True)
    
    # Si es Recepción, limitar campos que puede editar
    if is_recepcion(current_user):
        allowed_fields = [
            "nombres", "apellidos", "fecha_nacimiento", "sexo",
            "telefono", "email", "domicilio", "estado_civil",
            "ocupacion", "como_supo_de_nosotros"
        ]
        update_data = {k: v for k, v in update_data.items() if k in allowed_fields}
    
    for field, value in update_data.items():
        setattr(paciente, field, value)
    
    paciente.updated_by = current_user.id_usuario
    db.commit()
    db.refresh(paciente)
    
    return PacienteResponse.model_validate(paciente)


# =============================================================================
# ENDPOINT: DELETE /pacientes/{id} (Soft Delete)
# =============================================================================

@router.delete("/{paciente_id}")
async def soft_delete_paciente(
    paciente_id: int,
    current_user: SysUsuario = Depends(require_role(CLINICAL_ROLES)),  # Solo Admin/Podologo
    db: Session = Depends(get_core_db)
):
    """
    Desactiva un paciente (soft delete).
    
    El paciente no se elimina, solo se marca como eliminado.
    Se puede recuperar después.
    
    **Permisos:** Solo Admin y Podologo
    """
    from datetime import datetime, timezone
    
    paciente = db.query(Paciente).filter(
        Paciente.id_paciente == paciente_id,
        Paciente.deleted_at.is_(None)
    ).first()
    
    if not paciente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paciente no encontrado"
        )
    
    # Verificar clínica
    if current_user.clinica_id and paciente.id_clinica != current_user.clinica_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes acceso a este paciente"
        )
    
    # Soft delete
    paciente.deleted_at = datetime.now(timezone.utc)
    paciente.updated_by = current_user.id_usuario
    db.commit()
    
    return {"message": "Paciente desactivado", "id": paciente_id}


# =============================================================================
# ENDPOINT: DELETE /pacientes/{id}/purge (Hard Delete - Solo Admin)
# =============================================================================

@router.delete("/{paciente_id}/purge")
async def purge_paciente(
    paciente_id: int,
    confirm: bool = Query(False, description="Confirmar eliminación permanente"),
    current_user: SysUsuario = Depends(require_role([ROLE_ADMIN])),  # SOLO ADMIN
    db: Session = Depends(get_core_db)
):
    """
    Elimina un paciente PERMANENTEMENTE.
    
    ⚠️ **ADVERTENCIA:** Esta acción NO se puede deshacer.
    Todos los datos del paciente (historial, tratamientos, etc.) se eliminarán.
    
    **Permisos:** Solo Admin
    
    **Parámetros:**
    - confirm: Debe ser `true` para confirmar la eliminación
    """
    if not confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debe confirmar la eliminación permanente con ?confirm=true"
        )
    
    paciente = db.query(Paciente).filter(
        Paciente.id_paciente == paciente_id
    ).first()
    
    if not paciente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paciente no encontrado"
        )
    
    # Verificar clínica
    if current_user.clinica_id and paciente.id_clinica != current_user.clinica_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes acceso a este paciente"
        )
    
    # Hard delete (CASCADE eliminará historiales relacionados)
    db.delete(paciente)
    db.commit()
    
    return {
        "message": "Paciente eliminado permanentemente",
        "id": paciente_id,
        "warning": "Esta acción no se puede deshacer"
    }


# =============================================================================
# ENDPOINT: GET /pacientes/{id}/export-pdf
# =============================================================================

@router.get("/{paciente_id}/export-pdf")
async def export_patient_pdf(
    paciente_id: int,
    include_treatments: bool = Query(True, description="Incluir tratamientos"),
    include_notes: bool = Query(True, description="Incluir notas clínicas"),
    current_user: SysUsuario = Depends(require_role(CLINICAL_ROLES)),
    db: Session = Depends(get_core_db)
):
    """
    Exporta el expediente completo del paciente a PDF.
    
    **Permisos:** Solo Admin y Podologo
    
    **Parámetros:**
    - include_treatments: Incluir tratamientos en el PDF
    - include_notes: Incluir notas clínicas (evoluciones)
    
    **Retorna:** Archivo PDF descargable
    
    El PDF incluye:
    - Datos demográficos del paciente
    - Tratamientos (opcional)
    - Notas clínicas SOAP (opcional)
    
    **Ejemplo:**
    ```
    GET /api/v1/pacientes/1/export-pdf?include_treatments=true&include_notes=true
    ```
    """
    # Buscar paciente
    paciente = db.query(Paciente).filter(
        Paciente.id_paciente == paciente_id,
        Paciente.deleted_at.is_(None)
    ).first()
    
    if not paciente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paciente no encontrado"
        )
    
    # Verificar clínica
    if current_user.clinica_id and paciente.id_clinica != current_user.clinica_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes acceso a este paciente"
        )
    
    # Obtener tratamientos si se solicita
    tratamientos = None
    if include_treatments:
        tratamientos = db.query(Tratamiento).filter(
            Tratamiento.paciente_id == paciente_id
        ).order_by(Tratamiento.fecha_inicio.desc()).all()
    
    # Obtener evoluciones si se solicita
    evoluciones = None
    if include_notes and tratamientos:
        # Get all evolutions from all treatments
        tratamiento_ids = [t.id_tratamiento for t in tratamientos]
        evoluciones = db.query(EvolucionClinica).filter(
            EvolucionClinica.tratamiento_id.in_(tratamiento_ids)
        ).order_by(EvolucionClinica.fecha_sesion.desc()).all()
    
    # Generate PDF
    try:
        pdf_buffer = generate_patient_pdf(
            paciente=paciente,
            tratamientos=tratamientos,
            evoluciones=evoluciones,
            include_photos=False  # Photos not implemented yet
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generando PDF: {str(e)}"
        )
    
    # Return as streaming response
    filename = f"expediente_paciente_{paciente_id}_{datetime.now().strftime('%Y%m%d')}.pdf"
    
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )


# =============================================================================
# =============================================================================
# ENDPOINT: GET /pacientes/{id}/expediente/print
# =============================================================================

@router.get("/{paciente_id}/expediente/print", dependencies=[Depends(require_role(CLINICAL_ROLES))])
async def print_expediente(
    paciente_id: int,
    core_db: Session = Depends(get_core_db),
    ops_db: Session = Depends(get_ops_db)
):
    """
    Genera un expediente clínico en formato HTML listo para imprimir.
    
    **NOM-024 Compliance**: Endpoint específico para impresión de expedientes.
    
    **Permisos**: Admin y Podólogo (contiene información clínica sensible)
    
    **Formato**: HTML optimizado para impresión con CSS profesional
    
    **Incluye**:
    - Datos personales completos del paciente
    - Historial médico general
    - Todos los tratamientos registrados
    - Todas las evoluciones clínicas (notas SOAP)
    - Signos vitales
    - Formato listo para imprimir o convertir a PDF
    
    **Uso recomendado**:
    - Entregar copia física al paciente
    - Imprimir para archivo físico
    - Convertir a PDF con navegador (Ctrl+P → Guardar como PDF)
    """
    from backend.api.utils.expediente_export import exportar_expediente_html
    from fastapi.responses import HTMLResponse
    
    # Verificar que el paciente existe
    paciente = core_db.query(Paciente).filter_by(id_paciente=paciente_id).first()
    if not paciente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Paciente con ID {paciente_id} no encontrado"
        )
    
    try:
        # Generar HTML del expediente completo
        html_content = exportar_expediente_html(core_db, ops_db, paciente_id)
        
        return HTMLResponse(
            content=html_content,
            headers={
                "Content-Disposition": f"inline; filename=expediente_{paciente_id}.html"
            }
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generando expediente para impresión: {str(e)}"
        )


# NOM-024 COMPLIANCE: EXPORTAR EXPEDIENTE COMPLETO
# =============================================================================
# Endpoint para exportar el expediente completo de un paciente en múltiples formatos
# Requerido por NOM-024 para interoperabilidad y entrega de copias al paciente
# =============================================================================

@router.get("/{paciente_id}/exportar", dependencies=[Depends(require_role(CLINICAL_ROLES))])
async def exportar_expediente_completo(
    paciente_id: int,
    formato: str = Query("html", regex="^(html|json|xml)$", description="Formato de exportación: html, json, xml"),
    core_db: Session = Depends(get_core_db),
    ops_db: Session = Depends(get_ops_db)
):
    """
    Exporta el expediente clínico completo de un paciente.
    
    **NOM-024 Compliance**: Este endpoint cumple con los requisitos de:
    - Exportación de expedientes completos
    - Formatos estándar (HTML para lectura, JSON/XML para intercambio)
    - Preparación para interoperabilidad futura
    
    **Formatos disponibles**:
    - `html`: Documento elegante listo para imprimir (recomendado para pacientes)
    - `json`: Estructura preparada para HL7 CDA (para sistemas)
    - `xml`: Formato XML básico (preparación para estándares)
    
    **Permisos**: Admin y Podólogo (no Recepción, por contener datos clínicos)
    
    **Incluye**:
    - Datos personales del paciente
    - Historial médico completo
    - Todos los tratamientos registrados
    - Todas las evoluciones clínicas (notas SOAP)
    - Signos vitales históricos
    """
    from backend.api.utils.expediente_export import (
        exportar_expediente_html,
        exportar_expediente_json,
        exportar_expediente_xml
    )
    from fastapi.responses import HTMLResponse, JSONResponse, Response
    
    # Verificar que el paciente existe
    paciente = core_db.query(Paciente).filter_by(id_paciente=paciente_id).first()
    if not paciente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Paciente con ID {paciente_id} no encontrado"
        )
    
    try:
        if formato == "html":
            # Exportar como HTML elegante
            html_content = exportar_expediente_html(core_db, ops_db, paciente_id)
            
            return HTMLResponse(
                content=html_content,
                headers={
                    "Content-Disposition": f"inline; filename=expediente_{paciente_id}.html"
                }
            )
        
        elif formato == "json":
            # Exportar como JSON estructurado (HL7-like)
            json_data = exportar_expediente_json(core_db, ops_db, paciente_id)
            
            return JSONResponse(
                content=json_data,
                headers={
                    "Content-Disposition": f"attachment; filename=expediente_{paciente_id}.json"
                }
            )
        
        elif formato == "xml":
            # Exportar como XML (preparación para HL7 CDA)
            xml_content = exportar_expediente_xml(core_db, ops_db, paciente_id)
            
            return Response(
                content=xml_content,
                media_type="application/xml",
                headers={
                    "Content-Disposition": f"attachment; filename=expediente_{paciente_id}.xml"
                }
            )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error exportando expediente: {str(e)}"
        )
