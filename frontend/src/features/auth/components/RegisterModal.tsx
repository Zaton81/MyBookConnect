import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { register as doRegister } from '../../../lib/auth';
import { useAuth } from '../../../lib/useAuth';
import { es } from '../../../locales/es';
import { registerSchema, RegisterFormData } from '../schemas/authSchemas';

export type RegisterModalProps = {
  open: boolean;
  onClose: () => void;
  onRegisterSuccess?: (token: string) => void;
};

export default function RegisterModal({ open, onClose, onRegisterSuccess }: RegisterModalProps) {
  const { saveToken } = useAuth();
  const [serverError, setServerError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    watch,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<RegisterFormData>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      username: '',
      email: '',
      password: '',
    },
  });

  const passwordValue = watch('password') || '';

  const passwordChecks = [
    { label: 'Al menos 8 caracteres', passed: passwordValue.length >= 8 },
    { label: 'Una letra mayúscula', passed: /[A-Z]/.test(passwordValue) },
    { label: 'Una letra minúscula', passed: /[a-z]/.test(passwordValue) },
    { label: 'Un número', passed: /[0-9]/.test(passwordValue) },
    { label: 'Un símbolo especial', passed: /[!@#$%^&*(),.?"':{}|<>\[\]\\/~`_+=;-]/.test(passwordValue) },
  ];

  const onSubmit = async (data: RegisterFormData) => {
    setServerError(null);
    try {
      const resData = await doRegister(data.username, data.email, data.password);
      const token = resData.access_token || resData.token || '';
      saveToken(token);
      if (onRegisterSuccess) onRegisterSuccess(token);
      reset();
      onClose();
    } catch (err: any) {
      setServerError(err.message || 'Error en el registro');
    }
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl dark:bg-gray-800 border border-gray-100 dark:border-gray-700 max-h-[90vh] overflow-y-auto">
        <h3 className="mb-2 text-xl font-bold text-gray-900 dark:text-white">Registro</h3>
        <p className="mb-4 text-xs text-gray-600 dark:text-gray-400">{es.form_register.texto}</p>

        <form onSubmit={handleSubmit(onSubmit)} noValidate>
          <div className="mb-3">
            <label className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
              Email
            </label>
            <input
              type="email"
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

          <div className="mb-3">
            <label className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
              Usuario
            </label>
            <input
              type="text"
              {...register('username')}
              placeholder="Nombre de usuario"
              className={`w-full rounded-xl border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500 dark:bg-gray-700 dark:text-white ${
                errors.username ? 'border-red-500 bg-red-50/20' : 'border-gray-300 dark:border-gray-600'
              }`}
            />
            {errors.username && (
              <p className="mt-1 text-xs text-red-600 dark:text-red-400">{errors.username.message}</p>
            )}
          </div>

          <div className="mb-3">
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

            {passwordValue && (
              <div className="mt-2 p-2.5 bg-gray-50 dark:bg-gray-700/50 rounded-lg text-xs space-y-1">
                <p className="font-medium text-gray-700 dark:text-gray-300">La contraseña debe incluir:</p>
                {passwordChecks.map((req, idx) => (
                  <div key={idx} className="flex items-center gap-1.5">
                    <span>{req.passed ? '✅' : '⚪'}</span>
                    <span className={req.passed ? 'text-green-600 font-medium' : 'text-gray-400'}>
                      {req.label}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {serverError && (
            <p className="mb-3 text-sm text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 p-2.5 rounded-lg border border-red-200 dark:border-red-800">
              {serverError}
            </p>
          )}

          <div className="flex items-center justify-between pt-2">
            <button
              type="submit"
              disabled={isSubmitting}
              className="rounded-xl bg-teal-600 hover:bg-teal-700 px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition-all disabled:opacity-50 cursor-pointer"
            >
              {isSubmitting ? 'Registrando...' : 'Registrarme'}
            </button>
            <button
              type="button"
              onClick={() => {
                window.location.href = '/auth/google';
              }}
              className="rounded-xl border border-gray-300 dark:border-gray-600 px-4 py-2.5 text-xs font-medium hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
            >
              Registrar con Google
            </button>
          </div>
        </form>

        <div className="mt-4 text-xs text-gray-500 dark:text-gray-400 border-t border-gray-100 dark:border-gray-700 pt-3">
          <p className="mb-1">{es.form_register.detalles}</p>
          <p>{es.form_register.otros_detalles}</p>
        </div>

        <div className="mt-3 flex justify-end">
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
