import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Spinner } from 'flowbite-react';
import { useAuthStore } from '../store/auth';
import { resolveMediaUrl } from '../utils/media';

interface BookItem {
  id: number;
  title: string;
  cover?: string;
  author?: { id: number; name: string };
  published_date?: string;
}

interface ReadingListItem {
  id: number;
  book: BookItem;
  position: number;
  notes?: string;
  added_at: string;
}

interface ReadingList {
  id: number;
  name: string;
  slug: string;
  description: string;
  privacy: 'public' | 'followers' | 'private';
  created_at: string;
  updated_at: string;
  user: {
    id: number;
    username: string;
    avatar?: string;
  };
  items: ReadingListItem[];
  items_count: number;
  followers_count: number;
  is_following: boolean;
}

export function ReadingLists() {
  const { token, user: currentUser } = useAuthStore();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const apiUrl = (import.meta as any).env.VITE_API_URL || 'http://localhost:8000';

  const [activeTab, setActiveTab] = useState<'my' | 'explore' | 'followed'>('my');
  const [lists, setLists] = useState<ReadingList[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedList, setSelectedList] = useState<ReadingList | null>(null);

  // Modal Crear / Editar Lista
  const [modalOpen, setModalOpen] = useState(false);
  const [editingList, setEditingList] = useState<ReadingList | null>(null);
  const [formName, setFormName] = useState('');
  const [formDesc, setFormDesc] = useState('');
  const [formPrivacy, setFormPrivacy] = useState<'public' | 'followers' | 'private'>('public');
  const [savingList, setSavingList] = useState(false);

  // Añadir libro buscador
  const [bookSearchQuery, setBookSearchQuery] = useState('');
  const [bookSearchResults, setBookSearchResults] = useState<BookItem[]>([]);
  const [searchingBooks, setSearchingBooks] = useState(false);
  const [addingBook, setAddingBook] = useState(false);

  const fetchLists = async () => {
    setLoading(true);
    try {
      let endpoint = `${apiUrl}/api/v1/books/reading-lists/`;
      if (activeTab === 'my') {
        endpoint += '?my_lists=true';
      } else if (activeTab === 'followed') {
        endpoint += '?followed=true';
      }

      const headers: Record<string, string> = {};
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const res = await fetch(endpoint, { headers });
      if (res.ok) {
        const data = await res.json();
        const results = Array.isArray(data) ? data : data.results || [];
        setLists(results);

        // Si hay un ID seleccionado, sincronizarlo con la versión actualizada
        if (selectedList) {
          const found = results.find((l: ReadingList) => l.id === selectedList.id);
          if (found) setSelectedList(found);
        }
      }
    } catch (err) {
      console.error('Error fetching reading lists:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLists();
  }, [activeTab, token]);

  // Selección de lista por URL param inicial
  useEffect(() => {
    const listId = searchParams.get('id');
    if (listId && lists.length > 0) {
      const found = lists.find((l) => l.id === Number(listId));
      if (found) setSelectedList(found);
    }
  }, [searchParams, lists]);

  const handleOpenCreateModal = () => {
    setEditingList(null);
    setFormName('');
    setFormDesc('');
    setFormPrivacy('public');
    setModalOpen(true);
  };

  const handleOpenEditModal = (list: ReadingList) => {
    setEditingList(list);
    setFormName(list.name);
    setFormDesc(list.description);
    setFormPrivacy(list.privacy);
    setModalOpen(true);
  };

  const handleSaveList = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token || !formName.trim()) return;

    setSavingList(true);
    try {
      const url = editingList
        ? `${apiUrl}/api/v1/books/reading-lists/${editingList.id}/`
        : `${apiUrl}/api/v1/books/reading-lists/`;
      const method = editingList ? 'PATCH' : 'POST';

      const res = await fetch(url, {
        method,
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          name: formName.trim(),
          description: formDesc.trim(),
          privacy: formPrivacy,
        }),
      });

      if (res.ok) {
        setModalOpen(false);
        await fetchLists();
      } else {
        const errData = await res.json().catch(() => ({}));
        alert(errData.detail || 'Error al guardar la lista de lectura.');
      }
    } catch (err) {
      console.error(err);
      alert('Error de conexión al guardar la lista.');
    } finally {
      setSavingList(false);
    }
  };

  const handleDeleteList = async (listId: number) => {
    if (!window.confirm('¿Seguro que deseas eliminar esta lista de lectura?')) return;
    if (!token) return;

    try {
      const res = await fetch(`${apiUrl}/api/v1/books/reading-lists/${listId}/`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        if (selectedList?.id === listId) {
          setSelectedList(null);
        }
        await fetchLists();
      } else {
        alert('No se pudo eliminar la lista.');
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleToggleFollow = async (list: ReadingList) => {
    if (!token) {
      navigate('/login');
      return;
    }

    try {
      const action = list.is_following ? 'unfollow' : 'follow';
      const res = await fetch(`${apiUrl}/api/v1/books/reading-lists/${list.id}/${action}/`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        await fetchLists();
      }
    } catch (err) {
      console.error(err);
    }
  };

  // Buscar libros para añadir
  const handleSearchBooks = async (query: string) => {
    setBookSearchQuery(query);
    if (query.trim().length < 2) {
      setBookSearchResults([]);
      return;
    }

    setSearchingBooks(true);
    try {
      const headers: Record<string, string> = {};
      if (token) headers['Authorization'] = `Bearer ${token}`;
      const res = await fetch(`${apiUrl}/api/v1/books/?search=${encodeURIComponent(query)}`, { headers });
      if (res.ok) {
        const data = await res.json();
        const items = Array.isArray(data) ? data : data.results || [];
        setBookSearchResults(items);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setSearchingBooks(false);
    }
  };

  const handleAddBookToList = async (bookId: number) => {
    if (!selectedList || !token) return;
    setAddingBook(true);
    try {
      const res = await fetch(`${apiUrl}/api/v1/books/reading-lists/${selectedList.id}/add-book/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ book_id: bookId }),
      });
      if (res.ok) {
        setBookSearchQuery('');
        setBookSearchResults([]);
        await fetchLists();
      } else {
        const err = await res.json().catch(() => ({}));
        alert(err.detail || 'No se pudo añadir el libro.');
      }
    } catch (err) {
      console.error(err);
    } finally {
      setAddingBook(false);
    }
  };

  const handleRemoveBookFromList = async (bookId: number) => {
    if (!selectedList || !token) return;
    try {
      const res = await fetch(`${apiUrl}/api/v1/books/reading-lists/${selectedList.id}/remove-book/?book_id=${bookId}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        await fetchLists();
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleMoveBook = async (index: number, direction: 'up' | 'down') => {
    if (!selectedList || !token) return;
    const items = [...selectedList.items];
    const targetIndex = direction === 'up' ? index - 1 : index + 1;
    if (targetIndex < 0 || targetIndex >= items.length) return;

    // Swap positions
    const temp = items[index];
    items[index] = items[targetIndex];
    items[targetIndex] = temp;

    const payload = items.map((it, idx) => ({
      book_id: it.book.id,
      position: idx + 1,
    }));

    try {
      const res = await fetch(`${apiUrl}/api/v1/books/reading-lists/${selectedList.id}/reorder/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ items: payload }),
      });
      if (res.ok) {
        const updated = await res.json();
        setSelectedList(updated);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const isOwner = (list: ReadingList) => currentUser && list.user.id === currentUser.id;

  return (
    <div className="max-w-6xl mx-auto space-y-8 p-4 sm:p-6">
      {/* Cabecera */}
      <div className="bg-white dark:bg-slate-800 p-6 sm:p-8 rounded-3xl border border-slate-200/80 dark:border-slate-700 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-white tracking-tight flex items-center gap-2">
            <span>📚</span>
            <span>Listas de Lectura</span>
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            Organiza, comparte y descubre colecciones temáticas de libros (Favoritos, Por leer 2027, etc.).
          </p>
        </div>

        {token && (
          <button
            onClick={handleOpenCreateModal}
            className="bg-teal-600 hover:bg-teal-700 text-white font-bold text-sm px-5 py-2.5 rounded-2xl transition-all shadow-md shadow-teal-600/20 flex items-center justify-center gap-2 shrink-0"
          >
            <span>+</span>
            <span>Crear Lista</span>
          </button>
        )}
      </div>

      {/* Pestañas de navegación */}
      <div className="flex bg-slate-100 dark:bg-slate-800 p-1.5 rounded-2xl w-fit">
        <button
          onClick={() => {
            setActiveTab('my');
            setSelectedList(null);
          }}
          className={`px-5 py-2 rounded-xl text-xs font-bold transition-all ${
            activeTab === 'my'
              ? 'bg-white dark:bg-slate-700 text-teal-700 dark:text-teal-300 shadow-sm'
              : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
          }`}
        >
          📖 Mis Listas
        </button>
        <button
          onClick={() => {
            setActiveTab('explore');
            setSelectedList(null);
          }}
          className={`px-5 py-2 rounded-xl text-xs font-bold transition-all ${
            activeTab === 'explore'
              ? 'bg-white dark:bg-slate-700 text-teal-700 dark:text-teal-300 shadow-sm'
              : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
          }`}
        >
          🌍 Explorar Públicas
        </button>
        {token && (
          <button
            onClick={() => {
              setActiveTab('followed');
              setSelectedList(null);
            }}
            className={`px-5 py-2 rounded-xl text-xs font-bold transition-all ${
              activeTab === 'followed'
                ? 'bg-white dark:bg-slate-700 text-teal-700 dark:text-teal-300 shadow-sm'
                : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
            }`}
          >
            ⭐ Siguiendo
          </button>
        )}
      </div>

      {/* Contenido principal: Grid de Listas o Detalle */}
      {loading ? (
        <div className="text-center py-16">
          <Spinner size="xl" />
          <p className="text-sm text-slate-400 mt-3 font-medium">Cargando listas de lectura...</p>
        </div>
      ) : selectedList ? (
        /* Vista de Detalle de Lista */
        <div className="space-y-6">
          <button
            onClick={() => setSelectedList(null)}
            className="text-xs font-semibold text-teal-600 hover:text-teal-700 dark:text-teal-400 flex items-center gap-1.5 transition-colors"
          >
            ← Volver a las listas
          </button>

          <div className="bg-white dark:bg-slate-800 p-6 sm:p-8 rounded-3xl border border-slate-200/80 dark:border-slate-700 shadow-sm space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
              <div>
                <div className="flex items-center gap-3">
                  <h2 className="text-2xl font-bold text-slate-900 dark:text-white">
                    {selectedList.name}
                  </h2>
                  <span
                    className={`text-[11px] font-semibold px-2.5 py-0.5 rounded-full ${
                      selectedList.privacy === 'public'
                        ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300'
                        : selectedList.privacy === 'followers'
                        ? 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300'
                        : 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300'
                    }`}
                  >
                    {selectedList.privacy === 'public'
                      ? 'Pública'
                      : selectedList.privacy === 'followers'
                      ? 'Solo seguidores'
                      : 'Privada'}
                  </span>
                </div>
                {selectedList.description && (
                  <p className="text-sm text-slate-600 dark:text-slate-300 mt-2 max-w-2xl">
                    {selectedList.description}
                  </p>
                )}
                <div className="flex items-center gap-4 text-xs text-slate-400 mt-3">
                  <span>Por @{selectedList.user.username}</span>
                  <span>•</span>
                  <span>{selectedList.items?.length || 0} libros</span>
                  <span>•</span>
                  <span>{selectedList.followers_count || 0} seguidores</span>
                </div>
              </div>

              <div className="flex items-center gap-2">
                {!isOwner(selectedList) ? (
                  <button
                    onClick={() => handleToggleFollow(selectedList)}
                    className={`text-xs font-bold px-4 py-2 rounded-xl transition-all ${
                      selectedList.is_following
                        ? 'bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-300 hover:bg-red-50 hover:text-red-600'
                        : 'bg-teal-600 hover:bg-teal-700 text-white shadow-sm shadow-teal-600/20'
                    }`}
                  >
                    {selectedList.is_following ? 'Siguiendo ✓' : '+ Seguir Lista'}
                  </button>
                ) : (
                  <>
                    <button
                      onClick={() => handleOpenEditModal(selectedList)}
                      className="text-xs font-bold px-3.5 py-2 rounded-xl bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-200 hover:bg-slate-200 transition-colors"
                    >
                      ✏️ Editar
                    </button>
                    <button
                      onClick={() => handleDeleteList(selectedList.id)}
                      className="text-xs font-bold px-3.5 py-2 rounded-xl bg-red-50 text-red-600 hover:bg-red-100 transition-colors"
                    >
                      🗑️ Eliminar
                    </button>
                  </>
                )}
              </div>
            </div>

            {/* Añadir libro a la lista (Solo propietario) */}
            {isOwner(selectedList) && (
              <div className="border-t border-slate-100 dark:border-slate-700 pt-6">
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300 mb-2">
                  Añadir libro a esta lista
                </label>
                <div className="relative max-w-md">
                  <input
                    type="text"
                    value={bookSearchQuery}
                    onChange={(e) => handleSearchBooks(e.target.value)}
                    placeholder="Buscar por título o autor..."
                    className="w-full text-sm rounded-xl border border-slate-300 dark:border-slate-600 bg-slate-50 dark:bg-slate-700 dark:text-white py-2 px-3.5 focus:ring-teal-500"
                  />
                  {searchingBooks && (
                    <div className="absolute right-3 top-2.5">
                      <Spinner size="sm" />
                    </div>
                  )}

                  {bookSearchResults.length > 0 && (
                    <div className="absolute z-10 w-full mt-1 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-2xl shadow-xl max-h-60 overflow-y-auto divide-y divide-slate-100 dark:divide-slate-700">
                      {bookSearchResults.map((book) => (
                        <div
                          key={book.id}
                          className="p-2.5 flex items-center justify-between hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors"
                        >
                          <div className="flex items-center gap-3 min-w-0">
                            <div className="w-8 h-11 rounded bg-slate-100 dark:bg-slate-700 overflow-hidden shrink-0">
                              {book.cover ? (
                                <img
                                  src={resolveMediaUrl(book.cover)}
                                  alt={book.title}
                                  className="w-full h-full object-cover"
                                />
                              ) : (
                                <div className="w-full h-full flex items-center justify-center text-[8px] text-slate-400">
                                  📚
                                </div>
                              )}
                            </div>
                            <div className="truncate">
                              <p className="text-xs font-bold text-slate-800 dark:text-white truncate">
                                {book.title}
                              </p>
                              <p className="text-[10px] text-slate-400 truncate">
                                {book.author?.name || 'Autor desconocido'}
                              </p>
                            </div>
                          </div>
                          <button
                            disabled={addingBook}
                            onClick={() => handleAddBookToList(book.id)}
                            className="bg-teal-600 hover:bg-teal-700 text-white font-bold text-xs px-2.5 py-1 rounded-lg shrink-0 ml-2"
                          >
                            + Añadir
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Listado de libros ordenados */}
            <div className="border-t border-slate-100 dark:border-slate-700 pt-6">
              <h3 className="text-sm font-bold text-slate-800 dark:text-white mb-4">
                Libros en la lista ({selectedList.items?.length || 0})
              </h3>

              {!selectedList.items || selectedList.items.length === 0 ? (
                <div className="p-8 text-center bg-slate-50 dark:bg-slate-900/40 rounded-2xl text-slate-400 text-xs">
                  Esta lista aún no contiene ningún libro.
                </div>
              ) : (
                <div className="space-y-3">
                  {selectedList.items.map((item, idx) => (
                    <div
                      key={item.id}
                      className="p-3.5 bg-slate-50 dark:bg-slate-700/40 rounded-2xl border border-slate-100 dark:border-slate-700/60 flex items-center justify-between gap-4 group"
                    >
                      <div className="flex items-center gap-3.5 min-w-0">
                        <span className="w-6 text-center font-bold text-xs text-slate-400">
                          #{idx + 1}
                        </span>
                        <div
                          onClick={() => navigate(`/books/${item.book.id}`)}
                          className="w-12 h-16 rounded-xl bg-slate-200 dark:bg-slate-600 overflow-hidden shrink-0 shadow-sm cursor-pointer"
                        >
                          {item.book.cover ? (
                            <img
                              src={resolveMediaUrl(item.book.cover)}
                              alt={item.book.title}
                              className="w-full h-full object-cover group-hover:scale-105 transition-transform"
                            />
                          ) : (
                            <div className="w-full h-full flex items-center justify-center text-[10px] text-slate-400">
                              📚
                            </div>
                          )}
                        </div>
                        <div className="min-w-0">
                          <h4
                            onClick={() => navigate(`/books/${item.book.id}`)}
                            className="font-bold text-sm text-slate-900 dark:text-white truncate cursor-pointer hover:text-teal-600"
                          >
                            {item.book.title}
                          </h4>
                          <p className="text-xs text-slate-500 dark:text-slate-400 truncate mt-0.5">
                            {item.book.author?.name || 'Autor desconocido'}
                          </p>
                          {item.notes && (
                            <p className="text-[11px] text-slate-400 italic mt-1 line-clamp-1">
                              "{item.notes}"
                            </p>
                          )}
                        </div>
                      </div>

                      {isOwner(selectedList) && (
                        <div className="flex items-center gap-1.5 shrink-0">
                          <button
                            disabled={idx === 0}
                            onClick={() => handleMoveBook(idx, 'up')}
                            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 dark:hover:text-white disabled:opacity-30"
                            title="Subir posición"
                          >
                            ▲
                          </button>
                          <button
                            disabled={idx === selectedList.items.length - 1}
                            onClick={() => handleMoveBook(idx, 'down')}
                            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 dark:hover:text-white disabled:opacity-30"
                            title="Bajar posición"
                          >
                            ▼
                          </button>
                          <button
                            onClick={() => handleRemoveBookFromList(item.book.id)}
                            className="p-1.5 text-xs text-red-500 hover:text-red-700 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg ml-1"
                            title="Quitar de la lista"
                          >
                            ✕
                          </button>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      ) : (
        /* Vista de Grid de Listas */
        <div>
          {lists.length === 0 ? (
            <div className="bg-white dark:bg-slate-800 p-12 rounded-3xl text-center border border-slate-200/80 dark:border-slate-700 space-y-3">
              <span className="text-4xl">📂</span>
              <h3 className="font-bold text-base text-slate-800 dark:text-white">
                No hay listas disponibles
              </h3>
              <p className="text-xs text-slate-500 max-w-sm mx-auto">
                {activeTab === 'my'
                  ? 'Aún no has creado ninguna lista de lectura. ¡Crea la primera para organizar tus libros!'
                  : activeTab === 'followed'
                  ? 'No sigues ninguna lista de lectura aún.'
                  : 'Aún no hay listas públicas compartidas por la comunidad.'}
              </p>
              {activeTab === 'my' && token && (
                <button
                  onClick={handleOpenCreateModal}
                  className="mt-3 bg-teal-600 hover:bg-teal-700 text-white font-bold text-xs px-4 py-2 rounded-xl transition-all shadow-md"
                >
                  Crear mi primera lista
                </button>
              )}
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
              {lists.map((list) => (
                <div
                  key={list.id}
                  onClick={() => setSelectedList(list)}
                  className="group bg-white dark:bg-slate-800 p-6 rounded-3xl border border-slate-200/80 dark:border-slate-700 shadow-sm hover:shadow-lg transition-all duration-200 cursor-pointer flex flex-col justify-between"
                >
                  <div>
                    <div className="flex items-center justify-between gap-2 mb-2">
                      <span
                        className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                          list.privacy === 'public'
                            ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300'
                            : list.privacy === 'followers'
                            ? 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300'
                            : 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300'
                        }`}
                      >
                        {list.privacy === 'public'
                          ? 'Pública'
                          : list.privacy === 'followers'
                          ? 'Seguidores'
                          : 'Privada'}
                      </span>
                      <span className="text-[11px] text-slate-400">
                        {list.items_count || 0} {list.items_count === 1 ? 'libro' : 'libros'}
                      </span>
                    </div>

                    <h3 className="font-bold text-base text-slate-900 dark:text-white group-hover:text-teal-600 transition-colors truncate">
                      {list.name}
                    </h3>
                    <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 line-clamp-2 min-h-[32px]">
                      {list.description || 'Sin descripción.'}
                    </p>

                    {/* Previsualización en miniatura de portadas */}
                    <div className="flex items-center gap-1.5 mt-4 min-h-[48px]">
                      {list.items && list.items.length > 0 ? (
                        list.items.slice(0, 4).map((it) => (
                          <div
                            key={it.id}
                            className="w-8 h-12 rounded-lg bg-slate-100 dark:bg-slate-700 overflow-hidden shadow-sm shrink-0 border border-white dark:border-slate-800"
                          >
                            {it.book?.cover ? (
                              <img
                                src={resolveMediaUrl(it.book.cover)}
                                alt={it.book.title}
                                className="w-full h-full object-cover"
                              />
                            ) : (
                              <div className="w-full h-full flex items-center justify-center text-[7px] text-slate-400">
                                📖
                              </div>
                            )}
                          </div>
                        ))
                      ) : (
                        <div className="text-[11px] text-slate-400 italic">Lista vacía</div>
                      )}
                      {list.items && list.items.length > 4 && (
                        <span className="text-[10px] font-bold text-slate-400 ml-1">
                          +{list.items.length - 4} más
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="border-t border-slate-100 dark:border-slate-700/60 pt-3 mt-4 flex items-center justify-between text-xs text-slate-400">
                    <span>@{list.user.username}</span>
                    <span>{list.followers_count || 0} seguidores</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Modal Crear / Editar Lista */}
      {modalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
          <div className="bg-white dark:bg-slate-800 rounded-3xl p-6 sm:p-8 max-w-md w-full shadow-2xl border border-slate-200 dark:border-slate-700 space-y-5">
            <div className="flex items-center justify-between">
              <h3 className="font-bold text-lg text-slate-900 dark:text-white">
                {editingList ? 'Editar Lista de Lectura' : 'Nueva Lista de Lectura'}
              </h3>
              <button
                onClick={() => setModalOpen(false)}
                className="text-slate-400 hover:text-slate-600 dark:hover:text-white text-sm"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleSaveList} className="space-y-4">
              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300 mb-1">
                  Nombre de la lista *
                </label>
                <input
                  type="text"
                  required
                  value={formName}
                  onChange={(e) => setFormName(e.target.value)}
                  placeholder="Ej. Favoritos, Clásicos, Vacaciones..."
                  className="w-full text-sm rounded-xl border border-slate-300 dark:border-slate-600 bg-slate-50 dark:bg-slate-700 dark:text-white py-2 px-3 focus:ring-teal-500"
                />
              </div>

              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300 mb-1">
                  Descripción (opcional)
                </label>
                <textarea
                  rows={3}
                  value={formDesc}
                  onChange={(e) => setFormDesc(e.target.value)}
                  placeholder="Explica de qué trata esta colección..."
                  className="w-full text-sm rounded-xl border border-slate-300 dark:border-slate-600 bg-slate-50 dark:bg-slate-700 dark:text-white py-2 px-3 focus:ring-teal-500"
                />
              </div>

              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300 mb-1">
                  Privacidad
                </label>
                <select
                  value={formPrivacy}
                  onChange={(e) => setFormPrivacy(e.target.value as any)}
                  className="w-full text-sm rounded-xl border border-slate-300 dark:border-slate-600 bg-slate-50 dark:bg-slate-700 dark:text-white py-2 px-3 focus:ring-teal-500"
                >
                  <option value="public">Pública (Visible para todos)</option>
                  <option value="followers">Solo Seguidores</option>
                  <option value="private">Privada (Solo tú)</option>
                </select>
              </div>

              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setModalOpen(false)}
                  className="text-xs font-bold px-4 py-2 rounded-xl text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-700 transition-colors"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={savingList}
                  className="bg-teal-600 hover:bg-teal-700 text-white font-bold text-xs px-5 py-2.5 rounded-xl transition-all shadow-md"
                >
                  {savingList ? 'Guardando...' : editingList ? 'Actualizar' : 'Crear'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
