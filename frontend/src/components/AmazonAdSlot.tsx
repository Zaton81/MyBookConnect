import { useState, useEffect } from 'react';
import { getStoredCookieConsent, CookiePreferences } from './CookieBanner';

interface AmazonAdSlotProps {
  title?: string;
  bookTitle?: string;
  asin?: string;
  searchQuery?: string;
  variant?: 'banner' | 'card' | 'compact';
  className?: string;
}

export function AmazonAdSlot({
  title = 'Descubre en Amazon',
  bookTitle,
  asin,
  searchQuery,
  variant = 'banner',
  className = '',
}: AmazonAdSlotProps) {
  const [hasAdConsent, setHasAdConsent] = useState(true);
  const affiliateTag = import.meta.env.VITE_AMAZON_AFFILIATE_TAG || 'mybookconnect-21';

  useEffect(() => {
    const checkConsent = () => {
      const consent = getStoredCookieConsent();
      if (consent) {
        setHasAdConsent(consent.advertising);
      }
    };

    checkConsent();
    const handleUpdate = (e: CustomEvent<CookiePreferences>) => {
      setHasAdConsent(e.detail.advertising);
    };

    window.addEventListener('mbc:cookie-consent-updated', handleUpdate as EventListener);
    return () => window.removeEventListener('mbc:cookie-consent-updated', handleUpdate as EventListener);
  }, []);

  // Build appropriate Amazon destination link
  const amazonUrl = asin
    ? `https://www.amazon.es/dp/${asin}?tag=${affiliateTag}`
    : searchQuery || bookTitle
    ? `https://www.amazon.es/s?k=${encodeURIComponent(searchQuery || bookTitle || '')}&i=stripbooks&tag=${affiliateTag}`
    : `https://www.amazon.es/gp/browse.html?node=599364031&tag=${affiliateTag}`; // Default books category in Amazon ES

  if (variant === 'compact') {
    return (
      <a
        href={amazonUrl}
        target="_blank"
        rel="noopener noreferrer sponsored"
        className={`inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-amber-50 dark:bg-amber-950/40 text-amber-800 dark:text-amber-300 border border-amber-200 dark:border-amber-800/80 hover:bg-amber-100 dark:hover:bg-amber-900/40 transition-colors shadow-xs ${className}`}
        title="Ver este título o similares en Amazon (Enlace de afiliado)"
      >
        <span>🛒</span>
        <span>Ver en Amazon</span>
        <span className="text-[10px] text-amber-600 dark:text-amber-400 font-normal">(Afiliado)</span>
      </a>
    );
  }

  if (variant === 'card') {
    return (
      <aside
        role="complementary"
        aria-label="Recomendación patrocinada de Amazon"
        className={`p-4 rounded-2xl bg-gradient-to-br from-amber-50/70 via-white to-amber-50/40 dark:from-slate-900 dark:via-slate-900/90 dark:to-amber-950/20 border border-amber-200/80 dark:border-amber-800/60 shadow-sm ${className}`}
      >
        <div className="flex items-center justify-between text-[11px] font-medium text-amber-700 dark:text-amber-400 mb-2">
          <span className="flex items-center gap-1">
            <span className="text-sm">📦</span>
            Recomendado en Amazon
          </span>
          <span className="text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded bg-amber-100 dark:bg-amber-950 border border-amber-300 dark:border-amber-800 text-amber-800 dark:text-amber-300">
            Patrocinado
          </span>
        </div>

        <h4 className="text-sm font-bold text-slate-900 dark:text-white">
          {bookTitle ? `Consigue «${bookTitle}» en papel o Kindle` : title}
        </h4>
        <p className="text-xs text-slate-600 dark:text-slate-400 mt-1">
          Envíos rápidos con Amazon Prime y catálogo completo de lectura digital con Kindle Unlimited.
        </p>

        <div className="mt-3 flex items-center justify-between gap-2">
          <span className="text-[10px] text-slate-400 dark:text-slate-500">
            {hasAdConsent ? 'Enlace de afiliación' : 'Cookies publicitarias pausadas'}
          </span>
          <a
            href={amazonUrl}
            target="_blank"
            rel="noopener noreferrer sponsored"
            className="px-3 py-1.5 text-xs font-semibold bg-amber-500 hover:bg-amber-600 text-slate-950 rounded-lg shadow-sm transition-all flex items-center gap-1 cursor-pointer"
          >
            <span>Buscar en Amazon</span>
            <span aria-hidden="true">→</span>
          </a>
        </div>
      </aside>
    );
  }

  // Default: 'banner'
  return (
    <aside
      role="complementary"
      aria-label="Espacio patrocinado de Amazon"
      className={`relative overflow-hidden p-4 sm:p-5 rounded-2xl bg-gradient-to-r from-amber-500/10 via-amber-400/5 to-teal-500/10 border border-amber-200/80 dark:border-amber-900/60 shadow-sm ${className}`}
    >
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div className="flex items-start gap-3">
          <div className="w-10 h-10 rounded-xl bg-amber-500/20 text-amber-800 dark:text-amber-300 flex items-center justify-center text-xl shrink-0 font-bold">
            a
          </div>
          <div>
            <div className="flex items-center gap-2 mb-0.5">
              <span className="text-[10px] uppercase font-bold tracking-widest px-1.5 py-0.5 rounded bg-amber-200 dark:bg-amber-900/70 text-amber-900 dark:text-amber-200">
                Patrocinado • Amazon Associates
              </span>
            </div>
            <h4 className="text-sm sm:text-base font-bold text-slate-900 dark:text-white">
              {bookTitle ? `¿Quieres leer «${bookTitle}»?` : 'Encuentra tus próximas lecturas en Amazon'}
            </h4>
            <p className="text-xs text-slate-600 dark:text-slate-400 mt-0.5 max-w-xl">
              Accede a millones de títulos en tapa blanda, tapa dura o en formato digital con la app Kindle.
            </p>
          </div>
        </div>

        <a
          href={amazonUrl}
          target="_blank"
          rel="noopener noreferrer sponsored"
          className="whitespace-nowrap px-4 py-2 text-xs font-bold bg-amber-500 hover:bg-amber-600 active:scale-95 text-slate-950 rounded-xl shadow-sm transition-all flex items-center gap-1.5 shrink-0 cursor-pointer"
        >
          <span>Ver catálogo</span>
          <span aria-hidden="true">→</span>
        </a>
      </div>
    </aside>
  );
}
