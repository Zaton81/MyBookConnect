import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { User, AuthState } from '../types/auth';
import { authApi } from '../services/api';
import { api } from '../api/client';
import { queryClient } from '../app/queryClient';
import { queryKeys } from '../api/queryKeys';

interface AuthStore extends AuthState {
  login: (username: string, password: string) => Promise<void>;
  loginWithGoogle: (idToken: string) => Promise<void>;
  register: (username: string, email: string, password: string) => Promise<void>;
  logout: () => void;
  updateProfile: (data: FormData | Partial<User>) => Promise<void>;
  followUser: (userId: number) => Promise<void>;
  unfollowUser: (userId: number) => Promise<void>;
  getFollowStatus: (userId: number) => Promise<{ is_following: boolean; is_follower: boolean; is_mutual: boolean }>;
  getFollowing: () => Promise<User[]>;
  getFollowers: () => Promise<User[]>;
}

export const useAuthStore = create<AuthStore>()(
  persist(
    (set, get) => ({
      user: null,
      token: null,
      refreshToken: null,
      isAuthenticated: false,
      loading: false,
      error: null,

      login: async (username: string, password: string) => {
        try {
          const data = await authApi.login(username, password);
          const token = data.access;
          const refreshToken = data.refresh || null;

          if (!token) {
            throw new Error('No se recibió token del servidor');
          }

          set({ token, refreshToken, isAuthenticated: true, error: null });

          const user = await authApi.getProfile(token);
          set({ user });
          queryClient.invalidateQueries({ queryKey: queryKeys.users.profile() });
        } catch (error: any) {
          set({ token: null, refreshToken: null, isAuthenticated: false, user: null, error: error?.message });
          throw error;
        }
      },

      loginWithGoogle: async (idToken: string) => {
        try {
          const data = await authApi.loginWithGoogle(idToken);
          const token = data.access;
          const refreshToken = data.refresh || null;

          if (!token) {
            throw new Error('No se recibió token del servidor tras autenticación con Google');
          }

          set({ token, refreshToken, isAuthenticated: true, error: null });

          const user = data.user || (await authApi.getProfile(token));
          set({ user });
          queryClient.invalidateQueries({ queryKey: queryKeys.users.profile() });
        } catch (error: any) {
          set({ token: null, refreshToken: null, isAuthenticated: false, user: null, error: error?.message });
          throw error;
        }
      },

      register: async (username: string, email: string, password: string) => {
        try {
          await authApi.register(username, email, password, password);
          const loginData = await authApi.login(username, password);

          const token = loginData.access;
          const refreshToken = loginData.refresh || null;

          if (!token) {
            throw new Error('No se recibió token después del registro');
          }

          set({ token, refreshToken, isAuthenticated: true, error: null });

          const user = await authApi.getProfile(token);
          set({ user });
          queryClient.invalidateQueries({ queryKey: queryKeys.users.profile() });
        } catch (error: any) {
          set({ token: null, refreshToken: null, isAuthenticated: false, user: null, error: error?.message });
          throw error;
        }
      },

      logout: () => {
        const { refreshToken } = get();
        if (refreshToken) {
          api.post('/api/v1/auth/logout/', { refresh: refreshToken }).catch(() => {});
        }
        // Limpiar cache del servidor en TanStack Query
        queryClient.clear();
        set({
          user: null,
          token: null,
          refreshToken: null,
          isAuthenticated: false,
          error: null,
        });
      },

      updateProfile: async (data: FormData | Partial<User>) => {
        const { token } = get();
        if (!token) throw new Error('No hay sesión activa');

        try {
          const updatedUser = await authApi.updateProfile(token, data);
          set({ user: updatedUser });
          queryClient.invalidateQueries({ queryKey: queryKeys.users.all });
        } catch (error) {
          throw error;
        }
      },

      followUser: async (userId: number) => {
        const { token } = get();
        if (!token) throw new Error('No hay sesión activa');

        try {
          await api.post(`/api/v1/users/${userId}/follow/`);
          const updatedUser = await authApi.getProfile(token);
          set({ user: updatedUser });
          queryClient.invalidateQueries({ queryKey: queryKeys.social.all });
          queryClient.invalidateQueries({ queryKey: queryKeys.users.all });
        } catch (error) {
          throw error;
        }
      },

      unfollowUser: async (userId: number) => {
        const { token } = get();
        if (!token) throw new Error('No hay sesión activa');

        try {
          await api.post(`/api/v1/users/${userId}/unfollow/`);
          const updatedUser = await authApi.getProfile(token);
          set({ user: updatedUser });
          queryClient.invalidateQueries({ queryKey: queryKeys.social.all });
          queryClient.invalidateQueries({ queryKey: queryKeys.users.all });
        } catch (error) {
          throw error;
        }
      },

      getFollowStatus: async (userId: number) => {
        return api.get(`/api/v1/users/${userId}/follow-status/`);
      },

      getFollowing: async () => {
        const res: any = await api.get('/api/v1/users/following/');
        return Array.isArray(res) ? res : (res?.results || []);
      },

      getFollowers: async () => {
        const res: any = await api.get('/api/v1/users/followers/');
        return Array.isArray(res) ? res : (res?.results || []);
      },
    }),
    {
      name: 'auth-storage',
    }
  )
);