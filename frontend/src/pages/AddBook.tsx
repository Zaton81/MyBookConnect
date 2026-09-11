import React, { useState, useEffect } from 'react';
import { useAuthStore } from '../store/auth';
import { useNavigate } from 'react-router-dom';
import { Modal, Spinner } from 'flowbite-react';
import { resolveMediaUrl } from '../utils/media';

interface SearchBook {
  id: number;
  title: string;
  cover?: string;
  published_date?: string;
  author?: {
    id: number;
    name: string;
  };
  description?: string;
  categories?: Array<{ id?: number; name: string }>;
}

export function AddBook() {
  const { token } = useAuthStore();
  const navigate = useNavigate();

  const [activeTab, setActiveTab] = useState<'search' | 'manual'>('search');

  // Búsqueda inteligente
  const [search, setSearch] = useState('');
  const [searchResults, setSearchResults] = useState<SearchBook[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [searchSource, setSearchSource] = useState<string>('');
  const [offset, setOffset] = useState(0);

  // Modal para añadir a estantería
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [selectedBook, setSelectedBook] = useState<SearchBook | null>(null);
  const [format, setFormat] = useState<'digital' | 'fisico'>('digital');
  const [statusChoice, setStatusChoice] = useState<'read' | 'wishlist' | 'reading'>('reading');
  const [userRating, setUserRating] = useState<number | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Creación manual
  const [manualTitle, setManualTitle] = useState('');
  const [manualAuthor, setManualAuthor] = useState('');
  const [manualIsbn, setManualIsbn] = useState('');
  const [manualDesc, setManualDesc] = useState('');
  const [manualDate, setManualDate] = useState('');
  const [manualCover, setManualCover] = useState<File | null>(null);
  const [manualLoading, setManualLoading] = useState(false);

  const apiUrl = (import.meta as any).env.VITE_API_URL || 'http://localhost:8000';

  const handleSearch = async (q: string, currentOffset: number, signal?: AbortSignal, forceExternal: boolean = false) => {
    if (!token || q.length < 2) {
      setSearchResults([]);
      return;
    }
    setIsSearching(true);
    setSearchSource('Buscando en catálogo...');

    try {
      // 1. Buscar en la base de datos local
      const res = await fetch(`${apiUrl}/api/v1/books/?search=${encodeURIComponent(q)}`, {
        headers: { Authorization: `Bearer ${token}` },
        signal,
      });

      let localResults: SearchBook[] = [];
      if (res.ok) {
        const data = await res.json();
        localResults = Array.isArray(data) ? data : data.results || [];
      }

      // Verificar si hay una coincidencia cercana con el título buscado
      const normQ = q.toLowerCase().replace(/[^\w\s]/gi, '').trim();
      const hasCloseMatch = localResults.some((b) => {
        const normTitle = (b.title || '').toLowerCase().replace(/[^\w\s]/gi, '');
        return normTitle.includes(normQ) || normQ.includes(normTitle);
      });

      // 2. Si no hay coincidencia cercana, si hay pocos resultados o si se fuerza, buscar externamente
      const shouldQueryExternal = forceExternal || (!hasCloseMatch && q.length >= 3 && currentOffset === 0) || (localResults.length < 3 && currentOffset === 0);

      if (shouldQueryExternal) {
        setSearchSource('Consultando Google Books, OpenLibrary y Wikipedia...');
        const isIsbn = /^\d[\d-]{8,}[\dX]?$/.test(q.replace(/[\s-]/g, ''));
        const importBody = isIsbn ? { isbn: q } : { title: q, offset: currentOffset };

        const importRes = await fetch(`${apiUrl}/api/v1/books/import/`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify(importBody),
          signal,
        });

        if (importRes.ok) {
          const importData = await importRes.json();
          const created: SearchBook[] = Array.isArray(importData) ? importData : [importData];

          // Combinar resultados locales y externos sin duplicados por ID
          const map = new Map<number, SearchBook>();
          // Colocar los externos primero si coinciden con la búsqueda
          created.forEach((b) => map.set(b.id, b));
          localResults.forEach((b) => {
            if (!map.has(b.id)) map.set(b.id, b);
          });
          setSearchResults(Array.from(map.values()));
          return;
        }
      }

      setSearchResults(localResults);
    } catch (err: any) {
      if (err?.name !== 'AbortError') {
        console.error('Search error', err);
      }
    } finally {
      setIsSearching(false);
      setSearchSource('');
    }
  };

  useEffect(() => {
    const controller = new AbortController();
    const run = () => {
      setOffset(0);
      handleSearch(search.trim(), 0, controller.signal);
    };
    const t = setTimeout(run, 400);
    return () => {
      clearTimeout(t);
      controller.abort();
    };
  }, [search, token]);

  const handleAddBookToShelf = async () => {
    if (!selectedBook || !token) return;
    setIsSubmitting(true);
    try {
      const payload = {
        book_id: selectedBook.id,
        is_digital: format === 'digital',
        is_read: statusChoice === 'read',
        wishlist: statusChoice === 'wishlist',
        owned: true,
        rating: userRating,
      };

      const res = await fetch(`${apiUrl}/api/v1/books/user/books/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(payload),
      });

      if (res.ok) {
        setConfirmOpen(false);
        navigate('/library');
      } else {
        const err = await res.json().catch(() => ({}));
        alert(err.detail || 'El libro ya está en tu biblioteca o hubo un error.');
      }
    } catch (e) {
      console.error(e);
      alert('Error de conexión al guardar el libro.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCreateManual = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!manualTitle.trim() || !token) return;
    setManualLoading(true);

    try {
      let authorId: number | null = null;
      if (manualAuthor.trim()) {
        const authRes = await fetch(`${apiUrl}/api/v1/books/authors/`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ name: manualAuthor.trim() }),
        });
        if (authRes.ok) {
          const authData = await authRes.json();
          authorId = authData.id;
        }
      }

      const formData = new FormData();
      formData.append('title', manualTitle.trim());
      if (authorId) formData.append('author_id', String(authorId));
      if (manualIsbn.trim()) formData.append('isbn', manualIsbn.trim());
      if (manualDesc.trim()) formData.append('description', manualDesc.trim());
      if (manualDate) formData.append('published_date', manualDate);
      if (manualCover) formData.append('cover', manualCover);

      const bookRes = await fetch(`${apiUrl}/api/v1/books/`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });

      if (bookRes.ok) {
        const newBook = await bookRes.json();
        // Añadir automáticamente a la biblioteca
        await fetch(`${apiUrl}/api/v1/books/user/books/`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            book_id: newBook.id,
            is_digital: false,
            is_read: false,
            owned: true,
          }),
        });

        navigate(`/books/${newBook.id}`);
      } else {
        alert('Error al crear el libro.');
      }
    } catch (err) {
      console.error(err);
      alert('Error al guardar el libro.');
    } finally {
      setManualLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Encabezado */}
      <div className="bg-white dark:bg-slate-800 p-6 rounded-3xl border border-slate-200/80 dark:border-slate-700 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-white tracking-tight flex items-center gap-2">
            <span>✨</span>
            <span>Añadir a mi Biblioteca</span>
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            Busca en millones de libros externos o cataloga tus propias ediciones.
          </p>
        </div>

        {/* Pestañas */}
        <div className="flex bg-slate-100 dark:bg-slate-700/60 p-1.5 rounded-2xl">
          <button
            onClick={() => setActiveTab('search')}
            className={`px-4 py-2 rounded-xl text-xs font-bold transition-all ${
              activeTab === 'search'
                ? 'bg-white dark:bg-slate-800 text-teal-700 dark:text-teal-300 shadow-sm'
                : 'text-slate-600 dark:text-slate-400 hover:text-slate-900'
            }`}
          >
            🔍 Búsqueda Inteligente
          </button>
          <button
            onClick={() => setActiveTab('manual')}
            className={`px-4 py-2 rounded-xl text-xs font-bold transition-all ${
              activeTab === 'manual'
                ? 'bg-white dark:bg-slate-800 text-teal-700 dark:text-teal-300 shadow-sm'
                : 'text-slate-600 dark:text-slate-400 hover:text-slate-900'
            }`}
          >
            ✍️ Creación Manual
          </button>
        </div>
      </div>

      {activeTab === 'search' ? (
        <div className="space-y-6">
          {/* Barra de Búsqueda */}
          <div className="bg-white dark:bg-slate-800 p-6 rounded-3xl border border-slate-200/80 dark:border-slate-700 shadow-sm space-y-4">
            <div className="relative">
              <span className="absolute inset-y-0 left-0 flex items-center pl-4 text-xl text-slate-400">
                🔍
              </span>
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Escribe el título, autor o ISBN (ej. Cien años de soledad, Stephen King, 9788497592208)..."
                className="w-full pl-12 pr-4 py-3.5 text-base rounded-2xl border border-slate-200 dark:border-slate-700 bg-slate-50/70 dark:bg-slate-700/50 dark:text-white focus:ring-2 focus:ring-teal-500 focus:border-teal-500 shadow-inner"
              />
              {isSearching && (
                <div className="absolute inset-y-0 right-0 flex items-center pr-4">
                  <Spinner size="sm" color="info" />
                </div>
              )}
            </div>

            {searchSource && (
              <p className="text-xs text-teal-600 dark:text-teal-400 font-medium flex items-center gap-1.5 animate-pulse">
                <span>⚡</span>
                <span>{searchSource}</span>
              </p>
            )}

            {search.trim().length >= 2 && !isSearching && (
              <div className="flex justify-end">
                <button
                  type="button"
                  onClick={() => handleSearch(search.trim(), 0, undefined, true)}
                  className="text-xs text-teal-600 dark:text-teal-400 hover:text-teal-700 dark:hover:text-teal-300 font-semibold underline flex items-center gap-1"
                >
                  <span>🌐</span>
                  <span>¿No ves la edición exacta? Buscar en Google Books, OpenLibrary y Wikipedia</span>
                </button>
              </div>
            )}
          </div>

          {/* Resultados */}
          {searchResults.length > 0 ? (
            <div className="space-y-3">
              <h3 className="text-sm font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 px-1">
                Resultados encontrados ({searchResults.length})
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {searchResults.map((book) => (
                  <div
                    key={book.id}
                    className="bg-white dark:bg-slate-800 p-4 rounded-2xl border border-slate-200/80 dark:border-slate-700 shadow-sm hover:shadow-md transition-all flex gap-4"
                  >
                    <div className="w-20 h-28 rounded-xl overflow-hidden bg-slate-100 dark:bg-slate-700 shrink-0 shadow-sm">
                      {book.cover ? (
                        <img
                          src={resolveMediaUrl(book.cover)}
                          alt={book.title}
                          className="w-full h-full object-cover"
                          loading="lazy"
                        />
                      ) : (
                        <div className="w-full h-full flex items-center justify-center p-2 text-center text-[10px] font-semibold text-slate-400">
                          {book.title}
                        </div>
                      )}
                    </div>

                    <div className="flex-1 min-w-0 flex flex-col justify-between">
                      <div>
                        <h4 className="font-bold text-sm text-slate-900 dark:text-white truncate">
                          {book.title}
                        </h4>
                        <p className="text-xs text-slate-500 dark:text-slate-400 truncate mt-0.5">
                          {book.author?.name || 'Autor desconocido'}
                        </p>
                        {book.published_date && (
                          <span className="inline-block text-[11px] text-slate-400 mt-1">
                            Año: {new Date(book.published_date).getFullYear() || book.published_date}
                          </span>
                        )}
                        {book.categories && book.categories.length > 0 && (
                          <div className="flex flex-wrap gap-1 mt-1.5">
                            {book.categories.slice(0, 3).map((c: any) => (
                              <span
                                key={c.id || c.name}
                                className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-teal-50 text-teal-700 dark:bg-teal-900/30 dark:text-teal-300 border border-teal-100 dark:border-teal-800/40"
                              >
                                {c.name}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>

                      <div className="pt-2 flex items-center gap-2">
                        <button
                          onClick={() => {
                            setSelectedBook(book);
                            setConfirmOpen(true);
                          }}
                          className="bg-teal-600 hover:bg-teal-700 text-white font-bold text-xs px-3 py-1.5 rounded-xl transition-colors shadow-sm shadow-teal-600/20"
                        >
                          + Añadir a mi estantería
                        </button>
                        <button
                          onClick={() => navigate(`/books/${book.id}`)}
                          className="text-xs text-slate-500 hover:text-teal-600 font-medium hover:underline"
                        >
                          Ficha
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : search.length >= 2 && !isSearching ? (
            <div className="bg-white dark:bg-slate-800 p-10 rounded-3xl text-center border border-slate-200/80 dark:border-slate-700">
              <span className="text-3xl">🔎</span>
              <h3 className="font-bold text-base text-slate-800 dark:text-white mt-2">
                No se encontraron resultados
              </h3>
              <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
                No encontramos "{search}" en Google Books ni Wikipedia. Puedes añadirlo manualmente.
              </p>
              <button
                onClick={() => {
                  setManualTitle(search);
                  setActiveTab('manual');
                }}
                className="mt-4 bg-teal-600 hover:bg-teal-700 text-white font-bold text-xs px-4 py-2 rounded-xl transition-all shadow-md"
              >
                Crear libro manualmente
              </button>
            </div>
          ) : null}
        </div>
      ) : (
        /* ── Formulario Manual ── */
        <div className="bg-white dark:bg-slate-800 p-6 sm:p-8 rounded-3xl border border-slate-200/80 dark:border-slate-700 shadow-sm">
          <form onSubmit={handleCreateManual} className="space-y-4 max-w-xl mx-auto">
            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300 mb-1.5">
                Título del Libro *
              </label>
              <input
                type="text"
                required
                value={manualTitle}
                onChange={(e) => setManualTitle(e.target.value)}
                placeholder="Ej. El Señor de los Anillos"
                className="w-full text-sm rounded-xl border border-slate-300 dark:border-slate-600 bg-slate-50 dark:bg-slate-700 dark:text-white py-2.5 px-3.5 focus:ring-teal-500"
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300 mb-1.5">
                  Autor
                </label>
                <input
                  type="text"
                  value={manualAuthor}
                  onChange={(e) => setManualAuthor(e.target.value)}
                  placeholder="Ej. J.R.R. Tolkien"
                  className="w-full text-sm rounded-xl border border-slate-300 dark:border-slate-600 bg-slate-50 dark:bg-slate-700 dark:text-white py-2.5 px-3.5 focus:ring-teal-500"
                />
              </div>
              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300 mb-1.5">
                  ISBN (opcional)
                </label>
                <input
                  type="text"
                  value={manualIsbn}
                  onChange={(e) => setManualIsbn(e.target.value)}
                  placeholder="Ej. 9788445071793"
                  className="w-full text-sm rounded-xl border border-slate-300 dark:border-slate-600 bg-slate-50 dark:bg-slate-700 dark:text-white py-2.5 px-3.5 focus:ring-teal-500"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300 mb-1.5">
                  Fecha de Publicación
                </label>
                <input
                  type="date"
                  value={manualDate}
                  onChange={(e) => setManualDate(e.target.value)}
                  className="w-full text-sm rounded-xl border border-slate-300 dark:border-slate-600 bg-slate-50 dark:bg-slate-700 dark:text-white py-2 px-3 focus:ring-teal-500"
                />
              </div>
              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300 mb-1.5">
                  Portada (Imagen)
                </label>
                <input
                  type="file"
                  accept="image/*"
                  onChange={(e) => setManualCover(e.target.files?.[0] || null)}
                  className="w-full text-xs text-slate-500 file:mr-3 file:py-2 file:px-4 file:rounded-xl file:border-0 file:text-xs file:font-semibold file:bg-teal-50 file:text-teal-700 hover:file:bg-teal-100"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300 mb-1.5">
                Sinopsis o Descripción
              </label>
              <textarea
                rows={4}
                value={manualDesc}
                onChange={(e) => setManualDesc(e.target.value)}
                placeholder="Escribe una breve reseña o sinopsis de la obra..."
                className="w-full text-sm rounded-xl border border-slate-300 dark:border-slate-600 bg-slate-50 dark:bg-slate-700 dark:text-white p-3 focus:ring-teal-500"
              />
            </div>

            <div className="pt-2">
              <button
                type="submit"
                disabled={manualLoading || !manualTitle.trim()}
                className="w-full bg-teal-600 hover:bg-teal-700 text-white font-bold py-3 rounded-xl text-sm transition-all shadow-md shadow-teal-600/20 disabled:opacity-50"
              >
                {manualLoading ? 'Guardando libro...' : 'Guardar y Añadir a mi Biblioteca'}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* ── Modal de Configuración al Añadir a Estantería ── */}
      <Modal show={confirmOpen} onClose={() => setConfirmOpen(false)} size="md" popup>
        <div className="p-6 bg-white dark:bg-slate-800 rounded-2xl space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-100 dark:border-slate-700">
            <h3 className="text-base font-bold text-slate-900 dark:text-white">
              Añadir a mi Biblioteca
            </h3>
            <button
              onClick={() => setConfirmOpen(false)}
              className="text-slate-400 hover:text-slate-600 font-bold"
            >
              ✕
            </button>
          </div>

          {selectedBook && (
            <div className="flex gap-3 items-center p-3 rounded-xl bg-slate-50 dark:bg-slate-700/50">
              {selectedBook.cover ? (
                <img
                  src={resolveMediaUrl(selectedBook.cover)}
                  alt={selectedBook.title}
                  className="w-12 h-16 object-cover rounded shadow"
                />
              ) : (
                <div className="w-12 h-16 bg-teal-600 text-white rounded flex items-center justify-center text-[9px] p-1 text-center font-bold">
                  {selectedBook.title}
                </div>
              )}
              <div className="min-w-0 flex-1">
                <h4 className="font-bold text-sm text-slate-900 dark:text-white truncate">
                  {selectedBook.title}
                </h4>
                <p className="text-xs text-slate-500 dark:text-slate-400 truncate">
                  {selectedBook.author?.name || 'Autor desconocido'}
                </p>
              </div>
            </div>
          )}

          {/* Opciones */}
          <div className="space-y-3 pt-2">
            <div>
              <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1">
                Estado de Lectura
              </label>
              <div className="grid grid-cols-3 gap-2">
                {[
                  { id: 'reading', label: 'Leyendo' },
                  { id: 'read', label: 'Leído' },
                  { id: 'wishlist', label: 'Deseado' },
                ].map((s) => (
                  <button
                    key={s.id}
                    type="button"
                    onClick={() => setStatusChoice(s.id as any)}
                    className={`py-2 text-xs font-bold rounded-xl border transition-all ${
                      statusChoice === s.id
                        ? 'bg-teal-600 text-white border-teal-600 shadow'
                        : 'bg-white dark:bg-slate-700 text-slate-700 dark:text-slate-200 border-slate-200 dark:border-slate-600'
                    }`}
                  >
                    {s.label}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1">
                Formato
              </label>
              <div className="grid grid-cols-2 gap-2">
                {[
                  { id: 'digital', label: '📱 Digital (eBook / Audio)' },
                  { id: 'fisico', label: '📖 Físico (Papel)' },
                ].map((f) => (
                  <button
                    key={f.id}
                    type="button"
                    onClick={() => setFormat(f.id as any)}
                    className={`py-2 text-xs font-bold rounded-xl border transition-all ${
                      format === f.id
                        ? 'bg-teal-600 text-white border-teal-600 shadow'
                        : 'bg-white dark:bg-slate-700 text-slate-700 dark:text-slate-200 border-slate-200 dark:border-slate-600'
                    }`}
                  >
                    {f.label}
                  </button>
                ))}
              </div>
            </div>

            {statusChoice === 'read' && (
              <div>
                <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1">
                  Tu puntuación (opcional)
                </label>
                <select
                  value={userRating || ''}
                  onChange={(e) => setUserRating(e.target.value ? Number(e.target.value) : null)}
                  className="w-full text-xs font-semibold rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-700 py-2 px-3"
                >
                  <option value="">Sin puntuación inicial</option>
                  {[10, 9, 8, 7, 6, 5, 4, 3, 2, 1].map((n) => (
                    <option key={n} value={n}>
                      ⭐ {n}/10
                    </option>
                  ))}
                </select>
              </div>
            )}
          </div>

          <div className="pt-3">
            <button
              onClick={handleAddBookToShelf}
              disabled={isSubmitting}
              className="w-full bg-teal-600 hover:bg-teal-700 text-white font-bold py-2.5 rounded-xl text-sm transition-all shadow-md shadow-teal-600/20 disabled:opacity-50"
            >
              {isSubmitting ? 'Guardando...' : 'Confirmar y Guardar'}
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
