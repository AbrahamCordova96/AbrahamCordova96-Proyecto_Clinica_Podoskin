import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { User, AuthState } from '../types/auth.types';
import { authService } from '../services/authService';
import axios from 'axios';

interface AuthActions {
  login: (identifier: string, password: string) => Promise<void>;
  logout: () => void;
  setToken: (token: string) => void;
  clearError: () => void;
}

type AuthStore = AuthState & AuthActions;

export const useAuthStore = create<AuthStore>()(
  persist(
    (set, get) => ({
      user: null,
      token: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,

      login: async (identifier: string, password: string) => {
        set({ isLoading: true, error: null });
        
        try {
          const response = await authService.login({ username: identifier, password });
          
          const { access_token, user } = response;
          
          axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
          
          set({
            user,
            token: access_token,
            isAuthenticated: true,
            isLoading: false,
            error: null
          });
          
          try {
            const context = await authService.getUserContext(user.id_usuario);
            console.log('User context:', context);
          } catch (err) {
            console.warn('Failed to fetch user context:', err);
          }
          
        } catch (error: any) {
          set({
            isLoading: false,
            error: error.response?.data?.detail || error.message || 'Error de autenticación'
          });
          throw error;
        }
      },

      logout: () => {
        try {
          authService.logout();
        } catch (err) {
          console.warn('Logout error:', err);
        }
        
        delete axios.defaults.headers.common['Authorization'];
        
        set({
          user: null,
          token: null,
          isAuthenticated: false,
          error: null
        });
      },

      setToken: (token: string) => {
        axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
        set({ token });
      },

      clearError: () => set({ error: null })
    }),
    {
      name: 'podoskin-auth',
      partialize: (state) => ({
        user: state.user,
        token: state.token,
        isAuthenticated: state.isAuthenticated
      })
    }
  )
);
