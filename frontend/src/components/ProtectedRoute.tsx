import { Navigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '../store/auth';

interface ProtectedRouteProps {
  children: React.ReactNode;
  requireAuth?: boolean;
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ 
  children, 
  requireAuth = true 
}) => {
  const isAuthenticated = useAuthStore(state => state.isAuthenticated);
  const location = useLocation();

  if (requireAuth && !isAuthenticated) {
    // Usuario no autenticado intentando acceder a ruta protegida
    return <Navigate to="/" state={{ from: location }} replace />;
  }

  if (!requireAuth && isAuthenticated) {
    // Usuario autenticado intentando acceder a ruta pública (login/registro)
    return <Navigate to="/home" replace />;
  }

  return <>{children}</>;
};