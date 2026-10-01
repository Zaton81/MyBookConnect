import React, { useState, useEffect } from 'react';
import { Spinner } from 'flowbite-react';

interface SupportTicketItem {
  id: number;
  user: number;
  user_username?: string | null;
  user_email?: string | null;
  subject: string;
  message: string;
  category: 'technical' | 'account' | 'billing' | 'other' | string;
  priority: 'LOW' | 'NORMAL' | 'HIGH' | 'URGENT' | string;
  status: 'OPEN' | 'IN_PROGRESS' | 'RESOLVED' | 'CLOSED' | string;
  admin_response?: string | null;
  created_at: string;
  updated_at: string;
}

interface AdminSupportTabProps {
  token: string | null;
  apiUrl: string;
}

export function AdminSupportTab({ token, apiUrl }: AdminSupportTabProps) {
  const [tickets, setTickets] = useState<SupportTicketItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [priorityFilter, setPriorityFilter] = useState<string>('all');

  // Modal / Edición y respuesta
  const [selectedTicket, setSelectedTicket] = useState<SupportTicketItem | null>(null);
  const [editStatus, setEditStatus] = useState<string>('IN_PROGRESS');
  const [editPriority, setEditPriority] = useState<string>('NORMAL');
  const [adminResponse, setAdminResponse] = useState<string>('');
  const [saving, setSaving] = useState(false);
  const [actionMsg, setActionMsg] = useState<{ text: string; type: 'success' | 'error' } | null>(null);

  const fetchTickets = async () => {
    if (!token) return;
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (statusFilter !== 'all') params.append('status', statusFilter);
      if (priorityFilter !== 'all') params.append('priority', priorityFilter);

      const res = await fetch(`${apiUrl}/api/v1/beta/admin/support/?${params.toString()}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setTickets(Array.isArray(data) ? data : data.results || []);
      }
    } catch (e) {
      console.error('Error al cargar tickets de soporte:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTickets();
  }, [token, statusFilter, priorityFilter]);

  const handleOpenTicket = (ticket: SupportTicketItem) => {
    setSelectedTicket(ticket);
    setEditStatus(ticket.status);
    setEditPriority(ticket.priority);
    setAdminResponse(ticket.admin_response || '');
  };

  const handleSaveResolution = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token || !selectedTicket) return;
    setSaving(true);
    setActionMsg(null);

    try {
      const res = await fetch(`${apiUrl}/api/v1/beta/admin/support/${selectedTicket.id}/`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          status: editStatus,
          priority: editPriority,
          admin_response: adminResponse.trim(),
        }),
      });

      if (res.ok) {
        const updated = await res.json();
        setTickets((prev) => prev.map((t) => (t.id === updated.id ? updated : t)));
        setActionMsg({ text: 'Ticket actualizado y respuesta guardada con éxito.', type: 'success' });
        setSelectedTicket(null);
      } else {
        const err = await res.json().catch(() => ({}));
        setActionMsg({ text: err.detail || 'Error al actualizar el ticket.', type: 'error' });
      }
    } catch (err: any) {
      setActionMsg({ text: err.message || 'Error de conexión', type: 'error' });
    } finally {
      setSaving(false);
    }
  };

  const getPriorityBadge = (priority: string) => {
    const map: Record<string, { label: string; color: string }> = {
      URGENT: { label: '🔴 Urgente', color: 'bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-200' },
      HIGH: { label: '🟠 Alta', color: 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-200' },
      NORMAL: { label: '🔵 Normal', color: 'bg-sky-100 text-sky-800 dark:bg-sky-900/40 dark:text-sky-200' },
      LOW: { label: '⚪ Baja', color: 'bg-slate-100 text-slate-800 dark:bg-slate-700 dark:text-slate-200' },
    };
    const p = map[priority.toUpperCase()] || { label: priority, color: 'bg-slate-100 text-slate-700' };
    return <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${p.color}`}>{p.label}</span>;
  };

  const getStatusBadge = (status: string) => {
    const map: Record<string, { label: string; color: string }> = {
      OPEN: { label: '● Abierto', color: 'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-200' },
      IN_PROGRESS: { label: '● En Progreso', color: 'bg-purple-100 text-purple-800 dark:bg-purple-900/40 dark:text-purple-200' },
      RESOLVED: { label: '✓ Resuelto', color: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-200' },
      CLOSED: { label: '✕ Cerrado', color: 'bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300' },
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
            <span className="text-2xl">🎫</span>
            <h2 className="text-lg font-bold text-slate-900 dark:text-white">
              Mesa de Tickets de Soporte
            </h2>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-teal-50 text-teal-700 dark:bg-teal-900/30 dark:text-teal-300">
              {tickets.length} tickets
            </span>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 max-w-xl">
            Atención al lector, incidencias de acceso, fallos en la biblioteca y soporte técnico oficial.
          </p>
        </div>

        <button
          onClick={fetchTickets}
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
            <option value="OPEN">Abiertos</option>
            <option value="IN_PROGRESS">En Progreso</option>
            <option value="RESOLVED">Resueltos</option>
            <option value="CLOSED">Cerrados</option>
          </select>
        </div>

        <div>
          <label className="font-bold text-slate-500 mr-2">Prioridad:</label>
          <select
            value={priorityFilter}
            onChange={(e) => setPriorityFilter(e.target.value)}
            className="rounded-xl border border-slate-200 dark:border-slate-600 bg-slate-50 dark:bg-slate-900 py-1.5 px-3 text-xs focus:ring-2 focus:ring-teal-500"
          >
            <option value="all">Todas las prioridades</option>
            <option value="URGENT">Urgente</option>
            <option value="HIGH">Alta</option>
            <option value="NORMAL">Normal</option>
            <option value="LOW">Baja</option>
          </select>
        </div>
      </div>

      {/* Listado de tickets */}
      {loading ? (
        <div className="flex justify-center p-12">
          <Spinner size="xl" color="info" />
        </div>
      ) : tickets.length === 0 ? (
        <div className="text-center py-12 bg-white dark:bg-slate-800 rounded-3xl border border-dashed border-slate-200 dark:border-slate-700 text-slate-500 dark:text-slate-400 text-xs">
          No hay tickets de soporte con los filtros seleccionados.
        </div>
      ) : (
        <div className="bg-white dark:bg-slate-800 rounded-3xl border border-slate-200/80 dark:border-slate-700 shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-600 dark:text-slate-300">
              <thead className="bg-slate-50 dark:bg-slate-700/50 text-[11px] uppercase tracking-wider text-slate-500 dark:text-slate-400 border-b border-slate-200 dark:border-slate-700">
                <tr>
                  <th className="py-3.5 px-4 font-bold">Ticket</th>
                  <th className="py-3.5 px-4 font-bold">Usuario</th>
                  <th className="py-3.5 px-4 font-bold">Prioridad</th>
                  <th className="py-3.5 px-4 font-bold">Estado</th>
                  <th className="py-3.5 px-4 font-bold">Fecha</th>
                  <th className="py-3.5 px-4 font-bold text-right">Acción</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-700/50">
                {tickets.map((t) => (
                  <tr
                    key={t.id}
                    onClick={() => handleOpenTicket(t)}
                    className="hover:bg-slate-50/70 dark:hover:bg-slate-700/30 transition-colors cursor-pointer"
                  >
                    <td className="py-3 px-4">
                      <div className="font-bold text-slate-900 dark:text-white line-clamp-1">
                        #{t.id} - {t.subject}
                      </div>
                      <div className="text-[11px] text-slate-400 line-clamp-1 mt-0.5">
                        {t.message}
                      </div>
                    </td>
                    <td className="py-3 px-4 font-medium">
                      <div>{t.user_username || 'Usuario'}</div>
                      <div className="text-[10px] text-slate-400">{t.user_email || 'Sin email'}</div>
                    </td>
                    <td className="py-3 px-4">{getPriorityBadge(t.priority)}</td>
                    <td className="py-3 px-4">{getStatusBadge(t.status)}</td>
                    <td className="py-3 px-4 text-[11px] text-slate-400">
                      {new Date(t.created_at).toLocaleDateString('es-ES', {
                        day: 'numeric',
                        month: 'short',
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleOpenTicket(t);
                        }}
                        className="bg-teal-50 text-teal-700 dark:bg-teal-950/40 dark:text-teal-300 font-bold px-3 py-1.5 rounded-xl hover:bg-teal-100 transition-colors"
                      >
                        Gestionar
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Modal de Detalle y Respuesta a Ticket */}
      {selectedTicket && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-fadeIn">
          <div className="bg-white dark:bg-slate-800 rounded-3xl max-w-2xl w-full p-6 space-y-5 shadow-2xl border border-slate-200 dark:border-slate-700 max-h-[90vh] overflow-y-auto">
            <div className="flex items-start justify-between">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  {getPriorityBadge(selectedTicket.priority)}
                  {getStatusBadge(selectedTicket.status)}
                </div>
                <h2 className="text-base font-bold text-slate-900 dark:text-white">
                  Ticket #{selectedTicket.id}: {selectedTicket.subject}
                </h2>
                <div className="text-xs text-slate-500 mt-0.5">
                  Por {selectedTicket.user_username} ({selectedTicket.user_email || 'Sin correo'})
                </div>
              </div>
              <button
                onClick={() => setSelectedTicket(null)}
                className="text-slate-400 hover:text-slate-600 dark:hover:text-white text-xl font-bold p-1"
              >
                &times;
              </button>
            </div>

            <div className="p-4 bg-slate-50 dark:bg-slate-900/60 rounded-2xl text-xs space-y-2">
              <span className="font-bold text-slate-500 text-[10px] uppercase tracking-wider">
                Mensaje del Lector:
              </span>
              <p className="text-slate-800 dark:text-slate-200 leading-relaxed whitespace-pre-wrap">
                {selectedTicket.message}
              </p>
            </div>

            {/* Formulario de Respuesta y Resolución */}
            <form onSubmit={handleSaveResolution} className="space-y-4 pt-2 border-t border-slate-100 dark:border-slate-700">
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300">
                Resolución del Ticket de Soporte
              </h4>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1">
                    Estado del Ticket
                  </label>
                  <select
                    value={editStatus}
                    onChange={(e) => setEditStatus(e.target.value)}
                    className="w-full text-xs rounded-xl border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-900 p-2.5 focus:ring-2 focus:ring-teal-500 font-semibold"
                  >
                    <option value="OPEN">Abierto</option>
                    <option value="IN_PROGRESS">En Progreso</option>
                    <option value="RESOLVED">Resuelto</option>
                    <option value="CLOSED">Cerrado</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1">
                    Prioridad
                  </label>
                  <select
                    value={editPriority}
                    onChange={(e) => setEditPriority(e.target.value)}
                    className="w-full text-xs rounded-xl border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-900 p-2.5 focus:ring-2 focus:ring-teal-500 font-semibold"
                  >
                    <option value="LOW">Baja</option>
                    <option value="NORMAL">Normal</option>
                    <option value="HIGH">Alta</option>
                    <option value="URGENT">Urgente</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1">
                  Respuesta Oficial de Administración al Usuario
                </label>
                <textarea
                  rows={4}
                  value={adminResponse}
                  onChange={(e) => setAdminResponse(e.target.value)}
                  placeholder="Redacta la solución, aclaración o respuesta técnica que visualizará el usuario..."
                  className="w-full text-xs rounded-xl border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-900 p-2.5 focus:ring-2 focus:ring-teal-500 leading-relaxed"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setSelectedTicket(null)}
                  className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-600 hover:bg-slate-200 dark:text-slate-300 dark:hover:bg-slate-700"
                >
                  Cerrar
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="bg-teal-600 hover:bg-teal-700 text-white text-xs font-bold px-5 py-2 rounded-xl shadow-md transition-all disabled:opacity-50"
                >
                  {saving ? 'Guardando...' : 'Guardar Resolución'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
export default AdminSupportTab;
