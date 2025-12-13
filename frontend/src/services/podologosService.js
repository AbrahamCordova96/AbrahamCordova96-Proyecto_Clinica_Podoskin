import api from './api';

export const podologosService = {
  // Listar todos los podólogos activos
  getAll: async () => {
    const response = await api.get('/podologos');
    return response.data;
  },

  // Obtener podólogo por ID
  getById: async (id) => {
    const response = await api.get(`/podologos/${id}`);
    return response.data;
  },

  // Crear nuevo podólogo
  create: async (podologoData) => {
    const response = await api.post('/podologos', podologoData);
    return response.data;
  },

  // Actualizar podólogo
  update: async (id, podologoData) => {
    const response = await api.put(`/podologos/${id}`, podologoData);
    return response.data;
  },

  // Obtener agenda del podólogo
  getAgenda: async (id, fecha_inicio, fecha_fin) => {
    const response = await api.get(`/podologos/${id}/agenda`, {
      params: { fecha_inicio, fecha_fin }
    });
    return response.data;
  }
};
