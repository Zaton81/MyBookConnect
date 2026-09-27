import { useState, Suspense } from 'react';
import { Outlet } from 'react-router-dom';
import { Header } from './Header';
import { PublicHeader } from './PublicHeader';
import { FooterSection } from './Footer';
import { CookieBanner } from '../ui/CookieBanner';
import { AuthModal } from '../../features/auth';
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

export function PublicLayout() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [authMode, setAuthMode] = useState<'login' | 'register'>('login');

  const handleOpenAuth = (mode: 'login' | 'register') => {
    setAuthMode(mode);
    setIsAuthModalOpen(true);
  };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 flex flex-col font-sans antialiased">
      {isAuthenticated ? (
        <Header />
      ) : (
        <PublicHeader onOpenAuth={handleOpenAuth} />
      )}
      <main className="flex-1 w-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <Suspense fallback={<PageLoadingFallback />}>
          <Outlet />
        </Suspense>
      </main>
      <FooterSection />
      <CookieBanner />

      {/* Modal accesible desde el PublicHeader de cualquier página pública */}
      <AuthModal
        isOpen={isAuthModalOpen}
        initialMode={authMode}
        onClose={() => setIsAuthModalOpen(false)}
      />
    </div>
  );
}

export default PublicLayout;
