import React, { useState, useEffect } from 'react';
import { ReadingStreakData } from './types';
import { useAuthStore } from '../../../../store/auth';

interface ReadingStreakCardProps {
  streak?: ReadingStreakData;
  isOwn?: boolean;
  onStreakUpdated?: () => void;
}

export const ReadingStreakCard: React.FC<ReadingStreakCardProps> = ({
  streak,
  isOwn = false,
  onStreakUpdated,
}) => {
  const [logging, setLogging] = useState(false);
  const [justLogged, setJustLogged] = useState(false);

  const { token } = useAuthStore();
  const apiUrl = (import.meta as any).env.VITE_API_URL || 'http://localhost:8000';

  useEffect(() => {
    if (streak?.read_today) {
      setJustLogged(true);
    }
  }, [streak?.read_today]);

  const currentStreak = streak?.current_streak || 0;
  const longestStreak = streak?.longest_streak || 0;
  const readToday = Boolean(streak?.read_today || justLogged);

  const handleLogToday = async () => {
    if (!token || readToday || logging) return;
    setLogging(true);
    try {
      const res = await fetch(`${apiUrl}/api/v1/gamification/log/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          pages_read: 10,
          minutes_read: 15,
        }),
      });
      if (res.ok) {
        setJustLogged(true);
        if (onStreakUpdated) onStreakUpdated();
      }
    } catch (e) {
      console.error('Error recording reading session', e);
    } finally {
      setLogging(false);
    }
  };

  return (
    <div className="bg-white dark:bg-slate-800 rounded-3xl p-6 border border-slate-100 dark:border-slate-700/60 shadow-sm relative overflow-hidden">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div
            className={`w-12 h-12 rounded-2xl flex items-center justify-center text-2xl shadow-inner ${
              currentStreak > 0
                ? 'bg-gradient-to-tr from-amber-500 to-orange-500 text-white animate-pulse'
                : 'bg-slate-100 dark:bg-slate-700 text-slate-400'
            }`}
          >
            🔥
          </div>
          <div>
            <h3 className="font-bold text-slate-900 dark:text-white text-base flex items-center gap-2">
              <span>Racha de Lectura</span>
              {currentStreak >= 7 && (
                <span className="text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full bg-orange-100 text-orange-700 dark:bg-orange-950/70 dark:text-orange-300 font-extrabold">
                  ¡Imparable!
                </span>
              )}
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              {readToday
                ? '¡Lectura de hoy registrada! Hábito asegurado.'
                : 'Lee hoy para no perder tu racha activa.'}
            </p>
          </div>
        </div>

        {longestStreak > 0 && (
          <span className="text-[11px] font-semibold text-slate-500 dark:text-slate-400 bg-slate-50 dark:bg-slate-700/50 px-2.5 py-1 rounded-xl border border-slate-200/50 dark:border-slate-600/50">
            Récord: {longestStreak} {longestStreak === 1 ? 'día' : 'días'}
          </span>
        )}
      </div>

      <div className="mt-5 flex items-center justify-between pt-2 border-t border-slate-100 dark:border-slate-700/60">
        <div className="flex items-baseline gap-2">
          <span className="text-4xl font-black text-transparent bg-clip-text bg-gradient-to-r from-amber-500 to-orange-500">
            {currentStreak}
          </span>
          <span className="text-sm font-bold text-slate-600 dark:text-slate-300">
            {currentStreak === 1 ? 'día consecutivo' : 'días consecutivos'}
          </span>
        </div>

        {isOwn && (
          <button
            type="button"
            onClick={handleLogToday}
            disabled={readToday || logging}
            className={`px-4 py-2 rounded-xl text-xs font-bold transition-all shadow-sm flex items-center gap-1.5 ${
              readToday
                ? 'bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800/60 cursor-default'
                : 'bg-gradient-to-r from-orange-500 to-amber-500 hover:from-orange-600 hover:to-amber-600 text-white transform hover:-translate-y-0.5'
            }`}
          >
            <span>{readToday ? '✓' : '📖'}</span>
            <span>{readToday ? 'Leído hoy' : logging ? 'Registrando...' : 'He leído hoy'}</span>
          </button>
        )}
      </div>
    </div>
  );
};
