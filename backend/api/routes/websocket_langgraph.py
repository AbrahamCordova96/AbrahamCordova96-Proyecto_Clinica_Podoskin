# =============================================================================
# backend/api/routes/websocket_langgraph.py
# WebSocket endpoint for LangGraph streaming
# =============================================================================
# This module provides a WebSocket endpoint for bidirectional communication
# between the frontend and LangGraph streaming updates.
#
# Features:
#   - Real-time streaming of LangGraph job updates
#   - Job lifecycle management (start, update, cancel)
#   - Reconnection support with job_id
#   - Authentication via JWT
#
# WebSocket Protocol:
#   Client -> Server:
#     - start_job: { session_id, user_id, utterance, job_metadata }
#     - cancel: { job_id }
#     - followup: { job_id, utterance }
#   
#   Server -> Client:
#     - update: { type: "update", content, chunk_meta, job_id }
#     - final: { type: "final", content, job_id }
#     - error: { type: "error", message, job_id }
# =============================================================================

from typing import Optional, Dict, Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, status, Query
from sqlalchemy.orm import Session
import json
import logging
import asyncio
from datetime import datetime
import uuid

from backend.api.deps.database import get_auth_db
from backend.api.deps.auth import get_current_active_user
from backend.schemas.auth.models import SysUsuario

logger = logging.getLogger(__name__)


# =============================================================================
# ROUTER
# =============================================================================
router = APIRouter(tags=["WebSocket"])


# =============================================================================
# CONNECTION MANAGER
# =============================================================================

class ConnectionManager:
    """
    Manages WebSocket connections and job subscriptions.
    
    Supports:
    - Multiple connections per user
    - Job-based message routing
    - Reconnection to existing jobs
    """
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.job_subscriptions: Dict[str, str] = {}  # job_id -> connection_id
        
    async def connect(self, connection_id: str, websocket: WebSocket):
        """Accept and register a new WebSocket connection"""
        await websocket.accept()
        self.active_connections[connection_id] = websocket
        logger.info(f"WebSocket connected: {connection_id}")
        
    def disconnect(self, connection_id: str):
        """Unregister a WebSocket connection"""
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
            logger.info(f"WebSocket disconnected: {connection_id}")
            
        # Clean up job subscriptions for this connection
        jobs_to_remove = [
            job_id for job_id, conn_id in self.job_subscriptions.items()
            if conn_id == connection_id
        ]
        for job_id in jobs_to_remove:
            del self.job_subscriptions[job_id]
    
    async def send_message(self, connection_id: str, message: dict):
        """Send a message to a specific connection"""
        if connection_id in self.active_connections:
            websocket = self.active_connections[connection_id]
            await websocket.send_json(message)
    
    async def send_to_job(self, job_id: str, message: dict):
        """Send a message to the connection subscribed to a job"""
        if job_id in self.job_subscriptions:
            connection_id = self.job_subscriptions[job_id]
            await self.send_message(connection_id, message)
    
    def subscribe_to_job(self, job_id: str, connection_id: str):
        """Subscribe a connection to a job for updates"""
        self.job_subscriptions[job_id] = connection_id
        logger.info(f"Connection {connection_id} subscribed to job {job_id}")
    
    def unsubscribe_from_job(self, job_id: str):
        """Unsubscribe from a job"""
        if job_id in self.job_subscriptions:
            del self.job_subscriptions[job_id]


# Global connection manager
manager = ConnectionManager()


# =============================================================================
# WEBSOCKET ENDPOINT
# =============================================================================

@router.websocket("/ws/langgraph-stream")
async def langgraph_stream_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(None),
    db: Session = Depends(get_auth_db)
):
    """
    WebSocket endpoint for LangGraph streaming updates.
    
    **Authentication**: Pass JWT token as query parameter: ?token=<your_jwt>
    
    **Use Case (Narración de uso)**:
    When user asks "Muéstrame la agenda de mañana", the frontend opens WS
    with LangGraph, shows immediate "Permítame un momento..." bridge text,
    and receives partial updates (e.g., "Consultando disponibilidad...").
    These updates are shown in the "Agenda" tab and read aloud by Gemini
    while the final list is being prepared.
    
    **Protocol**:
    
    Client sends:
    ```json
    {
        "action": "start_job",
        "session_id": "session-123",
        "user_id": 1,
        "utterance": "Muéstrame la agenda de mañana",
        "job_metadata": {}
    }
    ```
    
    Server responds with job_id:
    ```json
    {
        "type": "job_started",
        "job_id": "job-uuid-123",
        "message": "Job iniciado"
    }
    ```
    
    Server streams updates:
    ```json
    {
        "type": "update",
        "job_id": "job-uuid-123",
        "content": "Consultando disponibilidad...",
        "chunk_meta": {"step": 1, "node_id": "fetch_appointments", "partial": true}
    }
    ```
    
    Server sends final result:
    ```json
    {
        "type": "final",
        "job_id": "job-uuid-123",
        "content": "Encontré 3 citas para mañana",
        "data": {...}
    }
    ```
    
    Client can cancel:
    ```json
    {
        "action": "cancel",
        "job_id": "job-uuid-123"
    }
    ```
    
    Client can follow up:
    ```json
    {
        "action": "followup",
        "job_id": "job-uuid-123",
        "utterance": "¿Y para pasado mañana?"
    }
    ```
    """
    # Generate unique connection ID
    connection_id = str(uuid.uuid4())
    
    # TODO: Implement proper JWT authentication from query parameter
    # For now, accept connection without auth (skeleton implementation)
    
    await manager.connect(connection_id, websocket)
    
    try:
        # Send welcome message
        await websocket.send_json({
            "type": "connected",
            "connection_id": connection_id,
            "message": "WebSocket conectado. Envía 'start_job' para comenzar."
        })
        
        # Main message loop
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            
            action = data.get("action")
            
            if action == "start_job":
                # Start a new LangGraph job
                job_id = await handle_start_job(connection_id, data, websocket)
                
            elif action == "cancel":
                # Cancel an existing job
                job_id = data.get("job_id")
                await handle_cancel_job(job_id, websocket)
                
            elif action == "followup":
                # Send a follow-up to existing job
                job_id = data.get("job_id")
                utterance = data.get("utterance")
                await handle_followup(job_id, utterance, websocket)
                
            elif action == "resubscribe":
                # Resubscribe to an existing job (for reconnection)
                job_id = data.get("job_id")
                manager.subscribe_to_job(job_id, connection_id)
                await websocket.send_json({
                    "type": "resubscribed",
                    "job_id": job_id,
                    "message": f"Reconectado a job {job_id}"
                })
                
            else:
                await websocket.send_json({
                    "type": "error",
                    "message": f"Acción desconocida: {action}"
                })
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {connection_id}")
        manager.disconnect(connection_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(connection_id)


# =============================================================================
# MESSAGE HANDLERS
# =============================================================================

async def handle_start_job(
    connection_id: str,
    data: dict,
    websocket: WebSocket
) -> str:
    """
    Handle start_job action.
    
    This creates a new LangGraph job and subscribes the connection to it.
    """
    # Generate unique job ID
    job_id = str(uuid.uuid4())
    
    # Subscribe connection to job
    manager.subscribe_to_job(job_id, connection_id)
    
    # Extract job parameters
    session_id = data.get("session_id")
    user_id = data.get("user_id")
    utterance = data.get("utterance")
    job_metadata = data.get("job_metadata", {})
    
    # Send job started confirmation
    await websocket.send_json({
        "type": "job_started",
        "job_id": job_id,
        "message": "Job iniciado",
        "session_id": session_id
    })
    
    # TODO: Actually invoke LangGraph here
    # For now, simulate streaming updates
    asyncio.create_task(
        simulate_langgraph_streaming(job_id, utterance)
    )
    
    return job_id


async def handle_cancel_job(job_id: str, websocket: WebSocket):
    """
    Handle cancel action.
    
    This cancels an in-progress LangGraph job.
    """
    # TODO: Actually cancel the LangGraph job
    
    await websocket.send_json({
        "type": "cancelled",
        "job_id": job_id,
        "message": f"Job {job_id} cancelado"
    })
    
    manager.unsubscribe_from_job(job_id)


async def handle_followup(job_id: str, utterance: str, websocket: WebSocket):
    """
    Handle followup action.
    
    This sends a follow-up utterance to an existing job context.
    """
    # TODO: Send followup to LangGraph
    
    await websocket.send_json({
        "type": "followup_received",
        "job_id": job_id,
        "message": "Procesando seguimiento..."
    })


# =============================================================================
# SIMULATION (Placeholder for actual LangGraph integration)
# =============================================================================

async def simulate_langgraph_streaming(job_id: str, utterance: str):
    """
    Simulate LangGraph streaming updates.
    
    This is a placeholder. In production, this should:
    1. Invoke actual LangGraph agent
    2. Stream updates from LangGraph subgraphs
    3. Handle errors and retries
    """
    try:
        # Simulate initial processing
        await asyncio.sleep(0.5)
        await manager.send_to_job(job_id, {
            "type": "update",
            "job_id": job_id,
            "content": "Procesando solicitud...",
            "chunk_meta": {"step": 1, "node_id": "parse_intent", "partial": True}
        })
        
        # Simulate data fetching
        await asyncio.sleep(1)
        await manager.send_to_job(job_id, {
            "type": "update",
            "job_id": job_id,
            "content": "Consultando base de datos...",
            "chunk_meta": {"step": 2, "node_id": "fetch_data", "partial": True}
        })
        
        # Simulate final response
        await asyncio.sleep(1)
        await manager.send_to_job(job_id, {
            "type": "final",
            "job_id": job_id,
            "content": f"Respuesta completa para: {utterance}",
            "data": {
                "result": "Ejemplo de resultado",
                "source_refs": [
                    {"table": "pacientes", "id": 123, "confidence": 1.0}
                ]
            },
            "chunk_meta": {"step": 3, "node_id": "format_response", "partial": False}
        })
        
    except Exception as e:
        logger.error(f"Error in LangGraph simulation: {e}")
        await manager.send_to_job(job_id, {
            "type": "error",
            "job_id": job_id,
            "message": str(e)
        })
