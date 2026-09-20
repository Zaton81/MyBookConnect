import React, { useState } from 'react';
import { Button, Spinner } from 'flowbite-react';
import { useAuthStore } from '../../../store/auth';

export interface ReportModalProps {
  isOpen: boolean;
  onClose: () => void;
  targetType: 'user' | 'review' | 'comment' | 'message';
  targetId: number;
  targetTitle?: string;
  onReportSubmitted?: () => void;
}

const REPORT_REASONS = [
  { value: 'SPAM', label: '📢 Spam o publicidad engañosa' },
  { value: 'HARASSMENT', label: '🛑 Acoso, intimidación o hostigamiento' },
  { value: 'HATE_SPEECH', label: '⛔ Incitación al odio o violencia' },
  { value: 'INAPPROPRIATE', label: '🔞 Contenido explícito o inapropiado' },
  { value: 'SPOILER', label: '🤫 Spoilers sin advertencia' },
  { value: 'COPYRIGHT', label: '⚖️ Infracción de derechos de autor' },
  { value: 'OTHER', label: '📝 Otro motivo' },
];

export const ReportModal: React.FC<ReportModalProps> = ({
  isOpen,
  onClose,
  targetType,
  targetId,
  targetTitle,
  onReportSubmitted,
}) => {
  const { token } = useAuthStore();
  const [reason, setReason] = useState<string>('SPAM');
  const [description, setDescription] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  if (!isOpen) return null;

  const targetLabel = {
    user: 'al usuario',
    review: 'la reseña',
    comment: 'el comentario',
    message: 'el mensaje',
  }[targetType] || 'el elemento';

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token) {
      setErrorMsg('Debes iniciar sesión para denunciar contenido.');
      return;
    }

    setIsSubmitting(true);
    setErrorMsg(null);
    setSuccessMsg(null);

    const apiUrl = (import.meta as any).env.VITE_API_URL || 'http://localhost:8000';

    try {
      const res = await fetch(`${apiUrl}/api/v1/reports/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          target_type: targetType,
          object_id: targetId,
          reason,
          description: description.trim(),
        }),
      });

      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        throw new Error(errorData.detail || errorData.error || 'Error al enviar la denuncia.');
      }

      setSuccessMsg('Denuncia enviada correctamente. El equipo de moderación la revisará a la brevedad.');
      if (onReportSubmitted) {
        onReportSubmitted();
      }
      setTimeout(() => {
        setSuccessMsg(null);
        setDescription('');
        onClose();
      }, 1600);
    } catch (err: any) {
      setErrorMsg(err.message || 'No se pudo registrar la denuncia. Inténtalo de nuevo.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fadeIn">
      <div className="bg-white dark:bg-slate-800 rounded-3xl max-w-md w-full p-6 shadow-2xl border border-slate-100 dark:border-slate-700 space-y-4">
        <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-700 pb-3">
          <div className="flex items-center gap-2">
            <span className="text-xl">🛡️</span>
            <div>
              <h3 className="text-base font-bold text-slate-900 dark:text-white">
                Denunciar {targetLabel}
              </h3>
              {targetTitle && (
                <p className="text-xs text-slate-500 dark:text-slate-400 truncate max-w-xs">
                  "{targetTitle}"
                </p>
              )}
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="w-8 h-8 rounded-full bg-slate-100 dark:bg-slate-700 flex items-center justify-center text-slate-500 hover:bg-slate-200 dark:hover:bg-slate-600 transition"
          >
            ✕
          </button>
        </div>

        {successMsg ? (
          <div className="p-4 rounded-2xl bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800 text-emerald-800 dark:text-emerald-300 text-xs font-semibold flex items-center gap-2">
            <span>✅</span>
            <span>{successMsg}</span>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            {errorMsg && (
              <div className="p-3 rounded-xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800 text-rose-700 dark:text-rose-300 text-xs font-semibold">
                {errorMsg}
              </div>
            )}

            <div>
              <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1.5">
                Motivo de la denuncia:
              </label>
              <select
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                className="w-full text-xs rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-700/60 p-2.5 text-slate-900 dark:text-white focus:ring-2 focus:ring-teal-500"
              >
                {REPORT_REASONS.map((r) => (
                  <option key={r.value} value={r.value}>
                    {r.label}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1.5">
                Detalles adicionales (opcional):
              </label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Explica qué norma o conducta infringe este elemento para facilitar la revisión..."
                rows={3}
                maxLength={500}
                className="w-full text-xs rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-700/60 p-2.5 text-slate-900 dark:text-white focus:ring-2 focus:ring-teal-500 resize-none"
              />
              <div className="text-[10px] text-right text-slate-400 mt-0.5">
                {description.length}/500 caracteres
              </div>
            </div>

            <p className="text-[11px] text-slate-500 dark:text-slate-400 leading-relaxed">
              Las denuncias infundadas o maliciosas reiteradas pueden suponer sanciones disciplinarias sobre la cuenta denunciante.
            </p>

            <div className="flex justify-end gap-2 pt-2 border-t border-slate-100 dark:border-slate-700">
              <Button color="light" size="xs" onClick={onClose} disabled={isSubmitting}>
                Cancelar
              </Button>
              <Button
                color="failure"
                size="xs"
                type="submit"
                disabled={isSubmitting}
              >
                {isSubmitting ? (
                  <div className="flex items-center gap-1.5">
                    <Spinner size="xs" />
                    <span>Enviando...</span>
                  </div>
                ) : (
                  '🚩 Enviar Denuncia'
                )}
              </Button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
};
