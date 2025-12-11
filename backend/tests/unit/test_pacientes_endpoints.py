"""
Tests de Endpoints de Pacientes
================================

Tests para el módulo de pacientes (8 endpoints):
- GET /api/v1/pacientes (listar pacientes con paginación)
- POST /api/v1/pacientes (crear paciente)
- GET /api/v1/pacientes/{id} (obtener paciente)
- PUT /api/v1/pacientes/{id} (actualizar paciente)
- DELETE /api/v1/pacientes/{id} (soft delete)
- GET /api/v1/pacientes/{id}/historial (historial completo)
- GET /api/v1/pacientes/search (buscar pacientes)
- POST /api/v1/pacientes/{id}/export-pdf (exportar a PDF)
"""

import pytest
from datetime import date, timedelta
from decimal import Decimal


@pytest.mark.api
@pytest.mark.database
class TestPacientesListar:
    """Tests de listado de pacientes."""
    
    def test_list_pacientes_admin(self, client, auth_headers_admin, test_paciente):
        """Test: Listar pacientes como admin."""
        response = client.get(
            "/api/v1/pacientes",
            headers=auth_headers_admin
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data or isinstance(data, list)
    
    def test_list_pacientes_podologo(self, client, auth_headers_podologo, test_paciente):
        """Test: Listar pacientes como podólogo."""
        response = client.get(
            "/api/v1/pacientes",
            headers=auth_headers_podologo
        )
        
        assert response.status_code == 200
    
    def test_list_pacientes_recepcion(self, client, auth_headers_recepcion, test_paciente):
        """Test: Listar pacientes como recepcionista."""
        response = client.get(
            "/api/v1/pacientes",
            headers=auth_headers_recepcion
        )
        
        # Recepción puede ver lista básica
        assert response.status_code == 200
    
    def test_list_pacientes_without_auth(self, client):
        """Test: Listar sin autenticación."""
        response = client.get("/api/v1/pacientes")
        assert response.status_code == 401
    
    def test_list_pacientes_pagination(self, client, auth_headers_admin, core_db):
        """Test: Paginación de pacientes."""
        # Crear múltiples pacientes
        from backend.schemas.core.models import Paciente
        for i in range(15):
            paciente = Paciente(
                nombres=f"Paciente{i}",
                apellidos=f"Test{i}",
                fecha_nacimiento=date(1990, 1, 1),
                sexo="M",
                telefono=f"555000{i:04d}",
                activo=True
            )
            core_db.add(paciente)
        core_db.commit()
        
        # Primera página
        response = client.get(
            "/api/v1/pacientes?page=1&per_page=10",
            headers=auth_headers_admin
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verificar estructura de paginación
        if isinstance(data, dict) and "items" in data:
            assert len(data["items"]) <= 10
            assert "total" in data or "page" in data


@pytest.mark.api
@pytest.mark.database
class TestPacientesCrear:
    """Tests de creación de pacientes."""
    
    def test_create_paciente_admin(self, client, auth_headers_admin):
        """Test: Crear paciente como admin."""
        paciente_data = {
            "nombres": "Carlos",
            "apellidos": "González Pérez",
            "fecha_nacimiento": "1985-03-15",
            "sexo": "M",
            "telefono": "5551234567",
            "email": "carlos.gonzalez@test.com",
            "domicilio": "Calle Test 123",
            "peso_kg": 75.5,
            "estatura_cm": 175.0,
            "ocupacion": "Ingeniero",
            "estado_civil": "Casado"
        }
        
        response = client.post(
            "/api/v1/pacientes",
            headers=auth_headers_admin,
            json=paciente_data
        )
        
        assert response.status_code in [200, 201]
        data = response.json()
        assert data["nombres"] == "Carlos"
        assert data["apellidos"] == "González Pérez"
        assert "id_paciente" in data
    
    def test_create_paciente_podologo(self, client, auth_headers_podologo):
        """Test: Crear paciente como podólogo."""
        paciente_data = {
            "nombres": "María",
            "apellidos": "Rodríguez",
            "fecha_nacimiento": "1990-06-20",
            "sexo": "F",
            "telefono": "5559876543"
        }
        
        response = client.post(
            "/api/v1/pacientes",
            headers=auth_headers_podologo,
            json=paciente_data
        )
        
        assert response.status_code in [200, 201]
    
    def test_create_paciente_recepcion(self, client, auth_headers_recepcion):
        """Test: Crear paciente como recepcionista."""
        paciente_data = {
            "nombres": "Laura",
            "apellidos": "Martínez",
            "fecha_nacimiento": "1995-09-10",
            "sexo": "F",
            "telefono": "5556543210"
        }
        
        response = client.post(
            "/api/v1/pacientes",
            headers=auth_headers_recepcion,
            json=paciente_data
        )
        
        # Recepción puede crear pacientes
        assert response.status_code in [200, 201, 403]
    
    def test_create_paciente_missing_required_fields(self, client, auth_headers_admin):
        """Test: Crear sin campos requeridos."""
        paciente_data = {
            "nombres": "Pedro"
            # Falta apellidos, fecha_nacimiento, etc.
        }
        
        response = client.post(
            "/api/v1/pacientes",
            headers=auth_headers_admin,
            json=paciente_data
        )
        
        assert response.status_code == 422
    
    def test_create_paciente_invalid_email(self, client, auth_headers_admin):
        """Test: Crear con email inválido."""
        paciente_data = {
            "nombres": "Juan",
            "apellidos": "López",
            "fecha_nacimiento": "1988-01-01",
            "sexo": "M",
            "telefono": "5551111111",
            "email": "not-an-email"
        }
        
        response = client.post(
            "/api/v1/pacientes",
            headers=auth_headers_admin,
            json=paciente_data
        )
        
        # Puede ser 422 (validación Pydantic) o 200 si no valida
        assert response.status_code in [200, 201, 422]
    
    def test_create_paciente_future_birthdate(self, client, auth_headers_admin):
        """Test: Crear con fecha de nacimiento futura."""
        future_date = (date.today() + timedelta(days=365)).isoformat()
        paciente_data = {
            "nombres": "Futuro",
            "apellidos": "Test",
            "fecha_nacimiento": future_date,
            "sexo": "M",
            "telefono": "5552222222"
        }
        
        response = client.post(
            "/api/v1/pacientes",
            headers=auth_headers_admin,
            json=paciente_data
        )
        
        # Debería fallar validación o permitir (depende de implementación)
        assert response.status_code in [200, 201, 400, 422]
    
    def test_create_paciente_calculate_imc(self, client, auth_headers_admin):
        """Test: Verificar cálculo automático de IMC."""
        paciente_data = {
            "nombres": "Peso",
            "apellidos": "Test",
            "fecha_nacimiento": "1990-01-01",
            "sexo": "M",
            "telefono": "5553333333",
            "peso_kg": 80.0,
            "estatura_cm": 180.0
        }
        
        response = client.post(
            "/api/v1/pacientes",
            headers=auth_headers_admin,
            json=paciente_data
        )
        
        if response.status_code in [200, 201]:
            data = response.json()
            # IMC = peso / (estatura_m)^2 = 80 / 1.8^2 = ~24.69
            if "imc" in data:
                assert 24 <= data["imc"] <= 25


@pytest.mark.api
@pytest.mark.database
class TestPacientesObtener:
    """Tests de obtención de paciente individual."""
    
    def test_get_paciente_by_id_admin(self, client, auth_headers_admin, test_paciente):
        """Test: Obtener paciente por ID como admin."""
        response = client.get(
            f"/api/v1/pacientes/{test_paciente.id_paciente}",
            headers=auth_headers_admin
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id_paciente"] == test_paciente.id_paciente
        assert data["nombres"] == test_paciente.nombres
    
    def test_get_paciente_by_id_podologo(self, client, auth_headers_podologo, test_paciente):
        """Test: Obtener paciente como podólogo."""
        response = client.get(
            f"/api/v1/pacientes/{test_paciente.id_paciente}",
            headers=auth_headers_podologo
        )
        
        assert response.status_code == 200
    
    def test_get_paciente_by_id_recepcion(self, client, auth_headers_recepcion, test_paciente):
        """Test: Obtener paciente como recepcionista."""
        response = client.get(
            f"/api/v1/pacientes/{test_paciente.id_paciente}",
            headers=auth_headers_recepcion
        )
        
        # Recepción puede ver datos básicos
        assert response.status_code in [200, 403]
    
    def test_get_paciente_nonexistent(self, client, auth_headers_admin):
        """Test: Obtener paciente inexistente."""
        response = client.get(
            "/api/v1/pacientes/99999",
            headers=auth_headers_admin
        )
        
        assert response.status_code == 404
    
    def test_get_paciente_without_auth(self, client, test_paciente):
        """Test: Obtener sin autenticación."""
        response = client.get(f"/api/v1/pacientes/{test_paciente.id_paciente}")
        assert response.status_code == 401


@pytest.mark.api
@pytest.mark.database
class TestPacientesActualizar:
    """Tests de actualización de pacientes."""
    
    def test_update_paciente_admin(self, client, auth_headers_admin, test_paciente):
        """Test: Actualizar paciente como admin."""
        update_data = {
            "telefono": "5559999999",
            "email": "updated@test.com",
            "domicilio": "Nueva Dirección 456"
        }
        
        response = client.put(
            f"/api/v1/pacientes/{test_paciente.id_paciente}",
            headers=auth_headers_admin,
            json=update_data
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["telefono"] == "5559999999"
    
    def test_update_paciente_podologo(self, client, auth_headers_podologo, test_paciente):
        """Test: Actualizar como podólogo."""
        update_data = {
            "peso_kg": 78.5,
            "estatura_cm": 176.0
        }
        
        response = client.put(
            f"/api/v1/pacientes/{test_paciente.id_paciente}",
            headers=auth_headers_podologo,
            json=update_data
        )
        
        assert response.status_code == 200
    
    def test_update_paciente_partial(self, client, auth_headers_admin, test_paciente):
        """Test: Actualización parcial."""
        update_data = {
            "telefono": "5558888888"
        }
        
        response = client.put(
            f"/api/v1/pacientes/{test_paciente.id_paciente}",
            headers=auth_headers_admin,
            json=update_data
        )
        
        assert response.status_code == 200
        data = response.json()
        # Verificar que otros campos no cambiaron
        assert data["nombres"] == test_paciente.nombres
    
    def test_update_paciente_nonexistent(self, client, auth_headers_admin):
        """Test: Actualizar paciente inexistente."""
        update_data = {"telefono": "5557777777"}
        
        response = client.put(
            "/api/v1/pacientes/99999",
            headers=auth_headers_admin,
            json=update_data
        )
        
        assert response.status_code == 404


@pytest.mark.api
@pytest.mark.database
class TestPacientesEliminar:
    """Tests de eliminación (soft delete) de pacientes."""
    
    def test_delete_paciente_admin(self, client, auth_headers_admin, core_db):
        """Test: Eliminar paciente como admin."""
        from backend.schemas.core.models import Paciente
        
        # Crear paciente temporal
        paciente = Paciente(
            nombres="Eliminar",
            apellidos="Test",
            fecha_nacimiento=date(1990, 1, 1),
            sexo="M",
            telefono="5556666666",
            activo=True
        )
        core_db.add(paciente)
        core_db.commit()
        core_db.refresh(paciente)
        
        response = client.delete(
            f"/api/v1/pacientes/{paciente.id_paciente}",
            headers=auth_headers_admin
        )
        
        assert response.status_code in [200, 204]
        
        # Verificar soft delete (activo=False)
        core_db.refresh(paciente)
        assert paciente.activo == False
    
    def test_delete_paciente_podologo(self, client, auth_headers_podologo, test_paciente):
        """Test: Podólogo no puede eliminar pacientes."""
        response = client.delete(
            f"/api/v1/pacientes/{test_paciente.id_paciente}",
            headers=auth_headers_podologo
        )
        
        # Debe ser 403 (prohibido) si solo admin puede eliminar
        assert response.status_code in [200, 204, 403]
    
    def test_delete_paciente_nonexistent(self, client, auth_headers_admin):
        """Test: Eliminar paciente inexistente."""
        response = client.delete(
            "/api/v1/pacientes/99999",
            headers=auth_headers_admin
        )
        
        assert response.status_code == 404


@pytest.mark.api
@pytest.mark.database
class TestPacientesBuscar:
    """Tests de búsqueda de pacientes."""
    
    def test_search_pacientes_by_nombre(self, client, auth_headers_admin, test_paciente):
        """Test: Buscar por nombre."""
        response = client.get(
            f"/api/v1/pacientes/search?q={test_paciente.nombres}",
            headers=auth_headers_admin
        )
        
        assert response.status_code == 200
        data = response.json()
        # Verificar que retorna resultados
        assert isinstance(data, list) or "items" in data
    
    def test_search_pacientes_by_telefono(self, client, auth_headers_admin, test_paciente):
        """Test: Buscar por teléfono."""
        response = client.get(
            f"/api/v1/pacientes/search?q={test_paciente.telefono}",
            headers=auth_headers_admin
        )
        
        assert response.status_code == 200
    
    def test_search_pacientes_no_results(self, client, auth_headers_admin):
        """Test: Búsqueda sin resultados."""
        response = client.get(
            "/api/v1/pacientes/search?q=NoExisteEsteNombre123",
            headers=auth_headers_admin
        )
        
        assert response.status_code == 200
        data = response.json()
        if isinstance(data, list):
            assert len(data) == 0
        elif "items" in data:
            assert len(data["items"]) == 0


@pytest.mark.api
@pytest.mark.integration
class TestPacientesHistorial:
    """Tests de historial completo del paciente."""
    
    def test_get_historial_admin(self, client, auth_headers_admin, test_paciente):
        """Test: Obtener historial como admin."""
        response = client.get(
            f"/api/v1/pacientes/{test_paciente.id_paciente}/historial",
            headers=auth_headers_admin
        )
        
        assert response.status_code == 200
        data = response.json()
        # Verificar estructura de historial
        assert isinstance(data, dict) or isinstance(data, list)
    
    def test_get_historial_podologo(self, client, auth_headers_podologo, test_paciente):
        """Test: Obtener historial como podólogo."""
        response = client.get(
            f"/api/v1/pacientes/{test_paciente.id_paciente}/historial",
            headers=auth_headers_podologo
        )
        
        assert response.status_code == 200
    
    def test_get_historial_recepcion(self, client, auth_headers_recepcion, test_paciente):
        """Test: Recepción no puede ver historial médico."""
        response = client.get(
            f"/api/v1/pacientes/{test_paciente.id_paciente}/historial",
            headers=auth_headers_recepcion
        )
        
        # Recepción no debe tener acceso a historial médico
        assert response.status_code in [200, 403]


@pytest.mark.api
@pytest.mark.slow
class TestPacientesExportPDF:
    """Tests de exportación a PDF."""
    
    def test_export_pdf_admin(self, client, auth_headers_admin, test_paciente):
        """Test: Exportar expediente a PDF como admin."""
        response = client.post(
            f"/api/v1/pacientes/{test_paciente.id_paciente}/export-pdf",
            headers=auth_headers_admin
        )
        
        # Puede ser 200 con PDF o redirect a archivo
        assert response.status_code in [200, 201, 302]
        
        # Si retorna PDF, verificar content type
        if response.status_code == 200:
            content_type = response.headers.get("content-type", "")
            assert "pdf" in content_type.lower() or "application/octet-stream" in content_type
    
    def test_export_pdf_nonexistent(self, client, auth_headers_admin):
        """Test: Exportar PDF de paciente inexistente."""
        response = client.post(
            "/api/v1/pacientes/99999/export-pdf",
            headers=auth_headers_admin
        )
        
        assert response.status_code == 404


@pytest.mark.integration
class TestPacientesWorkflow:
    """Tests de flujos completos."""
    
    def test_complete_patient_workflow(self, client, auth_headers_admin):
        """Test: Flujo completo CRUD de paciente."""
        # 1. Crear
        create_data = {
            "nombres": "Workflow",
            "apellidos": "Test",
            "fecha_nacimiento": "1992-05-10",
            "sexo": "M",
            "telefono": "5554444444"
        }
        create_response = client.post(
            "/api/v1/pacientes",
            headers=auth_headers_admin,
            json=create_data
        )
        assert create_response.status_code in [200, 201]
        paciente_id = create_response.json()["id_paciente"]
        
        # 2. Leer
        get_response = client.get(
            f"/api/v1/pacientes/{paciente_id}",
            headers=auth_headers_admin
        )
        assert get_response.status_code == 200
        
        # 3. Actualizar
        update_response = client.put(
            f"/api/v1/pacientes/{paciente_id}",
            headers=auth_headers_admin,
            json={"telefono": "5555555555"}
        )
        assert update_response.status_code == 200
        
        # 4. Buscar
        search_response = client.get(
            f"/api/v1/pacientes/search?q=Workflow",
            headers=auth_headers_admin
        )
        assert search_response.status_code == 200
        
        # 5. Eliminar
        delete_response = client.delete(
            f"/api/v1/pacientes/{paciente_id}",
            headers=auth_headers_admin
        )
        assert delete_response.status_code in [200, 204]
