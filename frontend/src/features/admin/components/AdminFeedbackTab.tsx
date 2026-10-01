import React, { useState, useEffect } from 'react';
import { Spinner } from 'flowbite-react';

interface FeedbackItem {
  id: number;
  user: number;
  user_username?: string | null;
  user_email?: string | null;
  category: 'BUG' | 'FEATURE' | 'USABILITY' | 'CONTENT' | 'PERFORMANCE' | 'OTHER' | string;
  title: string;
  description: string;
  page_url?: string | null;
  device_info?: string | null;
  status: 'NEW' | 'TRIAGED' | 'IN_PROGRESS' | 'RESOLVED' | 'DISMISSED' | string;
  admin_notes?: string | null;
  created_at: string;
  updated_at: string;
}

interface AdminFeedbackTabProps {
  token: string | null;
  apiUrl: string;
}

export function AdminFeedbackTab({ token, apiUrl }: AdminFeedbackTabProps) {
  const [feedbackList, setFeedbackList] = useState<FeedbackItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [categoryFilter, setCategoryFilter] = useState<string>('all');

  // Modal / Edición de triaje
  const [selectedFeedback, setSelectedFeedback] = useState<FeedbackItem | null>(null);
  const [editStatus, setEditStatus] = useState<string>('TRIAGED');
  const [adminNotes, setAdminNotes] = useState<string>('');
  const [saving, setSaving] = useState(false);
  const [actionMsg, setActionMsg] = useState<{ text: string; type: 'success' | 'error' } | null>(null);

  const fetchFeedback = async () => {
    if (!token) return;
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (statusFilter !== 'all') params.append('status', statusFilter);
      if (categoryFilter !== 'all') params.append('category', categoryFilter);

      const res = await fetch(`${apiUrl}/api/v1/beta/admin/feedback/?${params.toString()}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setFeedbackList(Array.isArray(data) ? data : data.results || []);
      }
    } catch (e) {
      console.error('Error al cargar feedback:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchFeedback();
  }, [token, statusFilter, categoryFilter]);

  const handleOpenDetail = (item: FeedbackItem) => {
    setSelectedFeedback(item);
    setEditStatus(item.status);
    setAdminNotes(item.admin_notes || '');
  };

  const handleSaveTriage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token || !selectedFeedback) return;
    setSaving(true);
    setActionMsg(null);

    try {
      const res = await fetch(`${apiUrl}/api/v1/beta/admin/feedback/${selectedFeedback.id}/`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          status: editStatus,
          admin_notes: adminNotes.trim(),
        }),
      });

      if (res.ok) {
        const updated = await res.json();
        setFeedbackList((prev) => prev.map((f) => (f.id === updated.id ? updated : f)));
        setActionMsg({ text: 'Triaje de feedback guardado correctamente.', type: 'success' });
        setSelectedFeedback(null);
      } else {
        const err = await res.json().catch(() => ({}));
        setActionMsg({ text: err.detail || 'Error al actualizar el feedback.', type: 'error' });
      }
    } catch (err: any) {
      setActionMsg({ text: err.message || 'Error de conexión', type: 'error' });
    } finally {
      setSaving(false);
    }
  };

  const getCategoryBadge = (category: string) => {
    const map: Record<string, { label: string; color: string }> = {
      BUG: { label: '🐛 Error', color: 'bg-rose-100 text-rose-800 dark:bg-rose-900/40 dark:text-rose-200' },
      FEATURE: { label: '✨ Función', color: 'bg-purple-100 text-purple-800 dark:bg-purple-900/40 dark:text-purple-200' },
      USABILITY: { label: '🎨 UX / Diseño', color: 'bg-sky-100 text-sky-800 dark:bg-sky-900/40 dark:text-sky-200' },
      CONTENT: { label: '📖 Contenido', color: 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-200' },
      PERFORMANCE: { label: '⚡ Rendimiento', color: 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900/40 dark:text-indigo-200' },
      OTHER: { label: '💬 Otro', color: 'bg-slate-100 text-slate-800 dark:bg-slate-700 dark:text-slate-200' },
    };
    const c = map[category.toUpperCase()] || { label: category, color: 'bg-slate-100 text-slate-700' };
    return <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${c.color}`}>{c.label}</span>;
  };

  const getStatusBadge = (status: string) => {
    const map: Record<string, { label: string; color: string }> = {
      NEW: { label: '● Nuevo', color: 'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-200' },
      TRIAGED: { label: '● En Triaje', color: 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-200' },
      IN_PROGRESS: { label: '● En Desarrollo', color: 'bg-purple-100 text-purple-800 dark:bg-purple-900/40 dark:text-purple-200' },
      RESOLVED: { label: '✓ Resuelto', color: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-200' },
      DISMISSED: { label: '✕ Desestimado', color: 'bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300' },
    };
    const s = map[status.toUpperCase()] || { label: status, color: 'bg-slate-100 text-slate-700' };
    return <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${s.color}`}>{s.label}</span>;
  };

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Cabecera */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-white dark:bg-slate-800 p-6 rounded-3xl border border-slate-200/80 dark:border-slate-700 shadow-sm">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-2xl">💬</span>
            <h2 className="text-lg font-bold text-slate-900 dark:text-white">
              Centro de Feedback de Usuarios
            </h2>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-teal-50 text-teal-700 dark:bg-teal-900/30 dark:text-teal-300">
              {feedbackList.length} incidencias
            </span>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 max-w-xl">
            Supervisa, prioriza y responde a las sugerencias, errores y opiniones remitidas por la comunidad de beta testers.
          </p>
        </div>

        <button
          onClick={fetchFeedback}
          className="bg-slate-100 hover:bg-slate-200 dark:bg-slate-700 dark:hover:bg-slate-600 text-slate-700 dark:text-slate-200 text-xs font-bold px-4 py-2.5 rounded-2xl transition-all shadow-xs flex items-center gap-1.5"
        >
          <span>🔄</span>
          <span>Actualizar</span>
        </button>
      </div>

      {actionMsg && (
        <div
          className={`p-3 rounded-2xl text-xs font-semibold flex items-center justify-between ${
            actionMsg.type === 'success'
              ? 'bg-emerald-50 text-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800'
              : 'bg-rose-50 text-rose-800 dark:bg-rose-950/40 dark:text-rose-300 border border-rose-200 dark:border-rose-800'
          }`}
        >
          <span>{actionMsg.text}</span>
          <button onClick={() => setActionMsg(null)} className="font-bold ml-2">
            &times;
          </button>
        </div>
      )}

      {/* Barra de Filtros */}
      <div className="flex flex-wrap items-center gap-3 bg-white dark:bg-slate-800 p-4 rounded-2xl border border-slate-200 dark:border-slate-700 text-xs">
        <div>
          <label className="font-bold text-slate-500 mr-2">Estado:</label>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="rounded-xl border border-slate-200 dark:border-slate-600 bg-slate-50 dark:bg-slate-900 py-1.5 px-3 text-xs focus:ring-2 focus:ring-teal-500"
          >
            <option value="all">Todos los estados</option>
            <option value="NEW">Nuevos</option>
            <option value="TRIAGED">En Triaje</option>
            <option value="IN_PROGRESS">En Desarrollo</option>
            <option value="RESOLVED">Resueltos</option>
            <option value="DISMISSED">Desestimados</option>
          </select>
        </div>

        <div>
          <label className="font-bold text-slate-500 mr-2">Categoría:</label>
          <select
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
            className="rounded-xl border border-slate-200 dark:border-slate-600 bg-slate-50 dark:bg-slate-900 py-1.5 px-3 text-xs focus:ring-2 focus:ring-teal-500"
          >
            <option value="all">Todas las categorías</option>
            <option value="BUG">Errores (Bug)</option>
            <option value="FEATURE">Nueva Función</option>
            <option value="USABILITY">Usabilidad / UX</option>
            <option value="CONTENT">Contenido</option>
            <option value="PERFORMANCE">Rendimiento</option>
            <option value="OTHER">Otros</option>
          </select>
        </div>
      </div>

      {/* Listado de feedback */}
      {loading ? (
        <div className="flex justify-center p-12">
          <Spinner size="xl" color="info" />
        </div>
      ) : feedbackList.length === 0 ? (
        <div className="text-center py-12 bg-white dark:bg-slate-800 rounded-3xl border border-dashed border-slate-200 dark:border-slate-700 text-slate-500 dark:text-slate-400 text-xs">
          No se encontraron reportes de feedback con los filtros actuales.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {feedbackList.map((item) => (
            <div
              key={item.id}
              onClick={() => handleOpenDetail(item)}
              className="bg-white dark:bg-slate-800 p-5 rounded-3xl border border-slate-200/80 dark:border-slate-700 shadow-sm hover:shadow-md hover:border-teal-500/50 transition-all cursor-pointer space-y-3"
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-center gap-2">
                  {getCategoryBadge(item.category)}
                  {getStatusBadge(item.status)}
                </div>
                <span className="text-[10px] text-slate-400">
                  {new Date(item.created_at).toLocaleDateString('es-ES', {
                    day: 'numeric',
                    month: 'short',
                    hour: '2-digit',
                    minute: '2-digit',
                  })}
                </span>
              </div>

              <div>
                <h3 className="text-sm font-bold text-slate-900 dark:text-white line-clamp-1">
                  {item.title}
                </h3>
                <p className="text-xs text-slate-600 dark:text-slate-300 mt-1 line-clamp-2">
                  {item.description}
                </p>
              </div>

              <div className="flex items-center justify-between pt-2 border-t border-slate-100 dark:border-slate-700 text-[11px] text-slate-500">
                <div className="flex items-center gap-1.5 font-medium">
                  <span>👤</span>
                  <span>{item.user_username || 'Usuario Anónimo'}</span>
                </div>
                {item.admin_notes && (
                  <span className="text-teal-600 dark:text-teal-400 font-bold flex items-center gap-1">
                    ✓ Con notas de triaje
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Modal / Panel de Detalle y Triaje */}
      {selectedFeedback && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-fadeIn">
          <div className="bg-white dark:bg-slate-800 rounded-3xl max-w-2xl w-full p-6 space-y-5 shadow-2xl border border-slate-200 dark:border-slate-700 max-h-[90vh] overflow-y-auto">
            <div className="flex items-start justify-between">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  {getCategoryBadge(selectedFeedback.category)}
                  {getStatusBadge(selectedFeedback.status)}
                </div>
                <h2 className="text-base font-bold text-slate-900 dark:text-white">
                  {selectedFeedback.title}
                </h2>
              </div>
              <button
                onClick={() => setSelectedFeedback(null)}
                className="text-slate-400 hover:text-slate-600 dark:hover:text-white text-xl font-bold p-1"
              >
                &times;
              </button>
            </div>

            <div className="p-4 bg-slate-50 dark:bg-slate-900/60 rounded-2xl space-y-2 text-xs">
              <p className="text-slate-800 dark:text-slate-200 leading-relaxed whitespace-pre-wrap">
                {selectedFeedback.description}
              </p>
              <div className="pt-2 border-t border-slate-200 dark:border-slate-800 text-[11px] text-slate-500 space-y-1">
                <div>
                  <strong>Remitente:</strong> {selectedFeedback.user_username} ({selectedFeedback.user_email || 'Sin email'})
                </div>
                {selectedFeedback.page_url && (
                  <div>
                    <strong>Página Origen:</strong> <span className="font-mono text-slate-600 dark:text-slate-400">{selectedFeedback.page_url}</span>
                  </div>
                )}
                {selectedFeedback.device_info && (
                  <div>
                    <strong>Dispositivo:</strong> <span className="font-mono text-slate-600 dark:text-slate-400">{selectedFeedback.device_info}</span>
                  </div>
                )}
              </div>
            </div>

            {/* Formulario de Triaje */}
            <form onSubmit={handleSaveTriage} className="space-y-4 pt-2 border-t border-slate-100 dark:border-slate-700">
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300">
                Resolución de Triaje Administrativo
              </h4>

              <div>
                <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1">
                  Actualizar Estado
                </label>
                <select
                  value={editStatus}
                  onChange={(e) => setEditStatus(e.target.value)}
                  className="w-full text-xs rounded-xl border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-900 p-2.5 focus:ring-2 focus:ring-teal-500 font-semibold"
                >
                  <option value="NEW">Nuevo</option>
                  <option value="TRIAGED">En Triaje (Revisado)</option>
                  <option value="IN_PROGRESS">En Desarrollo (Asignado)</option>
                  <option value="RESOLVED">Resuelto</option>
                  <option value="DISMISSED">Desestimado / No Reproducible</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1">
                  Notas de Administración / Respuesta Interna
                </label>
                <textarea
                  rows={3}
                  value={adminNotes}
                  onChange={(e) => setAdminNotes(e.target.value)}
                  placeholder="Detalles de la corrección, ticket de Jira/GitHub asociado o justificación..."
                  className="w-full text-xs rounded-xl border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-900 p-2.5 focus:ring-2 focus:ring-teal-500 leading-relaxed"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setSelectedFeedback(null)}
                  className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-600 hover:bg-slate-200 dark:text-slate-300 dark:hover:bg-slate-700"
                >
                  Cerrar
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="bg-teal-600 hover:bg-teal-700 text-white text-xs font-bold px-5 py-2 rounded-xl shadow-md transition-all disabled:opacity-50"
                >
                  {saving ? 'Guardando...' : 'Guardar Triaje'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
export default AdminFeedbackTab;
