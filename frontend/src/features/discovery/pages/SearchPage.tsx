import { useState, useEffect, useCallback } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { Spinner } from 'flowbite-react';
import { apiClient } from '../../../api/client';

interface AuthorResult {
  id: number;
  name: string;
  photo?: string | null;
  biography?: string | null;
  is_verified?: boolean;
  published_books_count?: number;
  total_readers_count?: number;
  total_reviews_count?: number;
  average_rating?: number;
}

interface BookResult {
  id: number;
  title: string;
  author?: { id: number; name: string } | null;
  authors?: Array<{ id: number; name: string }>;
  cover?: string | null;
  description?: string | null;
  isbn?: string | null;
  additional_isbns?: string[];
  average_rating?: number | null;
  reviews_count?: number;
}

interface UserResult {
  id: number;
  username: string;
  first_name?: string;
  last_name?: string;
  avatar?: string | null;
  bio?: string | null;
}

interface SearchResponse {
  query: string;
  type: string;
  total_results: number;
  books: BookResult[];
  authors: AuthorResult[];
  users: UserResult[];
}

export function SearchPage() {
  const [searchParams, setSearchParams] = useSearchParams();

  const queryFromUrl = searchParams.get('q') || '';
  const typeFromUrl = searchParams.get('type') || 'all';

  const [searchTerm, setSearchTerm] = useState(queryFromUrl);
  const [activeTab, setActiveTab] = useState<'all' | 'books' | 'authors' | 'users'>(
    (typeFromUrl as any) || 'all'
  );
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<SearchResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const executeSearch = useCallback(
    async (queryText: string, searchType: string) => {
      const trimmed = queryText.trim();
      if (!trimmed) {
        setData(null);
        return;
      }

      setLoading(true);
      setError(null);

      try {
        const params = new URLSearchParams({
          q: trimmed,
          type: searchType,
          limit: '20',
        });
        const res = await apiClient<SearchResponse>(`/api/v1/search/?${params.toString()}`, {
          method: 'GET',
          requireAuth: false,
        });
        setData(res);
      } catch (err: any) {
        setError('Error al consultar el motor de búsqueda. Inténtalo de nuevo.');
      } finally {
        setLoading(false);
      }
    },
    []
  );

  useEffect(() => {
    setSearchTerm(queryFromUrl);
    if (queryFromUrl.trim()) {
      executeSearch(queryFromUrl, typeFromUrl);
    }
  }, [queryFromUrl, typeFromUrl, executeSearch]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = searchTerm.trim();
    if (!trimmed) return;
    setSearchParams({ q: trimmed, type: activeTab });
  };

  const handleTabChange = (newTab: 'all' | 'books' | 'authors' | 'users') => {
    setActiveTab(newTab);
    if (searchTerm.trim()) {
      setSearchParams({ q: searchTerm.trim(), type: newTab });
    }
  };

  const quickSearches = [
    'La catedral del mar',
    'Dune',
    'Gabriel García Márquez',
    'Isabel Allende',
    'Ficción histórica',
    'Ciencia ficción',
  ];

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900 py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-6xl mx-auto space-y-8">
        {/* Cabecera y Buscador */}
        <div className="bg-white dark:bg-slate-800 rounded-3xl p-6 sm:p-8 shadow-sm border border-slate-200 dark:border-slate-700">
          <div className="text-center max-w-2xl mx-auto space-y-3 mb-6">
            <h1 className="text-3xl sm:text-4xl font-black text-slate-900 dark:text-white tracking-tight">
              Búsqueda <span className="text-teal-600 dark:text-teal-400">Global Unificada</span>
            </h1>
            <p className="text-sm sm:text-base text-slate-600 dark:text-slate-300">
              Encuentra libros (físicos y digitales unificados), autores verificados y lectores en toda la comunidad.
            </p>
          </div>

          <form onSubmit={handleSearchSubmit} className="max-w-3xl mx-auto" role="search">
            <div className="relative flex items-center">
              <span className="absolute left-4 text-slate-400 text-lg" aria-hidden="true">🔍</span>
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Busca por título, autor, ISBN o nombre de usuario..."
                aria-label="Término de búsqueda global (título, autor, ISBN o usuario)"
                className="w-full pl-12 pr-28 py-3.5 sm:py-4 rounded-2xl border border-slate-300 dark:border-slate-600 bg-slate-50 dark:bg-slate-700/50 text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-teal-500 focus-visible:ring-2 focus-visible:ring-teal-500 focus:border-transparent transition text-base shadow-inner"
              />
              <button
                type="submit"
                className="absolute right-2.5 px-5 py-2.5 rounded-xl bg-teal-600 hover:bg-teal-700 focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-teal-500 text-white font-bold text-sm shadow-md shadow-teal-700/20 transition-all transform hover:scale-[1.02] active:scale-[0.98]"
              >
                Buscar
              </button>
            </div>
          </form>

          {/* Sugerencias Rápidas */}
          {!data && !loading && (
            <div className="mt-6 flex flex-wrap items-center justify-center gap-2 text-xs text-slate-500 dark:text-slate-400">
              <span className="font-semibold">Búsquedas populares:</span>
              {quickSearches.map((item) => (
                <button
                  key={item}
                  type="button"
                  onClick={() => {
                    setSearchTerm(item);
                    setSearchParams({ q: item, type: activeTab });
                  }}
                  className="px-3 py-1 rounded-full bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-200 hover:bg-teal-50 dark:hover:bg-teal-900/30 hover:text-teal-700 dark:hover:text-teal-300 transition-colors"
                >
                  {item}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Pestañas de Filtrado */}
        {data && (
          <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-700 pb-3">
            <div className="flex gap-2 overflow-x-auto" role="tablist" aria-label="Filtrar tipo de resultado">
              {[
                { id: 'all', label: 'Todo', count: data.total_results },
                { id: 'books', label: 'Libros', count: data.books.length },
                { id: 'authors', label: 'Autores', count: data.authors.length },
                { id: 'users', label: 'Lectores', count: data.users.length },
              ].map((tab) => (
                <button
                  key={tab.id}
                  role="tab"
                  aria-selected={activeTab === tab.id}
                  onClick={() => handleTabChange(tab.id as any)}
                  className={`px-4 py-2 rounded-xl text-sm font-bold transition-all flex items-center gap-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-500 ${
                    activeTab === tab.id
                      ? 'bg-teal-600 text-white shadow-md shadow-teal-700/20'
                      : 'text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-800'
                  }`}
                >
                  <span>{tab.label}</span>
                  <span
                    className={`text-xs px-2 py-0.5 rounded-full ${
                      activeTab === tab.id
                        ? 'bg-white/20 text-white'
                        : 'bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-300'
                    }`}
                  >
                    {tab.count}
                  </span>
                </button>
              ))}
            </div>

            <span className="text-xs text-slate-500 dark:text-slate-400 hidden sm:inline">
              Resultados para: <span className="font-semibold text-slate-800 dark:text-slate-200">"{data.query}"</span>
            </span>
          </div>
        )}

        {/* Estado de Carga */}
        {loading && (
          <div className="p-16 flex flex-col items-center justify-center gap-3">
            <Spinner size="xl" color="info" />
            <p className="text-sm font-medium text-slate-500 dark:text-slate-400">
              Explorando el catálogo y la comunidad...
            </p>
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="p-4 rounded-2xl bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-300 text-sm text-center">
            {error}
          </div>
        )}

        {/* Resultados */}
        {data && !loading && (
          <div className="space-y-10">
            {/* Sin Resultados */}
            {data.total_results === 0 && (
              <div className="p-12 text-center bg-white dark:bg-slate-800 rounded-3xl border border-slate-200 dark:border-slate-700 space-y-3">
                <span className="text-4xl">📚🔍</span>
                <h3 className="text-lg font-bold text-slate-900 dark:text-white">
                  No se encontraron coincidencias
                </h3>
                <p className="text-sm text-slate-500 dark:text-slate-400 max-w-md mx-auto">
                  Prueba a buscar con palabras clave más generales, el nombre del autor o revisa que el ISBN no tenga caracteres extraños.
                </p>
              </div>
            )}

            {/* SECCIÓN LIBROS */}
            {(activeTab === 'all' || activeTab === 'books') && data.books.length > 0 && (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h2 className="text-xl font-extrabold text-slate-900 dark:text-white flex items-center gap-2">
                    <span>📖 Libros</span>
                    <span className="text-xs font-bold px-2 py-0.5 rounded-full bg-teal-100 dark:bg-teal-900/40 text-teal-800 dark:text-teal-300">
                      {data.books.length}
                    </span>
                  </h2>
                  {activeTab === 'all' && data.books.length >= 10 && (
                    <button
                      onClick={() => handleTabChange('books')}
                      className="text-xs font-semibold text-teal-600 dark:text-teal-400 hover:underline"
                    >
                      Ver todos los libros →
                    </button>
                  )}
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                  {data.books.map((book) => {
                    const extraIsbnsCount = (book.additional_isbns || []).length;
                    return (
                      <div
                        key={book.id}
                        className="bg-white dark:bg-slate-800 rounded-2xl p-4 border border-slate-200 dark:border-slate-700 hover:shadow-md transition flex gap-4 group"
                      >
                        <div className="w-20 h-28 flex-shrink-0 bg-slate-100 dark:bg-slate-700 rounded-xl overflow-hidden relative shadow-inner">
                          {book.cover ? (
                            <img
                              src={book.cover}
                              alt={book.title}
                              className="w-full h-full object-cover group-hover:scale-105 transition-transform"
                              loading="lazy"
                            />
                          ) : (
                            <div className="w-full h-full flex items-center justify-center text-2xl text-slate-400">
                              📖
                            </div>
                          )}
                        </div>

                        <div className="flex-1 flex flex-col justify-between min-w-0">
                          <div>
                            <Link
                              to={`/books/${book.id}`}
                              className="font-bold text-slate-900 dark:text-white hover:text-teal-600 dark:hover:text-teal-400 text-sm line-clamp-2 transition-colors"
                              title={book.title}
                            >
                              {book.title}
                            </Link>
                            <p className="text-xs text-slate-500 dark:text-slate-400 truncate mt-0.5">
                              {book.author ? (
                                <Link
                                  to={`/authors/${book.author.id}`}
                                  className="hover:underline hover:text-teal-600"
                                >
                                  {book.author.name}
                                </Link>
                              ) : (
                                'Autor desconocido'
                              )}
                            </p>

                            {/* Badge de Ediciones Unificadas */}
                            <div className="flex items-center gap-1.5 mt-2 flex-wrap">
                              {book.isbn && (
                                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300">
                                  ISBN: {book.isbn}
                                </span>
                              )}
                              {extraIsbnsCount > 0 && (
                                <span
                                  className="text-[10px] font-semibold px-1.5 py-0.5 rounded bg-teal-50 dark:bg-teal-900/30 text-teal-700 dark:text-teal-300"
                                  title={`Ediciones unificadas asociadas: ${book.additional_isbns?.join(', ')}`}
                                >
                                  +{extraIsbnsCount} {extraIsbnsCount === 1 ? 'edición' : 'ediciones'}
                                </span>
                              )}
                            </div>
                          </div>

                          <div className="flex items-center justify-between mt-3 pt-2 border-t border-slate-100 dark:border-slate-700/50">
                            <span className="text-xs font-bold text-amber-500 flex items-center gap-1">
                              ⭐ {book.average_rating ? Number(book.average_rating).toFixed(1) : '—'}
                              <span className="text-[10px] font-normal text-slate-400">
                                ({book.reviews_count || 0})
                              </span>
                            </span>
                            <Link
                              to={`/books/${book.id}`}
                              className="text-xs font-bold text-teal-600 dark:text-teal-400 hover:underline"
                            >
                              Ficha →
                            </Link>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* SECCIÓN AUTORES */}
            {(activeTab === 'all' || activeTab === 'authors') && data.authors.length > 0 && (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h2 className="text-xl font-extrabold text-slate-900 dark:text-white flex items-center gap-2">
                    <span>✍️ Autores</span>
                    <span className="text-xs font-bold px-2 py-0.5 rounded-full bg-purple-100 dark:bg-purple-900/40 text-purple-800 dark:text-purple-300">
                      {data.authors.length}
                    </span>
                  </h2>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                  {data.authors.map((author) => (
                    <div
                      key={author.id}
                      className="bg-white dark:bg-slate-800 rounded-2xl p-4 border border-slate-200 dark:border-slate-700 hover:shadow-md transition flex items-center gap-4"
                    >
                      <div className="w-16 h-16 rounded-full overflow-hidden bg-slate-100 dark:bg-slate-700 flex-shrink-0 relative shadow-inner">
                        {author.photo ? (
                          <img
                            src={author.photo}
                            alt={author.name}
                            className="w-full h-full object-cover"
                            loading="lazy"
                          />
                        ) : (
                          <div className="w-full h-full flex items-center justify-center text-xl text-slate-400">
                            ✍️
                          </div>
                        )}
                      </div>

                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-1.5">
                          <Link
                            to={`/authors/${author.id}`}
                            className="font-bold text-slate-900 dark:text-white hover:text-purple-600 text-sm truncate"
                          >
                            {author.name}
                          </Link>
                          {author.is_verified && (
                            <span
                              className="text-xs text-teal-600 dark:text-teal-400"
                              title="Autor Verificado"
                            >
                              ✓
                            </span>
                          )}
                        </div>

                        <div className="flex items-center gap-3 text-xs text-slate-500 dark:text-slate-400 mt-1">
                          <span>{author.published_books_count || 0} libros</span>
                          <span>•</span>
                          <span>{author.total_readers_count || 0} lectores</span>
                        </div>

                        <Link
                          to={`/authors/${author.id}`}
                          className="inline-block mt-2 text-xs font-bold text-purple-600 dark:text-purple-400 hover:underline"
                        >
                          Ver perfil de autor →
                        </Link>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* SECCIÓN LECTORES */}
            {(activeTab === 'all' || activeTab === 'users') && data.users.length > 0 && (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h2 className="text-xl font-extrabold text-slate-900 dark:text-white flex items-center gap-2">
                    <span>👥 Lectores de la Comunidad</span>
                    <span className="text-xs font-bold px-2 py-0.5 rounded-full bg-blue-100 dark:bg-blue-900/40 text-blue-800 dark:text-blue-300">
                      {data.users.length}
                    </span>
                  </h2>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                  {data.users.map((reader) => (
                    <div
                      key={reader.id}
                      className="bg-white dark:bg-slate-800 rounded-2xl p-4 border border-slate-200 dark:border-slate-700 hover:shadow-md transition flex items-center gap-4"
                    >
                      <div className="w-14 h-14 rounded-full overflow-hidden bg-slate-100 dark:bg-slate-700 flex-shrink-0 shadow-inner">
                        {reader.avatar ? (
                          <img
                            src={reader.avatar}
                            alt={reader.username}
                            className="w-full h-full object-cover"
                            loading="lazy"
                          />
                        ) : (
                          <div className="w-full h-full flex items-center justify-center font-bold text-slate-400">
                            {reader.username.charAt(0).toUpperCase()}
                          </div>
                        )}
                      </div>

                      <div className="flex-1 min-w-0">
                        <Link
                          to={`/users/${reader.id}`}
                          className="font-bold text-slate-900 dark:text-white hover:text-blue-600 text-sm truncate block"
                        >
                          @{reader.username}
                        </Link>
                        {reader.first_name && (
                          <p className="text-xs text-slate-500 dark:text-slate-400 truncate">
                            {reader.first_name} {reader.last_name || ''}
                          </p>
                        )}
                        <Link
                          to={`/users/${reader.id}`}
                          className="inline-block mt-1 text-xs font-bold text-blue-600 dark:text-blue-400 hover:underline"
                        >
                          Ver perfil →
                        </Link>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default SearchPage;
