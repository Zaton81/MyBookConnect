import { useState, useEffect, useMemo } from 'react';
import { Spinner, Modal, Button } from 'flowbite-react';
import {
  HiOutlineShieldCheck,
  HiOutlineCheck,
  HiOutlineX,
  HiOutlineExternalLink,
  HiOutlineSearch,
  HiOutlineMail,
  HiOutlineUser,
} from 'react-icons/hi';
import { useAuthStore } from '../../../store/auth';

interface AuthorClaim {
  id: number;
  author: {
    id: number;
    name: string;
    photo?: string;
  };
  user: {
    id: number;
    username: string;
    email: string;
  };
  contact_email: string;
  proof_description: string;
  supporting_link: string;
  status: 'pending' | 'approved' | 'rejected';
  admin_notes: string;
  resolved_at: string | null;
  created_at: string;
}

export function AdminAuthorClaimsTab() {
  const { token } = useAuthStore();
  const [claims, setClaims] = useState<AuthorClaim[]>([]);
  const [loading, setLoading] = useState(false);
  const [statusFilter, setStatusFilter] = useState<'all' | 'pending' | 'approved' | 'rejected'>('pending');
  const [search, setSearch] = useState('');
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' } | null>(null);

  // Modal para resolver reclamo
  const [selectedClaim, setSelectedClaim] = useState<AuthorClaim | null>(null);
  const [resolutionAction, setResolutionAction] = useState<'approve' | 'reject'>('approve');
  const [adminNotes, setAdminNotes] = useState('');
  const [resolving, setResolving] = useState(false);

  const apiUrl = (import.meta as any).env.VITE_API_URL || 'http://localhost:8000';

  const loadClaims = async () => {
    if (!token) return;
    try {
      setLoading(true);
      const res = await fetch(`${apiUrl}/api/v1/admin/author-claims/`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error('Error al cargar reclamaciones de autor');
      const data = await res.json();
      setClaims(Array.isArray(data) ? data : data.results || []);
    } catch (err: any) {
      console.error(err);
      setMessage({ text: err.message || 'Error de conexión', type: 'error' });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadClaims();
  }, [token]);

  const handleOpenResolve = (claim: AuthorClaim, action: 'approve' | 'reject') => {
    setSelectedClaim(claim);
    setResolutionAction(action);
    setAdminNotes(
      action === 'approve'
        ? 'Identidad y acreditación verificadas satisfactoriamente.'
        : 'La documentación aportada no permite corroborar fehacientemente la autoría de la página.'
    );
  };

  const handleResolve = async () => {
    if (!token || !selectedClaim) return;
    try {
      setResolving(true);
      const res = await fetch(`${apiUrl}/api/v1/admin/author-claims/${selectedClaim.id}/resolve/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          action: resolutionAction,
          admin_notes: adminNotes,
        }),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => null);
        throw new Error(errData?.error || 'No se pudo resolver la solicitud');
      }

      setMessage({
        text:
          resolutionAction === 'approve'
            ? `Página de autor verificada y vinculada a @${selectedClaim.user.username}`
            : `Solicitud de autoría rechazada para @${selectedClaim.user.username}`,
        type: 'success',
      });
      setSelectedClaim(null);
      await loadClaims();
    } catch (err: any) {
      setMessage({ text: err.message || 'Error al procesar la resolución', type: 'error' });
    } finally {
      setResolving(false);
    }
  };

  const filteredClaims = useMemo(() => {
    return claims.filter((c) => {
      const matchesStatus = statusFilter === 'all' || c.status === statusFilter;
      const q = search.toLowerCase().trim();
      const matchesSearch =
        !q ||
        c.author?.name.toLowerCase().includes(q) ||
        c.user?.username.toLowerCase().includes(q) ||
        c.user?.email.toLowerCase().includes(q) ||
        c.contact_email?.toLowerCase().includes(q);
      return matchesStatus && matchesSearch;
    });
  }, [claims, statusFilter, search]);

  const pendingCount = claims.filter((c) => c.status === 'pending').length;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 bg-white dark:bg-slate-900 p-6 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm">
        <div>
          <h2 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
            <HiOutlineShieldCheck className="w-6 h-6 text-teal-600" />
            Reclamaciones y Verificación de Autores
          </h2>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            Revisa solicitudes de escritores que desean reclamar y gestionar su perfil oficial en el catálogo.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <span className="px-3.5 py-1.5 rounded-full bg-amber-50 dark:bg-amber-950/40 text-amber-700 dark:text-amber-400 border border-amber-200 dark:border-amber-800 text-xs font-bold">
            {pendingCount} pendientes
          </span>
        </div>
      </div>

      {/* Alerts */}
      {message && (
        <div
          className={`p-4 rounded-xl text-sm flex items-center justify-between ${
            message.type === 'success'
              ? 'bg-emerald-50 dark:bg-emerald-950/40 text-emerald-800 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800'
              : 'bg-red-50 dark:bg-red-950/40 text-red-800 dark:text-red-300 border border-red-200 dark:border-red-800'
          }`}
        >
          <span>{message.text}</span>
          <button
            type="button"
            onClick={() => setMessage(null)}
            className="text-xs font-bold underline ml-4 cursor-pointer"
          >
            Cerrar
          </button>
        </div>
      )}

      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="relative flex-1">
          <HiOutlineSearch className="w-5 h-5 absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Buscar por autor, usuario o email de contacto..."
            className="w-full pl-10 pr-4 py-2 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-sm text-slate-900 dark:text-white focus:ring-2 focus:ring-teal-500"
          />
        </div>

        <div className="flex gap-1.5 p-1 bg-slate-100 dark:bg-slate-800/80 rounded-xl">
          {(['pending', 'approved', 'rejected', 'all'] as const).map((st) => (
            <button
              key={st}
              type="button"
              onClick={() => setStatusFilter(st)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all cursor-pointer ${
                statusFilter === st
                  ? 'bg-white dark:bg-slate-700 text-slate-900 dark:text-white shadow-sm font-semibold'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
              }`}
            >
              {st === 'pending'
                ? `Pendientes (${pendingCount})`
                : st === 'approved'
                ? 'Aprobadas'
                : st === 'rejected'
                ? 'Rechazadas'
                : 'Todas'}
            </button>
          ))}
        </div>
      </div>

      {/* Claims List */}
      {loading ? (
        <div className="flex justify-center py-16">
          <Spinner size="xl" className="fill-teal-600" />
        </div>
      ) : filteredClaims.length === 0 ? (
        <div className="text-center py-16 bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 text-slate-500">
          No hay reclamaciones que coincidan con los criterios de búsqueda.
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4">
          {filteredClaims.map((claim) => (
            <div
              key={claim.id}
              className="p-6 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-4 hover:border-slate-300 dark:hover:border-slate-700 transition-colors"
            >
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 dark:border-slate-800 pb-4">
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="text-lg font-bold text-slate-900 dark:text-white">
                      {claim.author?.name}
                    </h3>
                    <span
                      className={`inline-flex px-2 py-0.5 rounded-full text-xs font-bold uppercase tracking-wider ${
                        claim.status === 'pending'
                          ? 'bg-amber-100 dark:bg-amber-950/60 text-amber-800 dark:text-amber-300'
                          : claim.status === 'approved'
                          ? 'bg-emerald-100 dark:bg-emerald-950/60 text-emerald-800 dark:text-emerald-300'
                          : 'bg-red-100 dark:bg-red-950/60 text-red-800 dark:text-red-300'
                      }`}
                    >
                      {claim.status === 'pending'
                        ? 'Pendiente'
                        : claim.status === 'approved'
                        ? 'Aprobada'
                        : 'Rechazada'}
                    </span>
                  </div>
                  <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-500 dark:text-slate-400 mt-1">
                    <span className="flex items-center gap-1">
                      <HiOutlineUser className="w-3.5 h-3.5" />
                      Usuario: @{claim.user?.username} ({claim.user?.email})
                    </span>
                    <span className="flex items-center gap-1">
                      <HiOutlineMail className="w-3.5 h-3.5" />
                      Contacto: {claim.contact_email}
                    </span>
                    <span>
                      Fecha: {new Date(claim.created_at).toLocaleDateString()}
                    </span>
                  </div>
                </div>

                {claim.status === 'pending' && (
                  <div className="flex items-center gap-2">
                    <Button
                      size="sm"
                      className="bg-emerald-600 hover:bg-emerald-700 text-white"
                      onClick={() => handleOpenResolve(claim, 'approve')}
                    >
                      <HiOutlineCheck className="w-4 h-4 mr-1" />
                      Aprobar
                    </Button>
                    <Button
                      size="sm"
                      color="failure"
                      onClick={() => handleOpenResolve(claim, 'reject')}
                    >
                      <HiOutlineX className="w-4 h-4 mr-1" />
                      Rechazar
                    </Button>
                  </div>
                )}
              </div>

              {/* Claim Description & Proof */}
              <div className="space-y-2 text-sm">
                <div>
                  <span className="text-xs font-bold uppercase text-slate-500 dark:text-slate-400">
                    Acreditación y Motivo de Solicitud:
                  </span>
                  <p className="mt-1 p-3.5 rounded-xl bg-slate-50 dark:bg-slate-800/60 text-slate-700 dark:text-slate-300 text-xs sm:text-sm whitespace-pre-line leading-relaxed">
                    {claim.proof_description}
                  </p>
                </div>

                {claim.supporting_link && (
                  <div className="pt-1 flex items-center gap-1.5 text-xs">
                    <span className="font-semibold text-slate-500 dark:text-slate-400">
                      Enlace de verificación:
                    </span>
                    <a
                      href={claim.supporting_link}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-teal-600 dark:text-teal-400 hover:underline flex items-center gap-1 font-medium"
                    >
                      <span>{claim.supporting_link}</span>
                      <HiOutlineExternalLink className="w-3.5 h-3.5" />
                    </a>
                  </div>
                )}

                {claim.admin_notes && (
                  <div className="pt-2 text-xs text-slate-500 dark:text-slate-400 border-t border-slate-100 dark:border-slate-800">
                    <span className="font-bold">Notas de moderación:</span> {claim.admin_notes}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Modal Resolver Solicitud */}
      <Modal show={!!selectedClaim} onClose={() => setSelectedClaim(null)} size="md">
        <Modal.Header>
          <span className="font-bold text-slate-900 dark:text-white">
            {resolutionAction === 'approve'
              ? 'Aprobar Solicitud y Verificar Autor'
              : 'Rechazar Solicitud de Autor'}
          </span>
        </Modal.Header>
        <Modal.Body className="space-y-4">
          <p className="text-sm text-slate-600 dark:text-slate-300">
            {resolutionAction === 'approve'
              ? `Estás a punto de verificar a "${selectedClaim?.author?.name}" y vincularla permanentemente a la cuenta de @${selectedClaim?.user?.username}.`
              : `Estás a punto de desestimar la reclamación de @${selectedClaim?.user?.username} sobre "${selectedClaim?.author?.name}".`}
          </p>

          <div>
            <label className="block text-xs font-bold uppercase text-slate-600 dark:text-slate-300 mb-1">
              Mensaje o Notas para el solicitante (se le notificará)
            </label>
            <textarea
              rows={4}
              value={adminNotes}
              onChange={(e) => setAdminNotes(e.target.value)}
              className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm text-slate-900 dark:text-white focus:ring-2 focus:ring-teal-500"
            />
          </div>
        </Modal.Body>
        <Modal.Footer className="flex justify-end gap-2">
          <Button color="gray" onClick={() => setSelectedClaim(null)} disabled={resolving}>
            Cancelar
          </Button>
          <Button
            className={
              resolutionAction === 'approve'
                ? 'bg-emerald-600 hover:bg-emerald-700 text-white'
                : 'bg-red-600 hover:bg-red-700 text-white'
            }
            onClick={handleResolve}
            disabled={resolving}
          >
            {resolving ? <Spinner size="sm" className="mr-2" /> : null}
            {resolutionAction === 'approve' ? 'Confirmar Aprobación' : 'Confirmar Rechazo'}
          </Button>
        </Modal.Footer>
      </Modal>
    </div>
  );
}

export default AdminAuthorClaimsTab;
