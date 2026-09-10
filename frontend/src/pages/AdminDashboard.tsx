import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/auth';
import { Spinner } from 'flowbite-react';
import DOMPurify from 'dompurify';

export function AdminDashboard() {
  const navigate = useNavigate();
  const { user, token } = useAuthStore();

  // Redirigir a usuarios no autorizados
  const isAuthorized = user && (user.is_staff || user.is_superuser);

  useEffect(() => {
    if (!token || (user && !isAuthorized)) {
      navigate('/');
    }
  }, [user, token, isAuthorized, navigate]);

  const [activeTab, setActiveTab] = useState<'stats' | 'users' | 'catalog' | 'erratas' | 'legal'>('stats');

  // Estado de Métricas
  const [stats, setStats] = useState<any | null>(null);
  const [loadingStats, setLoadingStats] = useState(false);

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
  const handleUpdateUser = async (targetUser: any, field: 'is_active' | 'is_staff' | 'is_editor', value: boolean) => {
    if (!token) return;
    if (targetUser.id === user?.id && field === 'is_active' && !value) {
      alert('No puedes bloquear tu propia cuenta de administrador.');
      return;
    }
    if (targetUser.id === user?.id && field === 'is_staff' && !value) {
      alert('No puedes retirar tus propios permisos de administrador.');
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
            <span>🛡️ Panel de Control Superseguro</span>
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
          </div>
          <h1 className="text-2xl sm:text-3xl font-black tracking-tight">
            Administración del Sistema
          </h1>
          <p className="text-xs sm:text-sm text-slate-300 mt-1 max-w-xl">
            Gestión integral de usuarios, moderación de catálogo editorial, resolución de erratas y control legal de la plataforma.
          </p>
        </div>

        <div className="flex items-center gap-3 bg-white/10 backdrop-blur-md px-4 py-3 rounded-2xl border border-white/10 text-xs">
          <div className="w-10 h-10 rounded-full bg-teal-500 flex items-center justify-center font-bold text-sm text-slate-900 shadow">
            {user?.username?.slice(0, 2).toUpperCase()}
          </div>
          <div>
            <div className="font-bold">{user?.username}</div>
            <div className="text-[11px] text-teal-300">
              {user?.is_superuser ? 'Superadministrador' : 'Staff / Administrador'}
            </div>
          </div>
        </div>
      </header>

      {/* ── Barra de Pestañas de Navegación ── */}
      <nav className="flex flex-wrap gap-2 border-b border-slate-200 dark:border-slate-800 pb-3">
        {[
          { id: 'stats', label: '📊 Métricas Globales' },
          { id: 'users', label: '👥 Usuarios & Banners' },
          { id: 'catalog', label: '📚 Catálogo & Autores' },
          { id: 'erratas', label: '✍️ Erratas & Moderación' },
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
              <option value="staff">Solo Staff</option>
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
                    <th className="py-3 px-3">Roles</th>
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
                      <td className="py-3 px-3 space-x-1">
                        {u.is_staff && (
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-teal-100 text-teal-800">
                            Staff
                          </span>
                        )}
                        {u.is_editor && (
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-blue-100 text-blue-800">
                            Editor
                          </span>
                        )}
                        {!u.is_staff && !u.is_editor && (
                          <span className="text-slate-400 text-[11px]">Lector</span>
                        )}
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
                        {/* Botón Promover/Degradar Staff */}
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

      {/* ── 5. PESTAÑA: CMS LEGAL ── */}
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
