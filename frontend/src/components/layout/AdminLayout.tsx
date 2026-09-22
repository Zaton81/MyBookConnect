import { Suspense } from 'react';
import { Link, Navigate, Outlet, useLocation } from 'react-router-dom';
import { Header } from './Header';
import { FooterSection } from './Footer';
import { CookieBanner } from '../ui/CookieBanner';
import { useAuthStore } from '../../store/auth';

function PageLoadingFallback() {
  return (
    <div className="flex items-center justify-center min-h-[40vh]">
      <div className="text-teal-600 dark:text-teal-400 font-semibold flex items-center gap-2">
        <span className="animate-spin text-2xl">⏳</span>
        <span>Cargando panel de administración...</span>
      </div>
    </div>
  );
}

export function AdminLayout() {
  const { isAuthenticated, user } = useAuthStore();
  const location = useLocation();

  if (!isAuthenticated) {
    return <Navigate to="/" state={{ from: location }} replace />;
  }

  const isAuthorized = Boolean(
    user && (user.is_staff || user.is_superuser || user.role === 'ADMIN' || user.role === 'MODERATOR')
  );

  if (!isAuthorized) {
    return <Navigate to="/home" replace />;
  }

  const roleLabel = user?.is_superuser
    ? 'Superusuario'
    : user?.role === 'ADMIN' || user?.is_staff
    ? 'Administrador'
    : 'Moderador';

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 flex flex-col font-sans antialiased">
      <Header />

      {/* Barra de contexto administrativo */}
      <div className="bg-slate-900 text-slate-200 border-b border-slate-800 px-4 sm:px-6 lg:px-8 py-2.5">
        <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-3 text-xs">
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold bg-rose-900/80 text-rose-200 border border-rose-700">
              🛡️ {roleLabel}
            </span>
            <span className="text-slate-400 font-medium">
              Panel de Administración y Moderación de My Book Social
            </span>
          </div>
          <div className="flex items-center gap-3">
            <Link
              to="/home"
              className="text-slate-300 hover:text-white transition-colors underline underline-offset-4"
            >
              ← Volver al portal de usuario
            </Link>
          </div>
        </div>
      </div>

      <main className="flex-1 w-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <Suspense fallback={<PageLoadingFallback />}>
          <Outlet />
        </Suspense>
      </main>
      <FooterSection />
      <CookieBanner />
    </div>
  );
}

export default AdminLayout;
