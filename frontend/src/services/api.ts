import { api, apiClient } from '../api/client';

export const authApi = {
  async login(username: string, password: string) {
    return apiClient('/api/v1/auth/token/', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
      requireAuth: false,
    });
  },

  async register(username: string, email: string, password: string, password2?: string) {
    return apiClient('/api/v1/auth/register/', {
      method: 'POST',
      body: JSON.stringify({ username, email, password, password2 }),
      requireAuth: false,
    });
  },

  async getProfile(token?: string) {
    const headers = token ? { Authorization: `Bearer ${token}` } : undefined;
    return apiClient('/api/v1/auth/profile/', {
      method: 'GET',
      headers,
    });
  },

  async updateProfile(token: string | undefined, data: FormData | Record<string, any>) {
    const isFormData = data instanceof FormData;
    const headers: Record<string, string> = {};
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    return apiClient('/api/v1/auth/profile/update/', {
      method: 'PATCH',
      headers,
      body: isFormData ? data : JSON.stringify(data),
    });
  },
};