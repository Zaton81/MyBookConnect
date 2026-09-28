import React, { useState } from 'react';
import { Button, Spinner } from 'flowbite-react';
import { useAuthStore } from '../../store/auth';

export interface BetaFeedbackModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmitted?: () => void;
}

export const BETA_FEEDBACK_CATEGORIES = [
  { value: 'bug', label: '🐛 Error o fallo técnico (Bug)' },
  { value: 'confusing_ux', label: '❓ Experiencia confusa o poco clara (UX)' },
  { value: 'missing_feature', label: '💡 Funcionalidad ausente o sugerencia' },
  { value: 'performance', label: '⚡ Lentitud o problema de rendimiento' },
  { value: 'privacy_concern', label: '🔒 Inquietud sobre privacidad o datos' },
  { value: 'recommendation_quality', label: '🎯 Calidad de las recomendaciones' },
  { value: 'general_feedback', label: '💬 Impresión u opinión general' },
];

export const BetaFeedbackModal: React.FC<BetaFeedbackModalProps> = ({
  isOpen,
  onClose,
  onSubmitted,
}) => {
  const token = useAuthStore((state) => state.token);
  const [category, setCategory] = useState<string>('general_feedback');
  const [title, setTitle] = useState<string>('');
  const [description, setDescription] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token) {
      setErrorMsg('Debes iniciar sesión para enviar feedback de la beta.');
      return;
    }

    if (title.trim().length < 3) {
      setErrorMsg('El título debe tener al menos 3 caracteres.');
      return;
    }

    if (description.trim().length < 5) {
      setErrorMsg('Por favor describe tu observación con al menos 5 caracteres.');
      return;
    }

    setIsSubmitting(true);
    setErrorMsg(null);
    setSuccessMsg(null);

    const apiUrl = (import.meta as any).env?.VITE_API_URL || 'http://localhost:8000';

    try {
      const res = await fetch(`${apiUrl}/api/v1/beta/feedback/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          category,
          title: title.trim(),
          description: description.trim(),
          page_url: window.location.pathname || '/',
          device_info: navigator.userAgent?.slice(0, 250) || 'Web Browser',
        }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        const detail =
          data.detail ||
          data.title?.[0] ||
          data.description?.[0] ||
          'No se pudo registrar el feedback. Inténtalo de nuevo.';
        throw new Error(detail);
      }

      setSuccessMsg('¡Muchas gracias! Tu feedback ha sido registrado para el equipo.');
      setTitle('');
      setDescription('');
      if (onSubmitted) onSubmitted();

      setTimeout(() => {
        setSuccessMsg(null);
        onClose();
      }, 2000);
    } catch (err: any) {
      setErrorMsg(err.message || 'Error de conexión al enviar el feedback.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="beta-feedback-title"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fadeIn"
      onClick={onClose}
    >
      <div
        className="relative w-full max-w-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-2xl p-6 sm:p-7 overflow-hidden text-slate-800 dark:text-slate-100"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between pb-4 border-b border-slate-100 dark:border-slate-800">
          <div className="flex items-center gap-2">
            <span className="text-xl">🚀</span>
            <h2
              id="beta-feedback-title"
              className="text-lg font-bold text-slate-900 dark:text-white"
            >
              Feedback de Beta Cerrada
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Cerrar modal"
            className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
          >
            ✕
          </button>
        </div>

        <p className="mt-3 text-xs sm:text-sm text-slate-500 dark:text-slate-400">
          Tu opinión como probador de la beta es esencial para mejorar MyBookConnect antes del
          lanzamiento público.
        </p>

        {successMsg && (
          <div className="mt-4 p-3 bg-teal-50 dark:bg-teal-950/60 border border-teal-200 dark:border-teal-800 text-teal-800 dark:text-teal-200 rounded-xl text-sm flex items-center gap-2 animate-fadeIn">
            <span>✅</span>
            <span>{successMsg}</span>
          </div>
        )}

        {errorMsg && (
          <div className="mt-4 p-3 bg-rose-50 dark:bg-rose-950/60 border border-rose-200 dark:border-rose-800 text-rose-700 dark:text-rose-300 rounded-xl text-sm flex items-center gap-2 animate-fadeIn">
            <span>⚠️</span>
            <span>{errorMsg}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="mt-4 space-y-4">
          <div>
            <label
              htmlFor="beta-category"
              className="block text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1.5"
            >
              Tipo de observación
            </label>
            <select
              id="beta-category"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              disabled={isSubmitting}
              className="w-full text-sm rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white px-3.5 py-2.5 focus:ring-2 focus:ring-teal-500 focus:outline-none disabled:opacity-50"
            >
              {BETA_FEEDBACK_CATEGORIES.map((cat) => (
                <option key={cat.value} value={cat.value}>
                  {cat.label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label
              htmlFor="beta-title"
              className="block text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1.5"
            >
              Resumen breve
            </label>
            <input
              id="beta-title"
              type="text"
              placeholder="Ej. El filtrado por categorías no actualiza la lista"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              disabled={isSubmitting}
              maxLength={200}
              required
              className="w-full text-sm rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white px-3.5 py-2.5 focus:ring-2 focus:ring-teal-500 focus:outline-none disabled:opacity-50 placeholder-slate-400"
            />
          </div>

          <div>
            <label
              htmlFor="beta-description"
              className="block text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1.5"
            >
              Detalles / Pasos para reproducir
            </label>
            <textarea
              id="beta-description"
              rows={4}
              placeholder="Explica qué estabas intentando hacer, qué esperabas que ocurriera y qué ocurrió realmente..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              disabled={isSubmitting}
              required
              className="w-full text-sm rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white p-3.5 focus:ring-2 focus:ring-teal-500 focus:outline-none disabled:opacity-50 placeholder-slate-400 resize-none"
            />
          </div>

          <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-100 dark:border-slate-800">
            <Button
              color="gray"
              type="button"
              onClick={onClose}
              disabled={isSubmitting}
              className="rounded-xl"
            >
              Cancelar
            </Button>
            <Button
              type="submit"
              disabled={isSubmitting}
              className="bg-teal-600 hover:bg-teal-700 text-white font-medium rounded-xl shadow-md transition-all duration-200"
            >
              {isSubmitting ? (
                <div className="flex items-center gap-2">
                  <Spinner size="sm" />
                  <span>Enviando...</span>
                </div>
              ) : (
                'Enviar Feedback'
              )}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default BetaFeedbackModal;
