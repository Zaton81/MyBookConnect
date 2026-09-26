import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useAuthStore } from '../../../store/auth';
import { registerSchema, RegisterFormData } from '../schemas/authSchemas';
import { GoogleLoginButton } from '../components/GoogleLoginButton';

export const Register = () => {
  const navigate = useNavigate();
  const registerAction = useAuthStore((state) => state.register);
  const [serverError, setServerError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    watch,
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
    {
      label: 'Un símbolo especial',
      passed: /[!@#$%^&*(),.?"':{}|<>\[\]\\/~`_+=;-]/.test(passwordValue),
    },
  ];

  const onSubmit = async (data: RegisterFormData) => {
    setServerError(null);
    try {
      await registerAction(data.username, data.email, data.password);
      navigate('/profile/edit');
    } catch (err) {
      setServerError(err instanceof Error ? err.message : 'Error en el registro');
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div>
          <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">Crea tu cuenta</h2>
        </div>
        <form className="mt-8 space-y-5" onSubmit={handleSubmit(onSubmit)} noValidate>
          <div>
            <label htmlFor="username" className="block text-sm font-medium text-gray-700 mb-1">
              Nombre de usuario
            </label>
            <input
              id="username"
              type="text"
              {...register('username')}
              className={`appearance-none relative block w-full px-3 py-2 border rounded-md placeholder-gray-400 text-gray-900 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm ${
                errors.username ? 'border-red-500 bg-red-50/30' : 'border-gray-300'
              }`}
              placeholder="Nombre de usuario"
            />
            {errors.username && (
              <p className="mt-1 text-xs text-red-600">{errors.username.message}</p>
            )}
          </div>

          <div>
            <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">
              Email
            </label>
            <input
              id="email"
              type="email"
              {...register('email')}
              className={`appearance-none relative block w-full px-3 py-2 border rounded-md placeholder-gray-400 text-gray-900 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm ${
                errors.email ? 'border-red-500 bg-red-50/30' : 'border-gray-300'
              }`}
              placeholder="Email"
            />
            {errors.email && <p className="mt-1 text-xs text-red-600">{errors.email.message}</p>}
          </div>

          <div>
            <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-1">
              Contraseña
            </label>
            <input
              id="password"
              type="password"
              {...register('password')}
              className={`appearance-none relative block w-full px-3 py-2 border rounded-md placeholder-gray-400 text-gray-900 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm ${
                errors.password ? 'border-red-500 bg-red-50/30' : 'border-gray-300'
              }`}
              placeholder="Contraseña"
            />
            {errors.password && (
              <p className="mt-1 text-xs text-red-600">{errors.password.message}</p>
            )}

            {/* Comprobación de fortaleza reactiva */}
            {passwordValue && (
              <div className="mt-3 p-3 bg-gray-100 rounded-lg text-xs space-y-1">
                <p className="font-semibold text-gray-700 mb-1">Requisitos de contraseña:</p>
                {passwordChecks.map((req, idx) => (
                  <div key={idx} className="flex items-center gap-1.5">
                    <span>{req.passed ? '✅' : '⚪'}</span>
                    <span className={req.passed ? 'text-green-700 font-medium' : 'text-gray-500'}>
                      {req.label}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {serverError && (
            <div className="text-red-600 text-sm text-center bg-red-50 p-2.5 rounded-lg border border-red-200">
              {serverError}
            </div>
          )}

          <div>
            <button
              type="submit"
              disabled={isSubmitting}
              className="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:bg-indigo-400 cursor-pointer"
            >
              {isSubmitting ? 'Registrando...' : 'Registrarse'}
            </button>
          </div>

          <div className="relative my-4">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-gray-300 dark:border-slate-700" />
            </div>
            <div className="relative flex justify-center text-xs uppercase">
              <span className="bg-white dark:bg-slate-800 px-2 text-gray-500 dark:text-slate-400">
                O regístrate con
              </span>
            </div>
          </div>

          <GoogleLoginButton
            onSuccess={() => navigate('/')}
            onError={(err) => setServerError(err)}
            label="Continuar con Google"
          />
        </form>
      </div>
    </div>
  );
};

export default Register;
