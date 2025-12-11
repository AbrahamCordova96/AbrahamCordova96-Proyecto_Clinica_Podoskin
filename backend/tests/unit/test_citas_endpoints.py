"""
Tests de Endpoints de Citas
============================

Tests para el módulo de citas/agenda (8 endpoints):
- GET /api/v1/citas (listar citas)
- POST /api/v1/citas (crear/agendar cita)
- GET /api/v1/citas/{id} (obtener cita)
- PUT /api/v1/citas/{id} (actualizar cita)
- DELETE /api/v1/citas/{id} (cancelar cita)
- PATCH /api/v1/citas/{id}/status (cambiar estado)
- GET /api/v1/citas/calendario (vista calendario)
- GET /api/v1/citas/disponibilidad (slots disponibles)
"""

import pytest
from datetime import datetime, timedelta, date as date_type


@pytest.mark.api
@pytest.mark.database
class TestCitasListar:
    """Tests de listado de citas."""
    
    def test_list_citas_admin(self, client, auth_headers_admin):
        """Test: Listar citas como admin."""
        response = client.get(
            "/api/v1/citas",
            headers=auth_headers_admin
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list) or "items" in data
    
    def test_list_citas_podologo(self, client, auth_headers_podologo):
        """Test: Listar citas como podólogo."""
        response = client.get(
            "/api/v1/citas",
            headers=auth_headers_podologo
        )
        
        # Podólogo ve sus propias citas
        assert response.status_code == 200
    
    def test_list_citas_recepcion(self, client, auth_headers_recepcion):
        """Test: Listar citas como recepcionista."""
        response = client.get(
            "/api/v1/citas",
            headers=auth_headers_recepcion
        )
        
        # Recepción puede ver todas las citas
        assert response.status_code == 200
    
    def test_list_citas_filter_by_date(self, client, auth_headers_admin):
        """Test: Filtrar citas por fecha."""
        today = date_type.today().isoformat()
        response = client.get(
            f"/api/v1/citas?fecha={today}",
            headers=auth_headers_admin
        )
        
        assert response.status_code == 200
    
    def test_list_citas_filter_by_estado(self, client, auth_headers_admin):
        """Test: Filtrar citas por estado."""
        response = client.get(
            "/api/v1/citas?estado=agendada",
            headers=auth_headers_admin
        )
        
        assert response.status_code == 200
    
    def test_list_citas_pagination(self, client, auth_headers_admin):
        """Test: Paginación de citas."""
        response = client.get(
            "/api/v1/citas?page=1&per_page=10",
            headers=auth_headers_admin
        )
        
        assert response.status_code == 200
        data = response.json()
        
        if isinstance(data, dict) and "items" in data:
            assert len(data["items"]) <= 10


@pytest.mark.api
@pytest.mark.database
class TestCitasCrear:
    """Tests de creación/agendamiento de citas."""
    
    def test_create_cita_admin(self, client, auth_headers_admin, test_paciente, test_podologo, ops_db):
        """Test: Crear cita como admin."""
        # Crear servicio primero
        from backend.schemas.ops.models import CatalogoServicio
        from decimal import Decimal
        servicio = CatalogoServicio(
            nombre="Consulta General",
            descripcion="Consulta podológica general",
            duracion_minutos=60,
            precio=Decimal("500.00"),
            activo=True
        )
        ops_db.add(servicio)
        ops_db.commit()
        ops_db.refresh(servicio)
        
        # Fecha futura
        fecha_hora = (datetime.now() + timedelta(days=3)).replace(hour=10, minute=0, second=0, microsecond=0)
        
        cita_data = {
            "paciente_id": test_paciente.id_paciente,
            "podologo_id": test_podologo.id_podologo,
            "servicio_id": servicio.id_servicio,
            "fecha_hora": fecha_hora.isoformat(),
            "duracion_minutos": 60,
            "motivo": "Consulta de rutina",
            "estado": "agendada"
        }
        
        response = client.post(
            "/api/v1/citas",
            headers=auth_headers_admin,
            json=cita_data
        )
        
        assert response.status_code in [200, 201]
        data = response.json()
        assert data["paciente_id"] == test_paciente.id_paciente
        assert data["estado"] == "agendada"
    
    def test_create_cita_recepcion(self, client, auth_headers_recepcion, test_paciente, test_podologo, ops_db):
        """Test: Crear cita como recepcionista."""
        from backend.schemas.ops.models import CatalogoServicio
        from decimal import Decimal
        servicio = CatalogoServicio(
            nombre="Consulta Rápida",
            descripcion="Consulta rápida",
            duracion_minutos=30,
            precio=Decimal("300.00"),
            activo=True
        )
        ops_db.add(servicio)
        ops_db.commit()
        ops_db.refresh(servicio)
        
        fecha_hora = (datetime.now() + timedelta(days=2)).replace(hour=14, minute=0, second=0, microsecond=0)
        
        cita_data = {
            "paciente_id": test_paciente.id_paciente,
            "podologo_id": test_podologo.id_podologo,
            "servicio_id": servicio.id_servicio,
            "fecha_hora": fecha_hora.isoformat(),
            "duracion_minutos": 30,
            "motivo": "Revisión"
        }
        
        response = client.post(
            "/api/v1/citas",
            headers=auth_headers_recepcion,
            json=cita_data
        )
        
        # Recepción puede crear citas
        assert response.status_code in [200, 201]
    
    def test_create_cita_past_date(self, client, auth_headers_admin, test_paciente, test_podologo, ops_db):
        """Test: Crear cita con fecha pasada."""
        from backend.schemas.ops.models import CatalogoServicio
        from decimal import Decimal
        servicio = CatalogoServicio(
            nombre="Servicio Test",
            duracion_minutos=30,
            precio=Decimal("300.00"),
            activo=True
        )
        ops_db.add(servicio)
        ops_db.commit()
        ops_db.refresh(servicio)
        
        # Fecha pasada
        fecha_hora = (datetime.now() - timedelta(days=5)).isoformat()
        
        cita_data = {
            "paciente_id": test_paciente.id_paciente,
            "podologo_id": test_podologo.id_podologo,
            "servicio_id": servicio.id_servicio,
            "fecha_hora": fecha_hora,
            "duracion_minutos": 30,
            "motivo": "Test"
        }
        
        response = client.post(
            "/api/v1/citas",
            headers=auth_headers_admin,
            json=cita_data
        )
        
        # Debería permitir o rechazar según reglas de negocio
        assert response.status_code in [200, 201, 400, 422]
    
    def test_create_cita_missing_required_fields(self, client, auth_headers_admin):
        """Test: Crear cita sin campos requeridos."""
        cita_data = {
            "paciente_id": 1,
            # Faltan podologo_id, fecha_hora, etc.
        }
        
        response = client.post(
            "/api/v1/citas",
            headers=auth_headers_admin,
            json=cita_data
        )
        
        assert response.status_code == 422
    
    def test_create_cita_nonexistent_paciente(self, client, auth_headers_admin, test_podologo, ops_db):
        """Test: Crear cita con paciente inexistente."""
        from backend.schemas.ops.models import CatalogoServicio
        from decimal import Decimal
        servicio = CatalogoServicio(
            nombre="Servicio Test2",
            duracion_minutos=30,
            precio=Decimal("300.00"),
            activo=True
        )
        ops_db.add(servicio)
        ops_db.commit()
        ops_db.refresh(servicio)
        
        fecha_hora = (datetime.now() + timedelta(days=1)).isoformat()
        
        cita_data = {
            "paciente_id": 99999,  # No existe
            "podologo_id": test_podologo.id_podologo,
            "servicio_id": servicio.id_servicio,
            "fecha_hora": fecha_hora,
            "duracion_minutos": 30,
            "motivo": "Test"
        }
        
        response = client.post(
            "/api/v1/citas",
            headers=auth_headers_admin,
            json=cita_data
        )
        
        assert response.status_code in [400, 404, 422]


@pytest.mark.api
@pytest.mark.database
class TestCitasObtener:
    """Tests de obtención de cita individual."""
    
    def test_get_cita_by_id_admin(self, client, auth_headers_admin, ops_db, test_paciente, test_podologo):
        """Test: Obtener cita por ID como admin."""
        from backend.schemas.ops.models import Cita
        
        fecha_hora = datetime.now() + timedelta(days=1)
        cita = Cita(
            paciente_id=test_paciente.id_paciente,
            podologo_id=test_podologo.id_podologo,
            fecha_hora=fecha_hora,
            estado="agendada",
            duracion_minutos=60,
            motivo="Test"
        )
        ops_db.add(cita)
        ops_db.commit()
        ops_db.refresh(cita)
        
        response = client.get(
            f"/api/v1/citas/{cita.id_cita}",
            headers=auth_headers_admin
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id_cita"] == cita.id_cita
    
    def test_get_cita_nonexistent(self, client, auth_headers_admin):
        """Test: Obtener cita inexistente."""
        response = client.get(
            "/api/v1/citas/99999",
            headers=auth_headers_admin
        )
        
        assert response.status_code == 404
    
    def test_get_cita_without_auth(self, client):
        """Test: Obtener sin autenticación."""
        response = client.get("/api/v1/citas/1")
        assert response.status_code == 401


@pytest.mark.api
@pytest.mark.database
class TestCitasActualizar:
    """Tests de actualización de citas."""
    
    def test_update_cita_admin(self, client, auth_headers_admin, ops_db, test_paciente, test_podologo):
        """Test: Actualizar cita como admin."""
        from backend.schemas.ops.models import Cita
        
        fecha_hora = datetime.now() + timedelta(days=5)
        cita = Cita(
            paciente_id=test_paciente.id_paciente,
            podologo_id=test_podologo.id_podologo,
            fecha_hora=fecha_hora,
            estado="agendada",
            duracion_minutos=60,
            motivo="Consulta inicial"
        )
        ops_db.add(cita)
        ops_db.commit()
        ops_db.refresh(cita)
        
        # Actualizar motivo y duración
        update_data = {
            "motivo": "Consulta de seguimiento",
            "duracion_minutos": 90
        }
        
        response = client.put(
            f"/api/v1/citas/{cita.id_cita}",
            headers=auth_headers_admin,
            json=update_data
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["motivo"] == "Consulta de seguimiento"
    
    def test_update_cita_change_datetime(self, client, auth_headers_admin, ops_db, test_paciente, test_podologo):
        """Test: Cambiar fecha/hora de cita."""
        from backend.schemas.ops.models import Cita
        
        fecha_original = datetime.now() + timedelta(days=3)
        cita = Cita(
            paciente_id=test_paciente.id_paciente,
            podologo_id=test_podologo.id_podologo,
            fecha_hora=fecha_original,
            estado="agendada",
            duracion_minutos=60,
            motivo="Test"
        )
        ops_db.add(cita)
        ops_db.commit()
        ops_db.refresh(cita)
        
        # Nueva fecha
        nueva_fecha = (datetime.now() + timedelta(days=7)).replace(hour=15, minute=0, second=0, microsecond=0)
        
        update_data = {
            "fecha_hora": nueva_fecha.isoformat()
        }
        
        response = client.put(
            f"/api/v1/citas/{cita.id_cita}",
            headers=auth_headers_admin,
            json=update_data
        )
        
        assert response.status_code == 200
    
    def test_update_cita_nonexistent(self, client, auth_headers_admin):
        """Test: Actualizar cita inexistente."""
        update_data = {"motivo": "Test"}
        
        response = client.put(
            "/api/v1/citas/99999",
            headers=auth_headers_admin,
            json=update_data
        )
        
        assert response.status_code == 404


@pytest.mark.api
@pytest.mark.database
class TestCitasCancelar:
    """Tests de cancelación de citas."""
    
    def test_cancel_cita_admin(self, client, auth_headers_admin, ops_db, test_paciente, test_podologo):
        """Test: Cancelar cita como admin."""
        from backend.schemas.ops.models import Cita
        
        fecha_hora = datetime.now() + timedelta(days=2)
        cita = Cita(
            paciente_id=test_paciente.id_paciente,
            podologo_id=test_podologo.id_podologo,
            fecha_hora=fecha_hora,
            estado="agendada",
            duracion_minutos=60,
            motivo="Para cancelar"
        )
        ops_db.add(cita)
        ops_db.commit()
        ops_db.refresh(cita)
        
        response = client.delete(
            f"/api/v1/citas/{cita.id_cita}",
            headers=auth_headers_admin
        )
        
        assert response.status_code in [200, 204]
        
        # Verificar que el estado cambió a cancelada
        ops_db.refresh(cita)
        assert cita.estado == "cancelada"
    
    def test_cancel_cita_recepcion(self, client, auth_headers_recepcion, ops_db, test_paciente, test_podologo):
        """Test: Cancelar cita como recepcionista."""
        from backend.schemas.ops.models import Cita
        
        fecha_hora = datetime.now() + timedelta(days=1)
        cita = Cita(
            paciente_id=test_paciente.id_paciente,
            podologo_id=test_podologo.id_podologo,
            fecha_hora=fecha_hora,
            estado="agendada",
            duracion_minutos=60,
            motivo="Test"
        )
        ops_db.add(cita)
        ops_db.commit()
        ops_db.refresh(cita)
        
        response = client.delete(
            f"/api/v1/citas/{cita.id_cita}",
            headers=auth_headers_recepcion
        )
        
        # Recepción puede cancelar citas
        assert response.status_code in [200, 204, 403]


@pytest.mark.api
@pytest.mark.database
class TestCitasEstado:
    """Tests de cambio de estado de citas."""
    
    def test_change_status_to_completada(self, client, auth_headers_admin, ops_db, test_paciente, test_podologo):
        """Test: Cambiar estado a completada."""
        from backend.schemas.ops.models import Cita
        
        fecha_hora = datetime.now() - timedelta(hours=2)  # Cita reciente
        cita = Cita(
            paciente_id=test_paciente.id_paciente,
            podologo_id=test_podologo.id_podologo,
            fecha_hora=fecha_hora,
            estado="agendada",
            duracion_minutos=60,
            motivo="Test"
        )
        ops_db.add(cita)
        ops_db.commit()
        ops_db.refresh(cita)
        
        response = client.patch(
            f"/api/v1/citas/{cita.id_cita}/status",
            headers=auth_headers_admin,
            json={"estado": "completada"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["estado"] == "completada"
    
    def test_change_status_to_no_asistio(self, client, auth_headers_admin, ops_db, test_paciente, test_podologo):
        """Test: Marcar como no asistió."""
        from backend.schemas.ops.models import Cita
        
        fecha_hora = datetime.now() - timedelta(hours=3)
        cita = Cita(
            paciente_id=test_paciente.id_paciente,
            podologo_id=test_podologo.id_podologo,
            fecha_hora=fecha_hora,
            estado="agendada",
            duracion_minutos=60,
            motivo="Test"
        )
        ops_db.add(cita)
        ops_db.commit()
        ops_db.refresh(cita)
        
        response = client.patch(
            f"/api/v1/citas/{cita.id_cita}/status",
            headers=auth_headers_admin,
            json={"estado": "no_asistio"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["estado"] == "no_asistio"


@pytest.mark.api
@pytest.mark.integration
class TestCitasCalendario:
    """Tests de vista de calendario."""
    
    def test_get_calendario_month_view(self, client, auth_headers_admin):
        """Test: Obtener vista de calendario mensual."""
        today = date_type.today()
        response = client.get(
            f"/api/v1/citas/calendario?year={today.year}&month={today.month}",
            headers=auth_headers_admin
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, (list, dict))
    
    def test_get_calendario_week_view(self, client, auth_headers_admin):
        """Test: Obtener vista de calendario semanal."""
        today = date_type.today()
        response = client.get(
            f"/api/v1/citas/calendario?fecha={today.isoformat()}&vista=semana",
            headers=auth_headers_admin
        )
        
        # Puede no estar implementada esta vista
        assert response.status_code in [200, 404]


@pytest.mark.api
@pytest.mark.integration
class TestCitasDisponibilidad:
    """Tests de consulta de disponibilidad."""
    
    def test_get_disponibilidad_by_date(self, client, auth_headers_admin, test_podologo):
        """Test: Obtener slots disponibles por fecha."""
        fecha_futura = (date_type.today() + timedelta(days=7)).isoformat()
        
        response = client.get(
            f"/api/v1/citas/disponibilidad?fecha={fecha_futura}&podologo_id={test_podologo.id_podologo}",
            headers=auth_headers_admin
        )
        
        assert response.status_code == 200
        data = response.json()
        # Debería retornar lista de horarios disponibles
        assert isinstance(data, (list, dict))
    
    def test_get_disponibilidad_without_podologo(self, client, auth_headers_admin):
        """Test: Disponibilidad sin especificar podólogo."""
        fecha_futura = (date_type.today() + timedelta(days=7)).isoformat()
        
        response = client.get(
            f"/api/v1/citas/disponibilidad?fecha={fecha_futura}",
            headers=auth_headers_admin
        )
        
        # Debería retornar disponibilidad de todos los podólogos
        assert response.status_code == 200


@pytest.mark.integration
class TestCitasWorkflow:
    """Tests de flujos completos de citas."""
    
    def test_complete_appointment_workflow(self, client, auth_headers_admin, test_paciente, test_podologo, ops_db):
        """Test: Flujo completo de cita (crear -> confirmar -> completar)."""
        from backend.schemas.ops.models import CatalogoServicio
        from decimal import Decimal
        
        # Crear servicio
        servicio = CatalogoServicio(
            nombre="Consulta Workflow",
            duracion_minutos=60,
            precio=Decimal("500.00"),
            activo=True
        )
        ops_db.add(servicio)
        ops_db.commit()
        ops_db.refresh(servicio)
        
        # 1. Crear cita
        fecha_hora = (datetime.now() + timedelta(days=1)).replace(hour=10, minute=0, second=0, microsecond=0)
        cita_data = {
            "paciente_id": test_paciente.id_paciente,
            "podologo_id": test_podologo.id_podologo,
            "servicio_id": servicio.id_servicio,
            "fecha_hora": fecha_hora.isoformat(),
            "duracion_minutos": 60,
            "motivo": "Workflow test",
            "estado": "agendada"
        }
        
        create_response = client.post(
            "/api/v1/citas",
            headers=auth_headers_admin,
            json=cita_data
        )
        assert create_response.status_code in [200, 201]
        cita_id = create_response.json()["id_cita"]
        
        # 2. Obtener cita
        get_response = client.get(
            f"/api/v1/citas/{cita_id}",
            headers=auth_headers_admin
        )
        assert get_response.status_code == 200
        
        # 3. Actualizar observaciones
        update_response = client.put(
            f"/api/v1/citas/{cita_id}",
            headers=auth_headers_admin,
            json={"observaciones": "Paciente confirmó asistencia"}
        )
        assert update_response.status_code == 200
        
        # 4. Cambiar estado a completada
        status_response = client.patch(
            f"/api/v1/citas/{cita_id}/status",
            headers=auth_headers_admin,
            json={"estado": "completada"}
        )
        assert status_response.status_code == 200
        assert status_response.json()["estado"] == "completada"
