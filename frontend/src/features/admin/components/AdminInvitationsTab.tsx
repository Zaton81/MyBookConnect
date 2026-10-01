import React, { useState, useEffect } from 'react';
import { Spinner } from 'flowbite-react';

interface InvitationItem {
  id: number;
  code: string;
  invited_email?: string | null;
  max_uses: number;
  uses_count: number;
  is_active: boolean;
  is_valid: boolean;
  expires_at?: string | null;
  created_by_username?: string | null;
  created_at: string;
}

interface AdminInvitationsTabProps {
  token: string | null;
  apiUrl: string;
}

export function AdminInvitationsTab({ token, apiUrl }: AdminInvitationsTabProps) {
  const [invitations, setInvitations] = useState<InvitationItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [statusFilter, setStatusFilter] = useState<'all' | 'valid' | 'exhausted'>('all');
  const [copiedCode, setCopiedCode] = useState<string | null>(null);

  // Formulario de nueva invitación
  const [showForm, setShowForm] = useState(false);
  const [code, setCode] = useState('');
  const [invitedEmail, setInvitedEmail] = useState('');
  const [maxUses, setMaxUses] = useState(1);
  const [expiresAt, setExpiresAt] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [feedbackMsg, setFeedbackMsg] = useState<{ text: string; type: 'success' | 'error' } | null>(null);

  const fetchInvitations = async () => {
    if (!token) return;
    setLoading(true);
    try {
      const res = await fetch(`${apiUrl}/api/v1/beta/admin/invitations/`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setInvitations(Array.isArray(data) ? data : data.results || []);
      }
    } catch (e) {
      console.error('Error al cargar invitaciones:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchInvitations();
  }, [token]);

  const handleCreateInvitation = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token) return;
    setSubmitting(true);
    setFeedbackMsg(null);

    try {
      const payload: any = {
        max_uses: Number(maxUses) || 1,
      };
      if (code.trim()) payload.code = code.trim().toUpperCase();
      if (invitedEmail.trim()) payload.invited_email = invitedEmail.trim();
      if (expiresAt) payload.expires_at = new Date(expiresAt).toISOString();

      const res = await fetch(`${apiUrl}/api/v1/beta/admin/invitations/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(payload),
      });

      if (res.ok) {
        setFeedbackMsg({ text: 'Código de invitación generado correctamente.', type: 'success' });
        setCode('');
        setInvitedEmail('');
        setMaxUses(1);
        setExpiresAt('');
        setShowForm(false);
        fetchInvitations();
      } else {
        const err = await res.json().catch(() => ({}));
        setFeedbackMsg({
          text: err.code?.[0] || err.detail || 'Error al crear la invitación.',
          type: 'error',
        });
      }
    } catch (err: any) {
      setFeedbackMsg({ text: err.message || 'Error de conexión', type: 'error' });
    } finally {
      setSubmitting(false);
    }
  };

  const handleCopyLink = (invitationCode: string) => {
    const origin = window.location.origin;
    const url = `${origin}/register?ref=${invitationCode}`;
    navigator.clipboard.writeText(url);
    setCopiedCode(invitationCode);
    setTimeout(() => setCopiedCode(null), 2500);
  };

  const filteredInvitations = invitations.filter((inv) => {
    if (statusFilter === 'valid') return inv.is_valid;
    if (statusFilter === 'exhausted') return !inv.is_valid;
    return true;
  });

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Cabecera */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-white dark:bg-slate-800 p-6 rounded-3xl border border-slate-200/80 dark:border-slate-700 shadow-sm">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-2xl">🎟️</span>
            <h2 className="text-lg font-bold text-slate-900 dark:text-white">
              Gestión de Invitaciones a la Beta
            </h2>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 max-w-xl">
            Genera, audita y controla los códigos de acceso a la beta cerrada de la plataforma.
          </p>
        </div>

        <button
          onClick={() => setShowForm(!showForm)}
          className="bg-teal-600 hover:bg-teal-700 text-white text-xs font-bold px-4 py-2.5 rounded-2xl transition-all shadow-md shadow-teal-600/20 flex items-center gap-1.5"
        >
          <span>{showForm ? '✕ Cancelar' : '+ Nueva Invitación'}</span>
        </button>
      </div>

      {feedbackMsg && (
        <div
          className={`p-3 rounded-2xl text-xs font-semibold flex items-center justify-between ${
            feedbackMsg.type === 'success'
              ? 'bg-emerald-50 text-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800'
              : 'bg-rose-50 text-rose-800 dark:bg-rose-950/40 dark:text-rose-300 border border-rose-200 dark:border-rose-800'
          }`}
        >
          <span>{feedbackMsg.text}</span>
          <button onClick={() => setFeedbackMsg(null)} className="font-bold ml-2">
            &times;
          </button>
        </div>
      )}

      {/* Formulario de creación */}
      {showForm && (
        <form
          onSubmit={handleCreateInvitation}
          className="bg-slate-50 dark:bg-slate-800/80 p-5 rounded-3xl border border-slate-200 dark:border-slate-700 space-y-4 shadow-sm"
        >
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300">
            Crear Código de Invitación
          </h3>

          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1">
                Código (Opcional)
              </label>
              <input
                type="text"
                value={code}
                onChange={(e) => setCode(e.target.value)}
                placeholder="Ej: BETA2026VIP"
                maxLength={32}
                className="w-full text-xs rounded-xl border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-900 p-2.5 focus:ring-2 focus:ring-teal-500 uppercase font-mono"
              />
              <span className="text-[10px] text-slate-400">Si se deja vacío, se generará aleatoriamente</span>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1">
                Email Destinatario (Opcional)
              </label>
              <input
                type="email"
                value={invitedEmail}
                onChange={(e) => setInvitedEmail(e.target.value)}
                placeholder="lector@ejemplo.com"
                className="w-full text-xs rounded-xl border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-900 p-2.5 focus:ring-2 focus:ring-teal-500"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1">
                Usos Permitidos
              </label>
              <input
                type="number"
                min={1}
                max={500}
                value={maxUses}
                onChange={(e) => setMaxUses(Math.max(1, parseInt(e.target.value) || 1))}
                className="w-full text-xs rounded-xl border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-900 p-2.5 focus:ring-2 focus:ring-teal-500"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1">
                Fecha de Expiración
              </label>
              <input
                type="date"
                value={expiresAt}
                onChange={(e) => setExpiresAt(e.target.value)}
                className="w-full text-xs rounded-xl border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-900 p-2.5 focus:ring-2 focus:ring-teal-500"
              />
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={() => setShowForm(false)}
              className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-600 hover:bg-slate-200 dark:text-slate-300 dark:hover:bg-slate-700"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="bg-teal-600 hover:bg-teal-700 text-white text-xs font-bold px-5 py-2 rounded-xl shadow-md transition-all disabled:opacity-50"
            >
              {submitting ? 'Generando...' : 'Guardar Invitación'}
            </button>
          </div>
        </form>
      )}

      {/* Filtros */}
      <div className="flex items-center gap-2">
        <span className="text-xs font-bold text-slate-500 dark:text-slate-400">Filtrar:</span>
        {(['all', 'valid', 'exhausted'] as const).map((filter) => (
          <button
            key={filter}
            onClick={() => setStatusFilter(filter)}
            className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all ${
              statusFilter === filter
                ? 'bg-teal-600 text-white shadow-xs'
                : 'bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-slate-700 hover:bg-slate-100'
            }`}
          >
            {filter === 'all' ? 'Todas' : filter === 'valid' ? 'Disponibles / Válidas' : 'Agotadas / Expiradas'}
          </button>
        ))}
      </div>

      {/* Listado de invitaciones */}
      {loading ? (
        <div className="flex justify-center p-12">
          <Spinner size="xl" color="info" />
        </div>
      ) : filteredInvitations.length === 0 ? (
        <div className="text-center py-12 bg-white dark:bg-slate-800 rounded-3xl border border-dashed border-slate-200 dark:border-slate-700 text-slate-500 dark:text-slate-400 text-xs">
          No se encontraron invitaciones con el criterio seleccionado.
        </div>
      ) : (
        <div className="bg-white dark:bg-slate-800 rounded-3xl border border-slate-200/80 dark:border-slate-700 shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-600 dark:text-slate-300">
              <thead className="bg-slate-50 dark:bg-slate-700/50 text-[11px] uppercase tracking-wider text-slate-500 dark:text-slate-400 border-b border-slate-200 dark:border-slate-700">
                <tr>
                  <th className="py-3.5 px-4 font-bold">Código</th>
                  <th className="py-3.5 px-4 font-bold">Destinatario</th>
                  <th className="py-3.5 px-4 font-bold text-center">Usos</th>
                  <th className="py-3.5 px-4 font-bold">Estado</th>
                  <th className="py-3.5 px-4 font-bold">Expiración</th>
                  <th className="py-3.5 px-4 font-bold">Creado Por</th>
                  <th className="py-3.5 px-4 font-bold text-right">Acción</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-700/50">
                {filteredInvitations.map((inv) => (
                  <tr key={inv.id} className="hover:bg-slate-50/70 dark:hover:bg-slate-700/30 transition-colors">
                    <td className="py-3 px-4 font-mono font-bold text-slate-900 dark:text-white">
                      {inv.code}
                    </td>
                    <td className="py-3 px-4">
                      {inv.invited_email ? (
                        <span className="text-slate-700 dark:text-slate-300">{inv.invited_email}</span>
                      ) : (
                        <span className="text-slate-400 italic">Genérico</span>
                      )}
                    </td>
                    <td className="py-3 px-4 text-center font-bold">
                      <span className={inv.uses_count >= inv.max_uses ? 'text-rose-500' : 'text-teal-600 dark:text-teal-400'}>
                        {inv.uses_count}
                      </span>
                      <span className="text-slate-400"> / {inv.max_uses}</span>
                    </td>
                    <td className="py-3 px-4">
                      {inv.is_valid ? (
                        <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 dark:bg-emerald-900/40 text-emerald-800 dark:text-emerald-200">
                          ● Activa
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-rose-100 dark:bg-rose-900/40 text-rose-800 dark:text-rose-200">
                          ● Agotada / Expirada
                        </span>
                      )}
                    </td>
                    <td className="py-3 px-4 text-slate-500 text-[11px]">
                      {inv.expires_at ? new Date(inv.expires_at).toLocaleDateString('es-ES') : 'Sin límite'}
                    </td>
                    <td className="py-3 px-4 text-[11px] text-slate-500">
                      {inv.created_by_username || 'Sistema'}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <button
                        onClick={() => handleCopyLink(inv.code)}
                        className={`text-xs font-bold px-3 py-1.5 rounded-xl transition-all ${
                          copiedCode === inv.code
                            ? 'bg-emerald-600 text-white shadow-xs'
                            : 'bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-200 hover:bg-slate-200'
                        }`}
                      >
                        {copiedCode === inv.code ? '✓ ¡Enlace Copiado!' : '🔗 Copiar Enlace'}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
export default AdminInvitationsTab;
