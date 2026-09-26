import React, { useState } from 'react';
import { BadgeItem } from './types';

interface BadgesGridProps {
  badges?: {
    total_badges: number;
    unlocked_count: number;
    total_points: number;
    list: BadgeItem[];
  };
}

export const BadgesGrid: React.FC<BadgesGridProps> = ({ badges }) => {
  const [selectedCategory, setSelectedCategory] = useState<string>('all');

  const badgeList = badges?.list || [];
  const categories = [
    { key: 'all', label: 'Todas' },
    { key: 'reading', label: '📚 Lectura' },
    { key: 'streak', label: '🔥 Rachas' },
    { key: 'reviews', label: '✍️ Reseñas' },
    { key: 'challenges', label: '🎯 Retos' },
    { key: 'community', label: '🤝 Comunidad' },
  ];

  const filteredBadges =
    selectedCategory === 'all'
      ? badgeList
      : badgeList.filter((b) => b.category === selectedCategory);

  return (
    <div className="bg-white dark:bg-slate-800 rounded-3xl p-6 border border-slate-100 dark:border-slate-700/60 shadow-sm space-y-5">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h3 className="font-bold text-slate-900 dark:text-white text-lg flex items-center gap-2">
            <span>🏆</span>
            <span>Insignias y Logros</span>
          </h3>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            Reconocimientos desbloqueables por tus hábitos y aportes literarios
          </p>
        </div>

        <div className="flex items-center gap-2 self-start sm:self-auto">
          <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-bold bg-amber-50 dark:bg-amber-950/60 text-amber-800 dark:text-amber-300 border border-amber-200/60 dark:border-amber-800/60">
            ✨ {badges?.total_points || 0} pts
          </span>
          <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-bold bg-teal-50 dark:bg-teal-950/60 text-teal-800 dark:text-teal-300 border border-teal-200/60 dark:border-teal-800/60">
            {badges?.unlocked_count || 0} de {badges?.total_badges || 0}
          </span>
        </div>
      </div>

      {/* Categorías filtro */}
      <div className="flex flex-wrap gap-1.5 pt-1">
        {categories.map((cat) => (
          <button
            key={cat.key}
            type="button"
            onClick={() => setSelectedCategory(cat.key)}
            className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition-all ${
              selectedCategory === cat.key
                ? 'bg-slate-900 dark:bg-white text-white dark:text-slate-900 shadow-sm'
                : 'bg-slate-100 dark:bg-slate-700/60 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700'
            }`}
          >
            {cat.label}
          </button>
        ))}
      </div>

      {/* Grid de insignias */}
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3.5 pt-2">
        {filteredBadges.map((badge) => {
          const isUnlocked = badge.unlocked;
          return (
            <div
              key={badge.id}
              className={`p-4 rounded-2xl border transition-all duration-200 flex flex-col justify-between ${
                isUnlocked
                  ? 'bg-gradient-to-br from-teal-50/70 via-white to-emerald-50/50 dark:from-slate-800 dark:to-teal-950/30 border-teal-200 dark:border-teal-800/60 shadow-sm hover:shadow-md'
                  : 'bg-slate-50/50 dark:bg-slate-800/40 border-slate-200/60 dark:border-slate-700/40 opacity-60 hover:opacity-80'
              }`}
            >
              <div>
                <div className="flex items-start justify-between gap-2">
                  <div
                    className={`w-12 h-12 rounded-2xl flex items-center justify-center text-2xl shadow-inner ${
                      isUnlocked
                        ? 'bg-white dark:bg-slate-700 border border-teal-100 dark:border-teal-900/60'
                        : 'bg-slate-200 dark:bg-slate-700/80 grayscale'
                    }`}
                  >
                    {badge.icon}
                  </div>
                  <div className="flex flex-col items-end gap-1">
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded-md bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300">
                      +{badge.points} pts
                    </span>
                    {isUnlocked ? (
                      <span className="text-[10px] font-bold text-emerald-600 dark:text-emerald-400 flex items-center gap-0.5">
                        ✓ Desbloqueada
                      </span>
                    ) : (
                      <span className="text-[10px] text-slate-400 dark:text-slate-500 flex items-center gap-0.5">
                        🔒 Bloqueada
                      </span>
                    )}
                  </div>
                </div>

                <h4 className="mt-3 font-bold text-sm text-slate-900 dark:text-white">
                  {badge.name}
                </h4>
                <p className="mt-1 text-xs text-slate-500 dark:text-slate-400 leading-relaxed">
                  {badge.description}
                </p>
              </div>

              {isUnlocked && badge.awarded_at && (
                <div className="mt-3 pt-2 border-t border-teal-100/60 dark:border-teal-900/30 text-[10px] text-slate-400">
                  Conseguida el {new Date(badge.awarded_at).toLocaleDateString()}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
