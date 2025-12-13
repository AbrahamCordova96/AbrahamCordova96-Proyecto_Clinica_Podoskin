import api from './api';

export const tratamientosService = {
  // Listar tratamientos de un paciente
  getByPaciente: async (paciente_id) => {
    const response = await api.get(`/pacientes/${paciente_id}/tratamientos`);
    return response.data;
  },

  // Obtener tratamiento por ID
  getById: async (id) => {
    const response = await api.get(`/tratamientos/${id}`);
    return response.data;
  },

  // Crear nuevo tratamiento
  create: async (tratamientoData) => {
    const response = await api.post('/tratamientos', tratamientoData);
    return response.data;
  },

  // Actualizar tratamiento
  update: async (id, tratamientoData) => {
    const response = await api.put(`/tratamientos/${id}`, tratamientoData);
    return response.data;
  },

  // Completar tratamiento
  complete: async (id) => {
    const response = await api.patch(`/tratamientos/${id}/completar`);
    return response.data;
  }
};
