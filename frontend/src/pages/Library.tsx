import React, { useEffect, useState } from 'react';
import { useAuthStore } from '../store/auth';
import { useNavigate, Link } from 'react-router-dom';
import { Spinner } from 'flowbite-react';

const DEFAULT_PAGE_SIZE = 12;

interface UserBookItem {
  id: number;
  book: {
    id: number;
    title: string;
    cover?: string;
    author?: {
      id: number;
      name: string;
    };
    average_rating?: number;
    description?: string;
  };
  is_read: boolean;
  rating?: number;
  is_digital: boolean;
  owned: boolean;
  wishlist: boolean;
  notes?: string;
  updated_at: string;
}

export function Library() {
  const { user, token } = useAuthStore();
  const navigate = useNavigate();

  const [books, setBooks] = useState<UserBookItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [order, setOrder] = useState('fecha');
  const [filters, setFilters] = useState({
    is_read: '',
    wishlist: '',
    is_digital: '',
    owned: '',
    search: '',
  });
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState<number>(DEFAULT_PAGE_SIZE);
  const [totalCount, setTotalCount] = useState<number>(0);
  const [selectedBooks, setSelectedBooks] = useState<Set<number>>(new Set());
  const [refreshKey, setRefreshKey] = useState(0);

  const apiUrl = (import.meta as any).env.VITE_API_URL || 'http://localhost:8000';

  useEffect(() => {
    if (!token) return;
    const fetchUserBooks = async () => {
      setLoading(true);
      try {
        const params = new URLSearchParams();
        if (filters.is_read) params.set('is_read', filters.is_read);
        if (filters.wishlist) params.set('wishlist', filters.wishlist);
        if (filters.is_digital) params.set('is_digital', filters.is_digital);
        if (filters.owned) params.set('owned', filters.owned);
        if (filters.search) params.set('search', filters.search);
        params.set('page', String(page));
        params.set('page_size', String(pageSize));

        const ordering =
          order === 'fecha'
            ? '-updated_at'
            : order === 'nota'
            ? '-rating'
            : order === 'alfabetico'
            ? 'book__title'
            : '-updated_at';
        params.set('ordering', ordering);

        const res = await fetch(`${apiUrl}/api/v1/books/user/books/?${params.toString()}`, {
          headers: { Authorization: `Bearer ${token}` },
        });

        if (res.ok) {
          const data = await res.json();
          if (Array.isArray(data)) {
            setBooks(data);
            setTotalCount(data.length);
          } else {
            setBooks(data.results || []);
            setTotalCount(data.count || 0);
          }
        }
      } catch (e) {
        console.error('Error fetching library books', e);
      } finally {
        setLoading(false);
      }
    };

    fetchUserBooks();
  }, [token, filters, order, page, pageSize, refreshKey, apiUrl]);

  const updateField = async (ubId: number, field: string, val: any) => {
    if (!token) return;
    try {
      const res = await fetch(`${apiUrl}/api/v1/books/user/books/${ubId}/`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ [field]: val }),
      });
      if (res.ok) {
        setBooks((prev) =>
          prev.map((b) => (b.id === ubId ? { ...b, [field]: val } : b))
        );
      }
    } catch (e) {
      console.error(e);
    }
  };

  const deleteSelected = async () => {
    if (selectedBooks.size === 0 || !token) return;
    if (!window.confirm(`¿Seguro que deseas eliminar ${selectedBooks.size} libros de tu biblioteca?`)) return;

    for (const id of selectedBooks) {
      await fetch(`${apiUrl}/api/v1/books/user/books/${id}/`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      });
    }
    setSelectedBooks(new Set());
    setRefreshKey((k) => k + 1);
  };

  if (!user) return null;

  const totalPages = Math.ceil(totalCount / pageSize) || 1;

  // Estadísticas rápidas
  const readCount = books.filter((b) => b.is_read).length;
  const wishlistCount = books.filter((b) => b.wishlist).length;

  return (
    <div className="space-y-6">
      {/* ── Encabezado y Métricas ── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white dark:bg-slate-800 p-6 rounded-3xl border border-slate-200/80 dark:border-slate-700 shadow-sm">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-white tracking-tight flex items-center gap-2">
            <span>📚</span>
            <span>Mi Biblioteca</span>
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            Gestiona tus lecturas, listas de deseos y libros en propiedad.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-4 px-4 py-2 bg-slate-50 dark:bg-slate-700/50 rounded-2xl border border-slate-200/60 dark:border-slate-600 text-xs">
            <div>
              <span className="block font-bold text-base text-teal-600 dark:text-teal-400">{totalCount}</span>
              <span className="text-slate-500">Total</span>
            </div>
            <div className="w-px h-6 bg-slate-200 dark:bg-slate-600" />
            <div>
              <span className="block font-bold text-base text-emerald-600 dark:text-emerald-400">{readCount}</span>
              <span className="text-slate-500">Leídos</span>
            </div>
            <div className="w-px h-6 bg-slate-200 dark:bg-slate-600" />
            <div>
              <span className="block font-bold text-base text-amber-600 dark:text-amber-400">{wishlistCount}</span>
              <span className="text-slate-500">Wishlist</span>
            </div>
          </div>

          <button
            onClick={() => navigate('/books/add')}
            className="bg-teal-600 hover:bg-teal-700 text-white font-bold px-4 py-2.5 rounded-xl text-sm transition-all shadow-md shadow-teal-600/20 flex items-center gap-1.5"
          >
            <span>+</span>
            <span className="hidden sm:inline">Añadir Libro</span>
          </button>
        </div>
      </div>

      {/* ── Barra de Búsqueda y Filtros ── */}
      <div className="bg-white dark:bg-slate-800 p-4 rounded-2xl border border-slate-200/80 dark:border-slate-700 shadow-sm space-y-3">
        <div className="flex flex-col md:flex-row gap-3 items-center justify-between">
          <div className="relative w-full md:w-80">
            <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-slate-400">
              🔍
            </span>
            <input
              type="text"
              placeholder="Buscar en tu biblioteca..."
              value={filters.search}
              onChange={(e) => {
                setFilters((f) => ({ ...f, search: e.target.value }));
                setPage(1);
              }}
              className="w-full pl-9 pr-4 py-2 text-sm rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-700/50 dark:text-white focus:ring-2 focus:ring-teal-500 focus:border-teal-500"
            />
          </div>

          <div className="flex flex-wrap gap-2 w-full md:w-auto items-center">
            {/* Filtro Leído */}
            <select
              value={filters.is_read}
              onChange={(e) => {
                setFilters((f) => ({ ...f, is_read: e.target.value }));
                setPage(1);
              }}
              className="text-xs font-medium rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-700 dark:text-white py-2 px-3 focus:ring-teal-500"
            >
              <option value="">Lectura: Todas</option>
              <option value="true">✅ Leídos</option>
              <option value="false">⏳ Por leer</option>
            </select>

            {/* Filtro Wishlist */}
            <select
              value={filters.wishlist}
              onChange={(e) => {
                setFilters((f) => ({ ...f, wishlist: e.target.value }));
                setPage(1);
              }}
              className="text-xs font-medium rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-700 dark:text-white py-2 px-3 focus:ring-teal-500"
            >
              <option value="">Wishlist: Todos</option>
              <option value="true">⭐ En Wishlist</option>
              <option value="false">No en Wishlist</option>
            </select>

            {/* Filtro Formato */}
            <select
              value={filters.is_digital}
              onChange={(e) => {
                setFilters((f) => ({ ...f, is_digital: e.target.value }));
                setPage(1);
              }}
              className="text-xs font-medium rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-700 dark:text-white py-2 px-3 focus:ring-teal-500"
            >
              <option value="">Formato: Todos</option>
              <option value="true">📱 Digital</option>
              <option value="false">📖 Físico</option>
            </select>

            {/* Orden */}
            <select
              value={order}
              onChange={(e) => setOrder(e.target.value)}
              className="text-xs font-medium rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-700 dark:text-white py-2 px-3 focus:ring-teal-500"
            >
              <option value="fecha">Recientes</option>
              <option value="nota">Mejor valorados</option>
              <option value="alfabetico">Título A-Z</option>
            </select>

            {selectedBooks.size > 0 && (
              <button
                onClick={deleteSelected}
                className="bg-rose-600 hover:bg-rose-700 text-white font-bold px-3 py-1.5 rounded-xl text-xs transition-colors shadow"
              >
                Eliminar seleccionados ({selectedBooks.size})
              </button>
            )}
          </div>
        </div>
      </div>

      {/* ── Grid de Libros ── */}
      {loading ? (
        <div className="flex justify-center items-center py-24">
          <Spinner size="xl" color="info" />
        </div>
      ) : books.length === 0 ? (
        <div className="bg-white dark:bg-slate-800 rounded-3xl p-12 text-center border border-slate-200/80 dark:border-slate-700 shadow-sm">
          <div className="w-16 h-16 rounded-full bg-teal-50 dark:bg-teal-900/30 text-teal-600 flex items-center justify-center text-3xl mx-auto mb-4">
            📖
          </div>
          <h3 className="text-lg font-bold text-slate-900 dark:text-white">
            Tu biblioteca está vacía
          </h3>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-2 max-w-md mx-auto">
            {filters.search || filters.is_read || filters.wishlist
              ? 'No hay libros que coincidan con los filtros aplicados.'
              : 'Comienza buscando y agregando tus libros favoritos o pendientes.'}
          </p>
          <button
            onClick={() => navigate('/books/add')}
            className="mt-6 bg-teal-600 hover:bg-teal-700 text-white font-bold px-5 py-2.5 rounded-xl text-sm transition-all shadow-md shadow-teal-600/20"
          >
            Buscar libros para añadir
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
          {books.map((ub) => {
            const b = ub.book;
            const isSelected = selectedBooks.has(ub.id);

            return (
              <div
                key={ub.id}
                className={`bg-white dark:bg-slate-800 rounded-2xl border transition-all duration-200 overflow-hidden flex flex-col justify-between group shadow-sm hover:shadow-lg ${
                  isSelected
                    ? 'border-teal-500 ring-2 ring-teal-500/20'
                    : 'border-slate-200/80 dark:border-slate-700'
                }`}
              >
                <div className="p-4 space-y-3">
                  {/* Portada & Checkbox */}
                  <div className="relative aspect-[2/3] w-full rounded-xl overflow-hidden bg-slate-100 dark:bg-slate-700 shadow-inner">
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={(e) => {
                        const newSet = new Set(selectedBooks);
                        if (e.target.checked) newSet.add(ub.id);
                        else newSet.delete(ub.id);
                        setSelectedBooks(newSet);
                      }}
                      className="absolute top-2 left-2 z-10 rounded text-teal-600 focus:ring-teal-500 w-4 h-4 bg-white/90 border-slate-300"
                    />

                    {b.cover ? (
                      <img
                        src={b.cover}
                        alt={b.title}
                        className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300 cursor-pointer"
                        onClick={() => navigate(`/books/${b.id}`)}
                        loading="lazy"
                      />
                    ) : (
                      <div
                        onClick={() => navigate(`/books/${b.id}`)}
                        className="w-full h-full flex items-center justify-center p-4 text-center text-xs font-semibold text-slate-400 dark:text-slate-500 cursor-pointer"
                      >
                        {b.title}
                      </div>
                    )}

                    {/* Badges de Formato */}
                    <div className="absolute top-2 right-2 flex flex-col gap-1">
                      <span className="px-2 py-0.5 rounded-md text-[10px] font-bold bg-slate-900/80 text-white backdrop-blur-sm shadow">
                        {ub.is_digital ? '📱 Digital' : '📖 Físico'}
                      </span>
                      {ub.owned && (
                        <span className="px-2 py-0.5 rounded-md text-[10px] font-bold bg-teal-600/90 text-white backdrop-blur-sm shadow">
                          Tengo
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Título & Autor */}
                  <div>
                    <h3
                      onClick={() => navigate(`/books/${b.id}`)}
                      className="font-bold text-sm text-slate-900 dark:text-white truncate cursor-pointer hover:text-teal-600 transition-colors"
                      title={b.title}
                    >
                      {b.title}
                    </h3>
                    <p className="text-xs text-slate-500 dark:text-slate-400 truncate">
                      {b.author?.name ? (
                        <Link
                          to={`/authors/${b.author.id}`}
                          className="hover:underline hover:text-teal-600"
                        >
                          {b.author.name}
                        </Link>
                      ) : (
                        'Autor desconocido'
                      )}
                    </p>
                  </div>

                  {/* Puntuación Personal */}
                  <div className="flex items-center justify-between pt-1 text-xs">
                    <span className="text-slate-400">Mi nota:</span>
                    <select
                      value={ub.rating || ''}
                      onChange={(e) =>
                        updateField(ub.id, 'rating', e.target.value ? Number(e.target.value) : null)
                      }
                      className="text-xs font-semibold rounded-lg border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-700 py-1 px-2"
                    >
                      <option value="">Sin nota</option>
                      {[10, 9, 8, 7, 6, 5, 4, 3, 2, 1].map((n) => (
                        <option key={n} value={n}>
                          ⭐ {n}/10
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                {/* Botonera de Estado */}
                <div className="p-3 bg-slate-50/70 dark:bg-slate-700/30 border-t border-slate-100 dark:border-slate-700/60 flex items-center justify-between text-xs">
                  <button
                    onClick={() => updateField(ub.id, 'is_read', !ub.is_read)}
                    className={`px-2.5 py-1 rounded-lg font-semibold transition-colors ${
                      ub.is_read
                        ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300'
                        : 'bg-slate-200 text-slate-700 dark:bg-slate-700 dark:text-slate-300 hover:bg-slate-300'
                    }`}
                  >
                    {ub.is_read ? '✓ Leído' : '⏳ Por leer'}
                  </button>

                  <button
                    onClick={() => updateField(ub.id, 'wishlist', !ub.wishlist)}
                    className={`p-1.5 rounded-lg transition-colors ${
                      ub.wishlist
                        ? 'text-amber-500 font-bold'
                        : 'text-slate-400 hover:text-amber-500'
                    }`}
                    title={ub.wishlist ? 'Quitar de Wishlist' : 'Añadir a Wishlist'}
                  >
                    {ub.wishlist ? '⭐ Deseado' : '☆ Desear'}
                  </button>

                  <button
                    onClick={() => navigate(`/books/${b.id}`)}
                    className="text-teal-600 hover:text-teal-700 font-medium hover:underline text-[11px]"
                  >
                    Ver ficha ➔
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* ── Paginación ── */}
      {totalPages > 1 && (
        <div className="flex justify-center items-center gap-2 pt-4">
          <button
            disabled={page <= 1}
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            className="px-4 py-2 text-xs font-semibold rounded-xl bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 disabled:opacity-40 hover:bg-slate-50 transition-colors shadow-sm"
          >
            ← Anterior
          </button>
          <span className="text-xs font-medium text-slate-600 dark:text-slate-400 px-3">
            Página {page} de {totalPages}
          </span>
          <button
            disabled={page >= totalPages}
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            className="px-4 py-2 text-xs font-semibold rounded-xl bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 disabled:opacity-40 hover:bg-slate-50 transition-colors shadow-sm"
          >
            Siguiente →
          </button>
        </div>
      )}
    </div>
  );
}
