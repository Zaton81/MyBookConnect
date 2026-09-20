import React, { useState } from 'react';
import { ReadingGoalData } from './types';

interface ReadingGoalCardProps {
  goal?: ReadingGoalData;
  isOwn?: boolean;
  onGoalUpdated?: () => void;
}

export const ReadingGoalCard: React.FC<ReadingGoalCardProps> = ({
  goal,
  isOwn = false,
  onGoalUpdated,
}) => {
  const [isEditing, setIsEditing] = useState(false);
  const [targetBooks, setTargetBooks] = useState(goal?.target_books || 12);
  const [saving, setSaving] = useState(false);

  const apiUrl = (import.meta as any).env.VITE_API_URL || 'http://localhost:8000';
  const token = localStorage.getItem('access_token');

  const handleSaveGoal = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token) return;
    setSaving(true);
    try {
      const res = await fetch(`${apiUrl}/api/v1/gamification/goals/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          year: goal?.year || new Date().getFullYear(),
          target_books: Number(targetBooks),
        }),
      });
      if (res.ok) {
        setIsEditing(false);
        if (onGoalUpdated) onGoalUpdated();
      }
    } catch (err) {
      console.error('Error saving reading goal', err);
    } finally {
      setSaving(false);
    }
  };

  const getPacingBadge = () => {
    if (!goal || !goal.has_goal) return null;
    switch (goal.pacing_status) {
      case 'ahead':
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 dark:bg-emerald-950/70 dark:text-emerald-300">
            🚀 {goal.pacing_text}
          </span>
        );
      case 'on_track':
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-teal-100 text-teal-800 dark:bg-teal-950/70 dark:text-teal-300">
            🎯 {goal.pacing_text}
          </span>
        );
      case 'behind':
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-amber-100 text-amber-800 dark:bg-amber-950/70 dark:text-amber-300">
            ⏳ {goal.pacing_text}
          </span>
        );
      case 'completed':
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-purple-100 text-purple-800 dark:bg-purple-950/70 dark:text-purple-300">
            🏆 {goal.pacing_text || '¡Completado!'}
          </span>
        );
      default:
        return null;
    }
  };

  return (
    <div className="bg-white dark:bg-slate-800 rounded-3xl p-6 border border-slate-100 dark:border-slate-700/60 shadow-sm relative overflow-hidden">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2.5">
          <div className="w-10 h-10 rounded-2xl bg-amber-50 dark:bg-amber-950/50 flex items-center justify-center text-xl shadow-inner">
            🎯
          </div>
          <div>
            <h3 className="font-bold text-slate-900 dark:text-white text-base">
              Objetivo de Lectura {goal?.year || new Date().getFullYear()}
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Progreso personal anual de libros leídos
            </p>
          </div>
        </div>

        {isOwn && !isEditing && (
          <button
            onClick={() => setIsEditing(true)}
            className="text-xs text-teal-600 dark:text-teal-400 hover:underline font-semibold px-2 py-1 rounded-lg hover:bg-teal-50 dark:hover:bg-teal-950/40 transition-colors"
          >
            {goal?.has_goal ? 'Editar meta' : 'Fijar meta'}
          </button>
        )}
      </div>

      {isEditing ? (
        <form onSubmit={handleSaveGoal} className="mt-4 pt-4 border-t border-slate-100 dark:border-slate-700">
          <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
            ¿Cuántos libros quieres leer en {goal?.year || new Date().getFullYear()}?
          </label>
          <div className="flex items-center gap-2">
            <input
              type="number"
              min={1}
              max={500}
              value={targetBooks}
              onChange={(e) => setTargetBooks(Number(e.target.value))}
              className="w-24 px-3 py-1.5 text-sm rounded-xl border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-900 text-slate-900 dark:text-white focus:ring-2 focus:ring-teal-500"
              required
            />
            <span className="text-xs text-slate-500">libros</span>
            <button
              type="submit"
              disabled={saving}
              className="ml-auto px-4 py-1.5 bg-teal-600 hover:bg-teal-700 text-white text-xs font-bold rounded-xl transition-colors disabled:opacity-50"
            >
              {saving ? 'Guardando...' : 'Guardar'}
            </button>
            <button
              type="button"
              onClick={() => setIsEditing(false)}
              className="px-3 py-1.5 bg-slate-100 dark:bg-slate-700 hover:bg-slate-200 text-slate-700 dark:text-slate-300 text-xs font-medium rounded-xl transition-colors"
            >
              Cancelar
            </button>
          </div>
        </form>
      ) : goal?.has_goal ? (
        <div className="mt-5 space-y-3">
          <div className="flex items-baseline justify-between">
            <div>
              <span className="text-3xl font-black text-slate-900 dark:text-white">
                {goal.current_books}
              </span>
              <span className="text-sm font-semibold text-slate-400 dark:text-slate-500 ml-1">
                / {goal.target_books} libros
              </span>
            </div>
            <div className="text-right">
              <span className="text-lg font-bold text-teal-600 dark:text-teal-400">
                {goal.percentage}%
              </span>
            </div>
          </div>

          {/* Barra de progreso animada */}
          <div className="w-full h-3 bg-slate-100 dark:bg-slate-700/60 rounded-full overflow-hidden p-0.5">
            <div
              className="h-full bg-gradient-to-r from-teal-500 to-emerald-400 rounded-full transition-all duration-700"
              style={{ width: `${Math.min(100, goal.percentage)}%` }}
            />
          </div>

          <div className="flex items-center justify-between pt-1">
            <span className="text-xs text-slate-500 dark:text-slate-400">
              {goal.remaining_books > 0
                ? `Faltan ${goal.remaining_books} libros para tu meta`
                : '¡Has superado tu meta de este año! 🎉'}
            </span>
            {getPacingBadge()}
          </div>
        </div>
      ) : (
        <div className="mt-4 p-4 rounded-2xl bg-slate-50 dark:bg-slate-700/40 text-center">
          <p className="text-xs text-slate-500 dark:text-slate-400">
            Aún no hay un objetivo fijado para este año.
          </p>
          {isOwn && (
            <button
              onClick={() => setIsEditing(true)}
              className="mt-2 text-xs font-bold text-teal-600 dark:text-teal-400 hover:underline"
            >
              + Establecer mi meta de {new Date().getFullYear()}
            </button>
          )}
        </div>
      )}
    </div>
  );
};
