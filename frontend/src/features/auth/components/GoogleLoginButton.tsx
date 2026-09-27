import React, { useState } from 'react';
import { useAuthStore } from '../../../store/auth';

interface GoogleLoginButtonProps {
  onSuccess?: () => void;
  onError?: (error: string) => void;
  label?: string;
  disabled?: boolean;
}

export const GoogleLoginButton: React.FC<GoogleLoginButtonProps> = ({
  onSuccess,
  onError,
  label = 'Continuar con Google',
  disabled = false,
}) => {
  const [isLoading, setIsLoading] = useState(false);
  const loginWithGoogle = useAuthStore((state) => state.loginWithGoogle);

  const handleClick = async () => {
    if (disabled || isLoading) return;
    setIsLoading(true);

    try {
      // 1. Comprobar si Google Identity Services está disponible en window y tiene Client ID
      const googleClientId = (import.meta as any).env?.VITE_GOOGLE_CLIENT_ID;

      if (typeof window !== 'undefined' && (window as any).google?.accounts?.id && googleClientId) {
        // Flujo real de Google Identity Services
        const client = (window as any).google.accounts.oauth2.initTokenClient({
          client_id: googleClientId,
          scope: 'email profile openid',
          callback: async (response: any) => {
            if (response?.access_token || response?.credential) {
              const token = response.credential || response.access_token;
              await loginWithGoogle(token);
              if (onSuccess) onSuccess();
            } else {
              throw new Error('No se pudo completar la autenticación con Google');
            }
          },
        });
        client.requestAccessToken();
        setIsLoading(false);
        return;
      }

      // 2. Modo Desarrollo / Pruebas cuando no hay Google Client ID configurado
      // El backend acepta tokens de prueba bajo el formato "test-google-token-{email}"
      const testEmail = prompt(
        'Iniciar sesión con Google (Modo desarrollo / test):\nIntroduce tu correo electrónico de Google:',
        'lector.google@gmail.com'
      );

      if (!testEmail || !testEmail.trim()) {
        setIsLoading(false);
        return;
      }

      const mockToken = `test-google-token-${testEmail.trim()}`;
      await loginWithGoogle(mockToken);
      if (onSuccess) onSuccess();
    } catch (err: any) {
      const msg = err?.message || 'Error al iniciar sesión con Google';
      if (onError) onError(msg);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <button
      type="button"
      onClick={handleClick}
      disabled={disabled || isLoading}
      className="w-full flex items-center justify-center gap-3 py-2.5 px-4 bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 text-sm font-semibold rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm hover:shadow transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-slate-300 dark:focus:ring-slate-600 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
      title="Iniciar sesión de forma segura con tu cuenta de Google"
    >
      {isLoading ? (
        <svg
          className="animate-spin h-5 w-5 text-slate-600 dark:text-slate-300"
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
        >
          <circle
            className="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            strokeWidth="4"
          />
          <path
            className="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
          />
        </svg>
      ) : (
        <svg className="w-5 h-5 flex-shrink-0" viewBox="0 0 24 24">
          <path
            fill="#4285F4"
            d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
          />
          <path
            fill="#34A853"
            d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
          />
          <path
            fill="#FBBC05"
            d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
          />
          <path
            fill="#EA4335"
            d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
          />
        </svg>
      )}
      <span>{isLoading ? 'Conectando con Google...' : label}</span>
    </button>
  );
};

export default GoogleLoginButton;
