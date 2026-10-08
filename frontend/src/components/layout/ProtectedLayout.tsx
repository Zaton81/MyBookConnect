import { Suspense, useState } from 'react';
import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { Header } from './Header';
import { FooterSection } from './Footer';
import { CookieBanner } from '../ui/CookieBanner';
import { BetaFeedbackModal } from '../ui/BetaFeedbackModal';
import { useAuthStore } from '../../store/auth';
import { AudioPlayerBar } from '../audio/AudioPlayerBar';

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
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const location = useLocation();
  const [isFeedbackModalOpen, setIsFeedbackModalOpen] = useState(false);

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

      {/* Botón flotante accesible para feedback de la beta cerrada */}
      <button
        type="button"
        onClick={() => setIsFeedbackModalOpen(true)}
        title="Enviar feedback sobre la beta cerrada"
        aria-label="Enviar feedback sobre la beta"
        className="fixed bottom-5 right-5 z-40 flex items-center gap-2 bg-gradient-to-r from-teal-600 to-emerald-600 hover:from-teal-700 hover:to-emerald-700 text-white text-xs font-semibold px-3 py-2 rounded-full shadow-lg hover:shadow-xl transition-all duration-200 cursor-pointer backdrop-blur-sm"
      >
        <span className="text-sm">🚀</span>
        <span className="hidden sm:inline">Beta Feedback</span>
      </button>

      <AudioPlayerBar />

      <BetaFeedbackModal
        isOpen={isFeedbackModalOpen}
        onClose={() => setIsFeedbackModalOpen(false)}
      />
    </div>
  );
}

export default ProtectedLayout;
