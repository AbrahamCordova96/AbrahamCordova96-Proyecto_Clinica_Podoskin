import api from './api';

export const pacientesService = {
  // Listar pacientes con paginación
  getAll: async (page = 1, limit = 20, search = '') => {
    const response = await api.get('/pacientes', {
      params: { page, limit, search }
    });
    return response.data;
  },

  // Obtener un paciente por ID
  getById: async (id) => {
    const response = await api.get(`/pacientes/${id}`);
    return response.data;
  },

  // Crear nuevo paciente
  create: async (pacienteData) => {
    const response = await api.post('/pacientes', pacienteData);
    return response.data;
  },

  // Actualizar paciente
  update: async (id, pacienteData) => {
    const response = await api.put(`/pacientes/${id}`, pacienteData);
    return response.data;
  },

  // Eliminar paciente (soft delete)
  delete: async (id) => {
    const response = await api.delete(`/pacientes/${id}`);
    return response.data;
  },

  // Obtener historial completo del paciente
  getHistorial: async (id) => {
    const response = await api.get(`/pacientes/${id}/historial`);
    return response.data;
  },

  // Exportar expediente en HTML/PDF
  exportExpediente: async (id, formato = 'html') => {
    const response = await api.get(`/pacientes/${id}/expediente`, {
      params: { formato },
      responseType: formato === 'pdf' ? 'blob' : 'text'
    });
    return response.data;
  }
};
