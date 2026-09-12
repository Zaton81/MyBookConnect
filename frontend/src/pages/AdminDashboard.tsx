import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/auth';
import { Spinner } from 'flowbite-react';
import DOMPurify from 'dompurify';
import { AuditLog } from '../types/auth';

export function AdminDashboard() {
  const navigate = useNavigate();
  const { user, token } = useAuthStore();

  // Redirigir a usuarios no autorizados
  const isAuthorized = user && (user.is_staff || user.is_superuser || user.role === 'ADMIN' || user.role === 'MODERATOR');

  useEffect(() => {
    if (!token || (user && !isAuthorized)) {
      navigate('/');
    }
  }, [user, token, isAuthorized, navigate]);

  const [activeTab, setActiveTab] = useState<'stats' | 'users' | 'catalog' | 'erratas' | 'reports' | 'audit' | 'legal'>('stats');

  // Estado de Métricas
  const [stats, setStats] = useState<any | null>(null);
  const [loadingStats, setLoadingStats] = useState(false);

  // Estado de Auditoría & Logs (Fase 30)
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [loadingAudit, setLoadingAudit] = useState(false);
  const [auditStats, setAuditStats] = useState<any | null>(null);
  const [auditActionFilter, setAuditActionFilter] = useState<string>('all');
  const [auditActorFilter, setAuditActorFilter] = useState<string>('');
  const [auditSearch, setAuditSearch] = useState<string>('');
  const [selectedAuditLog, setSelectedAuditLog] = useState<AuditLog | null>(null);

  // Estado de Usuarios
  const [users, setUsers] = useState<any[]>([]);
  const [loadingUsers, setLoadingUsers] = useState(false);
  const [userSearch, setUserSearch] = useState('');
  const [userStatusFilter, setUserStatusFilter] = useState<'all' | 'active' | 'banned'>('all');
  const [userRoleFilter, setUserRoleFilter] = useState<'all' | 'staff' | 'editor'>('all');
  const [userActionMsg, setUserActionMsg] = useState<string | null>(null);

  // Estado de Catálogo
  const [catalogSubtab, setCatalogSubtab] = useState<'books' | 'authors'>('books');
  const [catalogItems, setCatalogItems] = useState<any[]>([]);
  const [loadingCatalog, setLoadingCatalog] = useState(false);
  const [catalogSearch, setCatalogSearch] = useState('');
  const [catalogMsg, setCatalogMsg] = useState<string | null>(null);

  // Estado de Erratas
  const [erratas, setErratas] = useState<any[]>([]);
  const [loadingErratas, setLoadingErratas] = useState(false);
  const [errataStatusFilter, setErrataStatusFilter] = useState<string>('all');
  const [selectedErrata, setSelectedErrata] = useState<any | null>(null);
  const [resolutionNotes, setResolutionNotes] = useState('');
  const [resolvingErrata, setResolvingErrata] = useState(false);

  // Estado de Moderación & Denuncias
  const [reports, setReports] = useState<any[]>([]);
  const [loadingReports, setLoadingReports] = useState(false);
  const [reportStats, setReportStats] = useState<any | null>(null);
  const [reportStatusFilter, setReportStatusFilter] = useState<string>('all');
  const [reportReasonFilter, setReportReasonFilter] = useState<string>('all');
  const [reportTargetFilter, setReportTargetFilter] = useState<string>('all');
  const [selectedReport, setSelectedReport] = useState<any | null>(null);
  const [modResolveStatus, setModResolveStatus] = useState<'RESOLVED' | 'REJECTED' | 'UNDER_REVIEW'>('RESOLVED');
  const [modResolveAction, setModResolveAction] = useState<string>('HIDE_CONTENT');
  const [modResolveNotes, setModResolveNotes] = useState<string>('');
  const [resolvingReport, setResolvingReport] = useState(false);
  const [reportActionMsg, setReportActionMsg] = useState<string | null>(null);

  // Estado de CMS Legal
  const [legalSlug, setLegalSlug] = useState<'terms' | 'privacy' | 'cookies' | 'legal_notice'>('terms');
  const [legalTitle, setLegalTitle] = useState('');
  const [legalContent, setLegalContent] = useState('');
  const [legalUpdatedBy, setLegalUpdatedBy] = useState<string | null>(null);
  const [legalUpdatedAt, setLegalUpdatedAt] = useState<string | null>(null);
  const [loadingLegal, setLoadingLegal] = useState(false);
  const [savingLegal, setSavingLegal] = useState(false);
  const [legalMsg, setLegalMsg] = useState<string | null>(null);
  const [legalPreviewMode, setLegalPreviewMode] = useState(false);

  const apiUrl = (import.meta as any).env.VITE_API_URL || 'http://localhost:8000';

  // 1. Cargar Estadísticas
  const fetchStats = async () => {
    if (!token) return;
    setLoadingStats(true);
    try {
      const res = await fetch(`${apiUrl}/api/v1/admin/stats/`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setStats(data);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoadingStats(false);
    }
  };

  // 2. Cargar Usuarios
  const fetchUsers = async () => {
    if (!token) return;
    setLoadingUsers(true);
    try {
      const params = new URLSearchParams();
      if (userSearch.trim()) params.append('search', userSearch.trim());
      if (userStatusFilter !== 'all') params.append('status', userStatusFilter);
      if (userRoleFilter !== 'all') params.append('role', userRoleFilter);

      const res = await fetch(`${apiUrl}/api/v1/admin/users/?${params.toString()}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setUsers(Array.isArray(data) ? data : data.results || []);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoadingUsers(false);
    }
  };

  // Toggle Ban / Role
  const handleUpdateUser = async (targetUser: any, field: 'is_active' | 'is_staff' | 'is_editor' | 'role', value: any) => {
    if (!token) return;
    if (targetUser.id === user?.id && field === 'is_active' && !value) {
      alert('No puedes bloquear tu propia cuenta de administrador.');
      return;
    }
    if (targetUser.id === user?.id && field === 'is_staff' && !value) {
      alert('No puedes retirar tus propios permisos de administrador.');
      return;
    }
    if (targetUser.id === user?.id && field === 'role' && value !== 'ADMIN') {
      alert('No puedes degradar tu propio rol de administrador.');
      return;
    }
    if (!window.confirm(`¿Confirmas cambiar ${field} a ${value} para ${targetUser.username}?`)) return;

    try {
      const res = await fetch(`${apiUrl}/api/v1/admin/users/${targetUser.id}/`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ [field]: value }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Error al actualizar usuario');
      }
      setUserActionMsg(`Usuario ${targetUser.username} actualizado con éxito.`);
      setTimeout(() => setUserActionMsg(null), 4000);
      fetchUsers();
      fetchStats();
    } catch (e: any) {
      alert(e.message);
    }
  };

  // 6. Cargar Reportes de Moderación
  const fetchReports = async () => {
    if (!token) return;
    setLoadingReports(true);
    try {
      const params = new URLSearchParams();
      if (reportStatusFilter !== 'all') params.append('status', reportStatusFilter);
      if (reportReasonFilter !== 'all') params.append('reason', reportReasonFilter);
      if (reportTargetFilter !== 'all') params.append('target_type', reportTargetFilter);

      const res = await fetch(`${apiUrl}/api/v1/admin/reports/?${params.toString()}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setReports(Array.isArray(data) ? data : data.results || []);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoadingReports(false);
    }
  };

  const fetchReportStats = async () => {
    if (!token) return;
    try {
      const res = await fetch(`${apiUrl}/api/v1/admin/reports/stats/`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setReportStats(data);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleResolveReport = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token || !selectedReport) return;
    setResolvingReport(true);
    try {
      const res = await fetch(`${apiUrl}/api/v1/admin/reports/${selectedReport.id}/`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          status: modResolveStatus,
          action_taken: modResolveStatus === 'RESOLVED' ? modResolveAction : '',
          resolution_notes: modResolveNotes,
        }),
      });
      if (res.ok) {
        setSelectedReport(null);
        setModResolveNotes('');
        setReportActionMsg('Expediente de moderación actualizado con éxito.');
        setTimeout(() => setReportActionMsg(null), 4000);
        fetchReports();
        fetchReportStats();
        fetchStats();
      } else {
        const err = await res.json();
        alert(err.detail || 'Error al procesar la resolución de la denuncia.');
      }
    } catch (e: any) {
      alert(e.message || 'Error de conexión');
    } finally {
      setResolvingReport(false);
    }
  };

  // 7. Cargar Registros de Auditoría (Fase 30)
  const fetchAuditLogs = async () => {
    if (!token) return;
    setLoadingAudit(true);
    try {
      const params = new URLSearchParams();
      if (auditActionFilter !== 'all') params.append('action', auditActionFilter);
      if (auditActorFilter.trim()) params.append('actor', auditActorFilter.trim());
      if (auditSearch.trim()) params.append('search', auditSearch.trim());

      const res = await fetch(`${apiUrl}/api/v1/admin/audit-logs/?${params.toString()}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setAuditLogs(Array.isArray(data) ? data : data.results || []);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoadingAudit(false);
    }
  };

  const fetchAuditStats = async () => {
    if (!token) return;
    try {
      const res = await fetch(`${apiUrl}/api/v1/admin/audit-logs/stats/`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setAuditStats(data);
      }
    } catch (e) {
      console.error(e);
    }
  };

  // 3. Cargar Catálogo (Libros o Autores)
  const fetchCatalog = async () => {
    if (!token) return;
    setLoadingCatalog(true);
    try {
      const endpoint = catalogSubtab === 'books' ? 'books' : 'authors';
      const params = new URLSearchParams();
      if (catalogSearch.trim()) params.append('search', catalogSearch.trim());

      const res = await fetch(`${apiUrl}/api/v1/admin/${endpoint}/?${params.toString()}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setCatalogItems(Array.isArray(data) ? data : data.results || []);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoadingCatalog(false);
    }
  };

  const handleEnrichItem = async (id: number) => {
    if (!token) return;
    const endpoint = catalogSubtab === 'books' ? 'books' : 'authors';
    setCatalogMsg('Re-enriqueciendo metadatos desde APIs abiertas...');
    try {
      const res = await fetch(`${apiUrl}/api/v1/admin/${endpoint}/${id}/enrich/`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        setCatalogMsg('Enriquecimiento completado con éxito.');
        fetchCatalog();
      } else {
        setCatalogMsg('No se encontraron nuevos datos adicionales.');
      }
    } catch (e) {
      setCatalogMsg('Error durante la sincronización externa.');
    }
    setTimeout(() => setCatalogMsg(null), 4000);
  };

  const handleDeleteItem = async (id: number, name: string) => {
    if (!token) return;
    if (!window.confirm(`¿Seguro que deseas eliminar "${name}" del catálogo?`)) return;
    const endpoint = catalogSubtab === 'books' ? 'books' : 'authors';
    try {
      const res = await fetch(`${apiUrl}/api/v1/admin/${endpoint}/${id}/`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        setCatalogMsg('Elemento eliminado del catálogo.');
        fetchCatalog();
        fetchStats();
      }
    } catch (e) {
      alert('Error eliminando elemento');
    }
    setTimeout(() => setCatalogMsg(null), 3000);
  };

  // 4. Cargar Erratas
  const fetchErratas = async () => {
    if (!token) return;
    setLoadingErratas(true);
    try {
      const params = new URLSearchParams();
      if (errataStatusFilter !== 'all') params.append('status', errataStatusFilter);
      const res = await fetch(`${apiUrl}/api/v1/admin/erratas/?${params.toString()}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setErratas(Array.isArray(data) ? data : data.results || []);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoadingErratas(false);
    }
  };

  const handleResolveErrata = async (statusVal: 'approved' | 'rejected') => {
    if (!token || !selectedErrata) return;
    setResolvingErrata(true);
    try {
      const res = await fetch(`${apiUrl}/api/v1/admin/erratas/${selectedErrata.id}/`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          status: statusVal,
          resolution_notes: resolutionNotes,
        }),
      });
      if (res.ok) {
        setSelectedErrata(null);
        setResolutionNotes('');
        fetchErratas();
        fetchStats();
      }
    } catch (e) {
      alert('Error al resolver reporte');
    } finally {
      setResolvingErrata(false);
    }
  };

  // 5. Cargar Documento Legal
  const fetchLegalDocument = async (slug: string) => {
    if (!token) return;
    setLoadingLegal(true);
    setLegalMsg(null);
    try {
      const res = await fetch(`${apiUrl}/api/v1/admin/legal/${slug}/`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setLegalTitle(data.title || '');
        setLegalContent(data.content || '');
        setLegalUpdatedBy(data.updated_by_username || null);
        setLegalUpdatedAt(data.updated_at || null);
      } else if (res.status === 404) {
        // Documento aún no personalizado en BD
        setLegalTitle(
          slug === 'terms'
            ? 'Términos del Servicio'
            : slug === 'privacy'
            ? 'Política de Privacidad'
            : slug === 'cookies'
            ? 'Política de Cookies'
            : 'Aviso Legal'
        );
        setLegalContent('');
        setLegalUpdatedBy(null);
        setLegalUpdatedAt(null);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoadingLegal(false);
    }
  };

  const handleSaveLegal = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token) return;
    setSavingLegal(true);
    setLegalMsg(null);
    try {
      // Probar PATCH primero o POST si no existía
      let res = await fetch(`${apiUrl}/api/v1/admin/legal/${legalSlug}/`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          slug: legalSlug,
          title: legalTitle,
          content: legalContent,
        }),
      });

      if (res.status === 404) {
        res = await fetch(`${apiUrl}/api/v1/admin/legal/`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            slug: legalSlug,
            title: legalTitle,
            content: legalContent,
          }),
        });
      }

      if (res.ok) {
        const saved = await res.json();
        setLegalUpdatedBy(saved.updated_by_username || user?.username);
        setLegalUpdatedAt(saved.updated_at || new Date().toISOString());
        setLegalMsg('Documento legal actualizado y publicado en vivo correctamente.');
        setTimeout(() => setLegalMsg(null), 4000);
      } else {
        throw new Error('No se pudo guardar el documento.');
      }
    } catch (err: any) {
      alert(err.message);
    } finally {
      setSavingLegal(false);
    }
  };

  // Efectos según pestaña activa
  useEffect(() => {
    if (activeTab === 'stats') fetchStats();
    if (activeTab === 'users') fetchUsers();
    if (activeTab === 'catalog') fetchCatalog();
    if (activeTab === 'erratas') fetchErratas();
    if (activeTab === 'reports') {
      fetchReports();
      fetchReportStats();
    }
    if (activeTab === 'audit') {
      fetchAuditLogs();
      fetchAuditStats();
    }
    if (activeTab === 'legal') fetchLegalDocument(legalSlug);
  }, [activeTab]);

  useEffect(() => {
    if (activeTab === 'catalog') fetchCatalog();
  }, [catalogSubtab]);

  useEffect(() => {
    if (activeTab === 'legal') fetchLegalDocument(legalSlug);
  }, [legalSlug]);

  if (!isAuthorized) {
    return (
      <div className="max-w-md mx-auto my-16 p-8 bg-white dark:bg-slate-800 rounded-3xl border border-rose-200 dark:border-rose-900 text-center space-y-4">
        <span className="text-5xl">⛔</span>
        <h2 className="text-xl font-bold text-slate-900 dark:text-white">Acceso Restringido</h2>
        <p className="text-xs text-slate-500 dark:text-slate-400">
          Esta sección está protegida y reservada exclusivamente para el equipo de administración de MyBookConnect.
        </p>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto space-y-8 pb-12">
      {/* ── Encabezado Principal de Administración ── */}
      <header className="bg-gradient-to-r from-slate-900 via-slate-800 to-teal-950 text-white p-6 sm:p-8 rounded-3xl shadow-lg border border-slate-700/60 flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-bold bg-teal-500/20 text-teal-300 border border-teal-500/40 mb-2">
            <span>🛡️ Panel de Control & Moderación</span>
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
          </div>
          <h1 className="text-2xl sm:text-3xl font-black tracking-tight">
            Administración del Sistema
          </h1>
          <p className="text-xs sm:text-sm text-slate-300 mt-1 max-w-xl">
            Gestión integral de usuarios, moderación de catálogo editorial, cola de denuncias, auditoría de seguridad y control legal.
          </p>
        </div>

        <div className="flex items-center gap-3 bg-white/10 backdrop-blur-md px-4 py-3 rounded-2xl border border-white/10 text-xs">
          <div className="w-10 h-10 rounded-full bg-teal-500 flex items-center justify-center font-bold text-sm text-slate-900 shadow">
            {user?.username?.slice(0, 2).toUpperCase()}
          </div>
          <div>
            <div className="font-bold">{user?.username}</div>
            <div className="text-[11px] text-teal-300">
              {user?.is_superuser
                ? 'Superadministrador'
                : user?.role === 'ADMIN'
                ? 'Administrador'
                : user?.role === 'MODERATOR'
                ? 'Moderador'
                : user?.role === 'EDITOR'
                ? 'Editor'
                : 'Staff'}
            </div>
          </div>
        </div>
      </header>

      {/* ── Barra de Pestañas de Navegación ── */}
      <nav className="flex flex-wrap gap-2 border-b border-slate-200 dark:border-slate-800 pb-3">
        {[
          { id: 'stats', label: '📊 Métricas Globales' },
          { id: 'users', label: '👥 Usuarios & Roles' },
          { id: 'catalog', label: '📚 Catálogo & Autores' },
          { id: 'erratas', label: '✍️ Erratas Editoriales' },
          { id: 'reports', label: '🛡️ Moderación & Denuncias' },
          ...(user?.is_superuser || user?.role === 'ADMIN' || user?.is_staff
            ? [{ id: 'audit', label: '📜 Auditoría & Logs' }]
            : []),
          { id: 'legal', label: '⚖️ CMS Legal' },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as any)}
            className={`px-4 py-2.5 rounded-2xl text-xs font-bold transition-all ${
              activeTab === tab.id
                ? 'bg-teal-600 text-white shadow-md'
                : 'bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700/60 border border-slate-200/80 dark:border-slate-700'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </nav>

      {/* ── 1. PESTAÑA: MÉTRICAS GLOBALES ── */}
      {activeTab === 'stats' && (
        <div className="space-y-6">
          {loadingStats ? (
            <div className="flex justify-center p-12">
              <Spinner size="xl" color="info" />
            </div>
          ) : stats ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
              {/* Tarjeta Usuarios */}
              <div className="bg-white dark:bg-slate-800 p-6 rounded-3xl border border-slate-200/80 dark:border-slate-700 shadow-sm space-y-2">
                <div className="text-2xl">👥</div>
                <div className="text-2xl font-black text-slate-900 dark:text-white">
                  {stats.users.total}
                </div>
                <div className="text-xs font-bold text-slate-500">Usuarios Registrados</div>
                <div className="flex gap-2 pt-2 text-[11px]">
                  <span className="text-emerald-600 font-semibold">● {stats.users.active} activos</span>
                  <span className="text-rose-500 font-semibold">● {stats.users.banned} bloqueados</span>
                </div>
              </div>

              {/* Tarjeta Libros */}
              <div className="bg-white dark:bg-slate-800 p-6 rounded-3xl border border-slate-200/80 dark:border-slate-700 shadow-sm space-y-2">
                <div className="text-2xl">📚</div>
                <div className="text-2xl font-black text-slate-900 dark:text-white">
                  {stats.catalog.books}
                </div>
                <div className="text-xs font-bold text-slate-500">Libros en Catálogo</div>
                <div className="text-[11px] text-teal-600 font-semibold pt-2">
                  {stats.catalog.user_shelves} libros añadidos a estanterías
                </div>
              </div>

              {/* Tarjeta Autores & Reseñas */}
              <div className="bg-white dark:bg-slate-800 p-6 rounded-3xl border border-slate-200/80 dark:border-slate-700 shadow-sm space-y-2">
                <div className="text-2xl">✍️</div>
                <div className="text-2xl font-black text-slate-900 dark:text-white">
                  {stats.catalog.authors}
                </div>
                <div className="text-xs font-bold text-slate-500">Autores Fichados</div>
                <div className="text-[11px] text-amber-600 font-semibold pt-2">
                  ⭐ {stats.catalog.reviews} reseñas públicas publicadas
                </div>
              </div>

              {/* Tarjeta Erratas */}
              <div className="bg-white dark:bg-slate-800 p-6 rounded-3xl border border-slate-200/80 dark:border-slate-700 shadow-sm space-y-2">
                <div className="text-2xl">🔔</div>
                <div className="text-2xl font-black text-slate-900 dark:text-white">
                  {stats.erratas.open}
                </div>
                <div className="text-xs font-bold text-slate-500">Erratas Pendientes</div>
                <div className="text-[11px] text-slate-400 pt-2">
                  {stats.erratas.total} reportes gestionados en total
                </div>
              </div>
            </div>
          ) : (
            <p className="text-xs text-slate-500">No se pudieron cargar las estadísticas.</p>
          )}
        </div>
      )}

      {/* ── 2. PESTAÑA: GESTIÓN DE USUARIOS ── */}
      {activeTab === 'users' && (
        <div className="bg-white dark:bg-slate-800 rounded-3xl border border-slate-200/80 dark:border-slate-700 p-6 sm:p-8 shadow-sm space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h2 className="text-lg font-bold text-slate-900 dark:text-white">Gestión de Usuarios</h2>
              <p className="text-xs text-slate-500">Control de estado de cuenta, roles y bloqueos de seguridad.</p>
            </div>
            {userActionMsg && (
              <div className="p-2.5 bg-emerald-50 text-emerald-800 dark:bg-emerald-900/30 rounded-xl text-xs font-semibold">
                {userActionMsg}
              </div>
            )}
          </div>

          {/* Filtros y Buscador */}
          <div className="flex flex-wrap gap-3 items-center">
            <input
              type="text"
              placeholder="Buscar por usuario o email..."
              value={userSearch}
              onChange={(e) => setUserSearch(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && fetchUsers()}
              className="text-xs rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-700 p-2.5 w-64 focus:ring-2 focus:ring-teal-500"
            />
            <select
              value={userStatusFilter}
              onChange={(e) => setUserStatusFilter(e.target.value as any)}
              className="text-xs rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-700 py-2 px-3"
            >
              <option value="all">Estado: Todos</option>
              <option value="active">Solo Activos</option>
              <option value="banned">Solo Bloqueados</option>
            </select>
            <select
              value={userRoleFilter}
              onChange={(e) => setUserRoleFilter(e.target.value as any)}
              className="text-xs rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-700 py-2 px-3"
            >
              <option value="all">Rol: Todos</option>
              <option value="staff">Solo Staff / Admin</option>
              <option value="moderator">Solo Moderadores</option>
              <option value="editor">Solo Editores</option>
            </select>
            <button
              onClick={fetchUsers}
              className="bg-teal-600 hover:bg-teal-700 text-white text-xs font-bold px-4 py-2 rounded-xl transition-all"
            >
              Filtrar
            </button>
          </div>

          {/* Tabla de Usuarios */}
          {loadingUsers ? (
            <div className="flex justify-center p-8">
              <Spinner size="lg" color="info" />
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-slate-200 dark:border-slate-700 text-slate-400 font-bold uppercase tracking-wider text-[10px]">
                    <th className="py-3 px-3">Usuario</th>
                    <th className="py-3 px-3">Email</th>
                    <th className="py-3 px-3">Estado</th>
                    <th className="py-3 px-3">Rol en Plataforma</th>
                    <th className="py-3 px-3">Actividad</th>
                    <th className="py-3 px-3 text-right">Acciones de Seguridad</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-700/60">
                  {users.map((u) => (
                    <tr key={u.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-700/30">
                      <td className="py-3 px-3 font-bold text-slate-900 dark:text-white flex items-center gap-2">
                        <div className="w-7 h-7 rounded-full bg-slate-200 dark:bg-slate-600 flex items-center justify-center text-[10px] font-bold">
                          {u.username.slice(0, 2).toUpperCase()}
                        </div>
                        <span>{u.username}</span>
                        {u.is_superuser && (
                          <span className="px-1.5 py-0.5 rounded text-[9px] bg-purple-100 text-purple-800 font-black">
                            ROOT
                          </span>
                        )}
                      </td>
                      <td className="py-3 px-3 text-slate-500">{u.email}</td>
                      <td className="py-3 px-3">
                        {u.is_active ? (
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300">
                            Activo
                          </span>
                        ) : (
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-rose-100 text-rose-800 dark:bg-rose-900/40 dark:text-rose-300">
                            Bloqueado
                          </span>
                        )}
                      </td>
                      <td className="py-3 px-3">
                        {/* Selector de rol */}
                        <select
                          value={u.role || (u.is_staff ? 'ADMIN' : u.is_editor ? 'EDITOR' : 'USER')}
                          disabled={!user?.is_superuser && user?.role !== 'ADMIN'}
                          onChange={(e) => handleUpdateUser(u, 'role', e.target.value)}
                          className="text-[11px] font-semibold rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 py-1 px-2 focus:ring-1 focus:ring-teal-500 cursor-pointer disabled:opacity-60"
                        >
                          <option value="USER">👤 Lector (USER)</option>
                          <option value="EDITOR">✍️ Editor (EDITOR)</option>
                          <option value="MODERATOR">🛡️ Moderador (MODERATOR)</option>
                          <option value="ADMIN">👑 Administrador (ADMIN)</option>
                        </select>
                      </td>
                      <td className="py-3 px-3 text-slate-500">
                        {u.books_count} libros • {u.reviews_count} reseñas
                      </td>
                      <td className="py-3 px-3 text-right space-x-2">
                        {/* Botón Banear / Desbanear */}
                        {u.id !== user?.id && (
                          <button
                            onClick={() => handleUpdateUser(u, 'is_active', !u.is_active)}
                            className={`px-2.5 py-1 rounded-lg text-xs font-bold transition-colors ${
                              u.is_active
                                ? 'bg-rose-100 hover:bg-rose-200 text-rose-700'
                                : 'bg-emerald-100 hover:bg-emerald-200 text-emerald-700'
                            }`}
                          >
                            {u.is_active ? 'Bloquear' : 'Desbloquear'}
                          </button>
                        )}
                        {/* Botón Staff directo */}
                        {user?.is_superuser && u.id !== user?.id && (
                          <button
                            onClick={() => handleUpdateUser(u, 'is_staff', !u.is_staff)}
                            className="px-2.5 py-1 rounded-lg text-xs font-semibold bg-slate-100 hover:bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-200"
                          >
                            {u.is_staff ? 'Quitar Staff' : 'Hacer Staff'}
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* ── 3. PESTAÑA: CATÁLOGO DE LIBROS Y AUTORES ── */}
      {activeTab === 'catalog' && (
        <div className="bg-white dark:bg-slate-800 rounded-3xl border border-slate-200/80 dark:border-slate-700 p-6 sm:p-8 shadow-sm space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h2 className="text-lg font-bold text-slate-900 dark:text-white">Moderación del Catálogo</h2>
              <p className="text-xs text-slate-500">Enriquecimiento automático y depuración de títulos y biografías.</p>
            </div>
            {catalogMsg && (
              <div className="p-2.5 bg-teal-50 text-teal-800 dark:bg-teal-900/30 rounded-xl text-xs font-semibold">
                {catalogMsg}
              </div>
            )}
          </div>

          {/* Subpestañas Libros / Autores */}
          <div className="flex gap-2">
            <button
              onClick={() => setCatalogSubtab('books')}
              className={`px-3 py-1.5 rounded-xl text-xs font-bold ${
                catalogSubtab === 'books'
                  ? 'bg-teal-600 text-white'
                  : 'bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300'
              }`}
            >
              📖 Libros
            </button>
            <button
              onClick={() => setCatalogSubtab('authors')}
              className={`px-3 py-1.5 rounded-xl text-xs font-bold ${
                catalogSubtab === 'authors'
                  ? 'bg-teal-600 text-white'
                  : 'bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300'
              }`}
            >
              ✍️ Autores
            </button>
          </div>

          {/* Buscador */}
          <div className="flex gap-3">
            <input
              type="text"
              placeholder={`Buscar ${catalogSubtab === 'books' ? 'libro o ISBN' : 'autor'}...`}
              value={catalogSearch}
              onChange={(e) => setCatalogSearch(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && fetchCatalog()}
              className="text-xs rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-700 p-2.5 w-72"
            />
            <button
              onClick={fetchCatalog}
              className="bg-teal-600 hover:bg-teal-700 text-white text-xs font-bold px-4 py-2 rounded-xl"
            >
              Buscar
            </button>
          </div>

          {/* Listado de elementos */}
          {loadingCatalog ? (
            <div className="flex justify-center p-8">
              <Spinner size="lg" color="info" />
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {catalogItems.map((item) => (
                <div
                  key={item.id}
                  className="p-4 rounded-2xl border border-slate-200 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-800/50 flex gap-4 items-start"
                >
                  <div className="w-16 h-20 rounded-xl overflow-hidden bg-slate-200 dark:bg-slate-700 shrink-0 border border-slate-300 dark:border-slate-600">
                    {(item.cover || item.photo) ? (
                      <img
                        src={(item.cover || item.photo).startsWith('http') ? (item.cover || item.photo) : `${apiUrl}${item.cover || item.photo}`}
                        alt={item.title || item.name}
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center text-[10px] text-slate-400 p-1 text-center font-bold">
                        Sin imagen
                      </div>
                    )}
                  </div>

                  <div className="flex-1 min-w-0 space-y-1">
                    <h4 className="text-xs font-bold text-slate-900 dark:text-white truncate">
                      {item.title || item.name}
                    </h4>
                    {item.author && (
                      <p className="text-[11px] text-teal-600 truncate">{item.author.name}</p>
                    )}
                    {item.isbn && (
                      <p className="text-[10px] text-slate-400 font-mono">ISBN: {item.isbn}</p>
                    )}
                    <p className="text-[11px] text-slate-500 line-clamp-2">
                      {item.description || item.biography || 'Sin descripción disponible.'}
                    </p>

                    <div className="flex gap-2 pt-2">
                      <button
                        onClick={() => handleEnrichItem(item.id)}
                        className="bg-amber-100 hover:bg-amber-200 text-amber-900 font-bold px-2.5 py-1 rounded-lg text-[10px] transition-colors"
                        title="Buscar portada y sinopsis en Wikipedia/Google Books"
                      >
                        ⚡ Re-enriquecer
                      </button>
                      <button
                        onClick={() => handleDeleteItem(item.id, item.title || item.name)}
                        className="bg-rose-100 hover:bg-rose-200 text-rose-700 font-bold px-2.5 py-1 rounded-lg text-[10px] transition-colors"
                      >
                        🗑 Eliminar
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── 4. PESTAÑA: ERRATAS Y MODERACIÓN ── */}
      {activeTab === 'erratas' && (
        <div className="bg-white dark:bg-slate-800 rounded-3xl border border-slate-200/80 dark:border-slate-700 p-6 sm:p-8 shadow-sm space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h2 className="text-lg font-bold text-slate-900 dark:text-white">Reportes de Erratas y Sugerencias</h2>
              <p className="text-xs text-slate-500">Revisión de solicitudes comunitarias de corrección de datos.</p>
            </div>
            <select
              value={errataStatusFilter}
              onChange={(e) => setErrataStatusFilter(e.target.value)}
              className="text-xs rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-700 py-2 px-3"
            >
              <option value="all">Estado: Todos</option>
              <option value="open">Abiertas</option>
              <option value="approved">Aprobadas</option>
              <option value="rejected">Rechazadas</option>
            </select>
          </div>

          {loadingErratas ? (
            <div className="flex justify-center p-8">
              <Spinner size="lg" color="info" />
            </div>
          ) : erratas.length === 0 ? (
            <p className="text-xs text-slate-400 py-8 text-center">No hay reportes de erratas en este filtro.</p>
          ) : (
            <div className="space-y-3">
              {erratas.map((errata) => (
                <div
                  key={errata.id}
                  className="p-4 rounded-2xl border border-slate-200 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-800/50 space-y-2"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-xs text-slate-900 dark:text-white">
                        {errata.type.toUpperCase()}
                      </span>
                      <span className="text-xs text-slate-400">• Por {errata.user}</span>
                      <span className="text-xs text-slate-400">
                        • {new Date(errata.created_at).toLocaleDateString()}
                      </span>
                    </div>
                    <span
                      className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                        errata.status === 'open'
                          ? 'bg-amber-100 text-amber-800'
                          : errata.status === 'approved'
                          ? 'bg-emerald-100 text-emerald-800'
                          : 'bg-rose-100 text-rose-800'
                      }`}
                    >
                      {errata.status}
                    </span>
                  </div>

                  <p className="text-xs text-slate-700 dark:text-slate-300 font-medium">
                    {errata.book ? `Libro: ${errata.book.title}` : (errata.author ? `Autor: ${errata.author.name}` : '')}
                  </p>
                  <p className="text-xs text-slate-600 dark:text-slate-400 bg-white dark:bg-slate-700/50 p-2.5 rounded-xl border border-slate-200/60 dark:border-slate-600">
                    "{errata.text}"
                  </p>

                  {errata.resolution_notes && (
                    <p className="text-[11px] text-teal-700 dark:text-teal-300 italic">
                      Resolución: {errata.resolution_notes} (Editor: {errata.editor || 'Staff'})
                    </p>
                  )}

                  {errata.status === 'open' && (
                    <div className="pt-2 flex justify-end gap-2">
                      <button
                        onClick={() => {
                          setSelectedErrata(errata);
                          setResolutionNotes('');
                        }}
                        className="bg-teal-600 hover:bg-teal-700 text-white text-xs font-bold px-3 py-1.5 rounded-xl"
                      >
                        Gestionar
                      </button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Modal de Resolución */}
          {selectedErrata && (
            <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
              <div className="bg-white dark:bg-slate-800 rounded-3xl max-w-lg w-full p-6 space-y-4 border border-slate-200 dark:border-slate-700 shadow-2xl">
                <h3 className="text-base font-bold text-slate-900 dark:text-white">
                  Resolver Errata #{selectedErrata.id}
                </h3>
                <p className="text-xs text-slate-600 dark:text-slate-300">
                  {selectedErrata.text}
                </p>

                <textarea
                  rows={3}
                  value={resolutionNotes}
                  onChange={(e) => setResolutionNotes(e.target.value)}
                  placeholder="Notas de resolución (ej: Portada actualizada, corrección de fecha)..."
                  className="w-full text-xs rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-700 p-3"
                />

                <div className="flex justify-end gap-2 pt-2">
                  <button
                    onClick={() => setSelectedErrata(null)}
                    className="px-4 py-2 rounded-xl text-xs font-bold text-slate-600"
                  >
                    Cancelar
                  </button>
                  <button
                    disabled={resolvingErrata}
                    onClick={() => handleResolveErrata('rejected')}
                    className="bg-rose-100 hover:bg-rose-200 text-rose-800 px-4 py-2 rounded-xl text-xs font-bold"
                  >
                    Rechazar
                  </button>
                  <button
                    disabled={resolvingErrata}
                    onClick={() => handleResolveErrata('approved')}
                    className="bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-2 rounded-xl text-xs font-bold shadow"
                  >
                    Aprobar & Cerrar
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── 5. PESTAÑA: COLA DE MODERACIÓN & DENUNCIAS (FASE 29) ── */}
      {activeTab === 'reports' && (
        <div className="bg-white dark:bg-slate-800 rounded-3xl border border-slate-200/80 dark:border-slate-700 p-6 sm:p-8 shadow-sm space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <div className="inline-flex items-center gap-2 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-teal-50 text-teal-700 dark:bg-teal-950/40 dark:text-teal-300 border border-teal-200 dark:border-teal-800 mb-1">
                <span>🛡️ Sistema Disciplinario & Moderación</span>
              </div>
              <h2 className="text-lg font-bold text-slate-900 dark:text-white">Cola de Denuncias</h2>
              <p className="text-xs text-slate-500">
                Supervisa y resuelve reportes sobre usuarios, reseñas, comentarios y mensajes de chat.
              </p>
            </div>
            {reportActionMsg && (
              <div className="p-2.5 bg-emerald-50 text-emerald-800 dark:bg-emerald-900/30 rounded-xl text-xs font-semibold">
                {reportActionMsg}
              </div>
            )}
          </div>

          {/* Métricas rápidas de moderación */}
          {reportStats && (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div className="p-3.5 rounded-2xl bg-amber-50 dark:bg-amber-950/30 border border-amber-200/80 dark:border-amber-800">
                <div className="text-[11px] font-bold text-amber-700 dark:text-amber-400">Abiertas (Pendientes)</div>
                <div className="text-xl font-black text-amber-900 dark:text-amber-200">{reportStats.by_status?.open || 0}</div>
              </div>
              <div className="p-3.5 rounded-2xl bg-blue-50 dark:bg-blue-950/30 border border-blue-200/80 dark:border-blue-800">
                <div className="text-[11px] font-bold text-blue-700 dark:text-blue-400">En Revisión</div>
                <div className="text-xl font-black text-blue-900 dark:text-blue-200">{reportStats.by_status?.under_review || 0}</div>
              </div>
              <div className="p-3.5 rounded-2xl bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-200/80 dark:border-emerald-800">
                <div className="text-[11px] font-bold text-emerald-700 dark:text-emerald-400">Resueltas</div>
                <div className="text-xl font-black text-emerald-900 dark:text-emerald-200">{reportStats.by_status?.resolved || 0}</div>
              </div>
              <div className="p-3.5 rounded-2xl bg-slate-50 dark:bg-slate-700/50 border border-slate-200 dark:border-slate-700">
                <div className="text-[11px] font-bold text-slate-600 dark:text-slate-300">Total Expedientes</div>
                <div className="text-xl font-black text-slate-900 dark:text-white">{reportStats.total || 0}</div>
              </div>
            </div>
          )}

          {/* Filtros de denuncias */}
          <div className="flex flex-wrap gap-3 items-center">
            <select
              value={reportStatusFilter}
              onChange={(e) => setReportStatusFilter(e.target.value)}
              className="text-xs rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-700 py-2 px-3"
            >
              <option value="all">Estado: Todos</option>
              <option value="OPEN">Abiertas (OPEN)</option>
              <option value="UNDER_REVIEW">En Revisión (UNDER_REVIEW)</option>
              <option value="RESOLVED">Resueltas (RESOLVED)</option>
              <option value="REJECTED">Rechazadas (REJECTED)</option>
            </select>

            <select
              value={reportReasonFilter}
              onChange={(e) => setReportReasonFilter(e.target.value)}
              className="text-xs rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-700 py-2 px-3"
            >
              <option value="all">Motivo: Todos</option>
              <option value="SPAM">Spam publicitario</option>
              <option value="HARASSMENT">Acoso o intimidación</option>
              <option value="HATE_SPEECH">Discurso de odio</option>
              <option value="INAPPROPRIATE">Contenido inapropiado</option>
              <option value="SPOILER">Spoiler no advertido</option>
              <option value="COPYRIGHT">Violación de derechos</option>
              <option value="OTHER">Otro motivo</option>
            </select>

            <select
              value={reportTargetFilter}
              onChange={(e) => setReportTargetFilter(e.target.value)}
              className="text-xs rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-700 py-2 px-3"
            >
              <option value="all">Tipo: Todos</option>
              <option value="review">Reseñas de libros</option>
              <option value="user">Perfiles de usuarios</option>
              <option value="comment">Comentarios en reseñas</option>
              <option value="message">Mensajes directos</option>
            </select>

            <button
              onClick={fetchReports}
              className="bg-teal-600 hover:bg-teal-700 text-white text-xs font-bold px-4 py-2 rounded-xl transition-all"
            >
              Filtrar Denuncias
            </button>
          </div>

          {/* Tabla de Denuncias */}
          {loadingReports ? (
            <div className="flex justify-center p-8">
              <Spinner size="lg" color="info" />
            </div>
          ) : reports.length === 0 ? (
            <div className="text-center py-12 border border-dashed border-slate-200 dark:border-slate-700 rounded-2xl">
              <div className="text-4xl mb-2">🎉</div>
              <p className="text-sm font-bold text-slate-700 dark:text-slate-300">¡Bandeja de moderación despejada!</p>
              <p className="text-xs text-slate-500 mt-1">No hay denuncias pendientes bajo los filtros seleccionados.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-slate-200 dark:border-slate-700 text-slate-400 font-bold uppercase tracking-wider text-[10px]">
                    <th className="py-3 px-3">Expediente</th>
                    <th className="py-3 px-3">Denunciante</th>
                    <th className="py-3 px-3">Motivo</th>
                    <th className="py-3 px-3">Elemento Denunciado</th>
                    <th className="py-3 px-3">Estado</th>
                    <th className="py-3 px-3">Medida Aplicada</th>
                    <th className="py-3 px-3 text-right">Gestión</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-700/60">
                  {reports.map((r) => {
                    const statusBadgeClass =
                      r.status === 'OPEN'
                        ? 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300'
                        : r.status === 'UNDER_REVIEW'
                        ? 'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300'
                        : r.status === 'RESOLVED'
                        ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300'
                        : 'bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-300';

                    const targetTypeBadge =
                      r.target_type === 'review'
                        ? 'bg-purple-100 text-purple-800'
                        : r.target_type === 'user'
                        ? 'bg-rose-100 text-rose-800'
                        : r.target_type === 'comment'
                        ? 'bg-teal-100 text-teal-800'
                        : 'bg-blue-100 text-blue-800';

                    return (
                      <tr key={r.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-700/30">
                        <td className="py-3 px-3 font-mono font-bold text-slate-900 dark:text-white">
                          #{r.id}
                          <div className="text-[10px] text-slate-400 font-sans">
                            {new Date(r.created_at).toLocaleDateString()}
                          </div>
                        </td>
                        <td className="py-3 px-3 font-semibold text-slate-700 dark:text-slate-300">
                          @{r.reporter_username}
                        </td>
                        <td className="py-3 px-3">
                          <span className="font-bold text-slate-800 dark:text-slate-200">
                            {r.reason_display || r.reason}
                          </span>
                          {r.description && (
                            <div className="text-[10px] text-slate-500 truncate max-w-xs" title={r.description}>
                              "{r.description}"
                            </div>
                          )}
                        </td>
                        <td className="py-3 px-3">
                          <div className="flex items-center gap-1.5 mb-1">
                            <span className={`px-1.5 py-0.2 text-[9px] font-bold uppercase rounded ${targetTypeBadge}`}>
                              {r.target_type}
                            </span>
                            <span className="text-[10px] text-slate-400 font-mono">id: {r.object_id}</span>
                          </div>
                          <div className="text-[11px] text-slate-600 dark:text-slate-400 max-w-xs">
                            {r.target_preview?.type === 'review' && (
                              <span>
                                Por <b>@{r.target_preview.author}</b> en <i>{r.target_preview.book_title}</i>: "{r.target_preview.snippet}"
                              </span>
                            )}
                            {r.target_preview?.type === 'user' && (
                              <span>
                                Usuario <b>@{r.target_preview.username}</b> ({r.target_preview.email})
                              </span>
                            )}
                            {r.target_preview?.type === 'comment' && (
                              <span>
                                Por <b>@{r.target_preview.author}</b>: "{r.target_preview.snippet}"
                              </span>
                            )}
                            {r.target_preview?.type === 'message' && (
                              <span>
                                De <b>@{r.target_preview.sender}</b>: "{r.target_preview.snippet}"
                              </span>
                            )}
                            {!['review', 'user', 'comment', 'message'].includes(r.target_preview?.type) && (
                              <span>{r.target_preview?.summary || 'Elemento objetivo'}</span>
                            )}
                          </div>
                        </td>
                        <td className="py-3 px-3">
                          <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${statusBadgeClass}`}>
                            {r.status_display || r.status}
                          </span>
                        </td>
                        <td className="py-3 px-3">
                          {r.action_taken ? (
                            <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-slate-100 text-slate-800 dark:bg-slate-700 dark:text-slate-200">
                              {r.action_taken}
                            </span>
                          ) : (
                            <span className="text-slate-400 text-[11px]">—</span>
                          )}
                        </td>
                        <td className="py-3 px-3 text-right">
                          <button
                            onClick={() => {
                              setSelectedReport(r);
                              setModResolveStatus(r.status === 'OPEN' ? 'RESOLVED' : r.status);
                              setModResolveAction(r.action_taken || 'HIDE_CONTENT');
                              setModResolveNotes('');
                            }}
                            className="bg-teal-600 hover:bg-teal-700 text-white text-xs font-bold px-3 py-1.5 rounded-xl shadow-sm transition-all"
                          >
                            Gestionar
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}

          {/* Modal de Resolución de Denuncia */}
          {selectedReport && (
            <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
              <div className="bg-white dark:bg-slate-800 rounded-3xl max-w-xl w-full p-6 space-y-4 border border-slate-200 dark:border-slate-700 shadow-2xl">
                <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-700 pb-3">
                  <div>
                    <span className="text-[10px] font-bold uppercase tracking-wider text-teal-600 dark:text-teal-400">
                      Resolución de Expediente #{selectedReport.id}
                    </span>
                    <h3 className="text-base font-bold text-slate-900 dark:text-white">
                      Denuncia por {selectedReport.reason_display || selectedReport.reason}
                    </h3>
                  </div>
                  <button
                    onClick={() => setSelectedReport(null)}
                    className="w-8 h-8 rounded-full bg-slate-100 dark:bg-slate-700 flex items-center justify-center text-slate-500 hover:bg-slate-200 font-bold"
                  >
                    ✕
                  </button>
                </div>

                {/* Resumen del reporte */}
                <div className="space-y-2 bg-slate-50 dark:bg-slate-700/50 p-3.5 rounded-2xl text-xs">
                  <div className="flex justify-between text-slate-500 text-[11px]">
                    <span>Denunciante: <b>@{selectedReport.reporter_username}</b></span>
                    <span>Fecha: {new Date(selectedReport.created_at).toLocaleString()}</span>
                  </div>
                  {selectedReport.description && (
                    <div className="text-slate-700 dark:text-slate-300">
                      <b>Declaración del usuario:</b> "{selectedReport.description}"
                    </div>
                  )}
                  <div className="pt-1 border-t border-slate-200/60 dark:border-slate-600">
                    <span className="font-bold text-slate-600 dark:text-slate-400">Elemento denunciado ({selectedReport.target_type}):</span>
                    <div className="mt-1 p-2 bg-white dark:bg-slate-800 rounded-xl border border-slate-200/60 dark:border-slate-700 text-slate-700 dark:text-slate-300">
                      {JSON.stringify(selectedReport.target_preview, null, 2)}
                    </div>
                  </div>
                </div>

                <form onSubmit={handleResolveReport} className="space-y-3">
                  <div>
                    <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1">
                      Estado de la Denuncia:
                    </label>
                    <select
                      value={modResolveStatus}
                      onChange={(e) => setModResolveStatus(e.target.value as any)}
                      className="w-full text-xs rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-700 p-2.5"
                    >
                      <option value="RESOLVED">✅ RESOLVED (Procedente / Aplicar medidas)</option>
                      <option value="REJECTED">❌ REJECTED (Desestimar / Sin infracción)</option>
                      <option value="UNDER_REVIEW">🔍 UNDER_REVIEW (Mantener en investigación)</option>
                    </select>
                  </div>

                  {modResolveStatus === 'RESOLVED' && (
                    <div>
                      <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1">
                        Medida Disciplinaria / Acción:
                      </label>
                      <select
                        value={modResolveAction}
                        onChange={(e) => setModResolveAction(e.target.value)}
                        className="w-full text-xs rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-700 p-2.5"
                      >
                        <option value="HIDE_CONTENT">🚫 HIDE_CONTENT (Ocultar contenido moderado)</option>
                        <option value="BAN_USER">⛔ BAN_USER (Bloquear/Desactivar cuenta de usuario)</option>
                        <option value="WARNING">⚠️ WARNING (Apercibimiento / Advertencia)</option>
                        <option value="DISMISS">ℹ️ DISMISS (Resolver sin acción directa)</option>
                      </select>
                    </div>
                  )}

                  <div>
                    <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1">
                      Notas Internas del Moderador:
                    </label>
                    <textarea
                      rows={3}
                      value={modResolveNotes}
                      onChange={(e) => setModResolveNotes(e.target.value)}
                      placeholder="Justificación de la resolución (ej: Lenguaje ofensivo ocultado conforme a directrices de comunidad)..."
                      className="w-full text-xs rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-700 p-2.5"
                    />
                  </div>

                  <div className="flex justify-end gap-2 pt-2">
                    <button
                      type="button"
                      onClick={() => setSelectedReport(null)}
                      className="px-4 py-2 rounded-xl text-xs font-bold text-slate-600 dark:text-slate-300 hover:bg-slate-100"
                    >
                      Cancelar
                    </button>
                    <button
                      type="submit"
                      disabled={resolvingReport}
                      className="bg-teal-600 hover:bg-teal-700 text-white font-bold text-xs px-5 py-2.5 rounded-xl shadow-md transition-all disabled:opacity-50"
                    >
                      {resolvingReport ? 'Guardando...' : 'Aplicar Resolución'}
                    </button>
                  </div>
                </form>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── 6. PESTAÑA: REGISTRO DE AUDITORÍA & LOGS (FASE 30) ── */}
      {activeTab === 'audit' && (
        <div className="bg-white dark:bg-slate-800 rounded-3xl border border-slate-200/80 dark:border-slate-700 p-6 sm:p-8 shadow-sm space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <div className="inline-flex items-center gap-2 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-purple-50 text-purple-700 dark:bg-purple-950/40 dark:text-purple-300 border border-purple-200 dark:border-purple-800 mb-1">
                <span>📜 Trazabilidad & Cumplimiento Normativo</span>
              </div>
              <h2 className="text-lg font-bold text-slate-900 dark:text-white">Bitácora Inmutable de Auditoría</h2>
              <p className="text-xs text-slate-500">
                Historial cronológico de eventos sensibles: cambios de privilegios, bloqueos, moderación y borrado de contenido.
              </p>
            </div>
          </div>

          {/* Tarjetas de Métricas de Auditoría */}
          {auditStats && (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div className="p-3.5 rounded-2xl bg-purple-50 dark:bg-purple-950/30 border border-purple-200/80 dark:border-purple-800">
                <div className="text-[11px] font-bold text-purple-700 dark:text-purple-400">Total Eventos</div>
                <div className="text-xl font-black text-purple-900 dark:text-purple-200">{auditStats.total || 0}</div>
              </div>
              <div className="p-3.5 rounded-2xl bg-teal-50 dark:bg-teal-950/30 border border-teal-200/80 dark:border-teal-800">
                <div className="text-[11px] font-bold text-teal-700 dark:text-teal-400">Últimas 24 Horas</div>
                <div className="text-xl font-black text-teal-900 dark:text-teal-200">{auditStats.last_24h || 0}</div>
              </div>
              <div className="p-3.5 rounded-2xl bg-blue-50 dark:bg-blue-950/30 border border-blue-200/80 dark:border-blue-800">
                <div className="text-[11px] font-bold text-blue-700 dark:text-blue-400">Últimos 7 Días</div>
                <div className="text-xl font-black text-blue-900 dark:text-blue-200">{auditStats.last_7d || 0}</div>
              </div>
              <div className="p-3.5 rounded-2xl bg-slate-50 dark:bg-slate-700/50 border border-slate-200 dark:border-slate-700">
                <div className="text-[11px] font-bold text-slate-600 dark:text-slate-300">Tipos de Acciones</div>
                <div className="text-xl font-black text-slate-900 dark:text-white">
                  {auditStats.by_action ? Object.keys(auditStats.by_action).length : 0}
                </div>
              </div>
            </div>
          )}

          {/* Filtros y Buscador de Auditoría */}
          <div className="flex flex-wrap gap-3 items-center">
            <select
              value={auditActionFilter}
              onChange={(e) => setAuditActionFilter(e.target.value)}
              className="text-xs rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-700 py-2 px-3"
            >
              <option value="all">Acción: Todas</option>
              <option value="ROLE_CHANGE">Cambios de Rol (ROLE_CHANGE)</option>
              <option value="USER_BAN">Bloqueos de Cuenta (USER_BAN)</option>
              <option value="USER_UNBAN">Desbloqueos de Cuenta (USER_UNBAN)</option>
              <option value="USER_BLOCK">Bloqueos Sociales (USER_BLOCK)</option>
              <option value="USER_UNBLOCK">Desbloqueos Sociales (USER_UNBLOCK)</option>
              <option value="MODERATION_RESOLVE">Resolución de Denuncia (MODERATION_RESOLVE)</option>
              <option value="MODERATION_REJECT">Rechazo de Denuncia (MODERATION_REJECT)</option>
              <option value="CONTENT_DELETE">Eliminación de Contenido (CONTENT_DELETE)</option>
              <option value="SECURITY_PASSWORD_CHANGE">Seguridad de Acceso</option>
            </select>

            <input
              type="text"
              placeholder="Filtrar por actor..."
              value={auditActorFilter}
              onChange={(e) => setAuditActorFilter(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && fetchAuditLogs()}
              className="text-xs rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-700 p-2.5 w-44"
            >
            </input>

            <input
              type="text"
              placeholder="Buscar en descripción..."
              value={auditSearch}
              onChange={(e) => setAuditSearch(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && fetchAuditLogs()}
              className="text-xs rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-700 p-2.5 w-56"
            />

            <button
              onClick={fetchAuditLogs}
              className="bg-purple-600 hover:bg-purple-700 text-white text-xs font-bold px-4 py-2 rounded-xl transition-all shadow-sm"
            >
              Filtrar Bitácora
            </button>
          </div>

          {/* Tabla de Registros de Auditoría */}
          {loadingAudit ? (
            <div className="flex justify-center p-8">
              <Spinner size="lg" color="purple" />
            </div>
          ) : auditLogs.length === 0 ? (
            <div className="text-center py-12 border border-dashed border-slate-200 dark:border-slate-700 rounded-2xl">
              <div className="text-4xl mb-2">📜</div>
              <p className="text-sm font-bold text-slate-700 dark:text-slate-300">No hay eventos registrados</p>
              <p className="text-xs text-slate-500 mt-1">No se encontraron eventos bajo los criterios de búsqueda especificados.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-slate-200 dark:border-slate-700 text-slate-400 font-bold uppercase tracking-wider text-[10px]">
                    <th className="py-3 px-3">Fecha y Hora</th>
                    <th className="py-3 px-3">Actor</th>
                    <th className="py-3 px-3">Acción Registrada</th>
                    <th className="py-3 px-3">Elemento Afectado</th>
                    <th className="py-3 px-3">IP Origen</th>
                    <th className="py-3 px-3 text-right">Detalle</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-700/60">
                  {auditLogs.map((log) => {
                    const actionBadgeClass =
                      log.action === 'ROLE_CHANGE'
                        ? 'bg-purple-100 text-purple-800 dark:bg-purple-900/40 dark:text-purple-300'
                        : log.action === 'USER_BAN'
                        ? 'bg-rose-100 text-rose-800 dark:bg-rose-900/40 dark:text-rose-300'
                        : log.action === 'USER_UNBAN'
                        ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300'
                        : log.action === 'USER_BLOCK'
                        ? 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300'
                        : log.action === 'USER_UNBLOCK'
                        ? 'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300'
                        : log.action === 'MODERATION_RESOLVE'
                        ? 'bg-teal-100 text-teal-800 dark:bg-teal-900/40 dark:text-teal-300'
                        : log.action === 'MODERATION_REJECT'
                        ? 'bg-slate-100 text-slate-800 dark:bg-slate-700 dark:text-slate-300'
                        : log.action === 'CONTENT_DELETE'
                        ? 'bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300'
                        : 'bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-300';

                    return (
                      <tr key={log.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-700/30">
                        <td className="py-3 px-3 font-mono text-[11px] text-slate-900 dark:text-white">
                          <div>{new Date(log.created_at).toLocaleDateString()}</div>
                          <div className="text-[10px] text-slate-400 font-sans">
                            {new Date(log.created_at).toLocaleTimeString()}
                          </div>
                        </td>
                        <td className="py-3 px-3 font-bold text-slate-700 dark:text-slate-200">
                          {log.actor_username ? `@${log.actor_username}` : 'Sistema'}
                        </td>
                        <td className="py-3 px-3">
                          <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${actionBadgeClass}`}>
                            {log.action_display || log.action}
                          </span>
                        </td>
                        <td className="py-3 px-3">
                          <div className="flex items-center gap-1.5 mb-0.5">
                            <span className="px-1.5 py-0.2 text-[9px] font-bold uppercase rounded bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 font-mono">
                              {log.target_type}
                            </span>
                            {log.object_id && (
                              <span className="text-[10px] text-slate-400 font-mono">id: {log.object_id}</span>
                            )}
                          </div>
                          <div className="text-[11px] text-slate-700 dark:text-slate-300 truncate max-w-sm" title={log.target_repr}>
                            {log.target_repr || '—'}
                          </div>
                        </td>
                        <td className="py-3 px-3 font-mono text-[11px] text-slate-500">
                          {log.ip_address || '—'}
                        </td>
                        <td className="py-3 px-3 text-right">
                          <button
                            onClick={() => setSelectedAuditLog(log)}
                            className="bg-slate-100 hover:bg-slate-200 dark:bg-slate-700 dark:hover:bg-slate-600 text-slate-700 dark:text-slate-200 text-xs font-bold px-3 py-1.5 rounded-xl transition-all"
                          >
                            Inspeccionar
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}

          {/* Modal de Inspección de Registro de Auditoría */}
          {selectedAuditLog && (
            <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
              <div className="bg-white dark:bg-slate-800 rounded-3xl max-w-xl w-full p-6 space-y-4 border border-slate-200 dark:border-slate-700 shadow-2xl">
                <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-700 pb-3">
                  <div>
                    <span className="text-[10px] font-bold uppercase tracking-wider text-purple-600 dark:text-purple-400">
                      Evento de Auditoría #{selectedAuditLog.id}
                    </span>
                    <h3 className="text-base font-bold text-slate-900 dark:text-white">
                      {selectedAuditLog.action_display || selectedAuditLog.action}
                    </h3>
                  </div>
                  <button
                    onClick={() => setSelectedAuditLog(null)}
                    className="w-8 h-8 rounded-full bg-slate-100 dark:bg-slate-700 flex items-center justify-center text-slate-500 hover:bg-slate-200 font-bold"
                  >
                    ✕
                  </button>
                </div>

                <div className="space-y-3 text-xs">
                  <div className="grid grid-cols-2 gap-3 bg-slate-50 dark:bg-slate-700/50 p-3.5 rounded-2xl">
                    <div>
                      <span className="text-slate-400 text-[10px] font-bold uppercase">Actor</span>
                      <div className="font-bold text-slate-800 dark:text-slate-200">
                        {selectedAuditLog.actor_username ? `@${selectedAuditLog.actor_username}` : 'Sistema'}
                      </div>
                    </div>
                    <div>
                      <span className="text-slate-400 text-[10px] font-bold uppercase">Fecha y Hora</span>
                      <div className="font-mono text-slate-800 dark:text-slate-200">
                        {new Date(selectedAuditLog.created_at).toLocaleString()}
                      </div>
                    </div>
                    <div>
                      <span className="text-slate-400 text-[10px] font-bold uppercase">Dirección IP</span>
                      <div className="font-mono text-slate-800 dark:text-slate-200">
                        {selectedAuditLog.ip_address || 'No registrada'}
                      </div>
                    </div>
                    <div>
                      <span className="text-slate-400 text-[10px] font-bold uppercase">Tipo de Objeto</span>
                      <div className="font-bold text-slate-800 dark:text-slate-200">
                        {selectedAuditLog.target_type} {selectedAuditLog.object_id ? `(ID: ${selectedAuditLog.object_id})` : ''}
                      </div>
                    </div>
                  </div>

                  <div>
                    <span className="text-slate-400 text-[10px] font-bold uppercase block mb-1">Elemento Afectado</span>
                    <div className="p-2.5 bg-slate-50 dark:bg-slate-700/40 rounded-xl font-medium text-slate-800 dark:text-slate-200">
                      {selectedAuditLog.target_repr || '—'}
                    </div>
                  </div>

                  {selectedAuditLog.user_agent && (
                    <div>
                      <span className="text-slate-400 text-[10px] font-bold uppercase block mb-1">User Agent</span>
                      <div className="p-2.5 bg-slate-50 dark:bg-slate-700/40 rounded-xl font-mono text-[10px] text-slate-600 dark:text-slate-400 truncate">
                        {selectedAuditLog.user_agent}
                      </div>
                    </div>
                  )}

                  <div>
                    <span className="text-slate-400 text-[10px] font-bold uppercase block mb-1">Metadatos Estructurados (Payload JSON)</span>
                    <pre className="p-3 bg-slate-900 text-teal-300 rounded-xl font-mono text-[11px] overflow-x-auto max-h-48 leading-relaxed">
                      {JSON.stringify(selectedAuditLog.metadata || {}, null, 2)}
                    </pre>
                  </div>
                </div>

                <div className="flex justify-end pt-2 border-t border-slate-100 dark:border-slate-700">
                  <button
                    onClick={() => setSelectedAuditLog(null)}
                    className="bg-slate-100 hover:bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-200 text-xs font-bold px-5 py-2.5 rounded-xl transition-all"
                  >
                    Cerrar Detalle
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── 7. PESTAÑA: CMS LEGAL ── */}
      {activeTab === 'legal' && (
        <div className="bg-white dark:bg-slate-800 rounded-3xl border border-slate-200/80 dark:border-slate-700 p-6 sm:p-8 shadow-sm space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h2 className="text-lg font-bold text-slate-900 dark:text-white">CMS de Políticas y Textos Legales</h2>
              <p className="text-xs text-slate-500">
                Edita los términos, políticas de privacidad y cookies que se publican en el sitio en tiempo real.
              </p>
            </div>
            {legalMsg && (
              <div className="p-2.5 bg-emerald-50 text-emerald-800 dark:bg-emerald-900/30 rounded-xl text-xs font-semibold">
                {legalMsg}
              </div>
            )}
          </div>

          {/* Selector de Documento Legal */}
          <div className="flex flex-wrap gap-2">
            {[
              { slug: 'terms', title: '📜 Términos del Servicio' },
              { slug: 'privacy', title: '🔒 Política de Privacidad' },
              { slug: 'cookies', title: '🍪 Política de Cookies' },
              { slug: 'legal_notice', title: '⚖️ Aviso Legal' },
            ].map((d) => (
              <button
                key={d.slug}
                onClick={() => setLegalSlug(d.slug as any)}
                className={`px-3.5 py-2 rounded-xl text-xs font-bold transition-all ${
                  legalSlug === d.slug
                    ? 'bg-teal-600 text-white'
                    : 'bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300'
                }`}
              >
                {d.title}
              </button>
            ))}
          </div>

          {loadingLegal ? (
            <div className="flex justify-center p-8">
              <Spinner size="lg" color="info" />
            </div>
          ) : (
            <form onSubmit={handleSaveLegal} className="space-y-4">
              <div>
                <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1">
                  Título del documento:
                </label>
                <input
                  type="text"
                  value={legalTitle}
                  onChange={(e) => setLegalTitle(e.target.value)}
                  className="w-full text-xs rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-700 p-2.5"
                  required
                />
              </div>

              <div className="flex items-center justify-between">
                <label className="block text-xs font-bold text-slate-700 dark:text-slate-300">
                  Contenido (Soporta Markdown / HTML):
                </label>
                <button
                  type="button"
                  onClick={() => setLegalPreviewMode(!legalPreviewMode)}
                  className="text-xs font-bold text-teal-600 hover:underline"
                >
                  {legalPreviewMode ? 'Ver Editor' : 'Vista Previa'}
                </button>
              </div>

              {!legalPreviewMode ? (
                <textarea
                  rows={14}
                  value={legalContent}
                  onChange={(e) => setLegalContent(e.target.value)}
                  placeholder="Escribe aquí el contenido legal en formato Markdown o HTML..."
                  className="w-full text-xs font-mono rounded-2xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-700 p-4 leading-relaxed"
                />
              ) : (
                <div
                  className="p-6 rounded-2xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/60 text-xs leading-relaxed max-h-96 overflow-y-auto prose dark:prose-invert max-w-none"
                  dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(legalContent) }}
                />
              )}

              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pt-2">
                <div className="text-[11px] text-slate-400">
                  {legalUpdatedAt ? (
                    <span>
                      Última modificación: {new Date(legalUpdatedAt).toLocaleString()} {legalUpdatedBy ? `por ${legalUpdatedBy}` : ''}
                    </span>
                  ) : (
                    <span>Aún no se ha guardado una versión personalizada en base de datos.</span>
                  )}
                </div>

                <button
                  type="submit"
                  disabled={savingLegal}
                  className="bg-teal-600 hover:bg-teal-700 text-white font-bold text-xs px-6 py-2.5 rounded-xl shadow-md transition-all disabled:opacity-50"
                >
                  {savingLegal ? 'Publicando...' : 'Guardar y Publicar Documento'}
                </button>
              </div>
            </form>
          )}
        </div>
      )}
    </div>
  );
}
