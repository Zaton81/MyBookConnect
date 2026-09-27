import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Spinner } from 'flowbite-react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useAuthStore } from '../../../store/auth';
import { resolveMediaUrl } from '../../../utils/media';
import { ReportModal } from '../../moderation';
import { readingListSchema, ReadingListFormData } from '../schemas/listSchemas';

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
  comments_count?: number;
  views_count?: number;
  is_following: boolean;
}

interface ReadingListComment {
  id: number;
  user: {
    id: number;
    username: string;
    avatar?: string;
  };
  content: string;
  created_at: string;
  can_delete: boolean;
}

export function ReadingLists() {
  const { token, user: currentUser } = useAuthStore();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const apiUrl = (import.meta as any).env.VITE_API_URL || 'http://localhost:8000';

  const [activeTab, setActiveTab] = useState<'my' | 'explore' | 'followed'>('my');
  const [lists, setLists] = useState<ReadingList[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedList, setSelectedList] = useState<ReadingList | null>(null);

  // Estados de comentarios (Fase 21)
  const [comments, setComments] = useState<ReadingListComment[]>([]);
  const [loadingComments, setLoadingComments] = useState(false);
  const [newComment, setNewComment] = useState('');
  const [submittingComment, setSubmittingComment] = useState(false);
  const [cloningList, setCloningList] = useState(false);
  const [shareToast, setShareToast] = useState(false);

  // Modal Crear / Editar Lista
  const [modalOpen, setModalOpen] = useState(false);
  const [editingList, setEditingList] = useState<ReadingList | null>(null);
  const [savingList, setSavingList] = useState(false);
  const [reportingList, setReportingList] = useState<ReadingList | null>(null);

  const {
    register: registerList,
    handleSubmit: handleSubmitList,
    reset: resetListForm,
    formState: { errors: listErrors },
  } = useForm<ReadingListFormData>({
    resolver: zodResolver(readingListSchema),
    defaultValues: {
      name: '',
      description: '',
      privacy: 'public',
    },
  });

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
        const items = Array.isArray(data) ? data : data.results || [];
        setLists(items);
        if (selectedList) {
          const updated = items.find((l: ReadingList) => l.id === selectedList.id);
          if (updated) setSelectedList(updated);
        }
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLists();
  }, [activeTab, token]);

  // Cargar comentarios al seleccionar una lista
  const fetchComments = async (listId: number) => {
    setLoadingComments(true);
    try {
      const headers: Record<string, string> = {};
      if (token) headers['Authorization'] = `Bearer ${token}`;
      const res = await fetch(`${apiUrl}/api/v1/books/reading-lists/${listId}/comments/`, {
        headers,
      });
      if (res.ok) {
        const data = await res.json();
        setComments(Array.isArray(data) ? data : []);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoadingComments(false);
    }
  };

  useEffect(() => {
    if (selectedList) {
      fetchComments(selectedList.id);
    } else {
      setComments([]);
    }
  }, [selectedList?.id]);

  const handleAddComment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedList || !token || !newComment.trim()) return;
    setSubmittingComment(true);
    try {
      const res = await fetch(`${apiUrl}/api/v1/books/reading-lists/${selectedList.id}/comments/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ content: newComment.trim() }),
      });
      if (res.ok) {
        setNewComment('');
        await fetchComments(selectedList.id);
        await fetchLists();
      } else {
        const err = await res.json().catch(() => ({}));
        alert(err.detail || 'Error al enviar el comentario.');
      }
    } catch (e) {
      console.error(e);
    } finally {
      setSubmittingComment(false);
    }
  };

  const handleDeleteComment = async (commentId: number) => {
    if (!selectedList || !token) return;
    try {
      const res = await fetch(
        `${apiUrl}/api/v1/books/reading-lists/${selectedList.id}/comments/${commentId}/`,
        {
          method: 'DELETE',
          headers: { Authorization: `Bearer ${token}` },
        }
      );
      if (res.ok) {
        await fetchComments(selectedList.id);
        await fetchLists();
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleCloneList = async (list: ReadingList) => {
    if (!token) {
      navigate('/login');
      return;
    }
    setCloningList(true);
    try {
      const res = await fetch(`${apiUrl}/api/v1/books/reading-lists/${list.id}/clone/`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const cloned = await res.json();
        alert(`¡Lista duplicada con éxito como "${cloned.name}" en tu biblioteca!`);
        setActiveTab('my');
        await fetchLists();
        setSelectedList(cloned);
      } else {
        const err = await res.json().catch(() => ({}));
        alert(err.detail || 'No se pudo duplicar la lista.');
      }
    } catch (e) {
      console.error(e);
    } finally {
      setCloningList(false);
    }
  };

  const handleShareList = (list: ReadingList) => {
    const shareUrl = `${window.location.origin}/reading-lists?id=${list.id}`;
    if (navigator.clipboard) {
      navigator.clipboard.writeText(shareUrl);
      setShareToast(true);
      setTimeout(() => setShareToast(false), 3000);
    } else {
      prompt('Copia el enlace a esta lista:', shareUrl);
    }
  };

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
    resetListForm({
      name: '',
      description: '',
      privacy: 'public',
    });
    setModalOpen(true);
  };

  const handleOpenEditModal = (list: ReadingList) => {
    setEditingList(list);
    resetListForm({
      name: list.name,
      description: list.description || '',
      privacy: list.privacy,
    });
    setModalOpen(true);
  };

  const onSubmitList = async (data: ReadingListFormData) => {
    if (!token) return;

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
          name: data.name.trim(),
          description: data.description?.trim() || '',
          privacy: data.privacy,
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
      const res = await fetch(`${apiUrl}/api/v1/books/?search=${encodeURIComponent(query)}`, {
        headers,
      });
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
      const res = await fetch(
        `${apiUrl}/api/v1/books/reading-lists/${selectedList.id}/remove-book/?book_id=${bookId}`,
        {
          method: 'DELETE',
          headers: { Authorization: `Bearer ${token}` },
        }
      );
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
            Organiza, comparte y descubre colecciones temáticas de libros (Favoritos, Por leer 2027,
            etc.).
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
                <div className="flex flex-wrap items-center gap-3 text-xs text-slate-500 dark:text-slate-400 mt-3 font-medium">
                  <span>Por @{selectedList.user.username}</span>
                  <span>•</span>
                  <span>
                    📚 {selectedList.items?.length || selectedList.items_count || 0} libros
                  </span>
                  <span>•</span>
                  <span>👥 {selectedList.followers_count || 0} seguidores</span>
                  <span>•</span>
                  <span>👁️ {selectedList.views_count || 0} aperturas</span>
                  <span>•</span>
                  <span>💬 {selectedList.comments_count || comments.length || 0} comentarios</span>
                </div>
              </div>

              <div className="flex flex-wrap items-center gap-2">
                {/* Botón Compartir */}
                <button
                  onClick={() => handleShareList(selectedList)}
                  className="text-xs font-bold px-3 py-2 rounded-xl bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-200 hover:bg-slate-200 transition-colors flex items-center gap-1.5 cursor-pointer"
                  title="Copiar enlace permanente a esta lista"
                >
                  <span>🔗</span>
                  <span>Compartir</span>
                </button>

                {!isOwner(selectedList) ? (
                  <>
                    {/* Botón Duplicar lista */}
                    <button
                      disabled={cloningList}
                      onClick={() => handleCloneList(selectedList)}
                      className="text-xs font-bold px-3 py-2 rounded-xl bg-teal-50 dark:bg-teal-900/30 text-teal-700 dark:text-teal-300 hover:bg-teal-100 dark:hover:bg-teal-900/50 transition-colors flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
                      title="Guardar una copia exacta de esta lista en mi biblioteca"
                    >
                      <span>📑</span>
                      <span>{cloningList ? 'Duplicando...' : 'Guardar copia'}</span>
                    </button>

                    <button
                      onClick={() => handleToggleFollow(selectedList)}
                      className={`text-xs font-bold px-4 py-2 rounded-xl transition-all cursor-pointer ${
                        selectedList.is_following
                          ? 'bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-300 hover:bg-red-50 hover:text-red-600'
                          : 'bg-teal-600 hover:bg-teal-700 text-white shadow-sm shadow-teal-600/20'
                      }`}
                    >
                      {selectedList.is_following ? 'Siguiendo ✓' : '+ Seguir Lista'}
                    </button>
                    <button
                      onClick={() => setReportingList(selectedList)}
                      className="text-xs font-semibold px-3 py-2 rounded-xl bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/30 transition-colors cursor-pointer"
                      title="Denunciar lista a moderación"
                    >
                      🚩 Denunciar
                    </button>
                  </>
                ) : (
                  <>
                    <button
                      onClick={() => handleOpenEditModal(selectedList)}
                      className="text-xs font-bold px-3.5 py-2 rounded-xl bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-200 hover:bg-slate-200 transition-colors cursor-pointer"
                    >
                      ✏️ Editar
                    </button>
                    <button
                      onClick={() => handleDeleteList(selectedList.id)}
                      className="text-xs font-bold px-3.5 py-2 rounded-xl bg-red-50 text-red-600 hover:bg-red-100 transition-colors cursor-pointer"
                    >
                      🗑️ Eliminar
                    </button>
                  </>
                )}
              </div>
            </div>

            {/* Toast de compartir copiado */}
            {shareToast && (
              <div className="p-3 bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800 text-emerald-700 dark:text-emerald-300 text-xs font-bold rounded-2xl flex items-center justify-between">
                <span>
                  ✓ ¡Enlace copiado al portapapeles! Ya puedes compartirlo con otros lectores.
                </span>
                <button
                  onClick={() => setShareToast(false)}
                  className="text-emerald-500 font-bold ml-2"
                >
                  ✕
                </button>
              </div>
            )}

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

            {/* SECCIÓN DE DEBATE Y COMENTARIOS DE LA LISTA (Fase 21) */}
            <div className="border-t border-slate-100 dark:border-slate-700 pt-6 space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="font-bold text-base text-slate-900 dark:text-white flex items-center gap-2">
                  <span>💬</span>
                  <span>Debate y Comentarios</span>
                  <span className="text-xs px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 font-bold">
                    {comments.length}
                  </span>
                </h3>
              </div>

              {/* Formulario para añadir comentario */}
              {token ? (
                <form onSubmit={handleAddComment} className="flex flex-col sm:flex-row gap-2">
                  <input
                    type="text"
                    value={newComment}
                    onChange={(e) => setNewComment(e.target.value)}
                    placeholder="Escribe tu opinión, recomendación o debate sobre esta lista..."
                    className="flex-1 px-4 py-2.5 rounded-xl border border-slate-300 dark:border-slate-600 bg-slate-50 dark:bg-slate-900 text-slate-900 dark:text-white text-xs sm:text-sm focus:outline-none focus:ring-2 focus:ring-teal-500"
                  />
                  <button
                    type="submit"
                    disabled={submittingComment || !newComment.trim()}
                    className="px-5 py-2.5 rounded-xl font-bold text-xs sm:text-sm text-white bg-teal-600 hover:bg-teal-700 disabled:opacity-50 transition-colors shadow-sm cursor-pointer whitespace-nowrap"
                  >
                    {submittingComment ? 'Publicando...' : 'Comentar'}
                  </button>
                </form>
              ) : (
                <div className="p-3 bg-slate-50 dark:bg-slate-900/50 rounded-2xl border border-slate-200/60 dark:border-slate-700/60 text-xs text-slate-500 text-center">
                  <span>Inicia sesión para participar en el debate de esta lista.</span>
                </div>
              )}

              {/* Listado de comentarios */}
              {loadingComments ? (
                <div className="py-4 text-center">
                  <Spinner size="sm" />
                </div>
              ) : comments.length === 0 ? (
                <p className="text-xs text-slate-400 py-3 text-center">
                  Aún no hay comentarios en esta lista. ¡Sé el primero en compartir tu opinión!
                </p>
              ) : (
                <div className="space-y-3 pt-2">
                  {comments.map((c) => (
                    <div
                      key={c.id}
                      className="p-3.5 rounded-2xl bg-slate-50 dark:bg-slate-900/40 border border-slate-100 dark:border-slate-700/50 flex items-start justify-between gap-3 text-xs"
                    >
                      <div className="flex items-start gap-2.5 flex-1 min-w-0">
                        <div className="w-7 h-7 rounded-full bg-teal-100 dark:bg-teal-900/60 text-teal-800 dark:text-teal-200 font-bold flex items-center justify-center shrink-0 text-xs">
                          {c.user.username.charAt(0).toUpperCase()}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1">
                            <span className="font-bold text-slate-900 dark:text-white">
                              @{c.user.username}
                            </span>
                            <span className="text-[10px] text-slate-400">
                              {new Date(c.created_at).toLocaleDateString()}
                            </span>
                          </div>
                          <p className="text-slate-700 dark:text-slate-300 text-xs leading-relaxed break-words">
                            {c.content}
                          </p>
                        </div>
                      </div>

                      {c.can_delete && (
                        <button
                          onClick={() => handleDeleteComment(c.id)}
                          className="text-slate-400 hover:text-red-500 p-1 rounded-lg transition-colors cursor-pointer"
                          title="Eliminar comentario"
                        >
                          ✕
                        </button>
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

            <form onSubmit={handleSubmitList(onSubmitList)} className="space-y-4">
              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300 mb-1">
                  Nombre de la lista *
                </label>
                <input
                  type="text"
                  {...registerList('name')}
                  placeholder="Ej. Favoritos, Clásicos, Vacaciones..."
                  className="w-full text-sm rounded-xl border border-slate-300 dark:border-slate-600 bg-slate-50 dark:bg-slate-700 dark:text-white py-2 px-3 focus:ring-teal-500"
                />
                {listErrors.name && (
                  <p className="text-xs text-rose-500 mt-1">{listErrors.name.message}</p>
                )}
              </div>

              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300 mb-1">
                  Descripción (opcional)
                </label>
                <textarea
                  rows={3}
                  {...registerList('description')}
                  placeholder="Explica de qué trata esta colección..."
                  className="w-full text-sm rounded-xl border border-slate-300 dark:border-slate-600 bg-slate-50 dark:bg-slate-700 dark:text-white py-2 px-3 focus:ring-teal-500"
                />
                {listErrors.description && (
                  <p className="text-xs text-rose-500 mt-1">{listErrors.description.message}</p>
                )}
              </div>

              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300 mb-1">
                  Privacidad
                </label>
                <select
                  {...registerList('privacy')}
                  className="w-full text-sm rounded-xl border border-slate-300 dark:border-slate-600 bg-slate-50 dark:bg-slate-700 dark:text-white py-2 px-3 focus:ring-teal-500"
                >
                  <option value="public">Pública (Visible para todos)</option>
                  <option value="followers">Solo Seguidores</option>
                  <option value="private">Privada (Solo tú)</option>
                </select>
                {listErrors.privacy && (
                  <p className="text-xs text-rose-500 mt-1">{listErrors.privacy.message}</p>
                )}
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

      {reportingList && (
        <ReportModal
          isOpen={!!reportingList}
          onClose={() => setReportingList(null)}
          targetType="list"
          targetId={reportingList.id}
          targetTitle={`Lista: ${reportingList.name}`}
        />
      )}
    </div>
  );
}

export default ReadingLists;
