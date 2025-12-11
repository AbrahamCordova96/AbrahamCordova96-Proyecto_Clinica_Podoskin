# =============================================================================
# backend/api/middleware/audit_middleware.py
# Audit Middleware for automatic logging of sensitive operations
# =============================================================================
# This middleware automatically logs requests to sensitive endpoints
# for audit, compliance, and traceability purposes.
#
# Features:
#   - Automatic logging of clinical data access
#   - PII/PHI masking in request bodies
#   - Response hashing for non-repudiation
#   - Configurable sensitive endpoints
# =============================================================================

from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.orm import Session
import json
import logging

from backend.api.utils.security_utils import (
    mask_request_body,
    compute_response_hash,
    create_source_refs
)
from backend.schemas.auth.models import AuditLog
from backend.api.deps.database import get_auth_db

logger = logging.getLogger(__name__)


class AuditMiddleware(BaseHTTPMiddleware):
    """
    Middleware that automatically logs sensitive operations to audit trail.
    
    Configuration:
    - SENSITIVE_PATHS: Paths that should be audited
    - SENSITIVE_METHODS: HTTP methods to audit (default: POST, PUT, DELETE, PATCH)
    """
    
    # Paths that should always be audited
    SENSITIVE_PATHS = [
        "/api/v1/pacientes",
        "/api/v1/tratamientos",
        "/api/v1/evoluciones",
        "/api/v1/citas",
        "/api/v1/usuarios",
        "/api/v1/finance",
    ]
    
    # Methods that represent data modification
    SENSITIVE_METHODS = ["POST", "PUT", "DELETE", "PATCH"]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process the request and log if it's sensitive.
        """
        # Check if this endpoint should be audited
        should_audit = self._should_audit(request)
        
        # Store request info for audit
        request_body = None
        if should_audit and request.method in self.SENSITIVE_METHODS:
            try:
                # Read request body (we need to cache it for audit)
                body_bytes = await request.body()
                if body_bytes:
                    request_body = body_bytes.decode('utf-8')
                    
                # We need to make body readable again for the endpoint
                # This is a workaround since body can only be read once
                async def receive():
                    return {"type": "http.request", "body": body_bytes}
                request._receive = receive
            except Exception as e:
                logger.error(f"Error reading request body for audit: {e}")
        
        # Process the request
        response = await call_next(request)
        
        # Log the audit entry after successful response (don't block on failure)
        if should_audit and response.status_code < 400:
            try:
                self._create_audit_log(request, response, request_body)
            except Exception as e:
                # Don't interrupt the request if audit logging fails
                logger.error(f"Failed to create audit log: {e}")
        
        return response
    
    def _should_audit(self, request: Request) -> bool:
        """
        Determine if a request should be audited.
        """
        # Skip health checks and non-sensitive endpoints
        if request.url.path in ["/", "/health", "/docs", "/redoc", "/openapi.json"]:
            return False
        
        # Audit all sensitive paths
        for sensitive_path in self.SENSITIVE_PATHS:
            if request.url.path.startswith(sensitive_path):
                return True
        
        # Audit all modification operations on API
        if request.method in self.SENSITIVE_METHODS and request.url.path.startswith("/api/v1"):
            return True
        
        return False
    
    def _create_audit_log(self, request: Request, response: Response, request_body: str = None):
        """
        Create an audit log entry (runs asynchronously, doesn't block request).
        
        Note: This is a simplified version. In production, this should be
        done asynchronously using a background task or message queue.
        """
        try:
            # Get database session
            db_gen = get_auth_db()
            db = next(db_gen)
            
            # Extract user info from request state (set by auth dependency)
            user_id = getattr(request.state, "user_id", None)
            username = getattr(request.state, "username", None)
            session_id = getattr(request.state, "session_id", None)
            
            # Get client IP
            client_ip = request.client.host if request.client else None
            
            # Mask sensitive data in request body
            masked_body = mask_request_body(request_body) if request_body else None
            
            # Determine action from method and path
            action = self._determine_action(request.method, request.url.path)
            
            # Determine affected table from path
            tabla_afectada = self._extract_table_from_path(request.url.path)
            
            # Create audit log entry
            audit_log = AuditLog(
                usuario_id=user_id,
                username=username,
                session_id=session_id,
                ip_address=client_ip,
                method=request.method,
                endpoint=request.url.path,
                accion=action,
                tabla_afectada=tabla_afectada,
                request_body=masked_body,
                # response_hash and source_refs should be added by endpoints
                # when they have the actual response data
            )
            
            db.add(audit_log)
            db.commit()
            
        except Exception as e:
            logger.error(f"Error creating audit log: {e}")
        finally:
            if db:
                db.close()
    
    def _determine_action(self, method: str, path: str) -> str:
        """
        Determine the action type from HTTP method.
        """
        action_map = {
            "GET": "READ",
            "POST": "CREATE",
            "PUT": "UPDATE",
            "PATCH": "UPDATE",
            "DELETE": "DELETE"
        }
        return action_map.get(method, method)
    
    def _extract_table_from_path(self, path: str) -> str:
        """
        Extract the affected table name from the API path.
        """
        # Remove /api/v1/ prefix and extract resource name
        path = path.replace("/api/v1/", "")
        
        # Extract first path segment as table name
        if "/" in path:
            table = path.split("/")[0]
        else:
            table = path
        
        return table
