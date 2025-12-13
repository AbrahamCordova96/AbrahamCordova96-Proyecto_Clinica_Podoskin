import api from './api';

export const citasService = {
  // Listar citas con filtros
  getAll: async (fecha = null, podologo_id = null, estado = null) => {
    const response = await api.get('/citas', {
      params: { fecha, podologo_id, estado }
    });
    return response.data;
  },

  // Obtener cita por ID
  getById: async (id) => {
    const response = await api.get(`/citas/${id}`);
    return response.data;
  },

  // Crear nueva cita
  create: async (citaData) => {
    const response = await api.post('/citas', citaData);
    return response.data;
  },

  // Actualizar cita
  update: async (id, citaData) => {
    const response = await api.put(`/citas/${id}`, citaData);
    return response.data;
  },

  // Cancelar cita
  cancel: async (id, motivo) => {
    const response = await api.patch(`/citas/${id}/cancelar`, { motivo });
    return response.data;
  },

  // Confirmar cita
  confirm: async (id) => {
    const response = await api.patch(`/citas/${id}/confirmar`);
    return response.data;
  },

  // Obtener disponibilidad de podólogo
  getDisponibilidad: async (podologo_id, fecha) => {
    const response = await api.get(`/citas/disponibilidad`, {
      params: { podologo_id, fecha }
    });
    return response.data;
  }
};
