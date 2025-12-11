# =============================================================================
# backend/api/utils/security_utils.py
# Security utilities for PII/PHI masking and response hashing
# =============================================================================
# This module provides utilities for:
#   - Masking sensitive data (PII/PHI) in logs and audit trails
#   - Computing response hashes for non-repudiation
#   - Data loss prevention (DLP) functions
# =============================================================================

import re
import hashlib
import json
from typing import Any, Dict, Optional


def mask_email(email: str) -> str:
    """
    Mask email address for privacy.
    Example: john.doe@example.com -> j***e@e***e.com
    """
    if not email or '@' not in email:
        return email
    
    local, domain = email.split('@', 1)
    if len(local) <= 2:
        masked_local = local[0] + '*'
    else:
        masked_local = local[0] + '***' + local[-1]
    
    domain_parts = domain.split('.')
    if len(domain_parts[0]) <= 2:
        masked_domain = domain_parts[0][0] + '*'
    else:
        masked_domain = domain_parts[0][0] + '***' + domain_parts[0][-1]
    
    return f"{masked_local}@{masked_domain}.{'.'.join(domain_parts[1:])}"


def mask_phone(phone: str) -> str:
    """
    Mask phone number for privacy.
    Example: +52 123 456 7890 -> +52 *** *** 7890
    """
    if not phone:
        return phone
    
    # Remove non-digit characters except +
    digits = re.sub(r'[^\d+]', '', phone)
    
    if len(digits) < 4:
        return '***'
    
    # Keep country code and last 4 digits
    if digits.startswith('+'):
        return f"{digits[:3]} *** *** {digits[-4:]}"
    else:
        return f"*** *** {digits[-4:]}"


def mask_identification(id_str: str) -> str:
    """
    Mask identification numbers (SSN, ID, etc.)
    Example: 123-45-6789 -> ***-**-6789
    """
    if not id_str:
        return id_str
    
    # Keep only last 4 characters
    if len(id_str) <= 4:
        return '***'
    
    return '***' + id_str[-4:]


def mask_sensitive_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively mask sensitive fields in a dictionary.
    
    Masks the following field patterns:
    - email, correo, mail
    - phone, telefono, celular, movil
    - ssn, curp, rfc, nss
    - password, contraseña, pwd
    - credit_card, tarjeta, card_number
    """
    if not isinstance(data, dict):
        return data
    
    masked_data = {}
    sensitive_patterns = {
        'email': mask_email,
        'correo': mask_email,
        'mail': mask_email,
        'telefono': mask_phone,
        'celular': mask_phone,
        'phone': mask_phone,
        'movil': mask_phone,
        'ssn': mask_identification,
        'curp': mask_identification,
        'rfc': mask_identification,
        'nss': mask_identification,
    }
    
    for key, value in data.items():
        key_lower = key.lower()
        
        # Complete masking for passwords and card numbers
        if any(pattern in key_lower for pattern in ['password', 'contraseña', 'pwd', 'credit_card', 'tarjeta', 'card_number']):
            masked_data[key] = '***MASKED***'
        # Pattern-based masking
        elif any(pattern in key_lower for pattern in sensitive_patterns.keys()):
            for pattern, mask_func in sensitive_patterns.items():
                if pattern in key_lower and isinstance(value, str):
                    masked_data[key] = mask_func(value)
                    break
            else:
                masked_data[key] = value
        # Recursively mask nested dicts
        elif isinstance(value, dict):
            masked_data[key] = mask_sensitive_data(value)
        # Recursively mask lists
        elif isinstance(value, list):
            masked_data[key] = [
                mask_sensitive_data(item) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            masked_data[key] = value
    
    return masked_data


def compute_response_hash(data: Any) -> str:
    """
    Compute SHA-256 hash of response data for non-repudiation.
    
    This hash can be stored in audit logs to verify that the assistant
    did not fabricate data after the fact.
    
    Args:
        data: Any JSON-serializable data
        
    Returns:
        SHA-256 hex digest of the data
    """
    if data is None:
        return ""
    
    # Convert to JSON string with sorted keys for consistent hashing
    json_str = json.dumps(data, sort_keys=True, ensure_ascii=False)
    
    # Compute SHA-256 hash
    hash_obj = hashlib.sha256(json_str.encode('utf-8'))
    
    return hash_obj.hexdigest()


def create_source_refs(table: str, record_id: int, fields: Optional[list] = None, confidence: float = 1.0) -> dict:
    """
    Create a source reference object for audit trails.
    
    This helps track the provenance of data shown by the assistant.
    
    Args:
        table: Database table name
        record_id: Record ID
        fields: List of field names accessed (optional)
        confidence: Confidence level (0.0 to 1.0)
        
    Returns:
        Dictionary with source reference information
    """
    source_ref = {
        "table": table,
        "id": record_id,
        "confidence": confidence
    }
    
    if fields:
        source_ref["excerpt"] = ", ".join(fields)
    
    return source_ref


def mask_request_body(body: Optional[str]) -> Optional[str]:
    """
    Mask sensitive data in request body string.
    
    Args:
        body: Request body as string (JSON)
        
    Returns:
        Masked request body
    """
    if not body:
        return body
    
    try:
        # Try to parse as JSON
        data = json.loads(body)
        masked_data = mask_sensitive_data(data)
        return json.dumps(masked_data)
    except (json.JSONDecodeError, TypeError):
        # If not JSON, return as is (or apply regex-based masking)
        return body
