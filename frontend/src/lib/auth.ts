const API_URL = 'http://localhost:8000/api/v1';

export async function login(username: string, password: string) {
  const res = await fetch(`${API_URL}/auth/token/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  });

  if (!res.ok) {
    const data = await res.json();
    // SimpleJWT devuelve detalles en 'detail' o errores generales
    throw new Error(data.detail || 'Error al iniciar sesión');
  }

  return res.json();
}

export async function register(username: string, email: string, password: string, password2: string) {
  const res = await fetch(`${API_URL}/auth/register/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, email, password, password2 }),
  });

  if (!res.ok) {
    // Intentar parsear errores por campo (DRF devuelve dicts) o mensaje general
    let data: any = null;
    try {
      data = await res.json();
    } catch (e) {
      throw new Error('Error en el registro');
    }

    // Si es un dict con campos, juntarlos en un string para mostrar
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

  return res.json();
}
