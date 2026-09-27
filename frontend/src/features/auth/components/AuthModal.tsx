import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { login as doLogin, register as doRegister } from '../../../lib/auth';
import { useAuth } from '../../../lib/useAuth';
import { useAuthStore } from '../../../store/auth';
import { authApi } from '../../../services/api';
import { GoogleLoginButton } from './GoogleLoginButton';

export interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  initialMode?: 'login' | 'register';
  onSuccess?: (token: string) => void;
}

export function AuthModal({
  isOpen,
  onClose,
  initialMode = 'login',
  onSuccess,
}: AuthModalProps) {
  const [mode, setMode] = useState<'login' | 'register'>(initialMode);
  const { saveToken } = useAuth();
  const navigate = useNavigate();

  // Sincronizar modo inicial si cambia prop
  useEffect(() => {
    if (isOpen) {
      setMode(initialMode);
    }
  }, [isOpen, initialMode]);

  // Cerrar con Escape y bloquear scroll del body
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    if (isOpen) {
      document.body.style.overflow = 'hidden';
      window.addEventListener('keydown', handleKeyDown);
    }
    return () => {
      document.body.style.overflow = '';
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="auth-modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/75 backdrop-blur-md animate-fade-in transition-all"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="relative w-full max-w-md rounded-3xl bg-white dark:bg-slate-900 border border-slate-100 dark:border-slate-800 shadow-2xl p-6 sm:p-8 overflow-hidden transform transition-all">
        {/* Glow decorativo de fondo */}
        <div className="absolute -top-24 -right-24 w-48 h-48 bg-teal-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute -bottom-24 -left-24 w-48 h-48 bg-emerald-500/10 rounded-full blur-3xl pointer-events-none" />

        {/* Botón cerrar */}
        <button
          onClick={onClose}
          aria-label="Cerrar ventana"
          className="absolute top-5 right-5 p-2 rounded-full text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors cursor-pointer"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>

        {/* Cabecera y Tabs de alternancia */}
        <div className="text-center mb-6">
          <div className="inline-flex items-center gap-2 mb-3">
            <span className="text-2xl">📚</span>
            <span className="font-extrabold text-xl text-slate-900 dark:text-white tracking-tight">
              MyBook<span className="text-teal-600 dark:text-teal-400">Social</span>
            </span>
          </div>

          <div className="flex p-1 bg-slate-100 dark:bg-slate-800/80 rounded-2xl max-w-xs mx-auto border border-slate-200/60 dark:border-slate-700/60">
            <button
              type="button"
              onClick={() => setMode('login')}
              className={`flex-1 py-2 text-xs sm:text-sm font-bold rounded-xl transition-all ${
                mode === 'login'
                  ? 'bg-white dark:bg-slate-900 text-teal-600 dark:text-teal-400 shadow-sm'
                  : 'text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200'
              }`}
            >
              Iniciar Sesión
            </button>
            <button
              type="button"
              onClick={() => setMode('register')}
              className={`flex-1 py-2 text-xs sm:text-sm font-bold rounded-xl transition-all ${
                mode === 'register'
                  ? 'bg-white dark:bg-slate-900 text-teal-600 dark:text-teal-400 shadow-sm'
                  : 'text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200'
              }`}
            >
              Crear Cuenta
            </button>
          </div>
        </div>

        {/* Contenido del formulario */}
        {mode === 'login' ? (
          <ModalLoginForm
            onSuccess={(token) => {
              saveToken(token);
              if (onSuccess) onSuccess(token);
              onClose();
              navigate('/home');
            }}
            onSwitchToRegister={() => setMode('register')}
          />
        ) : (
          <ModalRegisterForm
            onSuccess={(token) => {
              saveToken(token);
              if (onSuccess) onSuccess(token);
              onClose();
              navigate('/home');
            }}
            onSwitchToLogin={() => setMode('login')}
          />
        )}
      </div>
    </div>
  );
}

function ModalLoginForm({
  onSuccess,
  onSwitchToRegister,
}: {
  onSuccess: (token: string) => void;
  onSwitchToRegister: () => void;
}) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim() || !password) {
      setError('Por favor, completa todos los campos.');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const data = await doLogin(username.trim(), password);
      const token = data.access_token || data.token || data.access || '';
      useAuthStore.setState({ token, isAuthenticated: true });
      try {
        const user = await authApi.getProfile(token);
        useAuthStore.setState({ user });
      } catch (e) {
        // perfil opcional
      }
      onSuccess(token);
    } catch (err: any) {
      setError(err.message || 'Error al iniciar sesión. Revisa tus credenciales.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
          Usuario o Email
        </label>
        <div className="relative">
          <input
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="ej. lector_apasionado"
            required
            className="w-full px-4 py-2.5 rounded-xl border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent transition-all"
          />
        </div>
      </div>

      <div>
        <div className="flex items-center justify-between mb-1.5">
          <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300">
            Contraseña
          </label>
        </div>
        <div className="relative">
          <input
            type={showPassword ? 'text' : 'password'}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••"
            required
            className="w-full px-4 py-2.5 rounded-xl border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent pr-10 transition-all"
          />
          <button
            type="button"
            onClick={() => setShowPassword(!showPassword)}
            className="absolute inset-y-0 right-0 pr-3 flex items-center text-xs text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 cursor-pointer"
          >
            {showPassword ? 'Ocultar' : 'Ver'}
          </button>
        </div>
      </div>

      {error && (
        <div className="p-3 rounded-xl bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-800 text-red-600 dark:text-red-400 text-xs font-medium">
          {error}
        </div>
      )}

      <button
        type="submit"
        disabled={loading}
        className="w-full py-3 px-4 rounded-xl font-bold text-sm text-white bg-gradient-to-r from-teal-600 to-emerald-600 hover:from-teal-500 hover:to-emerald-500 shadow-lg shadow-teal-700/20 focus:outline-none focus:ring-2 focus:ring-teal-500 transition-all disabled:opacity-60 cursor-pointer"
      >
        {loading ? 'Iniciando sesión...' : 'Entrar a MyBookSocial'}
      </button>

      <div className="relative my-4">
        <div className="absolute inset-0 flex items-center">
          <div className="w-full border-t border-slate-200 dark:border-slate-800" />
        </div>
        <div className="relative flex justify-center text-xs uppercase">
          <span className="bg-white dark:bg-slate-900 px-3 text-slate-400 font-semibold tracking-wider">
            O continúa con
          </span>
        </div>
      </div>

      <GoogleLoginButton
        onSuccess={() => {
          const token = useAuthStore.getState().token;
          if (token) onSuccess(token);
        }}
        onError={(err) => setError(err)}
        label="Acceder con Google"
      />

      <p className="text-center text-xs text-slate-500 dark:text-slate-400 mt-4">
        ¿Aún no tienes cuenta?{' '}
        <button
          type="button"
          onClick={onSwitchToRegister}
          className="text-teal-600 dark:text-teal-400 font-bold hover:underline cursor-pointer"
        >
          Regístrate gratis
        </button>
      </p>
    </form>
  );
}

function ModalRegisterForm({
  onSuccess,
  onSwitchToLogin,
}: {
  onSuccess: (token: string) => void;
  onSwitchToLogin: () => void;
}) {
  const [email, setEmail] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [passwordConfirm, setPasswordConfirm] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const passwordChecks = [
    { label: '8+ car.', passed: password.length >= 8 },
    { label: 'Mayús.', passed: /[A-Z]/.test(password) },
    { label: 'Núm.', passed: /[0-9]/.test(password) },
    { label: 'Símbolo', passed: /[!@#$%^&*(),.?"':{}|<>\[\]\\/~`_+=;-]/.test(password) },
  ];

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim() || !email.trim() || !password) {
      setError('Por favor, completa todos los campos.');
      return;
    }
    if (password !== passwordConfirm) {
      setError('Las contraseñas no coinciden.');
      return;
    }
    const allPassed = passwordChecks.every((c) => c.passed);
    if (!allPassed) {
      setError('La contraseña debe tener al menos 8 caracteres, mayúscula, número y símbolo.');
      return;
    }

    setLoading(true);
    setError(null);
    try {
      await doRegister(username.trim(), email.trim(), password, passwordConfirm);
      const loginResponse = await authApi.login(username.trim(), password);
      const token = loginResponse.access;
      if (!token) throw new Error('No se recibió token tras el registro.');

      useAuthStore.setState({ token, isAuthenticated: true });
      try {
        const user = await authApi.getProfile(token);
        useAuthStore.setState({ user });
      } catch (e) {
        // perfil opcional
      }
      onSuccess(token);
    } catch (err: any) {
      setError(err.message || 'Error durante el registro. Intenta con otro usuario o email.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-3.5">
      <div>
        <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
          Nombre de usuario
        </label>
        <input
          type="text"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          placeholder="ej. lector_viajero"
          required
          className="w-full px-3.5 py-2 rounded-xl border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-white text-xs sm:text-sm focus:outline-none focus:ring-2 focus:ring-teal-500 transition-all"
        />
      </div>

      <div>
        <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
          Correo electrónico
        </label>
        <input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="tu@correo.com"
          required
          className="w-full px-3.5 py-2 rounded-xl border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-white text-xs sm:text-sm focus:outline-none focus:ring-2 focus:ring-teal-500 transition-all"
        />
      </div>

      <div className="grid grid-cols-2 gap-2">
        <div>
          <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
            Contraseña
          </label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••"
            required
            className="w-full px-3.5 py-2 rounded-xl border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-white text-xs sm:text-sm focus:outline-none focus:ring-2 focus:ring-teal-500 transition-all"
          />
        </div>
        <div>
          <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
            Confirmar
          </label>
          <input
            type="password"
            value={passwordConfirm}
            onChange={(e) => setPasswordConfirm(e.target.value)}
            placeholder="••••••••"
            required
            className="w-full px-3.5 py-2 rounded-xl border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-white text-xs sm:text-sm focus:outline-none focus:ring-2 focus:ring-teal-500 transition-all"
          />
        </div>
      </div>

      {/* Indicadores de fortaleza de contraseña */}
      {password && (
        <div className="flex items-center gap-1.5 flex-wrap pt-0.5">
          {passwordChecks.map((c, i) => (
            <span
              key={i}
              className={`text-[10px] px-2 py-0.5 rounded-full font-medium transition-colors ${
                c.passed
                  ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-300'
                  : 'bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400'
              }`}
            >
              {c.passed ? '✓' : '•'} {c.label}
            </span>
          ))}
        </div>
      )}

      {error && (
        <div className="p-2.5 rounded-xl bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-800 text-red-600 dark:text-red-400 text-xs font-medium">
          {error}
        </div>
      )}

      <button
        type="submit"
        disabled={loading}
        className="w-full py-2.5 px-4 rounded-xl font-bold text-sm text-white bg-gradient-to-r from-teal-600 to-emerald-600 hover:from-teal-500 hover:to-emerald-500 shadow-lg shadow-teal-700/20 focus:outline-none focus:ring-2 focus:ring-teal-500 transition-all disabled:opacity-60 cursor-pointer mt-1"
      >
        {loading ? 'Creando cuenta...' : 'Crear mi cuenta gratis'}
      </button>

      <p className="text-center text-xs text-slate-500 dark:text-slate-400 pt-1">
        ¿Ya eres miembro?{' '}
        <button
          type="button"
          onClick={onSwitchToLogin}
          className="text-teal-600 dark:text-teal-400 font-bold hover:underline cursor-pointer"
        >
          Inicia sesión aquí
        </button>
      </p>
    </form>
  );
}

export default AuthModal;
