import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { login as doLogin } from '../../../lib/auth';
import { useAuth } from '../../../lib/useAuth';
import { loginSchema, LoginFormData } from '../schemas/authSchemas';
import { GoogleLoginButton } from './GoogleLoginButton';
import { useAuthStore } from '../../../store/auth';

export type LoginModalProps = {
  open: boolean;
  onClose: () => void;
  onLoginSuccess?: (token: string) => void;
};

export default function LoginModal({ open, onClose, onLoginSuccess }: LoginModalProps) {
  const { saveToken } = useAuth();
  const [serverError, setServerError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      email: '',
      password: '',
    },
  });

  const onSubmit = async (data: LoginFormData) => {
    setServerError(null);
    try {
      const resData = await doLogin(data.email, data.password);
      const token = resData.access_token || resData.token || '';
      saveToken(token);
      if (onLoginSuccess) onLoginSuccess(token);
      reset();
      onClose();
    } catch (err: any) {
      setServerError(err.message || 'Error al iniciar sesión');
    }
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl dark:bg-gray-800 border border-gray-100 dark:border-gray-700">
        <h3 className="mb-4 text-xl font-bold text-gray-900 dark:text-white">Iniciar sesión</h3>
        <form onSubmit={handleSubmit(onSubmit)} noValidate>
          <div className="mb-4">
            <label className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
              Email o usuario
            </label>
            <input
              type="text"
              {...register('email')}
              placeholder="tu@ejemplo.com"
              className={`w-full rounded-xl border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500 dark:bg-gray-700 dark:text-white ${
                errors.email ? 'border-red-500 bg-red-50/20' : 'border-gray-300 dark:border-gray-600'
              }`}
            />
            {errors.email && (
              <p className="mt-1 text-xs text-red-600 dark:text-red-400">{errors.email.message}</p>
            )}
          </div>

          <div className="mb-4">
            <label className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
              Contraseña
            </label>
            <input
              type="password"
              {...register('password')}
              placeholder="Contraseña"
              className={`w-full rounded-xl border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500 dark:bg-gray-700 dark:text-white ${
                errors.password ? 'border-red-500 bg-red-50/20' : 'border-gray-300 dark:border-gray-600'
              }`}
            />
            {errors.password && (
              <p className="mt-1 text-xs text-red-600 dark:text-red-400">{errors.password.message}</p>
            )}
          </div>

          {serverError && (
            <p className="mb-4 text-sm text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 p-2.5 rounded-lg border border-red-200 dark:border-red-800">
              {serverError}
            </p>
          )}

          <div className="pt-2 space-y-3">
            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full rounded-xl bg-teal-600 hover:bg-teal-700 px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition-all disabled:opacity-50 cursor-pointer"
            >
              {isSubmitting ? 'Entrando...' : 'Entrar'}
            </button>

            <div className="relative my-2">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-gray-200 dark:border-gray-700" />
              </div>
              <div className="relative flex justify-center text-[11px] uppercase">
                <span className="bg-white dark:bg-gray-800 px-2 text-gray-400">
                  O entra con
                </span>
              </div>
            </div>

            <GoogleLoginButton
              onSuccess={() => {
                const token = useAuthStore.getState().token;
                if (token && onLoginSuccess) onLoginSuccess(token);
                reset();
                onClose();
              }}
              onError={(err) => setServerError(err)}
              label="Continuar con Google"
            />
          </div>
        </form>

        <div className="mt-5 flex justify-end border-t border-gray-100 dark:border-gray-700 pt-3">
          <button
            onClick={() => {
              reset();
              onClose();
            }}
            className="text-xs text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
          >
            Cerrar
          </button>
        </div>
      </div>
    </div>
  );
}
