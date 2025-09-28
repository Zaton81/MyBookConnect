import { useState } from 'react';

export function useAuth() {
  const [token, setToken] = useState<string | null>(
    typeof window !== 'undefined' ? localStorage.getItem('token') : null
  );

  function saveToken(t: string) {
    setToken(t);
    if (typeof window !== 'undefined') localStorage.setItem('token', t);
  }

  function clearToken() {
    setToken(null);
    if (typeof window !== 'undefined') localStorage.removeItem('token');
  }

  return { token, saveToken, clearToken };
}
