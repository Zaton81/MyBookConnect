import React, { useState } from 'react';
import { login as doLogin } from '../lib/auth';
import { useAuth } from '../lib/useAuth';

type Props = {
  open: boolean;
  onClose: () => void;
  onLoginSuccess?: (token: string) => void;
};

function getPasswordErrors(password: string) {
  const errors: string[] = [];
  if (password.length < 8) errors.push('Al menos 8 caracteres');
  if (!/[A-Z]/.test(password)) errors.push('Al menos una letra mayúscula');
  if (!/[a-z]/.test(password)) errors.push('Al menos una letra minúscula');
  if (!/[0-9]/.test(password)) errors.push('Al menos un número');
  if (!/[!@#$%^&*(),.?"':{}|<>\[\]\\/~`_+=;-]/.test(password)) errors.push('Al menos un símbolo');
  return errors;
}

export default function LoginModal({ open, onClose, onLoginSuccess }: Props) {
  const { saveToken } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const passwordErrors = getPasswordErrors(password);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const data = await doLogin(email, password);
      const token = data.access_token || data.token || '';
      saveToken(token);
      if (onLoginSuccess) onLoginSuccess(token);
      onClose();
    } catch (err: any) {
      setError(err.message || 'Error');
    } finally {
      setLoading(false);
    }
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="w-full max-w-md rounded bg-white p-6 dark:bg-gray-800">
        <h3 className="mb-4 text-xl font-semibold">Iniciar sesión</h3>
        <form onSubmit={handleSubmit}>
          <label className="mb-2 block text-sm font-medium">Email</label>
          <input
            type="email"
            title="email"
            placeholder="tu@ejemplo.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="mb-3 w-full rounded border px-3 py-2"
            required
          />

          <label className="mb-2 block text-sm font-medium">Contraseña</label>
          <input
            type="password"
            title="password"
            placeholder="Contraseña"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="mb-3 w-full rounded border px-3 py-2"
            required
          />

          {error && <p className="mb-3 text-sm text-red-600">{error}</p>}
          {password && passwordErrors.length > 0 && (
            <div className="mb-3 text-sm text-yellow-700">
              <p className="font-medium">Advertencia: la contraseña introducida parece débil:</p>
              <ul className="mt-1 list-inside list-disc text-sm">
                {passwordErrors.map((e) => (
                  <li key={e} className="text-yellow-700">{e}</li>
                ))}
              </ul>
            </div>
          )}

          <div className="flex items-center justify-between">
            <button
              type="submit"
              className="rounded bg-blue-600 px-4 py-2 text-white disabled:opacity-50"
              disabled={loading}
            >
              {loading ? 'Entrando...' : 'Entrar'}
            </button>
            <button
              type="button"
              onClick={() => {
                // Placeholder para login con Google (no implementado)
                window.location.href = '/auth/google';
              }}
              className="ml-3 rounded border px-4 py-2"
            >
              Entrar con Google
            </button>
          </div>
        </form>

        <div className="mt-4 flex justify-end">
          <button onClick={onClose} className="text-sm text-gray-500">
            Cerrar
          </button>
        </div>
      </div>
    </div>
  );
}
