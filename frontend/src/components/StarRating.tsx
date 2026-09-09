import React, { useState, useRef, useEffect } from 'react';

interface StarRatingProps {
  rating: number | null | undefined; // 0 to 10 or 0 to 5. We standardize display as 5 stars (rating/2 if > 5)
  maxRating?: number; // default 10 (backend is 1-10)
  totalReviews?: number;
  distribution?: Record<string | number, number>;
  size?: 'sm' | 'md' | 'lg';
  interactive?: boolean;
  onRatingChange?: (newRating: number) => void;
  showBreakdownOnHover?: boolean;
}

export function StarRating({
  rating,
  maxRating = 10,
  totalReviews = 0,
  distribution,
  size = 'md',
  interactive = false,
  onRatingChange,
  showBreakdownOnHover = true,
}: StarRatingProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [hoverRating, setHoverRating] = useState<number | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Normalizar la nota a escala 1 - 5 para las estrellas
  const numericRating = typeof rating === 'number' && !isNaN(rating) ? rating : 0;
  // Si maxRating es 10, escalamos a 5 estrellas:
  const normalized5 = maxRating === 10 ? numericRating / 2 : numericRating;

  // Cerrar popover al hacer clic fuera
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const sizeClasses = {
    sm: 'text-sm gap-0.5',
    md: 'text-base sm:text-lg gap-1',
    lg: 'text-2xl gap-1.5',
  };

  // Calcular agregados de distribución para 5 estrellas
  const distCounts = [5, 4, 3, 2, 1].map((stars) => {
    let count = 0;
    if (distribution) {
      if (maxRating === 10) {
        // Star 5: 9, 10; Star 4: 7, 8; Star 3: 5, 6; Star 2: 3, 4; Star 1: 1, 2
        const upper = stars * 2;
        const lower = upper - 1;
        count = (distribution[upper] || 0) + (distribution[lower] || 0);
      } else {
        count = distribution[stars] || 0;
      }
    }
    return { stars, count };
  });

  const totalVotesCount = distCounts.reduce((acc, curr) => acc + curr.count, 0) || totalReviews || 0;

  return (
    <div
      ref={containerRef}
      className="relative inline-flex items-center gap-2 group"
      onMouseEnter={() => showBreakdownOnHover && !interactive && setIsOpen(true)}
      onMouseLeave={() => showBreakdownOnHover && !interactive && setIsOpen(false)}
    >
      {/* Contenedor de Estrellas */}
      <div
        className={`inline-flex items-center cursor-pointer select-none ${sizeClasses[size]}`}
        onClick={() => !interactive && setIsOpen(!isOpen)}
        title={numericRating ? `${numericRating.toFixed(1)} / ${maxRating}` : 'Sin valoraciones'}
      >
        {[1, 2, 3, 4, 5].map((starIndex) => {
          const currentVal = hoverRating !== null ? hoverRating : normalized5;
          const isFilled = currentVal >= starIndex;
          const isHalf = !isFilled && currentVal >= starIndex - 0.5;

          return (
            <span
              key={starIndex}
              onMouseEnter={() => interactive && setHoverRating(starIndex * (maxRating / 5))}
              onMouseLeave={() => interactive && setHoverRating(null)}
              onClick={() => interactive && onRatingChange && onRatingChange(starIndex * (maxRating / 5))}
              className={`transition-transform duration-150 ${
                interactive ? 'hover:scale-125 cursor-pointer text-amber-400' : ''
              } ${
                isFilled
                  ? 'text-amber-400 drop-shadow-[0_0_2px_rgba(251,191,36,0.6)]'
                  : isHalf
                  ? 'text-amber-300'
                  : 'text-slate-300 dark:text-slate-600'
              }`}
            >
              ★
            </span>
          );
        })}
      </div>

      {/* Nota numérica y total */}
      {!interactive && (
        <button
          type="button"
          onClick={() => setIsOpen(!isOpen)}
          className="inline-flex items-baseline gap-1 text-xs font-bold text-slate-700 dark:text-slate-300 hover:text-teal-600 dark:hover:text-teal-400 transition-colors"
        >
          {numericRating > 0 ? (
            <>
              <span className="text-sm sm:text-base font-black text-slate-900 dark:text-white">
                {(normalized5).toFixed(1)}
              </span>
              <span className="text-[11px] text-slate-400 font-normal">/ 5</span>
              {totalVotesCount > 0 && (
                <span className="text-[11px] text-slate-400 font-normal ml-1">
                  ({totalVotesCount} {totalVotesCount === 1 ? 'voto' : 'votos'})
                </span>
              )}
            </>
          ) : (
            <span className="text-slate-400 italic">Sin valoraciones</span>
          )}
        </button>
      )}

      {/* Popover con Histograma de Distribución */}
      {isOpen && distribution && (
        <div className="absolute left-0 top-full mt-2 z-50 w-72 p-4 bg-white dark:bg-slate-900 rounded-2xl shadow-xl border border-slate-200 dark:border-slate-700 text-xs animate-in fade-in zoom-in-95 duration-150">
          <div className="flex items-center justify-between pb-3 border-b border-slate-100 dark:border-slate-800">
            <div>
              <div className="flex items-baseline gap-1.5">
                <span className="text-2xl font-black text-slate-900 dark:text-white">
                  {(normalized5).toFixed(1)}
                </span>
                <span className="text-xs text-slate-400">de 5</span>
              </div>
              <p className="text-[11px] text-slate-400">
                {totalVotesCount} {totalVotesCount === 1 ? 'valoración global' : 'valoraciones globales'}
              </p>
            </div>
            <div className="text-amber-400 text-lg">★★★★★</div>
          </div>

          {/* Barras de distribución */}
          <div className="space-y-2 pt-3">
            {distCounts.map(({ stars, count }) => {
              const pct = totalVotesCount > 0 ? Math.round((count / totalVotesCount) * 100) : 0;
              return (
                <div key={stars} className="flex items-center gap-2 text-[11px]">
                  <span className="w-12 text-slate-500 dark:text-slate-400 font-medium flex items-center gap-0.5">
                    {stars} <span className="text-amber-400 text-xs">★</span>
                  </span>
                  <div className="flex-1 h-2.5 bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-amber-400 to-amber-500 rounded-full transition-all duration-300"
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                  <span className="w-12 text-right text-slate-600 dark:text-slate-300 font-semibold">
                    {count} <span className="text-[10px] text-slate-400 font-normal">({pct}%)</span>
                  </span>
                </div>
              );
            })}
          </div>

          <div className="mt-3 pt-2 border-t border-slate-100 dark:border-slate-800 text-[10px] text-slate-400 text-center">
            Puntuación calculada en base a las reseñas y notas de la comunidad
          </div>
        </div>
      )}
    </div>
  );
}
