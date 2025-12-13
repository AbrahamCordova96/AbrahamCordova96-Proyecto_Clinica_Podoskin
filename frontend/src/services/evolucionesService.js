import api from './api';

export const evolucionesService = {
  // Listar evoluciones de un tratamiento
  getByTratamiento: async (tratamiento_id) => {
    const response = await api.get(`/tratamientos/${tratamiento_id}/evoluciones`);
    return response.data;
  },

  // Obtener evolución por ID
  getById: async (id) => {
    const response = await api.get(`/evoluciones/${id}`);
    return response.data;
  },

  // Crear nueva evolución (nota SOAP)
  create: async (evolucionData) => {
    const response = await api.post('/evoluciones', evolucionData);
    return response.data;
  },

  // Actualizar evolución
  update: async (id, evolucionData) => {
    const response = await api.put(`/evoluciones/${id}`, evolucionData);
    return response.data;
  }
};
