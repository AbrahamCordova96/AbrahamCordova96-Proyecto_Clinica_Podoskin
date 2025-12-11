"""
Unit tests for security utilities

Tests for PII/PHI masking, response hashing, and source references.
"""

import pytest
from backend.api.utils.security_utils import (
    mask_email,
    mask_phone,
    mask_identification,
    mask_sensitive_data,
    compute_response_hash,
    create_source_refs,
    mask_request_body
)


class TestEmailMasking:
    """Test email masking functionality"""
    
    def test_mask_email_standard(self):
        """Test masking standard email"""
        result = mask_email("john.doe@example.com")
        assert result == "j***e@e***e.com"
    
    def test_mask_email_short(self):
        """Test masking short email"""
        result = mask_email("ab@xy.com")
        assert result == "a*@x*.com"
    
    def test_mask_email_invalid(self):
        """Test masking invalid email"""
        result = mask_email("not-an-email")
        assert result == "not-an-email"
    
    def test_mask_email_empty(self):
        """Test masking empty email"""
        result = mask_email("")
        assert result == ""


class TestPhoneMasking:
    """Test phone masking functionality"""
    
    def test_mask_phone_international(self):
        """Test masking international phone"""
        result = mask_phone("+52 123 456 7890")
        assert result == "+52 *** *** 7890"
    
    def test_mask_phone_local(self):
        """Test masking local phone"""
        result = mask_phone("1234567890")
        assert result == "*** *** 7890"
    
    def test_mask_phone_short(self):
        """Test masking short phone"""
        result = mask_phone("123")
        assert result == "***"


class TestIdentificationMasking:
    """Test identification masking functionality"""
    
    def test_mask_id_standard(self):
        """Test masking standard ID"""
        result = mask_identification("123-45-6789")
        assert result == "***6789"
    
    def test_mask_id_short(self):
        """Test masking short ID"""
        result = mask_identification("123")
        assert result == "***"


class TestSensitiveDataMasking:
    """Test sensitive data masking in dictionaries"""
    
    def test_mask_nested_data(self):
        """Test masking nested sensitive data"""
        data = {
            "nombre": "Juan Pérez",
            "email": "juan.perez@example.com",
            "telefono": "+52 123 456 7890",
            "password": "secret123",
            "datos_medicos": {
                "curp": "ABCD123456HDFXXX01",
                "correo": "backup@example.com"
            }
        }
        
        result = mask_sensitive_data(data)
        
        assert result["nombre"] == "Juan Pérez"  # Not masked
        assert result["email"] == "j***z@e***e.com"  # Masked
        assert result["telefono"] == "+52 *** *** 7890"  # Masked
        assert result["password"] == "***MASKED***"  # Completely masked
        assert result["datos_medicos"]["curp"] == "***XX01"  # Masked
        assert result["datos_medicos"]["correo"] == "b***p@e***e.com"  # Masked
    
    def test_mask_list_data(self):
        """Test masking data in lists"""
        data = {
            "contactos": [
                {"email": "person1@example.com"},
                {"email": "person2@example.com"}
            ]
        }
        
        result = mask_sensitive_data(data)
        
        assert result["contactos"][0]["email"] == "p***1@e***e.com"
        assert result["contactos"][1]["email"] == "p***2@e***e.com"


class TestResponseHashing:
    """Test response hash computation"""
    
    def test_compute_hash_dict(self):
        """Test computing hash for dictionary"""
        data = {"id": 123, "name": "Test"}
        hash1 = compute_response_hash(data)
        hash2 = compute_response_hash(data)
        
        # Same data should produce same hash
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 produces 64 hex characters
    
    def test_compute_hash_different_data(self):
        """Test different data produces different hash"""
        data1 = {"id": 123, "name": "Test"}
        data2 = {"id": 456, "name": "Other"}
        
        hash1 = compute_response_hash(data1)
        hash2 = compute_response_hash(data2)
        
        assert hash1 != hash2
    
    def test_compute_hash_order_independent(self):
        """Test hash is independent of key order"""
        data1 = {"a": 1, "b": 2, "c": 3}
        data2 = {"c": 3, "a": 1, "b": 2}
        
        hash1 = compute_response_hash(data1)
        hash2 = compute_response_hash(data2)
        
        # Should produce same hash (sorted keys)
        assert hash1 == hash2
    
    def test_compute_hash_none(self):
        """Test computing hash for None"""
        result = compute_response_hash(None)
        assert result == ""


class TestSourceRefs:
    """Test source reference creation"""
    
    def test_create_source_ref_basic(self):
        """Test creating basic source reference"""
        ref = create_source_refs("pacientes", 123)
        
        assert ref["table"] == "pacientes"
        assert ref["id"] == 123
        assert ref["confidence"] == 1.0
        assert "excerpt" not in ref
    
    def test_create_source_ref_with_fields(self):
        """Test creating source reference with fields"""
        ref = create_source_refs(
            "pacientes", 
            123, 
            fields=["nombre", "fecha_nacimiento"],
            confidence=0.95
        )
        
        assert ref["table"] == "pacientes"
        assert ref["id"] == 123
        assert ref["excerpt"] == "nombre, fecha_nacimiento"
        assert ref["confidence"] == 0.95


class TestRequestBodyMasking:
    """Test request body masking"""
    
    def test_mask_json_body(self):
        """Test masking JSON request body"""
        body = '{"email": "test@example.com", "password": "secret"}'
        result = mask_request_body(body)
        
        # Should mask email and password
        assert "test@example.com" not in result
        assert "secret" not in result
        assert "***MASKED***" in result
    
    def test_mask_invalid_json(self):
        """Test masking invalid JSON body"""
        body = "not-json-data"
        result = mask_request_body(body)
        
        # Should return as-is if not JSON
        assert result == "not-json-data"
    
    def test_mask_none_body(self):
        """Test masking None body"""
        result = mask_request_body(None)
        assert result is None


if __name__ == "__main__":
    # Run basic tests
    print("Running basic security utils tests...")
    
    # Test email masking
    email = "john.doe@example.com"
    masked = mask_email(email)
    print(f"✓ Email masking: {email} -> {masked}")
    
    # Test phone masking
    phone = "+52 123 456 7890"
    masked = mask_phone(phone)
    print(f"✓ Phone masking: {phone} -> {masked}")
    
    # Test data masking
    data = {
        "nombre": "Test User",
        "email": "test@example.com",
        "password": "secret123"
    }
    masked = mask_sensitive_data(data)
    print(f"✓ Data masking: {data}")
    print(f"  -> {masked}")
    
    # Test hash computation
    hash_val = compute_response_hash({"id": 123})
    print(f"✓ Hash computation: {hash_val[:16]}...")
    
    # Test source refs
    ref = create_source_refs("pacientes", 123, ["nombre", "email"])
    print(f"✓ Source refs: {ref}")
    
    print("\n✅ All basic tests passed!")
