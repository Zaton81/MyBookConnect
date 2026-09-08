import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { User, AuthState } from '../types/auth';
import { authApi } from '../services/api';

interface AuthStore extends AuthState {
  login: (email: string, password: string) => Promise<void>;
  register: (username: string, email: string, password: string) => Promise<void>;
  logout: () => void;
  updateProfile: (data: FormData | Partial<User>) => Promise<void>;
  followUser: (userId: number) => Promise<void>;
  unfollowUser: (userId: number) => Promise<void>;
  getFollowStatus: (userId: number) => Promise<{is_following: boolean; is_follower: boolean; is_mutual: boolean}>;
  getFollowing: () => Promise<User[]>;
  getFollowers: () => Promise<User[]>;
}

export const useAuthStore = create<AuthStore>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      isAuthenticated: false,
      loading: false,
      error: null,

      login: async (username: string, password: string) => {
        try {
          console.log('Iniciando login en store...');
          const data = await authApi.login(username, password);
          console.log('Respuesta login en store:', data);
          
          // In SimpleJWT, token is ALWAYS in data.access
          const token = data.access;
          if (!token) {
            console.error('No se encontró token en la respuesta:', data);
            throw new Error('No se recibió token del servidor');
          }
          
          // Set token and isAuthenticated FIRST
          console.log('Token obtenido:', token);
          set({ token, isAuthenticated: true });
          
          // Then get profile with the token
          console.log('Obteniendo perfil con token:', token);
          const user = await authApi.getProfile(token);
          console.log('Perfil obtenido:', user);
          set({ user });
        } catch (error) {
          console.error('Error en login:', error);
          set({ token: null, isAuthenticated: false, user: null });
          throw error;
        }
      },

      register: async (username: string, email: string, password: string) => {
        try {
          console.log('Iniciando registro...');
          
          // First create the user
          await authApi.register(username, email, password, password);
          console.log('Usuario registrado, obteniendo token...');
          
          // Immediately login to get token
          const loginData = await authApi.login(username, password);
          console.log('Respuesta login post-registro:', loginData);
          
          // En SimpleJWT, el token viene en data.access
          const token = loginData.access;
          if (!token) {
            console.error('No se encontró token en la respuesta:', loginData);
            throw new Error('No se recibió token después del registro');
          }
          
          // Set token FIRST - this is crucial
          console.log('Token obtenido, estableciendo en store...');
          set({ token, isAuthenticated: true });
          
          // Now get profile
          console.log('Obteniendo perfil...');
          const user = await authApi.getProfile(token);
          console.log('Perfil obtenido:', user);
          set({ user });
          console.log('Registro completo');
        } catch (error) {
          console.error('Error en registro:', error);
          throw error;
        }
      },

      logout: () => {
        set({ 
          user: null, 
          token: null, 
          isAuthenticated: false 
        });
      },

      updateProfile: async (data: FormData | Partial<User>) => {
        const state = useAuthStore.getState();
        if (!state.token) throw new Error('No hay token');
        
        try {
          const updatedUser = await authApi.updateProfile(state.token, data);
          console.log('Perfil actualizado:', updatedUser);
          set({ user: updatedUser });
        } catch (error) {
          console.error('Error actualizando perfil:', error);
          throw error;
        }
      },

      followUser: async (userId: number) => {
        const state = useAuthStore.getState();
        if (!state.token) throw new Error('No hay token');
        
        try {
          const apiUrl = (import.meta as any).env.VITE_API_URL || 'http://localhost:8000';
          const response = await fetch(`${apiUrl}/api/v1/auth/users/${userId}/follow/`, {
            method: 'POST',
            headers: {
              'Authorization': `Bearer ${state.token}`,
              'Content-Type': 'application/json',
            },
          });
          
          if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Error al seguir usuario');
          }
          
          // Actualizar el perfil del usuario actual para reflejar el cambio
          const updatedUser = await authApi.getProfile(state.token);
          set({ user: updatedUser });
        } catch (error) {
          console.error('Error siguiendo usuario:', error);
          throw error;
        }
      },

      unfollowUser: async (userId: number) => {
        const state = useAuthStore.getState();
        if (!state.token) throw new Error('No hay token');
        
        try {
          const apiUrl = (import.meta as any).env.VITE_API_URL || 'http://localhost:8000';
          const response = await fetch(`${apiUrl}/api/v1/auth/users/${userId}/unfollow/`, {
            method: 'POST',
            headers: {
              'Authorization': `Bearer ${state.token}`,
              'Content-Type': 'application/json',
            },
          });
          
          if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Error al dejar de seguir usuario');
          }
          
          // Actualizar el perfil del usuario actual para reflejar el cambio
          const updatedUser = await authApi.getProfile(state.token);
          set({ user: updatedUser });
        } catch (error) {
          console.error('Error dejando de seguir usuario:', error);
          throw error;
        }
      },

      getFollowStatus: async (userId: number) => {
        const state = useAuthStore.getState();
        if (!state.token) throw new Error('No hay token');
        
        try {
          const apiUrl = (import.meta as any).env.VITE_API_URL || 'http://localhost:8000';
          const response = await fetch(`${apiUrl}/api/v1/auth/users/${userId}/follow-status/`, {
            headers: {
              'Authorization': `Bearer ${state.token}`,
            },
          });
          
          if (!response.ok) {
            throw new Error('Error al obtener estado de seguimiento');
          }
          
          return await response.json();
        } catch (error) {
          console.error('Error obteniendo estado de seguimiento:', error);
          throw error;
        }
      },

      getFollowing: async () => {
        const state = useAuthStore.getState();
        if (!state.token) throw new Error('No hay token');
        
        try {
          const apiUrl = (import.meta as any).env.VITE_API_URL || 'http://localhost:8000';
          const response = await fetch(`${apiUrl}/api/v1/auth/following/`, {
            headers: {
              'Authorization': `Bearer ${state.token}`,
            },
          });
          
          if (!response.ok) {
            throw new Error('Error al obtener lista de seguidos');
          }
          
          return await response.json();
        } catch (error) {
          console.error('Error obteniendo lista de seguidos:', error);
          throw error;
        }
      },

      getFollowers: async () => {
        const state = useAuthStore.getState();
        if (!state.token) throw new Error('No hay token');
        
        try {
          const apiUrl = (import.meta as any).env.VITE_API_URL || 'http://localhost:8000';
          const response = await fetch(`${apiUrl}/api/v1/auth/followers/`, {
            headers: {
              'Authorization': `Bearer ${state.token}`,
            },
          });
          
          if (!response.ok) {
            throw new Error('Error al obtener lista de seguidores');
          }
          
          return await response.json();
        } catch (error) {
          console.error('Error obteniendo lista de seguidores:', error);
          throw error;
        }
      },
    }),
    {
      name: 'auth-storage',
    }
  )
);