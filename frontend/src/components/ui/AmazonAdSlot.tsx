import { useState, useEffect } from 'react';
import { getStoredCookieConsent, CookiePreferences } from './CookieBanner';

interface AmazonAdSlotProps {
  title?: string;
  bookTitle?: string;
  authorName?: string;
  asin?: string;
  searchQuery?: string;
  variant?: 'banner' | 'card' | 'compact' | 'multiformat';
  className?: string;
}

export function AmazonAdSlot({
  title = 'Descubre en Amazon',
  bookTitle,
  authorName,
  asin,
  searchQuery,
  variant = 'banner',
  className = '',
}: AmazonAdSlotProps) {
  const [hasAdConsent, setHasAdConsent] = useState(true);
  const affiliateTag = import.meta.env.VITE_AMAZON_AFFILIATE_TAG || 'mybooksocial-21';

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
    return () =>
      window.removeEventListener('mbc:cookie-consent-updated', handleUpdate as EventListener);
  }, []);

  const query = searchQuery || (bookTitle ? `${bookTitle} ${authorName || ''}`.trim() : '');
  const encodedQuery = encodeURIComponent(query);

  // Enlaces por formato para compras cualificadas
  const paperbackUrl = asin
    ? `https://www.amazon.es/dp/${asin}?tag=${affiliateTag}`
    : query
      ? `https://www.amazon.es/s?k=${encodedQuery}&i=stripbooks&tag=${affiliateTag}`
      : `https://www.amazon.es/gp/browse.html?node=599364031&tag=${affiliateTag}`;

  const kindleUrl = query
    ? `https://www.amazon.es/s?k=${encodedQuery}&i=digital-text&tag=${affiliateTag}`
    : `https://www.amazon.es/kindle-dbs/storefront?tag=${affiliateTag}`;

  const audibleUrl = query
    ? `https://www.amazon.es/s?k=${encodedQuery}&i=audible&tag=${affiliateTag}`
    : `https://www.amazon.es/hz/audible/mlp?tag=${affiliateTag}`;

  if (variant === 'compact') {
    return (
      <a
        href={paperbackUrl}
        target="_blank"
        rel="noopener noreferrer sponsored"
        className={`inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-amber-50 dark:bg-amber-950/40 text-amber-800 dark:text-amber-300 border border-amber-200 dark:border-amber-800/80 hover:bg-amber-100 dark:hover:bg-amber-900/40 transition-colors shadow-xs ${className}`}
        title="Ver este título o similares en Amazon (Enlace de afiliado)"
      >
        <span>🛒</span>
        <span>Ver en Amazon</span>
        <span className="text-[10px] text-amber-600 dark:text-amber-400 font-normal">
          (Afiliado)
        </span>
      </a>
    );
  }

  if (variant === 'card' || variant === 'multiformat') {
    return (
      <aside
        role="complementary"
        aria-label="Opciones de compra y afiliación en Amazon"
        className={`p-4 rounded-2xl bg-gradient-to-br from-amber-50/70 via-white to-amber-50/40 dark:from-slate-900 dark:via-slate-900/90 dark:to-amber-950/20 border border-amber-200/80 dark:border-amber-800/60 shadow-sm ${className}`}
      >
        <div className="flex items-center justify-between text-[11px] font-medium text-amber-700 dark:text-amber-400 mb-2">
          <span className="flex items-center gap-1">
            <span className="text-sm">📦</span>
            Comprar o escuchar en Amazon
          </span>
          <span className="text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded bg-amber-100 dark:bg-amber-950 border border-amber-300 dark:border-amber-800 text-amber-800 dark:text-amber-300">
            Afiliado
          </span>
        </div>

        <h4 className="text-sm font-bold text-slate-900 dark:text-white">
          {bookTitle ? `Consigue «${bookTitle}» en tu formato favorito` : title}
        </h4>
        <p className="text-xs text-slate-600 dark:text-slate-400 mt-1">
          Elige entre edición física, formato digital Kindle o audiolibro narrado en Audible.
        </p>

        {/* Botones de formato múltiple */}
        <div className="mt-3 grid grid-cols-1 sm:grid-cols-3 gap-2">
          <a
            href={paperbackUrl}
            target="_blank"
            rel="noopener noreferrer sponsored"
            className="px-3 py-2 text-xs font-semibold bg-amber-500 hover:bg-amber-600 text-slate-950 rounded-xl shadow-xs transition-all flex items-center justify-center gap-1.5 cursor-pointer text-center"
          >
            <span>📖</span>
            <span>Libro Papel</span>
          </a>
          <a
            href={kindleUrl}
            target="_blank"
            rel="noopener noreferrer sponsored"
            className="px-3 py-2 text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-white dark:bg-slate-700 dark:hover:bg-slate-600 rounded-xl shadow-xs transition-all flex items-center justify-center gap-1.5 cursor-pointer text-center"
          >
            <span>📱</span>
            <span>Ebook Kindle</span>
          </a>
          <a
            href={audibleUrl}
            target="_blank"
            rel="noopener noreferrer sponsored"
            className="px-3 py-2 text-xs font-semibold bg-amber-100 hover:bg-amber-200 text-amber-950 dark:bg-amber-900/50 dark:hover:bg-amber-900/70 dark:text-amber-200 border border-amber-300/80 dark:border-amber-700 rounded-xl shadow-xs transition-all flex items-center justify-center gap-1.5 cursor-pointer text-center"
          >
            <span>🎧</span>
            <span>Audiolibro</span>
          </a>
        </div>

        <div className="mt-3 pt-2 border-t border-amber-100 dark:border-slate-800 flex items-center justify-between text-[10px] text-slate-400 dark:text-slate-500">
          <span>{hasAdConsent ? 'Enlace de afiliación transparente' : 'Cookies pausadas'}</span>
          <span>MyBookConnect puede percibir comisión</span>
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
              {bookTitle
                ? `¿Quieres leer «${bookTitle}»?`
                : 'Encuentra tus próximas lecturas en Amazon'}
            </h4>
            <p className="text-xs text-slate-600 dark:text-slate-400 mt-0.5 max-w-xl">
              Accede a millones de títulos en tapa blanda, tapa dura o en formato digital con la app
              Kindle.
            </p>
          </div>
        </div>

        <a
          href={paperbackUrl}
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

export default AmazonAdSlot;
