import React, { useState, useEffect } from 'react';
import { es } from '../locales/es';
import { login as doLogin, register as doRegister } from '../lib/auth';
import { useAuth } from '../lib/useAuth';
import { useNavigate } from 'react-router-dom';
import { authApi } from '../services/api';
import { useAuthStore } from '../store/auth';

export default function AuthBox() {
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const { saveToken } = useAuth();

  return (
    <div className="w-full max-w-md rounded bg-white p-6 shadow dark:bg-gray-800">
      {mode === 'login' ? (
        <LoginForm onSwitch={() => setMode('register')} onSuccess={(t: string) => saveToken(t)} />
      ) : (
        <RegisterForm onSwitch={() => setMode('login')} onSuccess={(t: string) => saveToken(t)} />
      )}
    </div>
  );
}

function LoginForm({ onSwitch, onSuccess }: any) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<{ username?: string; password?: string }>({});

  // Validación en tiempo real
  useEffect(() => {
    const errs: { username?: string; password?: string } = {};
    if (username && username.length < 3) errs.username = 'Introduce tu usuario';
    if (password === '') errs.password = 'Introduce tu contraseña';
    setFieldErrors(errs);
  }, [username, password]);

  function validateLoginFields() {
    const errs: { username?: string; password?: string } = {};
    if (username.length < 3) errs.username = 'Introduce tu usuario';
    if (password.length === 0) errs.password = 'Introduce tu contraseña';
    setFieldErrors(errs);
    return Object.keys(errs).length === 0;
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validateLoginFields()) return;
    setLoading(true);
    setError(null);
    try {
  const data = await doLogin(username, password);
  const token = data.access_token || data.token || data.access || '';
  // Guardar token localmente (useAuth)
  onSuccess(token);
  // Actualizar store inmediatamente para activar protecciones/redirecciones
  useAuthStore.setState({ token, isAuthenticated: true });
  // Obtener perfil desde el backend y actualizar usuario en el store
  const user = await authApi.getProfile(token);
  useAuthStore.setState({ user });
  // navegar a home
  navigate('/home');
    } catch (err: any) {
      setError(err.message || 'Error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <h2 className="mb-4 text-2xl font-bold">Inicia sesión</h2>
      <form onSubmit={handleSubmit}>
        <label className="mb-2 block text-sm font-medium">Usuario</label>
        <input title="username" name="username" placeholder="tu_usuario" className="mb-1 w-full rounded border px-3 py-2" value={username} onChange={(e) => setUsername(e.target.value)} required />
        {fieldErrors.username && <p className="mb-2 text-sm text-red-600">{fieldErrors.username}</p>}
        <label className="mb-2 block text-sm font-medium">Contraseña</label>
        <input title="password" name="password" type="password" placeholder="Contraseña" className="mb-1 w-full rounded border px-3 py-2" value={password} onChange={(e) => setPassword(e.target.value)} required />
        {fieldErrors.password && <p className="mb-2 text-sm text-red-600">{fieldErrors.password}</p>}
        {error && <p className="mb-3 text-sm text-red-600">{error}</p>}
        <div className="flex items-center justify-between">
          <button type="submit" className="rounded bg-blue-600 px-4 py-2 text-white" disabled={loading}>{loading ? 'Entrando...' : 'Entrar'}</button>
          <button type="button" onClick={onSwitch} className="ml-3 rounded border px-4 py-2">Registrarse</button>
        </div>
      </form>
    </div>
  );
}

function RegisterForm({ onSwitch, onSuccess }: any) {
  const [email, setEmail] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [passwordConfirm, setPasswordConfirm] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<{ email?: string; username?: string; password?: string }>({});
  const navigate = useNavigate();

  function getPasswordErrors(password: string) {
    const errors: string[] = [];
    if (password.length < 8) errors.push('Al menos 8 caracteres');
    if (!/[A-Z]/.test(password)) errors.push('Al menos una letra mayúscula');
    if (!/[a-z]/.test(password)) errors.push('Al menos una letra minúscula');
    if (!/[0-9]/.test(password)) errors.push('Al menos un número');
    if (!/[!@#$%^&*(),.?"':{}|<>\[\]\\/~`_+=;-]/.test(password)) errors.push('Al menos un símbolo');
    return errors;
  }

  // Validación en tiempo real
  useEffect(() => {
    const errs: { email?: string; username?: string; password?: string } = {};
    if (email && !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) errs.email = 'Introduce un email válido';
    if (username && username.length < 3) errs.username = 'El usuario debe tener al menos 3 caracteres';
    if (password) {
      const pwErrors = getPasswordErrors(password);
      if (pwErrors.length > 0) errs.password = pwErrors.join(', ');
    }
    if (password && passwordConfirm && password !== passwordConfirm) {
      errs.password = (errs.password ? errs.password + '. ' : '') + 'Las contraseñas no coinciden';
    }
    setFieldErrors(errs);
  }, [email, username, password, passwordConfirm]);

  function validateRegisterFields() {
    const errs: { email?: string; username?: string; password?: string } = {};
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) errs.email = 'Introduce un email válido';
    if (username.length < 3) errs.username = 'El usuario debe tener al menos 3 caracteres';
    const pwErrors = getPasswordErrors(password);
    if (pwErrors.length > 0) errs.password = pwErrors.join(', ');
    if (password !== passwordConfirm) errs.password = (errs.password ? errs.password + '. ' : '') + 'Las contraseñas no coinciden';
    setFieldErrors(errs);
    return Object.keys(errs).length === 0;
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (!validateRegisterFields()) return;
    setLoading(true);
    try {
      // First register the user
      await doRegister(username, email, password, passwordConfirm);
      
      // Then immediately login to get token
      const loginResponse = await authApi.login(username, password);
      const token = loginResponse.access;
      if (!token) throw new Error('No se recibió token después del registro');
      
      // Save token locally
      onSuccess(token);
      
      // Update store with token first
      useAuthStore.setState({ token, isAuthenticated: true });
      
      // Get profile
      const user = await authApi.getProfile(token);
      useAuthStore.setState({ user });
      
      // Navigate to profile edit
      navigate('/profile/edit');
    } catch (err: any) {
      const msg = err?.message || 'Error';
      // Intentar parsear mensajes en formato 'field: msg | field2: msg2'
      if (typeof msg === 'string' && msg.includes(':')) {
        const parts = msg.split('|').map(p => p.trim());
        const newFieldErrors: any = {};
        parts.forEach(part => {
          const idx = part.indexOf(':');
          if (idx > -1) {
            const key = part.slice(0, idx).trim();
            const value = part.slice(idx + 1).trim();
            // Normalizar nombre de campo 'password' al input 'password'
            newFieldErrors[key] = value;
          }
        });
        if (Object.keys(newFieldErrors).length > 0) {
          setFieldErrors((prev) => ({ ...prev, ...newFieldErrors }));
          setError(null);
        } else {
          setError(msg);
        }
      } else {
        setError(msg);
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <h2 className="mb-4 text-2xl font-bold">{es.form_register.texto}</h2>
      <form onSubmit={handleSubmit}>
  <label className="mb-2 block text-sm font-medium">Email</label>
  <input title="email" placeholder="tu@ejemplo.com" className="mb-1 w-full rounded border px-3 py-2" value={email} onChange={(e) => setEmail(e.target.value)} required />
  {fieldErrors.email && <p className="mb-2 text-sm text-red-600">{fieldErrors.email}</p>}
  <label className="mb-2 block text-sm font-medium">Usuario</label>
  <input title="username" placeholder="Nombre de usuario" className="mb-1 w-full rounded border px-3 py-2" value={username} onChange={(e) => setUsername(e.target.value)} required />
  {fieldErrors.username && <p className="mb-2 text-sm text-red-600">{fieldErrors.username}</p>}
  <label className="mb-2 block text-sm font-medium">Contraseña</label>
  <input title="password" type="password" placeholder="Contraseña" className="mb-1 w-full rounded border px-3 py-2" value={password} onChange={(e) => setPassword(e.target.value)} required />
  {fieldErrors.password && <p className="mb-2 text-sm text-red-600">{fieldErrors.password}</p>}
  <label className="mb-2 block text-sm font-medium">Confirmar Contraseña</label>
  <input title="password_confirm" type="password" placeholder="Confirmar Contraseña" className="mb-1 w-full rounded border px-3 py-2" value={passwordConfirm} onChange={(e) => setPasswordConfirm(e.target.value)} required />
        {error && <p className="mb-3 text-sm text-red-600">{error}</p>}
        <div className="flex items-center justify-between">
          <button type="submit" className="rounded bg-green-600 px-4 py-2 text-white" disabled={loading}>{loading ? 'Registrando...' : 'Registrarme'}</button>
          <button type="button" onClick={onSwitch} className="ml-3 rounded border px-4 py-2">Volver a Iniciar sesión</button>
        </div>
      </form>
      <div className="mt-4 text-sm text-gray-600 dark:text-gray-400">
        <p className="mb-1">{es.form_register.detalles}</p>
        <p className="mb-1">{es.form_register.otros_detalles}</p>
      </div>
    </div>
  );
}
