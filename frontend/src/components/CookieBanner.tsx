import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';

export interface CookiePreferences {
  necessary: boolean;
  analytics: boolean;
  advertising: boolean; // Amazon affiliate & ad cookies
  timestamp: string;
}

const STORAGE_KEY = 'mbc_cookie_consent';

export function getStoredCookieConsent(): CookiePreferences | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

export function saveCookieConsent(prefs: Omit<CookiePreferences, 'timestamp'>): CookiePreferences {
  const full: CookiePreferences = {
    ...prefs,
    necessary: true,
    timestamp: new Date().toISOString(),
  };
  localStorage.setItem(STORAGE_KEY, JSON.stringify(full));
  window.dispatchEvent(new CustomEvent('mbc:cookie-consent-updated', { detail: full }));
  return full;
}

export function openCookiePreferences(): void {
  window.dispatchEvent(new CustomEvent('mbc:open-cookie-preferences'));
}

export function CookieBanner() {
  const [isVisible, setIsVisible] = useState(false);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [analytics, setAnalytics] = useState(true);
  const [advertising, setAdvertising] = useState(true);

  useEffect(() => {
    const saved = getStoredCookieConsent();
    if (!saved) {
      // Small delay for smooth entry animation
      const timer = setTimeout(() => setIsVisible(true), 600);
      return () => clearTimeout(timer);
    } else {
      setAnalytics(saved.analytics);
      setAdvertising(saved.advertising);
    }
  }, []);

  useEffect(() => {
    const handleOpenModal = () => {
      const saved = getStoredCookieConsent();
      if (saved) {
        setAnalytics(saved.analytics);
        setAdvertising(saved.advertising);
      }
      setIsModalOpen(true);
    };

    window.addEventListener('mbc:open-cookie-preferences', handleOpenModal);
    return () => window.removeEventListener('mbc:open-cookie-preferences', handleOpenModal);
  }, []);

  const handleAcceptAll = () => {
    saveCookieConsent({ necessary: true, analytics: true, advertising: true });
    setIsVisible(false);
    setIsModalOpen(false);
  };

  const handleRejectNonEssential = () => {
    saveCookieConsent({ necessary: true, analytics: false, advertising: false });
    setIsVisible(false);
    setIsModalOpen(false);
  };

  const handleSaveCustom = () => {
    saveCookieConsent({ necessary: true, analytics, advertising });
    setIsVisible(false);
    setIsModalOpen(false);
  };

  return (
    <>
      {/* Floating Sticky Bottom Banner */}
      {isVisible && !isModalOpen && (
        <aside
          role="dialog"
          aria-label="Aviso de cookies y privacidad"
          className="fixed bottom-4 left-4 right-4 md:left-auto md:right-6 md:max-w-xl z-50 animate-in fade-in slide-in-from-bottom-5 duration-300"
        >
          <div className="p-5 rounded-2xl bg-white/95 dark:bg-slate-900/95 backdrop-blur-md border border-slate-200/80 dark:border-slate-800 shadow-2xl shadow-slate-900/10 text-slate-800 dark:text-slate-200">
            <div className="flex items-start gap-3">
              <div className="text-2xl select-none" aria-hidden="true">🍪</div>
              <div className="flex-1 text-sm leading-relaxed">
                <h3 className="font-semibold text-slate-900 dark:text-white mb-1">
                  Tu privacidad en MyBookConnect
                </h3>
                <p className="text-xs text-slate-600 dark:text-slate-400">
                  Utilizamos cookies técnicas para el funcionamiento seguro de la plataforma, y cookies opcionales para análisis y gestión de publicidad/enlaces de afiliación (como el Programa de Afiliados de Amazon). Puedes aceptarlas, rechazarlas o personalizarlas en cualquier momento.
                </p>
                <div className="mt-2 text-xs flex gap-3 text-teal-600 dark:text-teal-400 font-medium">
                  <Link to="/cookies" className="hover:underline">
                    Política de cookies
                  </Link>
                  <span>•</span>
                  <Link to="/privacy" className="hover:underline">
                    Privacidad
                  </Link>
                </div>
              </div>
            </div>

            <div className="mt-4 pt-3 border-t border-slate-100 dark:border-slate-800/80 flex flex-wrap items-center justify-end gap-2">
              <button
                type="button"
                onClick={() => setIsModalOpen(true)}
                className="px-3 py-1.5 text-xs font-medium text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition-colors"
              >
                Configurar
              </button>
              <button
                type="button"
                onClick={handleRejectNonEssential}
                className="px-3 py-1.5 text-xs font-medium border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition-colors"
              >
                Solo necesarias
              </button>
              <button
                type="button"
                onClick={handleAcceptAll}
                className="px-4 py-1.5 text-xs font-semibold bg-teal-600 hover:bg-teal-700 text-white rounded-lg shadow-sm transition-colors"
              >
                Aceptar todas
              </button>
            </div>
          </div>
        </aside>
      )}

      {/* Granular Cookie Preferences Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/60 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="w-full max-w-lg rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-2xl p-6 text-slate-800 dark:text-slate-200 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between pb-4 border-b border-slate-100 dark:border-slate-800">
              <div className="flex items-center gap-2">
                <span className="text-xl">⚙️</span>
                <h2 className="text-lg font-bold text-slate-900 dark:text-white">
                  Preferencias de Cookies
                </h2>
              </div>
              <button
                type="button"
                onClick={() => setIsModalOpen(false)}
                className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 p-1 rounded-lg"
                aria-label="Cerrar modal"
              >
                ✕
              </button>
            </div>

            <p className="mt-3 text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
              Elige qué cookies permites en tu navegador. Puedes revisar la información detallada sobre su uso en nuestra{' '}
              <Link to="/cookies" className="text-teal-600 dark:text-teal-400 underline" onClick={() => setIsModalOpen(false)}>
                Política de Cookies
              </Link>.
            </p>

            <div className="mt-5 space-y-4">
              {/* Category 1: Technical & Essential */}
              <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200/70 dark:border-slate-700/60">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-sm font-semibold text-slate-900 dark:text-white flex items-center gap-1.5">
                      Cookies Técnicas y Esenciales
                      <span className="text-[10px] uppercase font-bold tracking-wider px-1.5 py-0.5 rounded bg-teal-100 dark:bg-teal-900/60 text-teal-700 dark:text-teal-300">
                        Obligatorias
                      </span>
                    </h3>
                    <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                      Imprescindibles para mantener tu sesión activa, seguridad contra ataques CSRF y recordar tus preferencias básicas.
                    </p>
                  </div>
                  <input
                    type="checkbox"
                    checked
                    disabled
                    className="h-4 w-4 rounded text-teal-600 border-slate-300 focus:ring-teal-500 opacity-60 cursor-not-allowed"
                  />
                </div>
              </div>

              {/* Category 2: Analytics */}
              <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200/70 dark:border-slate-700/60">
                <div className="flex items-center justify-between">
                  <div className="pr-3">
                    <h3 className="text-sm font-semibold text-slate-900 dark:text-white">
                      Cookies de Análisis y Rendimiento
                    </h3>
                    <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                      Nos ayudan a entender de forma agregada cómo los usuarios navegan y usan MyBookConnect para optimizar tiempos de carga y descubrir errores.
                    </p>
                  </div>
                  <input
                    type="checkbox"
                    id="chk-analytics"
                    checked={analytics}
                    onChange={(e) => setAnalytics(e.target.checked)}
                    className="h-4 w-4 rounded text-teal-600 border-slate-300 focus:ring-teal-500 cursor-pointer"
                  />
                </div>
              </div>

              {/* Category 3: Advertising & Affiliate (Amazon) */}
              <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200/70 dark:border-slate-700/60">
                <div className="flex items-center justify-between">
                  <div className="pr-3">
                    <h3 className="text-sm font-semibold text-slate-900 dark:text-white">
                      Cookies de Publicidad y Afiliación (Amazon)
                    </h3>
                    <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                      Permiten mostrar sugerencias de compra de libros y medir transacciones del Programa de Afiliados de Amazon. Ayudan al sustento y mantenimiento del proyecto sin coste extra para ti.
                    </p>
                  </div>
                  <input
                    type="checkbox"
                    id="chk-advertising"
                    checked={advertising}
                    onChange={(e) => setAdvertising(e.target.checked)}
                    className="h-4 w-4 rounded text-teal-600 border-slate-300 focus:ring-teal-500 cursor-pointer"
                  />
                </div>
              </div>
            </div>

            <div className="mt-6 pt-4 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between gap-2">
              <button
                type="button"
                onClick={handleRejectNonEssential}
                className="px-3 py-2 text-xs font-medium text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white rounded-lg transition-colors"
              >
                Rechazar todo
              </button>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={handleSaveCustom}
                  className="px-4 py-2 text-xs font-medium border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition-colors"
                >
                  Guardar selección
                </button>
                <button
                  type="button"
                  onClick={handleAcceptAll}
                  className="px-4 py-2 text-xs font-semibold bg-teal-600 hover:bg-teal-700 text-white rounded-lg shadow-sm transition-colors"
                >
                  Aceptar todas
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
