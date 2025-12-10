# backend/schemas/auth/auth_utils.py
"""
Password hashing utilities with Argon2 support.

This module provides secure password hashing using Argon2id (recommended by OWASP).
Maintains backward compatibility with existing bcrypt passwords.

Migration strategy:
- New passwords use Argon2id (more secure, resistant to GPU attacks)
- Old bcrypt passwords still work (automatically detected)
- Passwords are migrated to Argon2 on next login
"""
from passlib.context import CryptContext

# Configure password context with Argon2 as primary and bcrypt for backward compatibility
# Argon2id is the recommended variant (hybrid of Argon2i and Argon2d)
pwd_context = CryptContext(
    schemes=["argon2", "bcrypt"],
    deprecated="auto",
    argon2__memory_cost=65536,  # 64 MB (OWASP recommended minimum)
    argon2__time_cost=3,        # 3 iterations (OWASP recommended minimum)
    argon2__parallelism=4,      # 4 parallel threads
)

def hash_password(password: str) -> str:
    """
    Hash a password using Argon2id.
    
    Args:
        password: Plain text password to hash
        
    Returns:
        Hashed password string
        
    Example:
        >>> hashed = hash_password("SecurePass123!")
        >>> hashed.startswith("$argon2id$")
        True
    """
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against a hash.
    
    Automatically detects hash type (Argon2 or bcrypt) and verifies accordingly.
    
    Args:
        plain_password: Plain text password to verify
        hashed_password: Hashed password to compare against
        
    Returns:
        True if password matches, False otherwise
        
    Example:
        >>> hashed = hash_password("SecurePass123!")
        >>> verify_password("SecurePass123!", hashed)
        True
        >>> verify_password("WrongPass", hashed)
        False
    """
    return pwd_context.verify(plain_password, hashed_password)

def needs_rehash(hashed_password: str) -> bool:
    """
    Check if a password hash needs to be updated.
    
    Returns True if the hash uses deprecated algorithm (bcrypt) or
    outdated Argon2 parameters.
    
    Args:
        hashed_password: Hashed password to check
        
    Returns:
        True if password should be rehashed, False otherwise
        
    Example:
        >>> bcrypt_hash = "$2b$12$..."  # Old bcrypt hash
        >>> needs_rehash(bcrypt_hash)
        True
        >>> argon2_hash = "$argon2id$..."  # New Argon2 hash
        >>> needs_rehash(argon2_hash)
        False
    """
    return pwd_context.needs_update(hashed_password)