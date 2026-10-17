import { useAuthStore } from '../../../store/auth';

/**
 * Hook de autenticación unificado sobre Zustand useAuthStore.
 * Proporciona compatibilidad con métodos auxiliares y acceso reactivo
 * al usuario, token y acciones de autenticación.
 */
export function useAuth() {
  const store = useAuthStore();
  return {
    ...store,
    saveToken: (t: string) => {
      useAuthStore.setState({ token: t, isAuthenticated: true });
    },
    clearToken: () => {
      store.logout();
    },
  };
}

export default useAuth;
