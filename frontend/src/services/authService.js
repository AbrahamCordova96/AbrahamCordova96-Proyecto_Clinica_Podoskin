import api from './api';

export const authService = {
  // Login con username, email o ID
  login: async (identifier, password) => {
    const response = await api.post('/auth/login', {
      username: identifier, // Puede ser username, email o ID
      password
    });
    return response.data;
  },

  // Obtener usuario actual
  getCurrentUser: async () => {
    const response = await api.get('/auth/me');
    return response.data;
  },

  // Cambiar contraseña
  changePassword: async (oldPassword, newPassword) => {
    const response = await api.post('/auth/change-password', {
      old_password: oldPassword,
      new_password: newPassword
    });
    return response.data;
  },

  // Logout (limpiar localStorage)
  logout: () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
  }
};
