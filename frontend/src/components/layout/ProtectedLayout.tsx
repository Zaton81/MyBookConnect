import { Suspense } from 'react';
import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { Header } from './Header';
import { FooterSection } from './Footer';
import { CookieBanner } from '../ui/CookieBanner';
import { useAuthStore } from '../../store/auth';

function PageLoadingFallback() {
  return (
    <div className="flex items-center justify-center min-h-[40vh]">
      <div className="text-teal-600 dark:text-teal-400 font-semibold flex items-center gap-2">
        <span className="animate-spin text-2xl">⏳</span>
        <span>Cargando contenido...</span>
      </div>
    </div>
  );
}

export function ProtectedLayout() {
  const isAuthenticated = useAuthStore(state => state.isAuthenticated);
  const location = useLocation();

  if (!isAuthenticated) {
    return <Navigate to="/" state={{ from: location }} replace />;
  }

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 flex flex-col font-sans antialiased">
      <Header />
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

export default ProtectedLayout;
