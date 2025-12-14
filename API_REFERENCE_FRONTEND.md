# 📚 API Reference - PodoSkin Backend

**Fecha:** 13 de Diciembre de 2024  
**Base URL:** `http://localhost:8000/api/v1`  
**Autenticación:** Bearer Token JWT (excepto `/auth/login`)

---

## 📖 Tabla de Contenidos

1. [Autenticación](#1-autenticación)
2. [Pacientes](#2-pacientes)
3. [Citas](#3-citas)
4. [Tratamientos](#4-tratamientos)
5. [Evoluciones Clínicas](#5-evoluciones-clínicas)
6. [Evidencias Fotográficas](#6-evidencias-fotográficas)
7. [Podólogos](#7-podólogos)
8. [Servicios](#8-servicios)
9. [Prospectos](#9-prospectos)
10. [Usuarios](#10-usuarios)
11. [Auditoría](#11-auditoría)
12. [Finanzas](#12-finanzas)
13. [Historial Detalles](#13-historial-detalles)
14. [Chat IA](#14-chat-ia)
15. [Estadísticas](#15-estadísticas)
16. [Notificaciones](#16-notificaciones)
17. [Integración](#17-integración)
18. [WebSocket](#18-websocket)

---

## 1. Autenticación

**Prefix:** `/auth`

### Endpoints

#### `POST /auth/login`
Iniciar sesión con username, email o ID estructurado.

**Request:**
```json
{
  "username": "admin",  // Puede ser username, email o ID estructurado
  "password": "Admin2024!"
}
```

**Response 200:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "user": {
    "id_usuario": 1,
    "nombre_usuario": "admin",
    "email": "admin@podoskin.local",
    "rol": "Admin",
    "clinica_id": 1,
    "has_gemini_key": false,
    "gemini_key_status": null
  }
}
```

#### `GET /auth/me`
Obtener perfil del usuario actual.

**Headers:** `Authorization: Bearer {token}`

**Response 200:**
```json
{
  "id_usuario": 1,
  "nombre_usuario": "admin",
  "rol": "Admin",
  "email": "admin@podoskin.local",
  "activo": true,
  "clinica_id": 1,
  "last_login": "2024-12-13T14:00:00Z"
}
```

#### `PUT /auth/change-password`
Cambiar contraseña del usuario actual.

**Request:**
```json
{
  "current_password": "Admin2024!",
  "new_password": "NewPassword123!"
}
```

**Response 200:**
```json
{
  "message": "Contraseña actualizada exitosamente",
  "success": true
}
```

### 🎯 Uso en Frontend

```typescript
// services/authService.ts
import axios from 'axios';

const API_URL = 'http://localhost:8000/api/v1';

export const authService = {
  // Login
  login: async (username: string, password: string) => {
    const response = await axios.post(`${API_URL}/auth/login`, {
      username,
      password
    });
    
    // Guardar token
    localStorage.setItem('token', response.data.access_token);
    localStorage.setItem('user', JSON.stringify(response.data.user));
    
    return response.data;
  },
  
  // Obtener perfil actual
  getMe: async () => {
    const token = localStorage.getItem('token');
    const response = await axios.get(`${API_URL}/auth/me`, {
      headers: { Authorization: `Bearer ${token}` }
    });
    return response.data;
  },
  
  // Cambiar contraseña
  changePassword: async (currentPassword: string, newPassword: string) => {
    const token = localStorage.getItem('token');
    const response = await axios.put(
      `${API_URL}/auth/change-password`,
      { current_password: currentPassword, new_password: newPassword },
      { headers: { Authorization: `Bearer ${token}` } }
    );
    return response.data;
  },
  
  // Logout
  logout: () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
  }
};
```

**Ejemplo de uso en componente:**
```typescript
// LoginForm.tsx
import { authService } from '@/services/authService';

const LoginForm = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  
  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const data = await authService.login(username, password);
      console.log('Login exitoso:', data.user);
      // Redirigir a dashboard
      navigate('/dashboard');
    } catch (error) {
      console.error('Error en login:', error);
    }
  };
  
  return (
    <form onSubmit={handleLogin}>
      {/* Form fields */}
    </form>
  );
};
```

---

## 2. Pacientes

**Prefix:** `/pacientes`  
**Permisos:** Admin, Podologo, Recepcion

### Endpoints

#### `GET /pacientes`
Listar pacientes con paginación.

**Query Params:**
- `skip` (number, default: 0)
- `limit` (number, default: 20)
- `search` (string, opcional)

**Response 200:**
```json
{
  "total": 150,
  "skip": 0,
  "limit": 20,
  "pacientes": [
    {
      "id_paciente": 1,
      "nombres": "María",
      "apellidos": "García López",
      "fecha_nacimiento": "1985-05-15",
      "telefono": "5551234567",
      "email": "maria@email.com",
      "sexo": "F",
      "created_at": "2024-01-15T10:00:00Z"
    }
  ]
}
```

#### `GET /pacientes/buscar`
Buscar pacientes por nombre, apellido o teléfono.

**Query Params:**
- `q` (string, requerido): Término de búsqueda
- `limit` (number, default: 10)

**Response 200:**
```json
[
  {
    "id_paciente": 1,
    "nombres": "María",
    "apellidos": "García",
    "telefono": "5551234567",
    "email": "maria@email.com"
  }
]
```

#### `GET /pacientes/{paciente_id}`
Obtener detalles de un paciente.

**Response 200:**
```json
{
  "id_paciente": 1,
  "nombres": "María",
  "apellidos": "García López",
  "fecha_nacimiento": "1985-05-15",
  "edad": 39,
  "telefono": "5551234567",
  "email": "maria@email.com",
  "sexo": "F",
  "domicilio": "Calle Principal 123",
  "peso_kg": 65.5,
  "estatura_cm": 165,
  "imc": 24.0,
  "tipo_sangre": "O+",
  "curp": "GAML850515MDFRRR03",
  "created_at": "2024-01-15T10:00:00Z"
}
```

#### `POST /pacientes`
Crear nuevo paciente.

**Request:**
```json
{
  "nombres": "Juan",
  "apellidos": "Pérez López",
  "fecha_nacimiento": "1990-03-20",
  "telefono": "5559876543",
  "email": "juan@email.com",
  "sexo": "M",
  "domicilio": "Av. Revolución 456",
  "peso_kg": 75.0,
  "estatura_cm": 175,
  "tipo_sangre": "A+"
}
```

**Response 201:**
```json
{
  "id_paciente": 2,
  "nombres": "Juan",
  "apellidos": "Pérez López",
  "codigo_interno": "EZJU-1213-00003",
  "created_at": "2024-12-13T14:00:00Z"
}
```

#### `PUT /pacientes/{paciente_id}`
Actualizar datos de paciente.

**Request:**
```json
{
  "telefono": "5559999999",
  "email": "nuevo@email.com",
  "peso_kg": 76.5
}
```

**Response 200:**
```json
{
  "id_paciente": 2,
  "nombres": "Juan",
  "apellidos": "Pérez López",
  "telefono": "5559999999",
  "email": "nuevo@email.com",
  "peso_kg": 76.5
}
```

#### `DELETE /pacientes/{paciente_id}`
Eliminar paciente (soft delete).

**Response 204:** No Content

#### `GET /pacientes/{paciente_id}/expediente/print`
Generar expediente imprimible (HTML).

**Permisos:** Admin, Podologo

**Response 200:**
```html
<!DOCTYPE html>
<html>
  <!-- HTML formateado del expediente -->
</html>
```

#### `GET /pacientes/{paciente_id}/exportar`
Exportar expediente en formato JSON o XML.

**Query Params:**
- `format` (string): "json" o "xml"

**Response 200:**
```json
{
  "paciente": {...},
  "tratamientos": [...],
  "evoluciones": [...],
  "evidencias": [...]
}
```

### 🎯 Uso en Frontend

```typescript
// services/pacientesService.ts
import axios from 'axios';

const API_URL = 'http://localhost:8000/api/v1';

const getAuthHeader = () => ({
  headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
});

export const pacientesService = {
  // Listar pacientes
  list: async (skip = 0, limit = 20, search = '') => {
    const params = new URLSearchParams({ 
      skip: skip.toString(), 
      limit: limit.toString() 
    });
    if (search) params.append('search', search);
    
    const response = await axios.get(
      `${API_URL}/pacientes?${params}`,
      getAuthHeader()
    );
    return response.data;
  },
  
  // Buscar pacientes
  search: async (query: string, limit = 10) => {
    const response = await axios.get(
      `${API_URL}/pacientes/buscar?q=${encodeURIComponent(query)}&limit=${limit}`,
      getAuthHeader()
    );
    return response.data;
  },
  
  // Obtener un paciente
  get: async (id: number) => {
    const response = await axios.get(
      `${API_URL}/pacientes/${id}`,
      getAuthHeader()
    );
    return response.data;
  },
  
  // Crear paciente
  create: async (data: PacienteCreate) => {
    const response = await axios.post(
      `${API_URL}/pacientes`,
      data,
      getAuthHeader()
    );
    return response.data;
  },
  
  // Actualizar paciente
  update: async (id: number, data: PacienteUpdate) => {
    const response = await axios.put(
      `${API_URL}/pacientes/${id}`,
      data,
      getAuthHeader()
    );
    return response.data;
  },
  
  // Eliminar paciente
  delete: async (id: number) => {
    await axios.delete(
      `${API_URL}/pacientes/${id}`,
      getAuthHeader()
    );
  },
  
  // Exportar expediente
  exportExpediente: async (id: number, format: 'json' | 'xml' = 'json') => {
    const response = await axios.get(
      `${API_URL}/pacientes/${id}/exportar?format=${format}`,
      getAuthHeader()
    );
    return response.data;
  },
  
  // Imprimir expediente (abre en nueva ventana)
  printExpediente: (id: number) => {
    const token = localStorage.getItem('token');
    const url = `${API_URL}/pacientes/${id}/expediente/print`;
    window.open(`${url}?token=${token}`, '_blank');
  }
};
```

**Ejemplo de uso en componente:**
```typescript
// PacientesListView.tsx
import { pacientesService } from '@/services/pacientesService';

const PacientesListView = () => {
  const [pacientes, setPacientes] = useState([]);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(0);
  const [total, setTotal] = useState(0);
  
  useEffect(() => {
    loadPacientes();
  }, [page]);
  
  const loadPacientes = async () => {
    setLoading(true);
    try {
      const data = await pacientesService.list(page * 20, 20);
      setPacientes(data.pacientes);
      setTotal(data.total);
    } catch (error) {
      console.error('Error cargando pacientes:', error);
    } finally {
      setLoading(false);
    }
  };
  
  const handleSearch = async (query: string) => {
    if (!query) {
      loadPacientes();
      return;
    }
    
    try {
      const results = await pacientesService.search(query);
      setPacientes(results);
    } catch (error) {
      console.error('Error buscando pacientes:', error);
    }
  };
  
  return (
    <div>
      <SearchInput onSearch={handleSearch} />
      <PacientesList data={pacientes} loading={loading} />
      <Pagination page={page} total={total} onChange={setPage} />
    </div>
  );
};
```

---

## 3. Citas

**Prefix:** `/citas`  
**Permisos:** Admin, Podologo, Recepcion

### Endpoints

#### `GET /citas`
Listar citas.

**Query Params:**
- `fecha_inicio` (date, opcional): Filtrar desde fecha
- `fecha_fin` (date, opcional): Filtrar hasta fecha
- `paciente_id` (number, opcional)
- `podologo_id` (number, opcional)
- `status` (string, opcional): "Programada", "Confirmada", "En Curso", "Completada", "Cancelada"

**Response 200:**
```json
[
  {
    "id_cita": 1,
    "paciente_id": 5,
    "podologo_id": 2,
    "fecha_cita": "2024-12-15",
    "hora_inicio": "10:00:00",
    "hora_fin": "10:30:00",
    "status": "Programada",
    "motivo": "Revisión general",
    "notas": ""
  }
]
```

#### `GET /citas/agenda/{fecha}`
Obtener agenda del día.

**Response 200:**
```json
[
  {
    "id_cita": 1,
    "hora_inicio": "10:00",
    "hora_fin": "10:30",
    "paciente_nombre": "María García",
    "podologo_nombre": "Dr. Ornelas",
    "status": "Confirmada",
    "motivo": "Revisión general"
  }
]
```

#### `GET /citas/disponibilidad`
Consultar horarios disponibles.

**Query Params:**
- `fecha` (date, requerido)
- `podologo_id` (number, requerido)
- `duracion_minutos` (number, default: 30)

**Response 200:**
```json
{
  "fecha": "2024-12-15",
  "podologo_id": 2,
  "horarios_disponibles": [
    "09:00",
    "09:30",
    "11:00",
    "14:00",
    "15:30"
  ]
}
```

#### `GET /citas/{cita_id}`
Obtener detalles de una cita.

**Response 200:**
```json
{
  "id_cita": 1,
  "paciente": {
    "id_paciente": 5,
    "nombres": "María",
    "apellidos": "García"
  },
  "podologo": {
    "id_podologo": 2,
    "nombres": "Santiago",
    "apellidos": "Ornelas"
  },
  "fecha_cita": "2024-12-15",
  "hora_inicio": "10:00:00",
  "hora_fin": "10:30:00",
  "status": "Programada",
  "motivo": "Revisión general",
  "notas": ""
}
```

#### `POST /citas`
Crear nueva cita.

**Request:**
```json
{
  "paciente_id": 5,
  "podologo_id": 2,
  "fecha_cita": "2024-12-15",
  "hora_inicio": "10:00:00",
  "hora_fin": "10:30:00",
  "motivo": "Revisión general",
  "notas": "Primera visita"
}
```

**Response 201:**
```json
{
  "id_cita": 1,
  "paciente_id": 5,
  "podologo_id": 2,
  "fecha_cita": "2024-12-15",
  "hora_inicio": "10:00:00",
  "status": "Programada",
  "created_at": "2024-12-13T14:00:00Z"
}
```

#### `PUT /citas/{cita_id}`
Actualizar cita completa.

**Request:**
```json
{
  "fecha_cita": "2024-12-16",
  "hora_inicio": "11:00:00",
  "hora_fin": "11:30:00",
  "motivo": "Control de tratamiento"
}
```

**Response 200:**
```json
{
  "id_cita": 1,
  "fecha_cita": "2024-12-16",
  "hora_inicio": "11:00:00",
  "updated_at": "2024-12-13T14:05:00Z"
}
```

#### `PATCH /citas/{cita_id}/status`
Cambiar solo el status de una cita.

**Request:**
```json
{
  "status": "Confirmada"
}
```

**Response 200:**
```json
{
  "id_cita": 1,
  "status": "Confirmada",
  "updated_at": "2024-12-13T14:10:00Z"
}
```

#### `DELETE /citas/{cita_id}`
Cancelar cita (soft delete).

**Response 204:** No Content

### 🎯 Uso en Frontend

```typescript
// services/citasService.ts
import axios from 'axios';
import { format } from 'date-fns';

const API_URL = 'http://localhost:8000/api/v1';

const getAuthHeader = () => ({
  headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
});

export const citasService = {
  // Listar citas
  list: async (filters?: CitasFilters) => {
    const params = new URLSearchParams();
    if (filters?.fecha_inicio) params.append('fecha_inicio', filters.fecha_inicio);
    if (filters?.fecha_fin) params.append('fecha_fin', filters.fecha_fin);
    if (filters?.paciente_id) params.append('paciente_id', filters.paciente_id.toString());
    if (filters?.status) params.append('status', filters.status);
    
    const response = await axios.get(
      `${API_URL}/citas?${params}`,
      getAuthHeader()
    );
    return response.data;
  },
  
  // Obtener agenda del día
  getAgenda: async (fecha: Date) => {
    const fechaStr = format(fecha, 'yyyy-MM-dd');
    const response = await axios.get(
      `${API_URL}/citas/agenda/${fechaStr}`,
      getAuthHeader()
    );
    return response.data;
  },
  
  // Consultar disponibilidad
  getDisponibilidad: async (fecha: Date, podologoId: number, duracion = 30) => {
    const fechaStr = format(fecha, 'yyyy-MM-dd');
    const response = await axios.get(
      `${API_URL}/citas/disponibilidad?fecha=${fechaStr}&podologo_id=${podologoId}&duracion_minutos=${duracion}`,
      getAuthHeader()
    );
    return response.data;
  },
  
  // Obtener una cita
  get: async (id: number) => {
    const response = await axios.get(
      `${API_URL}/citas/${id}`,
      getAuthHeader()
    );
    return response.data;
  },
  
  // Crear cita
  create: async (data: CitaCreate) => {
    const response = await axios.post(
      `${API_URL}/citas`,
      data,
      getAuthHeader()
    );
    return response.data;
  },
  
  // Actualizar cita
  update: async (id: number, data: CitaUpdate) => {
    const response = await axios.put(
      `${API_URL}/citas/${id}`,
      data,
      getAuthHeader()
    );
    return response.data;
  },
  
  // Cambiar status
  updateStatus: async (id: number, status: string) => {
    const response = await axios.patch(
      `${API_URL}/citas/${id}/status`,
      { status },
      getAuthHeader()
    );
    return response.data;
  },
  
  // Cancelar cita
  cancel: async (id: number) => {
    await axios.delete(
      `${API_URL}/citas/${id}`,
      getAuthHeader()
    );
  }
};
```

**Ejemplo de uso en componente:**
```typescript
// AgendaView.tsx
import { citasService } from '@/services/citasService';
import { startOfDay, addDays } from 'date-fns';

const AgendaView = () => {
  const [fecha, setFecha] = useState(new Date());
  const [citas, setCitas] = useState([]);
  const [loading, setLoading] = useState(false);
  
  useEffect(() => {
    loadAgenda();
  }, [fecha]);
  
  const loadAgenda = async () => {
    setLoading(true);
    try {
      const data = await citasService.getAgenda(fecha);
      setCitas(data);
    } catch (error) {
      console.error('Error cargando agenda:', error);
    } finally {
      setLoading(false);
    }
  };
  
  const handleStatusChange = async (citaId: number, newStatus: string) => {
    try {
      await citasService.updateStatus(citaId, newStatus);
      toast.success('Status actualizado');
      loadAgenda(); // Recargar
    } catch (error) {
      toast.error('Error actualizando status');
    }
  };
  
  return (
    <div>
      <DatePicker value={fecha} onChange={setFecha} />
      <AgendaList 
        citas={citas} 
        loading={loading}
        onStatusChange={handleStatusChange}
      />
    </div>
  );
};
```

---

## 4. Tratamientos

**Prefix:** `/tratamientos`  
**Permisos:** Admin, Podologo

### Endpoints

#### `GET /tratamientos`
Listar tratamientos (carpetas de problemas).

**Query Params:**
- `paciente_id` (number, opcional)
- `estado` (string, opcional): "Activo", "En Curso", "Completado", "Suspendido"

**Response 200:**
```json
[
  {
    "id_tratamiento": 1,
    "paciente_id": 5,
    "problema": "Uña encarnada pie derecho",
    "diagnostico": "Onicocriptosis",
    "fecha_inicio": "2024-11-01",
    "fecha_fin": null,
    "estado_tratamiento": "En Curso",
    "created_at": "2024-11-01T10:00:00Z"
  }
]
```

#### `GET /tratamientos/{tratamiento_id}`
Obtener detalles de un tratamiento con sus evoluciones.

**Response 200:**
```json
{
  "id_tratamiento": 1,
  "paciente": {
    "id_paciente": 5,
    "nombres": "María",
    "apellidos": "García"
  },
  "problema": "Uña encarnada pie derecho",
  "diagnostico": "Onicocriptosis",
  "fecha_inicio": "2024-11-01",
  "fecha_fin": null,
  "estado_tratamiento": "En Curso",
  "evoluciones": [
    {
      "id_evolucion": 10,
      "fecha_evolucion": "2024-11-01",
      "nota_soap": "S: Dolor en dedo gordo...",
      "podologo_nombre": "Dr. Ornelas"
    }
  ]
}
```

#### `POST /tratamientos`
Crear nuevo tratamiento.

**Request:**
```json
{
  "paciente_id": 5,
  "problema": "Uña encarnada pie derecho",
  "diagnostico": "Onicocriptosis",
  "plan_tratamiento": "Aplicar técnica de curetaje...",
  "fecha_inicio": "2024-12-13"
}
```

**Response 201:**
```json
{
  "id_tratamiento": 2,
  "paciente_id": 5,
  "problema": "Uña encarnada pie derecho",
  "estado_tratamiento": "Activo",
  "created_at": "2024-12-13T14:00:00Z"
}
```

#### `PUT /tratamientos/{tratamiento_id}`
Actualizar tratamiento.

**Request:**
```json
{
  "diagnostico": "Onicocriptosis grado II",
  "plan_tratamiento": "Plan actualizado..."
}
```

**Response 200:**
```json
{
  "id_tratamiento": 2,
  "diagnostico": "Onicocriptosis grado II",
  "updated_at": "2024-12-13T14:05:00Z"
}
```

#### `PATCH /tratamientos/{tratamiento_id}/status`
Cambiar estado del tratamiento.

**Request:**
```json
{
  "estado": "Completado",
  "fecha_fin": "2024-12-13"
}
```

**Response 200:**
```json
{
  "id_tratamiento": 2,
  "estado_tratamiento": "Completado",
  "fecha_fin": "2024-12-13"
}
```

#### `DELETE /tratamientos/{tratamiento_id}`
Eliminar tratamiento (soft delete).

**Response 204:** No Content

### 🎯 Uso en Frontend

```typescript
// services/tratamientosService.ts
import axios from 'axios';

const API_URL = 'http://localhost:8000/api/v1';

const getAuthHeader = () => ({
  headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
});

export const tratamientosService = {
  // Listar tratamientos
  list: async (pacienteId?: number, estado?: string) => {
    const params = new URLSearchParams();
    if (pacienteId) params.append('paciente_id', pacienteId.toString());
    if (estado) params.append('estado', estado);
    
    const response = await axios.get(
      `${API_URL}/tratamientos?${params}`,
      getAuthHeader()
    );
    return response.data;
  },
  
  // Obtener tratamiento con evoluciones
  get: async (id: number) => {
    const response = await axios.get(
      `${API_URL}/tratamientos/${id}`,
      getAuthHeader()
    );
    return response.data;
  },
  
  // Crear tratamiento
  create: async (data: TratamientoCreate) => {
    const response = await axios.post(
      `${API_URL}/tratamientos`,
      data,
      getAuthHeader()
    );
    return response.data;
  },
  
  // Actualizar tratamiento
  update: async (id: number, data: TratamientoUpdate) => {
    const response = await axios.put(
      `${API_URL}/tratamientos/${id}`,
      data,
      getAuthHeader()
    );
    return response.data;
  },
  
  // Cambiar estado
  updateStatus: async (id: number, estado: string, fechaFin?: string) => {
    const response = await axios.patch(
      `${API_URL}/tratamientos/${id}/status`,
      { estado, fecha_fin: fechaFin },
      getAuthHeader()
    );
    return response.data;
  },
  
  // Eliminar tratamiento
  delete: async (id: number) => {
    await axios.delete(
      `${API_URL}/tratamientos/${id}`,
      getAuthHeader()
    );
  }
};
```

**Ejemplo de uso:**
```typescript
// TratamientosView.tsx
const TratamientosView = ({ pacienteId }: { pacienteId: number }) => {
  const [tratamientos, setTratamientos] = useState([]);
  
  useEffect(() => {
    loadTratamientos();
  }, [pacienteId]);
  
  const loadTratamientos = async () => {
    try {
      const data = await tratamientosService.list(pacienteId);
      setTratamientos(data);
    } catch (error) {
      console.error('Error:', error);
    }
  };
  
  const handleComplete = async (id: number) => {
    try {
      await tratamientosService.updateStatus(
        id, 
        'Completado', 
        format(new Date(), 'yyyy-MM-dd')
      );
      toast.success('Tratamiento completado');
      loadTratamientos();
    } catch (error) {
      toast.error('Error');
    }
  };
  
  return <TratamientosList data={tratamientos} onComplete={handleComplete} />;
};
```

---

## 5. Evoluciones Clínicas

**Prefix:** `/evoluciones`  
**Permisos:** Admin, Podologo

### Endpoints

#### `GET /evoluciones`
Listar evoluciones (notas SOAP).

**Query Params:**
- `tratamiento_id` (number, opcional)
- `paciente_id` (number, opcional)
- `podologo_id` (number, opcional)

**Response 200:**
```json
[
  {
    "id_evolucion": 1,
    "tratamiento_id": 5,
    "podologo_id": 2,
    "fecha_evolucion": "2024-12-13",
    "nota_soap": "S: Dolor leve\nO: Inflamación reducida\nA: Mejoría evidente\nP: Continuar tratamiento",
    "created_at": "2024-12-13T14:00:00Z"
  }
]
```

#### `GET /evoluciones/{evolucion_id}`
Obtener detalles de una evolución.

**Response 200:**
```json
{
  "id_evolucion": 1,
  "tratamiento": {
    "id_tratamiento": 5,
    "problema": "Uña encarnada"
  },
  "podologo": {
    "id_podologo": 2,
    "nombres": "Santiago",
    "apellidos": "Ornelas"
  },
  "fecha_evolucion": "2024-12-13",
  "nota_soap": "S: Dolor leve\nO: Inflamación reducida...",
  "diagnostico_cie10": "L60.0",
  "procedimiento": "Curetaje",
  "created_at": "2024-12-13T14:00:00Z"
}
```

#### `POST /evoluciones`
Crear nueva evolución clínica.

**Request:**
```json
{
  "tratamiento_id": 5,
  "podologo_id": 2,
  "fecha_evolucion": "2024-12-13",
  "nota_soap": "S: Paciente refiere dolor moderado\nO: Inflamación visible en dedo gordo\nA: Onicocriptosis en fase aguda\nP: Aplicar tratamiento conservador",
  "diagnostico_cie10": "L60.0",
  "procedimiento": "Curetaje ungueal"
}
```

**Response 201:**
```json
{
  "id_evolucion": 2,
  "tratamiento_id": 5,
  "fecha_evolucion": "2024-12-13",
  "created_at": "2024-12-13T14:00:00Z"
}
```

#### `PUT /evoluciones/{evolucion_id}`
Actualizar evolución.

**Request:**
```json
{
  "nota_soap": "S: Dolor leve actualizado...",
  "diagnostico_cie10": "L60.1"
}
```

**Response 200:**
```json
{
  "id_evolucion": 2,
  "nota_soap": "S: Dolor leve actualizado...",
  "updated_at": "2024-12-13T14:05:00Z"
}
```

#### `DELETE /evoluciones/{evolucion_id}`
Eliminar evolución (soft delete).

**Response 204:** No Content

### 🎯 Uso en Frontend

```typescript
// services/evolucionesService.ts
import axios from 'axios';

const API_URL = 'http://localhost:8000/api/v1';

const getAuthHeader = () => ({
  headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
});

export const evolucionesService = {
  // Listar evoluciones
  list: async (tratamientoId?: number) => {
    const params = tratamientoId 
      ? `?tratamiento_id=${tratamientoId}` 
      : '';
    
    const response = await axios.get(
      `${API_URL}/evoluciones${params}`,
      getAuthHeader()
    );
    return response.data;
  },
  
  // Obtener evolución
  get: async (id: number) => {
    const response = await axios.get(
      `${API_URL}/evoluciones/${id}`,
      getAuthHeader()
    );
    return response.data;
  },
  
  // Crear evolución
  create: async (data: EvolucionCreate) => {
    const response = await axios.post(
      `${API_URL}/evoluciones`,
      data,
      getAuthHeader()
    );
    return response.data;
  },
  
  // Actualizar evolución
  update: async (id: number, data: EvolucionUpdate) => {
    const response = await axios.put(
      `${API_URL}/evoluciones/${id}`,
      data,
      getAuthHeader()
    );
    return response.data;
  },
  
  // Eliminar evolución
  delete: async (id: number) => {
    await axios.delete(
      `${API_URL}/evoluciones/${id}`,
      getAuthHeader()
    );
  }
};
```

**Ejemplo de uso:**
```typescript
// EvolucionForm.tsx
const EvolucionForm = ({ tratamientoId }: { tratamientoId: number }) => {
  const [soap, setSoap] = useState({
    subjetivo: '',
    objetivo: '',
    analisis: '',
    plan: ''
  });
  
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    const notaSOAP = `S: ${soap.subjetivo}\nO: ${soap.objetivo}\nA: ${soap.analisis}\nP: ${soap.plan}`;
    
    try {
      await evolucionesService.create({
        tratamiento_id: tratamientoId,
        podologo_id: currentUser.id_usuario,
        fecha_evolucion: format(new Date(), 'yyyy-MM-dd'),
        nota_soap: notaSOAP
      });
      
      toast.success('Evolución registrada');
      onSuccess();
    } catch (error) {
      toast.error('Error al registrar evolución');
    }
  };
  
  return (
    <form onSubmit={handleSubmit}>
      <textarea 
        placeholder="Subjetivo: ¿Qué dice el paciente?"
        value={soap.subjetivo}
        onChange={(e) => setSoap({...soap, subjetivo: e.target.value})}
      />
      <textarea 
        placeholder="Objetivo: ¿Qué observas?"
        value={soap.objetivo}
        onChange={(e) => setSoap({...soap, objetivo: e.target.value})}
      />
      {/* Más campos */}
      <button type="submit">Guardar Evolución</button>
    </form>
  );
};
```

---

*Continuará en la siguiente parte debido a la longitud...*

¿Quiero que continúe con los módulos restantes (Evidencias, Podólogos, Servicios, Prospectos, Usuarios, Auditoría, Finanzas, Chat IA, Estadísticas, Notificaciones, Integración y WebSocket)?
