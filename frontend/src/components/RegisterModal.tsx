import React, { useState } from 'react';
import { register as doRegister } from '../lib/auth';
import { useAuth } from '../lib/useAuth';
import { es } from '../locales/es';

function getPasswordErrors(password: string) {
  const errors: string[] = [];
  if (password.length < 8) errors.push('Al menos 8 caracteres');
  if (!/[A-Z]/.test(password)) errors.push('Al menos una letra mayúscula');
  if (!/[a-z]/.test(password)) errors.push('Al menos una letra minúscula');
  if (!/[0-9]/.test(password)) errors.push('Al menos un número');
  if (!/[!@#$%^&*(),.?"':{}|<>\[\]\\/~`_+=;-]/.test(password)) errors.push('Al menos un símbolo');
  return errors;
}

type Props = {
  open: boolean;
  onClose: () => void;
  onRegisterSuccess?: (token: string) => void;
};

export default function RegisterModal({ open, onClose, onRegisterSuccess }: Props) {
  const { saveToken } = useAuth();
  const [email, setEmail] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const passwordErrors = getPasswordErrors(password);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    if (passwordErrors.length > 0) {
      setError('La contraseña no cumple los requisitos: ' + passwordErrors.join(', '));
      setLoading(false);
      return;
    }

    try {
      const data = await doRegister(username, email, password);
      const token = data.access_token || data.token || '';
      saveToken(token);
      if (onRegisterSuccess) onRegisterSuccess(token);
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
        <h3 className="mb-4 text-xl font-semibold">Registro</h3>
        {/* Texto localizado arriba del formulario */}
        <p className="mb-3 text-sm text-gray-700 dark:text-gray-300">{es.form_register.texto}</p>
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

          <label className="mb-2 block text-sm font-medium">Usuario</label>
          <input
            type="text"
            title="username"
            placeholder="Nombre de usuario"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
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

          {password && (
            <div className="mb-3 text-sm">
              <p className="font-medium">La contraseña debe incluir:</p>
              <ul className="mt-1 list-inside list-disc text-sm">
                <li className={password.length >= 8 ? 'text-green-600' : 'text-red-600'}>Al menos 8 caracteres</li>
                <li className={/[A-Z]/.test(password) ? 'text-green-600' : 'text-red-600'}>Al menos una letra mayúscula</li>
                <li className={/[a-z]/.test(password) ? 'text-green-600' : 'text-red-600'}>Al menos una letra minúscula</li>
                <li className={/[0-9]/.test(password) ? 'text-green-600' : 'text-red-600'}>Al menos un número</li>
                <li className={/[!@#$%^&*(),.?"':{}|<>\[\]\\/~`_+=;-]/.test(password) ? 'text-green-600' : 'text-red-600'}>Al menos un símbolo</li>
              </ul>
            </div>
          )}

          {error && <p className="mb-3 text-sm text-red-600">{error}</p>}

          <div className="flex items-center justify-between">
            <button
              type="submit"
              className="rounded bg-green-600 px-4 py-2 text-white disabled:opacity-50"
              disabled={loading}
            >
              {loading ? 'Registrando...' : 'Registrarme'}
            </button>
            <button
              type="button"
              onClick={() => {
                // Placeholder para registro con Google (no implementado)
                window.location.href = '/auth/google';
              }}
              className="ml-3 rounded border px-4 py-2"
            >
              Registrar con Google
            </button>
          </div>
        </form>

        {/* Textos localizados debajo del formulario */}
        <div className="mt-4 text-sm text-gray-600 dark:text-gray-400">
          <p className="mb-1">{es.form_register.detalles}</p>
          <p className="mb-1">{es.form_register.otros_detalles}</p>
        </div>

        <div className="mt-4 flex justify-end">
          <button onClick={onClose} className="text-sm text-gray-500">
            Cerrar
          </button>
        </div>
      </div>
    </div>
  );
}
