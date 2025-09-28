const API_URL = 'http://localhost:8000/api/v1';

export const authApi = {
  async login(username: string, password: string) {
    console.log('Intentando login con username:', username);
    const response = await fetch(`${API_URL}/auth/token/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ username, password }),
    });

    if (!response.ok) {
      let error: any = null;
      try { error = await response.json(); } catch (e) {}
      console.error('Error en login:', error);
      throw new Error(error?.detail || 'Error al iniciar sesión');
    }

    const data = await response.json();
    console.log('Respuesta login:', data);
    return data;
  },

  async register(username: string, email: string, password: string, password2?: string) {
    const response = await fetch(`${API_URL}/auth/register/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ username, email, password, password2 }),
    });

    if (!response.ok) {
      let data: any = null;
      try { data = await response.json(); } catch (e) {}
      if (data && typeof data === 'object') {
        const parts: string[] = [];
        for (const key of Object.keys(data)) {
          const val = data[key];
          if (Array.isArray(val)) parts.push(`${key}: ${val.join(', ')}`);
          else parts.push(`${key}: ${String(val)}`);
        }
        throw new Error(parts.join(' | '));
      }
      throw new Error(data?.detail || 'Error en el registro');
    }

    return response.json();
  },

  async getProfile(token: string) {
    console.log('Obteniendo perfil con token:', token);
    const response = await fetch(`${API_URL}/auth/profile/`, {
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error('Error al obtener el perfil');
    }

    return response.json();
  },

  async updateProfile(token: string, data: any) {
    const response = await fetch(`${API_URL}/auth/profile/update/`, {
      method: 'PATCH',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      throw new Error('Error al actualizar el perfil');
    }

    return response.json();
  },
};