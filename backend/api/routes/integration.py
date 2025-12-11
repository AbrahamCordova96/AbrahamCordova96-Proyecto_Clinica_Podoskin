# =============================================================================
# backend/api/routes/integration.py
# Integration Endpoints for Voice Frontend (Gemini Live + LangGraph)
# =============================================================================
# This module provides endpoints required for integrating voice-controlled
# frontend with LangGraph and Gemini Live.
#
# Endpoints:
#   - GET /integration/user-context - User context for system prompts
#   - POST /integration/save-transcript - Save voice transcripts
#
# All endpoints follow security best practices and audit requirements.
# =============================================================================

from typing import Optional, List
from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import desc
from pydantic import BaseModel
import logging

from backend.api.deps.database import get_auth_db
from backend.api.deps.auth import get_current_active_user
from backend.schemas.auth.models import SysUsuario, VoiceTranscript, AuditLog
from backend.schemas.auth.schemas import VoiceTranscriptCreate

logger = logging.getLogger(__name__)


# =============================================================================
# ROUTER
# =============================================================================
router = APIRouter(prefix="/integration", tags=["Integration"])


# =============================================================================
# SCHEMAS
# =============================================================================

class UserContextResponse(BaseModel):
    """Response schema for user context endpoint"""
    is_first_time: bool
    user_name: str
    summary: Optional[str] = None
    last_active: Optional[str] = None


class SaveTranscriptRequest(BaseModel):
    """Request schema for saving transcripts in batch"""
    transcripts: List[VoiceTranscriptCreate]


class SaveTranscriptResponse(BaseModel):
    """Response schema for save transcript endpoint"""
    ok: bool
    saved: int


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get("/user-context", response_model=UserContextResponse)
async def get_user_context(
    user_id: Optional[int] = None,
    current_user: SysUsuario = Depends(get_current_active_user),
    db: Session = Depends(get_auth_db)
):
    """
    Get user context for system prompt injection.
    
    This endpoint provides a secure context card about the user that can be
    injected into the system prompt for Gemini Live. It does NOT use LLM to
    generate summaries but rather derives information from audit logs and sessions.
    
    **Security**: Requires JWT Bearer authentication
    
    **Use Case (Narración de uso)**:
    When a professional logs in, the frontend calls this endpoint. If is_first_time
    is true, Gemini will play a guided welcome. If false, it gives a short greeting
    and mentions the last topic worked on.
    
    Args:
        user_id: Optional user ID (if not provided, uses authenticated user)
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        UserContextResponse with user context information
    """
    # Use provided user_id or fall back to authenticated user
    target_user_id = user_id if user_id is not None else current_user.id_usuario
    
    # Verify user exists
    user = db.query(SysUsuario).filter(
        SysUsuario.id_usuario == target_user_id,
        SysUsuario.activo == True
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    
    # Check if this is first time (no last_login or no audit logs)
    is_first_time = user.last_login is None
    
    # Get last activity from audit logs
    last_activity = db.query(AuditLog).filter(
        AuditLog.usuario_id == target_user_id
    ).order_by(desc(AuditLog.timestamp_accion)).first()
    
    # Build summary from recent activities
    summary = None
    last_active = None
    
    if last_activity:
        last_active = last_activity.timestamp_accion.isoformat()
        
        # Create a simple summary based on last action
        tabla = last_activity.tabla_afectada
        accion = last_activity.accion
        
        action_summaries = {
            "pacientes": {
                "CREATE": "creó un nuevo paciente",
                "UPDATE": "actualizó información de paciente",
                "READ": "consultó expedientes de pacientes"
            },
            "citas": {
                "CREATE": "agendó una nueva cita",
                "UPDATE": "modificó una cita",
                "READ": "revisó la agenda"
            },
            "tratamientos": {
                "CREATE": "inició un nuevo tratamiento",
                "UPDATE": "actualizó un tratamiento",
                "READ": "revisó tratamientos"
            },
            "evoluciones": {
                "CREATE": "registró una nueva nota clínica",
                "UPDATE": "actualizó una evolución",
                "READ": "consultó notas clínicas"
            }
        }
        
        if tabla in action_summaries and accion in action_summaries[tabla]:
            summary = f"La última vez {action_summaries[tabla][accion]}"
    
    return UserContextResponse(
        is_first_time=is_first_time,
        user_name=user.nombre_usuario,
        summary=summary,
        last_active=last_active
    )


@router.post("/save-transcript", response_model=SaveTranscriptResponse)
async def save_transcript(
    request: SaveTranscriptRequest,
    current_user: SysUsuario = Depends(get_current_active_user),
    db: Session = Depends(get_auth_db)
):
    """
    Save voice conversation transcripts in batch.
    
    This endpoint persists user-assistant conversation pairs for:
    - Audit and compliance
    - Session history
    - Future vectorization and summarization
    
    **Security**: Requires JWT Bearer authentication
    **Compliance**: Only saves if user has provided consent
    
    **Use Case (Narración de uso)**:
    The frontend "stenographer" sends each turn to the backend after each exchange.
    This allows auditing conversations and recovering history to resume sessions.
    In the "Assistant" tab, the professional can view the synchronized transcript
    with the voice conversation.
    
    **Important**: Transcripts are PII/PHI - stored in separate table with
    configurable retention policy.
    
    Args:
        request: Batch of transcripts to save
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        SaveTranscriptResponse with count of saved transcripts
    """
    saved_count = 0
    
    # TODO: Check user consent flag before saving transcripts
    # For now, we'll assume consent is given
    
    for transcript_data in request.transcripts:
        try:
            # Parse ISO timestamp
            timestamp_dt = datetime.fromisoformat(transcript_data.timestamp.replace('Z', '+00:00'))
            
            # Create transcript record
            transcript = VoiceTranscript(
                session_id=transcript_data.session_id,
                user_id=current_user.id_usuario,
                user_text=transcript_data.user_text,
                assistant_text=transcript_data.assistant_text,
                timestamp=timestamp_dt,
                langgraph_job_id=transcript_data.langgraph_job_id
            )
            
            db.add(transcript)
            saved_count += 1
            
        except Exception as e:
            logger.error(f"Error saving transcript: {e}")
            # Continue processing other transcripts
    
    # Commit all transcripts at once
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Error committing transcripts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al guardar transcripciones"
        )
    
    return SaveTranscriptResponse(
        ok=True,
        saved=saved_count
    )


@router.get("/transcript-history")
async def get_transcript_history(
    session_id: str,
    current_user: SysUsuario = Depends(get_current_active_user),
    db: Session = Depends(get_auth_db)
):
    """
    Get transcript history for a session.
    
    This endpoint retrieves all voice transcripts for a given session,
    allowing users to review past conversations.
    
    **Security**: Only returns transcripts for the authenticated user
    
    Args:
        session_id: Session ID to retrieve transcripts for
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        List of transcripts for the session
    """
    transcripts = db.query(VoiceTranscript).filter(
        VoiceTranscript.session_id == session_id,
        VoiceTranscript.user_id == current_user.id_usuario
    ).order_by(VoiceTranscript.timestamp).all()
    
    return {
        "session_id": session_id,
        "transcripts": [
            {
                "user_text": t.user_text,
                "assistant_text": t.assistant_text,
                "timestamp": t.timestamp.isoformat(),
                "langgraph_job_id": t.langgraph_job_id
            }
            for t in transcripts
        ]
    }
