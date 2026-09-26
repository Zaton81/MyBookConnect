import React, { useState } from 'react';
import { ChallengeItem } from './types';
import { useAuthStore } from '../../../../store/auth';

interface ActiveChallengesCardProps {
  challenges?: ChallengeItem[];
  isOwn?: boolean;
  onChallengeUpdated?: () => void;
}

export const ActiveChallengesCard: React.FC<ActiveChallengesCardProps> = ({
  challenges = [],
  isOwn = false,
  onChallengeUpdated,
}) => {
  const [joiningSlug, setJoiningSlug] = useState<string | null>(null);

  const { token } = useAuthStore();
  const apiUrl = (import.meta as any).env.VITE_API_URL || 'http://localhost:8000';

  const handleJoinChallenge = async (slug: string) => {
    if (!token || joiningSlug) return;
    setJoiningSlug(slug);
    try {
      const res = await fetch(`${apiUrl}/api/v1/gamification/challenges/${slug}/join/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
      });
      if (res.ok && onChallengeUpdated) {
        onChallengeUpdated();
      }
    } catch (e) {
      console.error('Error joining challenge', e);
    } finally {
      setJoiningSlug(null);
    }
  };

  if (challenges.length === 0) {
    return (
      <div className="bg-white dark:bg-slate-800 rounded-3xl p-6 border border-slate-100 dark:border-slate-700/60 shadow-sm">
        <div className="flex items-center gap-2.5 mb-3">
          <div className="w-10 h-10 rounded-2xl bg-indigo-50 dark:bg-indigo-950/50 flex items-center justify-center text-xl shadow-inner">
            🎯
          </div>
          <div>
            <h3 className="font-bold text-slate-900 dark:text-white text-base">Retos de Lectura</h3>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Desafíos comunitarios por tiempo limitado
            </p>
          </div>
        </div>
        <p className="text-xs text-slate-500 dark:text-slate-400 text-center py-4 bg-slate-50 dark:bg-slate-700/30 rounded-2xl">
          No hay retos activos en este momento. ¡Vuelve pronto para nuevos desafíos literarios!
        </p>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-slate-800 rounded-3xl p-6 border border-slate-100 dark:border-slate-700/60 shadow-sm space-y-4">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2.5">
          <div className="w-10 h-10 rounded-2xl bg-indigo-50 dark:bg-indigo-950/50 flex items-center justify-center text-xl shadow-inner">
            🎯
          </div>
          <div>
            <h3 className="font-bold text-slate-900 dark:text-white text-base">Retos de Lectura</h3>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Desafíos temáticos y mensuales para impulsar tu ritmo
            </p>
          </div>
        </div>

        <span className="text-xs font-bold text-indigo-600 dark:text-indigo-400 bg-indigo-50 dark:bg-indigo-950/60 px-2.5 py-1 rounded-full border border-indigo-200/50 dark:border-indigo-800/50">
          {challenges.length} {challenges.length === 1 ? 'reto' : 'retos'}
        </span>
      </div>

      <div className="space-y-3 pt-1">
        {challenges.map((ch) => {
          const isCompleted = ch.is_completed;
          return (
            <div
              key={ch.id}
              className={`p-4 rounded-2xl border transition-all ${
                isCompleted
                  ? 'bg-gradient-to-r from-emerald-50/60 to-teal-50/40 dark:from-emerald-950/30 dark:to-slate-800 border-emerald-200 dark:border-emerald-800/60'
                  : 'bg-slate-50/70 dark:bg-slate-750 border-slate-200/70 dark:border-slate-700/60'
              }`}
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="flex items-center gap-2">
                    <h4 className="font-bold text-sm text-slate-900 dark:text-white">{ch.title}</h4>
                    {isCompleted && (
                      <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800 dark:bg-emerald-900/60 dark:text-emerald-300">
                        ✓ ¡Completado!
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 leading-relaxed">
                    {ch.description}
                  </p>
                </div>

                {ch.badge_reward && (
                  <div className="text-center shrink-0" title={`Premio: ${ch.badge_reward.name}`}>
                    <span className="text-2xl">{ch.badge_reward.icon}</span>
                  </div>
                )}
              </div>

              {/* Barra de progreso */}
              <div className="mt-3 pt-2">
                <div className="flex items-center justify-between text-xs mb-1.5 font-semibold text-slate-600 dark:text-slate-300">
                  <span>
                    Progreso: {ch.current_progress} / {ch.target_count}
                  </span>
                  <span className="text-indigo-600 dark:text-indigo-400">{ch.percentage}%</span>
                </div>
                <div className="w-full h-2 bg-slate-200/70 dark:bg-slate-700 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all duration-500 ${
                      isCompleted
                        ? 'bg-emerald-500'
                        : 'bg-gradient-to-r from-indigo-500 to-teal-400'
                    }`}
                    style={{ width: `${Math.min(100, ch.percentage)}%` }}
                  />
                </div>
              </div>

              <div className="mt-3 flex items-center justify-between text-[11px] text-slate-400 dark:text-slate-500">
                <span>Finaliza el {new Date(ch.end_date).toLocaleDateString()}</span>

                {isOwn && !isCompleted && ch.current_progress === 0 && (
                  <button
                    type="button"
                    onClick={() => handleJoinChallenge(ch.slug)}
                    disabled={joiningSlug === ch.slug}
                    className="text-xs font-bold text-indigo-600 dark:text-indigo-400 hover:underline"
                  >
                    {joiningSlug === ch.slug ? 'Inscribiendo...' : 'Participar en el reto ➔'}
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
