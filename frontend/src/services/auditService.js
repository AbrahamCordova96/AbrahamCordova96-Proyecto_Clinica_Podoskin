// Servicio para gestionar auditoría
import api from './api';

export const auditService = {
  // Obtener todos los logs de auditoría
  getAll: async () => {
    const response = await api.get('/audit');
    return response.data;
  },

  // Obtener logs filtrados por usuario
  getByUser: async (userId) => {
    const response = await api.get(`/audit/usuario/${userId}`);
    return response.data;
  },

  // Obtener logs filtrados por entidad
  getByEntity: async (entity, entityId) => {
    const url = entityId 
      ? `/audit/entity/${entity}/${entityId}`
      : `/audit/entity/${entity}`;
    const response = await api.get(url);
    return response.data;
  }
};
