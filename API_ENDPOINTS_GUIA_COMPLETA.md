# 📚 API Reference Completa - PodoSkin Backend

**Fecha:** 13 de Diciembre de 2024  
**Base URL:** `http://localhost:8000/api/v1`  
**Autenticación:** Bearer Token JWT (excepto `/auth/login`)

---

## 📖 Índice Rápido

| Módulo | Endpoints | Permisos | Descripción |
|--------|-----------|----------|-------------|
| [Autenticación](#autenticación) | 3 | Público/Auth | Login, perfil, cambio de contraseña |
| [Pacientes](#pacientes) | 8 | Admin, Podologo, Recepcion | Gestión de expedientes |
| [Citas](#citas) | 8 | Admin, Podologo, Recepcion | Agenda y programación |
| [Tratamientos](#tratamientos) | 6 | Admin, Podologo | Carpetas de problemas |
| [Evoluciones](#evoluciones) | 5 | Admin, Podologo | Notas SOAP clínicas |
| [Evidencias](#evidencias) | 8 | Admin, Podologo | Fotos clínicas |
| [Podólogos](#podólogos) | 5 | Admin | Personal clínico |
| [Servicios](#servicios) | 5 | Admin, Podologo | Catálogo de servicios |
| [Prospectos](#prospectos) | 5 | Admin, Recepcion | Leads/contactos |
| [Usuarios](#usuarios) | 8 | Admin | Gestión de usuarios |
| [Auditoría](#auditoría) | 3 | Admin, Podologo | Logs de cambios |
| [Finanzas](#finanzas) | 7 | Admin | Pagos y transacciones |
| [Historial](#historial) | 16 | Admin, Podologo | Alergias, suplementos, etc |
| [Chat IA](#chat-ia) | 5 | Todos | Chatbot inteligente |
| [Estadísticas](#estadísticas) | 2 | Admin, Podologo | Dashboard y reportes |
| [Notificaciones](#notificaciones) | 3 | Admin, Recepcion | Recordatorios de citas |
| [Integración](#integración) | 3 | Todos | Contexto de usuario y transcripts |
| [WebSocket](#websocket) | 1 | Todos | Streaming en tiempo real |

**Total:** 101 endpoints

---

## Autenticación

**Base:** `/auth`

### Endpoints

| Método | Ruta | Descripción | Permisos |
|--------|------|-------------|----------|
| POST | `/login` | Iniciar sesión (username/email/ID) | Público |
| GET | `/me` | Obtener perfil actual | Auth |
| PUT | `/change-password` | Cambiar contraseña | Auth |

### 🎯 Frontend Service

```typescript
// services/authService.ts
export const authService = {
  login: async (username: string, password: string) => {
    const { data } = await axios.post('/auth/login', { username, password });
    localStorage.setItem('token', data.access_token);
    localStorage.setItem('user', JSON.stringify(data.user));
    return data;
  },
  
  getMe: async () => {
    const { data } = await axios.get('/auth/me', {
      headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
    });
    return data;
  },
  
  changePassword: async (currentPassword: string, newPassword: string) => {
    const { data } = await axios.put('/auth/change-password', {
      current_password: currentPassword,
      new_password: newPassword
    }, {
      headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
    });
    return data;
  },
  
  logout: () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
  }
};

// Uso en componente
const handleLogin = async () => {
  try {
    await authService.login(username, password);
    navigate('/dashboard');
  } catch (error) {
    console.error('Error:', error);
  }
};
```

---

## Pacientes

**Base:** `/pacientes`  
**Permisos:** Admin, Podologo, Recepcion

### Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/` | Listar pacientes (paginado) |
| GET | `/buscar?q={query}` | Buscar por nombre/teléfono |
| GET | `/{id}` | Obtener detalles de paciente |
| POST | `/` | Crear nuevo paciente |
| PUT | `/{id}` | Actualizar paciente |
| DELETE | `/{id}` | Eliminar (soft delete) |
| DELETE | `/{id}/purge` | Eliminar permanentemente (Admin) |
| GET | `/{id}/expediente/print` | Expediente HTML imprimible |
| GET | `/{id}/exportar?format=json` | Exportar expediente |

### 🎯 Frontend Service

```typescript
// services/pacientesService.ts
const getHeaders = () => ({
  headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
});

export const pacientesService = {
  list: async (skip = 0, limit = 20, search = '') => {
    const params = new URLSearchParams({ 
      skip: skip.toString(), 
      limit: limit.toString() 
    });
    if (search) params.append('search', search);
    
    const { data } = await axios.get(
      `/pacientes?${params}`, 
      getHeaders()
    );
    return data;
  },
  
  search: async (query: string) => {
    const { data } = await axios.get(
      `/pacientes/buscar?q=${encodeURIComponent(query)}`,
      getHeaders()
    );
    return data;
  },
  
  get: async (id: number) => {
    const { data } = await axios.get(`/pacientes/${id}`, getHeaders());
    return data;
  },
  
  create: async (paciente: PacienteCreate) => {
    const { data } = await axios.post('/pacientes', paciente, getHeaders());
    return data;
  },
  
  update: async (id: number, paciente: PacienteUpdate) => {
    const { data } = await axios.put(`/pacientes/${id}`, paciente, getHeaders());
    return data;
  },
  
  delete: async (id: number) => {
    await axios.delete(`/pacientes/${id}`, getHeaders());
  },
  
  exportExpediente: async (id: number, format: 'json' | 'xml' = 'json') => {
    const { data } = await axios.get(
      `/pacientes/${id}/exportar?format=${format}`,
      getHeaders()
    );
    return data;
  },
  
  printExpediente: (id: number) => {
    const token = localStorage.getItem('token');
    window.open(
      `/pacientes/${id}/expediente/print?token=${token}`, 
      '_blank'
    );
  }
};

// Uso en componente
const PacientesList = () => {
  const [pacientes, setPacientes] = useState([]);
  const [page, setPage] = useState(0);
  
  useEffect(() => {
    loadPacientes();
  }, [page]);
  
  const loadPacientes = async () => {
    const data = await pacientesService.list(page * 20, 20);
    setPacientes(data.pacientes);
  };
  
  return <Table data={pacientes} />;
};
```

---

## Citas

**Base:** `/citas`  
**Permisos:** Admin, Podologo, Recepcion

### Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/` | Listar citas (con filtros) |
| GET | `/agenda/{fecha}` | Agenda del día |
| GET | `/disponibilidad` | Horarios disponibles |
| GET | `/{id}` | Detalles de cita |
| POST | `/` | Crear cita |
| PUT | `/{id}` | Actualizar cita completa |
| PATCH | `/{id}/status` | Cambiar solo status |
| DELETE | `/{id}` | Cancelar cita |

### 🎯 Frontend Service

```typescript
// services/citasService.ts
import { format } from 'date-fns';

export const citasService = {
  list: async (filters?: {
    fecha_inicio?: string;
    fecha_fin?: string;
    paciente_id?: number;
    status?: string;
  }) => {
    const params = new URLSearchParams();
    if (filters?.fecha_inicio) params.append('fecha_inicio', filters.fecha_inicio);
    if (filters?.fecha_fin) params.append('fecha_fin', filters.fecha_fin);
    if (filters?.paciente_id) params.append('paciente_id', filters.paciente_id.toString());
    if (filters?.status) params.append('status', filters.status);
    
    const { data } = await axios.get(`/citas?${params}`, getHeaders());
    return data;
  },
  
  getAgenda: async (fecha: Date) => {
    const fechaStr = format(fecha, 'yyyy-MM-dd');
    const { data } = await axios.get(`/citas/agenda/${fechaStr}`, getHeaders());
    return data;
  },
  
  getDisponibilidad: async (fecha: Date, podologoId: number, duracion = 30) => {
    const fechaStr = format(fecha, 'yyyy-MM-dd');
    const { data } = await axios.get(
      `/citas/disponibilidad?fecha=${fechaStr}&podologo_id=${podologoId}&duracion_minutos=${duracion}`,
      getHeaders()
    );
    return data;
  },
  
  get: async (id: number) => {
    const { data } = await axios.get(`/citas/${id}`, getHeaders());
    return data;
  },
  
  create: async (cita: CitaCreate) => {
    const { data } = await axios.post('/citas', cita, getHeaders());
    return data;
  },
  
  update: async (id: number, cita: CitaUpdate) => {
    const { data } = await axios.put(`/citas/${id}`, cita, getHeaders());
    return data;
  },
  
  updateStatus: async (id: number, status: string) => {
    const { data } = await axios.patch(`/citas/${id}/status`, { status }, getHeaders());
    return data;
  },
  
  cancel: async (id: number) => {
    await axios.delete(`/citas/${id}`, getHeaders());
  }
};

// Uso en componente
const AgendaView = () => {
  const [fecha, setFecha] = useState(new Date());
  const [citas, setCitas] = useState([]);
  
  useEffect(() => {
    loadAgenda();
  }, [fecha]);
  
  const loadAgenda = async () => {
    const data = await citasService.getAgenda(fecha);
    setCitas(data);
  };
  
  const handleStatusChange = async (citaId: number, newStatus: string) => {
    await citasService.updateStatus(citaId, newStatus);
    loadAgenda();
  };
  
  return (
    <div>
      <DatePicker value={fecha} onChange={setFecha} />
      <CitasList citas={citas} onStatusChange={handleStatusChange} />
    </div>
  );
};
```

---

## Tratamientos

**Base:** `/tratamientos`  
**Permisos:** Admin, Podologo

### Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/` | Listar tratamientos |
| GET | `/{id}` | Detalles con evoluciones |
| POST | `/` | Crear tratamiento |
| PUT | `/{id}` | Actualizar tratamiento |
| PATCH | `/{id}/status` | Cambiar estado |
| DELETE | `/{id}` | Eliminar tratamiento |

### 🎯 Frontend Service

```typescript
// services/tratamientosService.ts
export const tratamientosService = {
  list: async (pacienteId?: number, estado?: string) => {
    const params = new URLSearchParams();
    if (pacienteId) params.append('paciente_id', pacienteId.toString());
    if (estado) params.append('estado', estado);
    
    const { data } = await axios.get(`/tratamientos?${params}`, getHeaders());
    return data;
  },
  
  get: async (id: number) => {
    const { data } = await axios.get(`/tratamientos/${id}`, getHeaders());
    return data;
  },
  
  create: async (tratamiento: TratamientoCreate) => {
    const { data } = await axios.post('/tratamientos', tratamiento, getHeaders());
    return data;
  },
  
  update: async (id: number, tratamiento: TratamientoUpdate) => {
    const { data } = await axios.put(`/tratamientos/${id}`, tratamiento, getHeaders());
    return data;
  },
  
  updateStatus: async (id: number, estado: string, fechaFin?: string) => {
    const { data } = await axios.patch(
      `/tratamientos/${id}/status`,
      { estado, fecha_fin: fechaFin },
      getHeaders()
    );
    return data;
  },
  
  delete: async (id: number) => {
    await axios.delete(`/tratamientos/${id}`, getHeaders());
  }
};

// Uso
const handleComplete = async (tratamientoId: number) => {
  await tratamientosService.updateStatus(
    tratamientoId,
    'Completado',
    format(new Date(), 'yyyy-MM-dd')
  );
};
```

---

## Evoluciones

**Base:** `/evoluciones`  
**Permisos:** Admin, Podologo

### Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/` | Listar evoluciones (notas SOAP) |
| GET | `/{id}` | Detalles de evolución |
| POST | `/` | Crear evolución |
| PUT | `/{id}` | Actualizar evolución |
| DELETE | `/{id}` | Eliminar evolución |

### 🎯 Frontend Service

```typescript
// services/evolucionesService.ts
export const evolucionesService = {
  list: async (tratamientoId?: number) => {
    const params = tratamientoId ? `?tratamiento_id=${tratamientoId}` : '';
    const { data } = await axios.get(`/evoluciones${params}`, getHeaders());
    return data;
  },
  
  get: async (id: number) => {
    const { data } = await axios.get(`/evoluciones/${id}`, getHeaders());
    return data;
  },
  
  create: async (evolucion: EvolucionCreate) => {
    const { data } = await axios.post('/evoluciones', evolucion, getHeaders());
    return data;
  },
  
  update: async (id: number, evolucion: EvolucionUpdate) => {
    const { data } = await axios.put(`/evoluciones/${id}`, evolucion, getHeaders());
    return data;
  },
  
  delete: async (id: number) => {
    await axios.delete(`/evoluciones/${id}`, getHeaders());
  }
};

// Helper para formato SOAP
export const formatSOAP = (soap: {
  subjetivo: string;
  objetivo: string;
  analisis: string;
  plan: string;
}) => {
  return `S: ${soap.subjetivo}\nO: ${soap.objetivo}\nA: ${soap.analisis}\nP: ${soap.plan}`;
};

// Uso
const EvolucionForm = ({ tratamientoId }) => {
  const [soap, setSoap] = useState({
    subjetivo: '',
    objetivo: '',
    analisis: '',
    plan: ''
  });
  
  const handleSubmit = async () => {
    await evolucionesService.create({
      tratamiento_id: tratamientoId,
      podologo_id: currentUser.id_usuario,
      fecha_evolucion: format(new Date(), 'yyyy-MM-dd'),
      nota_soap: formatSOAP(soap)
    });
  };
  
  return <SOAPEditor value={soap} onChange={setSoap} onSubmit={handleSubmit} />;
};
```

---

## Evidencias

**Base:** `/evidencias`  
**Permisos:** Admin, Podologo

### Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/` | Listar evidencias |
| GET | `/evolucion/{id}` | Por evolución |
| GET | `/tratamiento/{id}` | Por tratamiento |
| GET | `/{id}` | Detalles de evidencia |
| POST | `/` | Crear evidencia |
| POST | `/upload` | Subir archivo (multipart) |
| PUT | `/{id}` | Actualizar evidencia |
| DELETE | `/{id}` | Eliminar evidencia |

### 🎯 Frontend Service

```typescript
// services/evidenciasService.ts
export const evidenciasService = {
  list: async () => {
    const { data } = await axios.get('/evidencias', getHeaders());
    return data;
  },
  
  getByEvolucion: async (evolucionId: number) => {
    const { data } = await axios.get(`/evidencias/evolucion/${evolucionId}`, getHeaders());
    return data;
  },
  
  getByTratamiento: async (tratamientoId: number) => {
    const { data } = await axios.get(`/evidencias/tratamiento/${tratamientoId}`, getHeaders());
    return data;
  },
  
  get: async (id: number) => {
    const { data } = await axios.get(`/evidencias/${id}`, getHeaders());
    return data;
  },
  
  create: async (evidencia: EvidenciaCreate) => {
    const { data } = await axios.post('/evidencias', evidencia, getHeaders());
    return data;
  },
  
  upload: async (file: File, evolucionId: number, descripcion: string) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('evolucion_id', evolucionId.toString());
    formData.append('descripcion', descripcion);
    
    const { data } = await axios.post('/evidencias/upload', formData, {
      headers: {
        ...getHeaders().headers,
        'Content-Type': 'multipart/form-data'
      }
    });
    return data;
  },
  
  update: async (id: number, evidencia: EvidenciaUpdate) => {
    const { data } = await axios.put(`/evidencias/${id}`, evidencia, getHeaders());
    return data;
  },
  
  delete: async (id: number) => {
    await axios.delete(`/evidencias/${id}`, getHeaders());
  }
};

// Uso - Upload de archivo
const EvidenciaUpload = ({ evolucionId }) => {
  const [file, setFile] = useState<File | null>(null);
  const [descripcion, setDescripcion] = useState('');
  
  const handleUpload = async () => {
    if (!file) return;
    
    try {
      await evidenciasService.upload(file, evolucionId, descripcion);
      toast.success('Foto subida exitosamente');
    } catch (error) {
      toast.error('Error subiendo foto');
    }
  };
  
  return (
    <div>
      <input type="file" accept="image/*" onChange={(e) => setFile(e.target.files?.[0] || null)} />
      <input value={descripcion} onChange={(e) => setDescripcion(e.target.value)} placeholder="Descripción" />
      <button onClick={handleUpload}>Subir</button>
    </div>
  );
};
```

---

## Podólogos

**Base:** `/podologos`  
**Permisos:** Admin

### Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/` | Listar podólogos |
| GET | `/{id}` | Detalles de podólogo |
| POST | `/` | Crear podólogo |
| PUT | `/{id}` | Actualizar podólogo |
| DELETE | `/{id}` | Eliminar podólogo |

### 🎯 Frontend Service

```typescript
// services/podologosService.ts
export const podologosService = {
  list: async () => {
    const { data } = await axios.get('/podologos', getHeaders());
    return data;
  },
  
  get: async (id: number) => {
    const { data } = await axios.get(`/podologos/${id}`, getHeaders());
    return data;
  },
  
  create: async (podologo: PodologoCreate) => {
    const { data } = await axios.post('/podologos', podologo, getHeaders());
    return data;
  },
  
  update: async (id: number, podologo: PodologoUpdate) => {
    const { data } = await axios.put(`/podologos/${id}`, podologo, getHeaders());
    return data;
  },
  
  delete: async (id: number) => {
    await axios.delete(`/podologos/${id}`, getHeaders());
  }
};
```

---

## Servicios

**Base:** `/servicios`  
**Permisos:** Admin, Podologo

### Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/` | Listar servicios del catálogo |
| GET | `/{id}` | Detalles de servicio |
| POST | `/` | Crear servicio |
| PUT | `/{id}` | Actualizar servicio |
| DELETE | `/{id}` | Eliminar servicio |

### 🎯 Frontend Service

```typescript
// services/serviciosService.ts
export const serviciosService = {
  list: async () => {
    const { data } = await axios.get('/servicios', getHeaders());
    return data;
  },
  
  get: async (id: number) => {
    const { data } = await axios.get(`/servicios/${id}`, getHeaders());
    return data;
  },
  
  create: async (servicio: ServicioCreate) => {
    const { data } = await axios.post('/servicios', servicio, getHeaders());
    return data;
  },
  
  update: async (id: number, servicio: ServicioUpdate) => {
    const { data } = await axios.put(`/servicios/${id}`, servicio, getHeaders());
    return data;
  },
  
  delete: async (id: number) => {
    await axios.delete(`/servicios/${id}`, getHeaders());
  }
};
```

---

## Prospectos

**Base:** `/prospectos`  
**Permisos:** Admin, Recepcion

### Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/` | Listar prospectos (leads) |
| GET | `/{id}` | Detalles de prospecto |
| POST | `/` | Crear prospecto |
| PUT | `/{id}` | Actualizar prospecto |
| POST | `/{id}/convertir` | Convertir a paciente |

### 🎯 Frontend Service

```typescript
// services/prospectosService.ts
export const prospectosService = {
  list: async () => {
    const { data } = await axios.get('/prospectos', getHeaders());
    return data;
  },
  
  get: async (id: number) => {
    const { data } = await axios.get(`/prospectos/${id}`, getHeaders());
    return data;
  },
  
  create: async (prospecto: ProspectoCreate) => {
    const { data } = await axios.post('/prospectos', prospecto, getHeaders());
    return data;
  },
  
  update: async (id: number, prospecto: ProspectoUpdate) => {
    const { data } = await axios.put(`/prospectos/${id}`, prospecto, getHeaders());
    return data;
  },
  
  convertirAPaciente: async (id: number) => {
    const { data } = await axios.post(`/prospectos/${id}/convertir`, {}, getHeaders());
    return data;
  }
};

// Uso
const handleConvertir = async (prospectoId: number) => {
  const paciente = await prospectosService.convertirAPaciente(prospectoId);
  toast.success(`Convertido a paciente ID: ${paciente.id_paciente}`);
  navigate(`/pacientes/${paciente.id_paciente}`);
};
```

---

## Usuarios

**Base:** `/usuarios`  
**Permisos:** Admin

### Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/` | Listar usuarios del sistema |
| GET | `/{id}` | Detalles de usuario |
| POST | `/` | Crear usuario |
| PUT | `/{id}` | Actualizar usuario |
| PUT | `/{id}/reset-password` | Resetear contraseña |
| DELETE | `/{id}` | Eliminar usuario |
| GET | `/{id}/gemini-key/status` | Estado de API Key Gemini |
| PUT | `/{id}/gemini-key` | Configurar API Key Gemini |
| DELETE | `/{id}/gemini-key` | Eliminar API Key Gemini |

### 🎯 Frontend Service

```typescript
// services/usuariosService.ts
export const usuariosService = {
  list: async () => {
    const { data } = await axios.get('/usuarios', getHeaders());
    return data;
  },
  
  get: async (id: number) => {
    const { data } = await axios.get(`/usuarios/${id}`, getHeaders());
    return data;
  },
  
  create: async (usuario: UsuarioCreate) => {
    const { data } = await axios.post('/usuarios', usuario, getHeaders());
    return data;
  },
  
  update: async (id: number, usuario: UsuarioUpdate) => {
    const { data } = await axios.put(`/usuarios/${id}`, usuario, getHeaders());
    return data;
  },
  
  resetPassword: async (id: number, newPassword: string) => {
    const { data } = await axios.put(
      `/usuarios/${id}/reset-password`,
      { new_password: newPassword },
      getHeaders()
    );
    return data;
  },
  
  delete: async (id: number) => {
    await axios.delete(`/usuarios/${id}`, getHeaders());
  },
  
  getGeminiKeyStatus: async (id: number) => {
    const { data } = await axios.get(`/usuarios/${id}/gemini-key/status`, getHeaders());
    return data;
  },
  
  setGeminiKey: async (id: number, apiKey: string) => {
    const { data } = await axios.put(
      `/usuarios/${id}/gemini-key`,
      { api_key: apiKey },
      getHeaders()
    );
    return data;
  },
  
  deleteGeminiKey: async (id: number) => {
    await axios.delete(`/usuarios/${id}/gemini-key`, getHeaders());
  }
};
```

---

## Auditoría

**Base:** `/audit`  
**Permisos:** Admin, Podologo

### Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/` | Listar logs de auditoría |
| GET | `/{tabla}/{registro_id}` | Historial de un registro |
| GET | `/export` | Exportar logs (CSV) |

### 🎯 Frontend Service

```typescript
// services/auditService.ts
export const auditService = {
  list: async (filters?: {
    tabla?: string;
    accion?: string;
    usuario_id?: number;
    fecha_inicio?: string;
    fecha_fin?: string;
  }) => {
    const params = new URLSearchParams();
    if (filters?.tabla) params.append('tabla', filters.tabla);
    if (filters?.accion) params.append('accion', filters.accion);
    if (filters?.usuario_id) params.append('usuario_id', filters.usuario_id.toString());
    if (filters?.fecha_inicio) params.append('fecha_inicio', filters.fecha_inicio);
    if (filters?.fecha_fin) params.append('fecha_fin', filters.fecha_fin);
    
    const { data } = await axios.get(`/audit?${params}`, getHeaders());
    return data;
  },
  
  getHistory: async (tabla: string, registroId: number) => {
    const { data } = await axios.get(`/audit/${tabla}/${registroId}`, getHeaders());
    return data;
  },
  
  export: async (filters?: any) => {
    const params = new URLSearchParams(filters);
    const { data } = await axios.get(`/audit/export?${params}`, {
      ...getHeaders(),
      responseType: 'blob'
    });
    
    // Descargar archivo CSV
    const url = window.URL.createObjectURL(new Blob([data]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `audit_log_${Date.now()}.csv`);
    document.body.appendChild(link);
    link.click();
    link.remove();
  }
};
```

---

## Finanzas

**Base:** `/finance`  
**Permisos:** Admin

### Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/metodos` | Listar métodos de pago |
| POST | `/metodos` | Crear método de pago |
| GET | `/pagos` | Listar pagos |
| POST | `/pagos` | Registrar pago |
| GET | `/pagos/{id}` | Detalles de pago |
| POST | `/pagos/{id}/transacciones` | Agregar transacción |

### 🎯 Frontend Service

```typescript
// services/financeService.ts
export const financeService = {
  // Métodos de pago
  listMetodosPago: async () => {
    const { data } = await axios.get('/finance/metodos', getHeaders());
    return data;
  },
  
  createMetodoPago: async (metodo: { nombre: string; activo: boolean }) => {
    const { data } = await axios.post('/finance/metodos', metodo, getHeaders());
    return data;
  },
  
  // Pagos
  listPagos: async (filters?: { cita_id?: number; fecha_inicio?: string; fecha_fin?: string }) => {
    const params = new URLSearchParams();
    if (filters?.cita_id) params.append('cita_id', filters.cita_id.toString());
    if (filters?.fecha_inicio) params.append('fecha_inicio', filters.fecha_inicio);
    if (filters?.fecha_fin) params.append('fecha_fin', filters.fecha_fin);
    
    const { data } = await axios.get(`/finance/pagos?${params}`, getHeaders());
    return data;
  },
  
  createPago: async (pago: PagoCreate) => {
    const { data } = await axios.post('/finance/pagos', pago, getHeaders());
    return data;
  },
  
  getPago: async (id: number) => {
    const { data } = await axios.get(`/finance/pagos/${id}`, getHeaders());
    return data;
  },
  
  addTransaccion: async (pagoId: number, transaccion: TransaccionCreate) => {
    const { data } = await axios.post(
      `/finance/pagos/${pagoId}/transacciones`,
      transaccion,
      getHeaders()
    );
    return data;
  }
};
```

---

## Historial

**Base:** `/historial`  
**Permisos:** Admin, Podologo

### Endpoints - Alergias

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/alergias` | Listar alergias |
| GET | `/alergias/{id}` | Detalles |
| POST | `/alergias` | Crear alergia |
| PUT | `/alergias/{id}` | Actualizar |
| DELETE | `/alergias/{id}` | Eliminar |

### Endpoints - Suplementos

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/suplementos` | Listar suplementos |
| GET | `/suplementos/{id}` | Detalles |
| POST | `/suplementos` | Crear |
| PUT | `/suplementos/{id}` | Actualizar |
| DELETE | `/suplementos/{id}` | Eliminar |

### Endpoints - Antecedentes No Patológicos

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/antecedentes-no-patologicos` | Listar |
| GET | `/antecedentes-no-patologicos/{id}` | Detalles |
| POST | `/antecedentes-no-patologicos` | Crear |
| PUT | `/antecedentes-no-patologicos/{id}` | Actualizar |
| DELETE | `/antecedentes-no-patologicos/{id}` | Eliminar |

### Endpoints - Conversaciones Digitales

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/conversaciones-digitales` | Listar |
| GET | `/conversaciones-digitales/{id}` | Detalles |
| POST | `/conversaciones-digitales` | Crear |
| PUT | `/conversaciones-digitales/{id}` | Actualizar |
| DELETE | `/conversaciones-digitales/{id}` | Eliminar |

### 🎯 Frontend Service

```typescript
// services/historialService.ts
export const historialService = {
  // Alergias
  alergias: {
    list: async (pacienteId: number) => {
      const { data } = await axios.get(
        `/historial/alergias?paciente_id=${pacienteId}`,
        getHeaders()
      );
      return data;
    },
    
    create: async (alergia: AlergiaCreate) => {
      const { data } = await axios.post('/historial/alergias', alergia, getHeaders());
      return data;
    },
    
    update: async (id: number, alergia: AlergiaUpdate) => {
      const { data } = await axios.put(`/historial/alergias/${id}`, alergia, getHeaders());
      return data;
    },
    
    delete: async (id: number) => {
      await axios.delete(`/historial/alergias/${id}`, getHeaders());
    }
  },
  
  // Suplementos
  suplementos: {
    list: async (pacienteId: number) => {
      const { data } = await axios.get(
        `/historial/suplementos?paciente_id=${pacienteId}`,
        getHeaders()
      );
      return data;
    },
    
    create: async (suplemento: SuplementoCreate) => {
      const { data } = await axios.post('/historial/suplementos', suplemento, getHeaders());
      return data;
    },
    
    update: async (id: number, suplemento: SuplementoUpdate) => {
      const { data } = await axios.put(`/historial/suplementos/${id}`, suplemento, getHeaders());
      return data;
    },
    
    delete: async (id: number) => {
      await axios.delete(`/historial/suplementos/${id}`, getHeaders());
    }
  },
  
  // Antecedentes
  antecedentes: {
    list: async (pacienteId: number) => {
      const { data } = await axios.get(
        `/historial/antecedentes-no-patologicos?paciente_id=${pacienteId}`,
        getHeaders()
      );
      return data;
    },
    
    create: async (antecedente: AntecedenteCreate) => {
      const { data } = await axios.post(
        '/historial/antecedentes-no-patologicos',
        antecedente,
        getHeaders()
      );
      return data;
    },
    
    update: async (id: number, antecedente: AntecedenteUpdate) => {
      const { data } = await axios.put(
        `/historial/antecedentes-no-patologicos/${id}`,
        antecedente,
        getHeaders()
      );
      return data;
    },
    
    delete: async (id: number) => {
      await axios.delete(`/historial/antecedentes-no-patologicos/${id}`, getHeaders());
    }
  }
};
```

---

## Chat IA

**Base:** `/chat`  
**Permisos:** Todos

### Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/` | Enviar mensaje al agente |
| GET | `/health` | Estado del agente IA |
| GET | `/capabilities` | Capacidades del agente |
| GET | `/commands` | Catálogo de comandos |
| GET | `/commands/{id}` | Detalle de comando |

### 🎯 Frontend Service

```typescript
// services/chatService.ts
export const chatService = {
  sendMessage: async (message: string, threadId?: string) => {
    const { data } = await axios.post('/chat', {
      message,
      thread_id: threadId
    }, getHeaders());
    return data;
  },
  
  getHealth: async () => {
    const { data } = await axios.get('/chat/health', getHeaders());
    return data;
  },
  
  getCapabilities: async () => {
    const { data } = await axios.get('/chat/capabilities', getHeaders());
    return data;
  },
  
  getCommands: async () => {
    const { data } = await axios.get('/chat/commands', getHeaders());
    return data;
  },
  
  getCommand: async (commandId: string) => {
    const { data } = await axios.get(`/chat/commands/${commandId}`, getHeaders());
    return data;
  }
};

// Uso - Chat simple
const ChatWidget = () => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [threadId, setThreadId] = useState<string | null>(null);
  
  const handleSend = async () => {
    if (!input.trim()) return;
    
    // Agregar mensaje del usuario
    setMessages(prev => [...prev, { role: 'user', content: input }]);
    
    try {
      const response = await chatService.sendMessage(input, threadId || undefined);
      
      // Guardar thread_id para continuidad
      if (response.thread_id) {
        setThreadId(response.thread_id);
      }
      
      // Agregar respuesta del bot
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: response.message 
      }]);
      
      setInput('');
    } catch (error) {
      console.error('Error:', error);
      setMessages(prev => [...prev, { 
        role: 'error', 
        content: 'Error al procesar mensaje' 
      }]);
    }
  };
  
  return (
    <div className="chat-widget">
      <div className="messages">
        {messages.map((msg, i) => (
          <div key={i} className={`message ${msg.role}`}>
            {msg.content}
          </div>
        ))}
      </div>
      <input
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyPress={(e) => e.key === 'Enter' && handleSend()}
        placeholder="Pregunta algo..."
      />
      <button onClick={handleSend}>Enviar</button>
    </div>
  );
};
```

---

## Estadísticas

**Base:** `/statistics`  
**Permisos:** Admin, Podologo

### Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/dashboard` | Estadísticas completas del dashboard |
| GET | `/summary` | Resumen ejecutivo |

### 🎯 Frontend Service

```typescript
// services/statisticsService.ts
export const statisticsService = {
  getDashboard: async () => {
    const { data } = await axios.get('/statistics/dashboard', getHeaders());
    return data;
  },
  
  getSummary: async () => {
    const { data } = await axios.get('/statistics/summary', getHeaders());
    return data;
  }
};

// Uso - Dashboard
const DashboardView = () => {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  
  useEffect(() => {
    loadStats();
  }, []);
  
  const loadStats = async () => {
    const data = await statisticsService.getDashboard();
    setStats(data);
  };
  
  if (!stats) return <Loading />;
  
  return (
    <div className="dashboard">
      <StatCard 
        title="Pacientes Activos" 
        value={stats.pacientes_activos} 
        icon="users"
      />
      <StatCard 
        title="Citas Hoy" 
        value={stats.citas_hoy} 
        icon="calendar"
      />
      <StatCard 
        title="Ingresos del Mes" 
        value={`$${stats.ingresos_mes.toLocaleString()}`} 
        icon="dollar"
      />
      <StatCard 
        title="Tratamientos en Curso" 
        value={stats.tratamientos_en_curso} 
        icon="medical"
      />
    </div>
  );
};
```

---

## Notificaciones

**Base:** `/notifications`  
**Permisos:** Admin, Recepcion

### Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/appointment-reminder` | Enviar recordatorio individual |
| POST | `/bulk-reminders` | Enviar recordatorios masivos |
| GET | `/upcoming-reminders` | Ver próximos recordatorios |

### 🎯 Frontend Service

```typescript
// services/notificationsService.ts
export const notificationsService = {
  sendReminder: async (citaId: number) => {
    const { data } = await axios.post(
      '/notifications/appointment-reminder',
      { cita_id: citaId },
      getHeaders()
    );
    return data;
  },
  
  sendBulkReminders: async (fecha: string) => {
    const { data } = await axios.post(
      '/notifications/bulk-reminders',
      { fecha },
      getHeaders()
    );
    return data;
  },
  
  getUpcomingReminders: async () => {
    const { data } = await axios.get('/notifications/upcoming-reminders', getHeaders());
    return data;
  }
};

// Uso
const handleSendReminder = async (citaId: number) => {
  try {
    await notificationsService.sendReminder(citaId);
    toast.success('Recordatorio enviado');
  } catch (error) {
    toast.error('Error al enviar recordatorio');
  }
};
```

---

## Integración

**Base:** `/integration`  
**Permisos:** Todos

### Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/user-context` | Contexto del usuario actual |
| POST | `/save-transcript` | Guardar transcripción de conversación |
| GET | `/transcript-history` | Historial de transcripciones |

### 🎯 Frontend Service

```typescript
// services/integrationService.ts
export const integrationService = {
  getUserContext: async () => {
    const { data } = await axios.get('/integration/user-context', getHeaders());
    return data;
  },
  
  saveTranscript: async (transcript: {
    session_id: string;
    user_text: string;
    assistant_text: string;
  }) => {
    const { data } = await axios.post(
      '/integration/save-transcript',
      transcript,
      getHeaders()
    );
    return data;
  },
  
  getTranscriptHistory: async (sessionId?: string) => {
    const params = sessionId ? `?session_id=${sessionId}` : '';
    const { data } = await axios.get(
      `/integration/transcript-history${params}`,
      getHeaders()
    );
    return data;
  }
};
```

---

## WebSocket

**Base:** `ws://localhost:8000/ws/langgraph`  
**Permisos:** Todos

### Conexión

```typescript
// services/websocketService.ts
export class WebSocketService {
  private ws: WebSocket | null = null;
  private token: string;
  
  constructor(token: string) {
    this.token = token;
  }
  
  connect(onMessage: (data: any) => void, onError: (error: any) => void) {
    this.ws = new WebSocket(`ws://localhost:8000/ws/langgraph?token=${this.token}`);
    
    this.ws.onopen = () => {
      console.log('WebSocket conectado');
    };
    
    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      onMessage(data);
    };
    
    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      onError(error);
    };
    
    this.ws.onclose = () => {
      console.log('WebSocket desconectado');
    };
  }
  
  send(message: any) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    }
  }
  
  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
}

// Uso - Streaming de chat
const ChatWithStreaming = () => {
  const [messages, setMessages] = useState([]);
  const wsRef = useRef<WebSocketService | null>(null);
  
  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) return;
    
    const ws = new WebSocketService(token);
    
    ws.connect(
      (data) => {
        if (data.type === 'update') {
          // Update parcial
          setMessages(prev => [
            ...prev.slice(0, -1),
            { ...prev[prev.length - 1], content: data.content }
          ]);
        } else if (data.type === 'final') {
          // Respuesta final
          setMessages(prev => [
            ...prev.slice(0, -1),
            { role: 'assistant', content: data.content, final: true }
          ]);
        }
      },
      (error) => {
        console.error('WebSocket error:', error);
      }
    );
    
    wsRef.current = ws;
    
    return () => {
      ws.disconnect();
    };
  }, []);
  
  const handleSend = (message: string) => {
    // Agregar mensaje del usuario
    setMessages(prev => [...prev, { role: 'user', content: message }]);
    
    // Agregar placeholder para respuesta
    setMessages(prev => [...prev, { role: 'assistant', content: '', final: false }]);
    
    // Enviar mensaje por WebSocket
    wsRef.current?.send({
      type: 'start_job',
      utterance: message,
      session_id: `session_${Date.now()}`,
      user_id: currentUser.id_usuario
    });
  };
  
  return <ChatUI messages={messages} onSend={handleSend} />;
};
```

---

## 🔧 Configuración Global

### Axios Instance Configurado

```typescript
// api/axios.ts
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

// Crear instancia de axios
export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json'
  }
});

// Interceptor para agregar token automáticamente
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Interceptor para manejar errores
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Token expirado, redirigir a login
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Helper para headers con auth
export const getAuthHeaders = () => ({
  headers: {
    Authorization: `Bearer ${localStorage.getItem('token')}`
  }
});
```

### Variables de Entorno

```bash
# frontend/.env
VITE_API_URL=http://localhost:8000/api/v1
VITE_WS_URL=ws://localhost:8000/ws
```

---

## 📊 Tipos TypeScript

```typescript
// types/api.ts

// Auth
export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface User {
  id_usuario: number;
  nombre_usuario: string;
  email: string;
  rol: 'Admin' | 'Podologo' | 'Recepcion';
  clinica_id: number;
  has_gemini_key: boolean;
  gemini_key_status: string | null;
}

// Pacientes
export interface Paciente {
  id_paciente: number;
  nombres: string;
  apellidos: string;
  fecha_nacimiento: string;
  edad?: number;
  telefono: string;
  email?: string;
  sexo: 'M' | 'F' | 'Otro';
  domicilio?: string;
  peso_kg?: number;
  estatura_cm?: number;
  imc?: number;
  tipo_sangre?: string;
  curp?: string;
  codigo_interno?: string;
  created_at: string;
}

export interface PacienteCreate {
  nombres: string;
  apellidos: string;
  fecha_nacimiento: string;
  telefono: string;
  email?: string;
  sexo: 'M' | 'F' | 'Otro';
  domicilio?: string;
  peso_kg?: number;
  estatura_cm?: number;
  tipo_sangre?: string;
}

export interface PacienteUpdate {
  telefono?: string;
  email?: string;
  domicilio?: string;
  peso_kg?: number;
  estatura_cm?: number;
}

// Citas
export interface Cita {
  id_cita: number;
  paciente_id: number;
  podologo_id: number;
  fecha_cita: string;
  hora_inicio: string;
  hora_fin: string;
  status: 'Programada' | 'Confirmada' | 'En Curso' | 'Completada' | 'Cancelada';
  motivo: string;
  notas?: string;
  created_at: string;
}

export interface CitaCreate {
  paciente_id: number;
  podologo_id: number;
  fecha_cita: string;
  hora_inicio: string;
  hora_fin: string;
  motivo: string;
  notas?: string;
}

// Tratamientos
export interface Tratamiento {
  id_tratamiento: number;
  paciente_id: number;
  problema: string;
  diagnostico?: string;
  plan_tratamiento?: string;
  fecha_inicio: string;
  fecha_fin?: string;
  estado_tratamiento: 'Activo' | 'En Curso' | 'Completado' | 'Suspendido';
  created_at: string;
}

// Evoluciones
export interface Evolucion {
  id_evolucion: number;
  tratamiento_id: number;
  podologo_id: number;
  fecha_evolucion: string;
  nota_soap: string;
  diagnostico_cie10?: string;
  procedimiento?: string;
  created_at: string;
}

// Chat
export interface ChatMessage {
  role: 'user' | 'assistant' | 'error';
  content: string;
  timestamp?: string;
}

export interface ChatRequest {
  message: string;
  thread_id?: string;
}

export interface ChatResponse {
  success: boolean;
  message: string;
  data?: any;
  intent?: string;
  thread_id?: string;
  processing_time_ms: number;
}
```

---

## 🚀 Hook Personalizado para API

```typescript
// hooks/useApi.ts
import { useState, useCallback } from 'react';

export function useApi<T>(apiFunc: (...args: any[]) => Promise<T>) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const execute = useCallback(
    async (...args: any[]) => {
      setLoading(true);
      setError(null);
      
      try {
        const result = await apiFunc(...args);
        setData(result);
        return result;
      } catch (err: any) {
        const errorMsg = err.response?.data?.detail || err.message || 'Error desconocido';
        setError(errorMsg);
        throw err;
      } finally {
        setLoading(false);
      }
    },
    [apiFunc]
  );

  return { data, loading, error, execute };
}

// Uso
const PacientesView = () => {
  const { data: pacientes, loading, error, execute: loadPacientes } = useApi(
    pacientesService.list
  );
  
  useEffect(() => {
    loadPacientes(0, 20);
  }, []);
  
  if (loading) return <Loading />;
  if (error) return <Error message={error} />;
  
  return <Table data={pacientes?.pacientes || []} />;
};
```

---

## 📌 Notas Finales

### Autenticación

Todos los endpoints (excepto `/auth/login`) requieren el header:
```
Authorization: Bearer {token}
```

### Paginación

Los endpoints con listados soportan paginación con query params:
- `skip`: Número de registros a saltar (default: 0)
- `limit`: Máximo de resultados (default: 20, max: 100)

### Soft Deletes

Los endpoints DELETE usan soft delete por defecto (marcan como inactivo). Solo Admin puede hacer hard delete con `/purge`.

### Filtros por Fecha

Formato ISO 8601: `YYYY-MM-DD` (ej: `2024-12-13`)

### Códigos de Estado HTTP

- `200 OK`: Operación exitosa
- `201 Created`: Recurso creado
- `204 No Content`: Eliminación exitosa
- `400 Bad Request`: Datos inválidos
- `401 Unauthorized`: Sin autenticación
- `403 Forbidden`: Sin permisos
- `404 Not Found`: Recurso no existe
- `422 Unprocessable Entity`: Validación Pydantic fallida
- `500 Internal Server Error`: Error del servidor

### Rate Limiting

- Login: 5 intentos/minuto por IP
- Chat: 30 requests/minuto por IP
- Otros: 100 requests/minuto por IP

---

**Última actualización:** 13 de Diciembre de 2024  
**Total de Endpoints:** 101  
**Versión API:** v1
