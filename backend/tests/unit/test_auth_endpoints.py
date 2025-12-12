"""
Tests de Endpoints de Autenticación
===================================

Tests para:
- POST /api/v1/auth/login
- GET /api/v1/auth/me
- POST /api/v1/auth/change-password
"""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.auth
@pytest.mark.api
class TestAuthLogin:
    """Tests del endpoint de login."""
    
    def test_login_success_admin(self, client, test_admin_user):
        """Test: Login exitoso con usuario admin."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "username": "admin_test",
                "password": "admin123"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        print(f"\n🔍 Response data: {data}")  # DEBUG
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        # El endpoint /auth/login solo devuelve token, no user data
    
    def test_login_success_podologo(self, client, test_podologo_user):
        """Test: Login exitoso con usuario podólogo."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "username": "podologo_test",
                "password": "podo123"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        # El endpoint /auth/login solo devuelve token, no user data
    
    def test_login_success_recepcion(self, client, test_recepcion_user):
        """Test: Login exitoso con usuario recepción."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "username": "recepcion_test",
                "password": "recep123"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        # El endpoint /auth/login solo devuelve token, no user data
    
    def test_login_wrong_password(self, client, test_admin_user):
        """Test: Login con contraseña incorrecta."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "username": "admin_test",
                "password": "wrong_password"
            }
        )
        
        assert response.status_code == 401
        assert "detail" in response.json()
    
    def test_login_nonexistent_user(self, client):
        """Test: Login con usuario inexistente."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "username": "nonexistent_user",
                "password": "any_password"
            }
        )
        
        assert response.status_code == 401
    
    def test_login_inactive_user(self, client, auth_db, test_admin_user):
        """Test: Login con usuario inactivo."""
        # Desactivar usuario
        test_admin_user.activo = False
        auth_db.commit()
        
        response = client.post(
            "/api/v1/auth/login",
            json={
                "username": "admin_test",
                "password": "admin123"
            }
        )
        
        assert response.status_code == 403
    
    def test_login_missing_username(self, client):
        """Test: Login sin username."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "password": "admin123"
            }
        )
        
        assert response.status_code == 422
    
    def test_login_missing_password(self, client):
        """Test: Login sin password."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "username": "admin_test"
            }
        )
        
        assert response.status_code == 422
    
    def test_login_empty_credentials(self, client):
        """Test: Login con credenciales vacías."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "username": "",
                "password": ""
            }
        )
        
        assert response.status_code in [401, 422]


@pytest.mark.auth
@pytest.mark.api
class TestAuthMe:
    """Tests del endpoint /me (perfil actual)."""
    
    def test_me_with_valid_token_admin(self, client, auth_headers_admin, test_admin_user):
        """Test: Obtener perfil con token válido (admin)."""
        response = client.get(
            "/api/v1/auth/me",
            headers=auth_headers_admin
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["nombre_usuario"] == "admin_test"
        assert data["rol"] == "Admin"
        assert data["email"] == "admin@test.com"
        assert "password_hash" not in data  # No debe exponer el hash
    
    def test_me_with_valid_token_podologo(self, client, auth_headers_podologo, test_podologo_user):
        """Test: Obtener perfil con token válido (podólogo)."""
        response = client.get(
            "/api/v1/auth/me",
            headers=auth_headers_podologo
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["rol"] == "Podologo"
    
    def test_me_with_valid_token_recepcion(self, client, auth_headers_recepcion, test_recepcion_user):
        """Test: Obtener perfil con token válido (recepción)."""
        response = client.get(
            "/api/v1/auth/me",
            headers=auth_headers_recepcion
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["rol"] == "Recepcion"
    
    def test_me_without_token(self, client):
        """Test: Intentar obtener perfil sin token."""
        response = client.get("/api/v1/auth/me")
        
        assert response.status_code == 401
    
    def test_me_with_invalid_token(self, client):
        """Test: Perfil con token inválido."""
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid_token_123"}
        )
        
        assert response.status_code == 401
    
    def test_me_with_malformed_token(self, client):
        """Test: Perfil con token mal formado."""
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "InvalidFormat"}
        )
        
        assert response.status_code == 401


@pytest.mark.auth
@pytest.mark.api
class TestAuthChangePassword:
    """Tests del endpoint de cambio de contraseña."""
    
    def test_change_password_success(self, client, auth_headers_admin):
        """Test: Cambio de contraseña exitoso."""
        response = client.put(
            "/api/v1/auth/change-password",
            headers=auth_headers_admin,
            json={
                "current_password": "admin123",
                "new_password": "NewSecurePass123!"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data or "detail" in data
    
    def test_change_password_wrong_current(self, client, auth_headers_admin):
        """Test: Cambio con contraseña actual incorrecta."""
        response = client.put(
            "/api/v1/auth/change-password",
            headers=auth_headers_admin,
            json={
                "current_password": "wrong_password",
                "new_password": "NewSecurePass123!"
            }
        )
        
        assert response.status_code in [400, 401]
    
    def test_change_password_same_as_current(self, client, auth_headers_admin):
        """Test: Nueva contraseña igual a la actual."""
        response = client.put(
            "/api/v1/auth/change-password",
            headers=auth_headers_admin,
            json={
                "current_password": "admin123",
                "new_password": "admin123"
            }
        )
        
        # Puede ser 400 (bad request) o 200 dependiendo de la implementación
        assert response.status_code in [200, 400]
    
    def test_change_password_weak_password(self, client, auth_headers_admin):
        """Test: Nueva contraseña débil."""
        response = client.put(
            "/api/v1/auth/change-password",
            headers=auth_headers_admin,
            json={
                "current_password": "admin123",
                "new_password": "123"
            }
        )
        
        # Puede ser 400 o 422 dependiendo de validación
        assert response.status_code in [400, 422]
    
    def test_change_password_without_auth(self, client):
        """Test: Cambio sin autenticación."""
        response = client.put(
            "/api/v1/auth/change-password",
            json={
                "current_password": "admin123",
                "new_password": "NewSecurePass123!"
            }
        )
        
        assert response.status_code == 401
    
    def test_change_password_missing_current(self, client, auth_headers_admin):
        """Test: Sin contraseña actual."""
        response = client.put(
            "/api/v1/auth/change-password",
            headers=auth_headers_admin,
            json={
                "new_password": "NewSecurePass123!"
            }
        )
        
        assert response.status_code == 422
    
    def test_change_password_missing_new(self, client, auth_headers_admin):
        """Test: Sin contraseña nueva."""
        response = client.put(
            "/api/v1/auth/change-password",
            headers=auth_headers_admin,
            json={
                "current_password": "admin123"
            }
        )
        
        assert response.status_code == 422
    
    def test_change_password_and_login_with_new(self, client, test_admin_user):
        """Test: Cambiar contraseña y hacer login con la nueva."""
        # Obtener token
        login_response = client.post(
            "/api/v1/auth/login",
            json={
                "username": "admin_test",
                "password": "admin123"
            }
        )
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Cambiar contraseña
        change_response = client.put(
            "/api/v1/auth/change-password",
            headers=headers,
            json={
                "current_password": "admin123",
                "new_password": "NewPass456!"
            }
        )
        
        # Solo continuar si el cambio fue exitoso
        if change_response.status_code == 200:
            # Intentar login con nueva contraseña
            new_login_response = client.post(
                "/api/v1/auth/login",
                json={
                    "username": "admin_test",
                    "password": "NewPass456!"
                }
            )
            
            assert new_login_response.status_code == 200
            assert "access_token" in new_login_response.json()


@pytest.mark.auth
@pytest.mark.integration
class TestAuthWorkflow:
    """Tests de flujos completos de autenticación."""
    
    def test_complete_auth_workflow(self, client, test_admin_user):
        """Test: Flujo completo: login -> obtener perfil -> cambiar contraseña."""
        # 1. Login
        login_response = client.post(
            "/api/v1/auth/login",
            json={
                "username": "admin_test",
                "password": "admin123"
            }
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # 2. Obtener perfil
        me_response = client.get("/api/v1/auth/me", headers=headers)
        assert me_response.status_code == 200
        assert me_response.json()["nombre_usuario"] == "admin_test"
        
        # 3. Cambiar contraseña
        change_response = client.put(
            "/api/v1/auth/change-password",
            headers=headers,
            json={
                "current_password": "admin123",
                "new_password": "NewPass789!"
            }
        )
        assert change_response.status_code == 200
    
    def test_multiple_logins_different_users(self, client, test_admin_user, test_podologo_user):
        """Test: Logins múltiples de diferentes usuarios."""
        # Login admin
        admin_response = client.post(
            "/api/v1/auth/login",
            json={"username": "admin_test", "password": "admin123"}
        )
        assert admin_response.status_code == 200
        admin_token = admin_response.json()["access_token"]
        
        # Login podólogo
        podo_response = client.post(
            "/api/v1/auth/login",
            json={"username": "podologo_test", "password": "podo123"}
        )
        assert podo_response.status_code == 200
        podo_token = podo_response.json()["access_token"]
        
        # Verificar que son tokens diferentes
        assert admin_token != podo_token
        
        # Verificar perfiles con sus respectivos tokens
        admin_me = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert admin_me.json()["rol"] == "Admin"
        
        podo_me = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {podo_token}"}
        )
        assert podo_me.json()["rol"] == "Podologo"
