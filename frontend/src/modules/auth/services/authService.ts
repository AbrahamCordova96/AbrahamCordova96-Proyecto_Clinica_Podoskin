import axios from 'axios';
import { LoginResponse, LoginCredentials } from '../types/auth.types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

export const authServiceReal = {
  login: async (credentials: LoginCredentials): Promise<LoginResponse> => {
    const response = await axios.post(
      `${API_BASE_URL}/auth/login`,
      credentials,
      {
        headers: {
          'Content-Type': 'application/json',
        }
      }
    );
    
    return response.data;
  },

  getUserContext: async (userId?: number) => {
    const response = await axios.get(
      `${API_BASE_URL}/integration/user-context`,
      { params: userId ? { user_id: userId } : {} }
    );
    return response.data;
  },

  logout: async (): Promise<void> => {
  }
};

import { authServiceMock } from './authService.mock';

export const USE_MOCK = false;

export const authService = USE_MOCK ? authServiceMock : authServiceReal;
