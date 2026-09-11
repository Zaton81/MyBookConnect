import React, { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useAuthStore } from '../store/auth';
import { Spinner } from 'flowbite-react';
import DOMPurify from 'dompurify';
import { createErrata } from '../services/erratas';
import { AIAssistantModal } from '../components/AIAssistantModal';
import { AmazonAdSlot } from '../components/AmazonAdSlot';
import { StarRating } from '../components/StarRating';
import { BookReviewsSection } from '../components/BookReviewsSection';
import { resolveMediaUrl } from '../utils/media';

interface ContextualRecommendation {
  id: number;
  title: string;
  cover?: string;
  author_name: string;
  average_rating?: number;
  score: number;
  reason: string;
}

export function BookDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { token, user } = useAuthStore();

  const [book, setBook] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [relatedBooks, setRelatedBooks] = useState<ContextualRecommendation[]>([]);

  // Estado de estantería del usuario
  const [userBook, setUserBook] = useState<any | null>(null);
  const [readingStatus, setReadingStatus] = useState<'want_to_read' | 'reading' | 'read' | 'abandoned'>('want_to_read');
  const [progress, setProgress] = useState<number>(0);
  const [currentPage, setCurrentPage] = useState<number>(0);
  const [startedAt, setStartedAt] = useState<string>('');
  const [finishedAt, setFinishedAt] = useState<string>('');
  const [isDigital, setIsDigital] = useState<boolean>(false);
  const [isRead, setIsRead] = useState<boolean>(false);
  const [rating, setRating] = useState<number | ''>('');
  const [notes, setNotes] = useState<string>('');
  const [wishlist, setWishlist] = useState<boolean>(false);
  const [isEditing, setIsEditing] = useState(false);
  const [savingShelf, setSavingShelf] = useState(false);

  // Análisis de BookAI
  const [aiSummary, setAiSummary] = useState<string | null>(null);
  const [loadingAi, setLoadingAi] = useState(false);
  const [isAiModalOpen, setIsAiModalOpen] = useState(false);

  // Reporte de Erratas
  const [errataText, setErrataText] = useState<string>('');
  const [errataType, setErrataType] = useState<'errata' | 'suggestion' | 'other'>('errata');
  const [errataSuccess, setErrataSuccess] = useState(false);

  const apiUrl = (import.meta as any).env.VITE_API_URL || 'http://localhost:8000';

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    setError(null);

    const headers: Record<string, string> = token ? { Authorization: `Bearer ${token}` } : {};

    // Cargar detalles del libro
    fetch(`${apiUrl}/api/v1/books/${id}/`, { headers })
      .then(async (r) => {
        if (!r.ok) {
          if (r.status === 404) throw new Error('Libro no encontrado');
          throw new Error('No se pudo cargar el libro');
        }
        return r.json();
      })
      .then((data) => {
        if (data?.cover && typeof data.cover === 'string' && data.cover.startsWith('/')) {
          data.cover = `${apiUrl}${data.cover}`;
        }
        setBook(data);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));

    // Cargar entrada del usuario en su estantería solo si está autenticado
    if (token) {
      fetch(`${apiUrl}/api/v1/books/user/books/by-book/${id}/`, { headers })
        .then(async (r) => {
          if (r.status === 404) return null;
          if (!r.ok) return null;
          return r.json();
        })
        .then((found) => {
          if (found) {
            setUserBook(found);
            setReadingStatus(found.status || (found.is_read ? 'read' : 'want_to_read'));
            setProgress(found.progress ?? (found.is_read ? 100 : 0));
            setCurrentPage(found.current_page ?? 0);
            setStartedAt(found.started_at || '');
            setFinishedAt(found.finished_at || '');
            setIsDigital(!!found.is_digital);
            setIsRead(!!found.is_read);
            setWishlist(!!found.wishlist);
            setRating(found.rating ?? '');
            setNotes(found.notes || '');
          } else {
            setUserBook(null);
          }
        })
        .catch(() => {});
    } else {
      setUserBook(null);
    }

    // Cargar libros recomendados contextuales (Fase 24)
    fetch(`${apiUrl}/api/v1/books/${id}/recommendations/?limit=5`, { headers })
      .then((r) => (r.ok ? r.json() : []))
      .then((data) => {
        if (Array.isArray(data)) {
          setRelatedBooks(data);
        }
      })
      .catch(() => {});
  }, [id, token, apiUrl]);

  const refreshBookDetails = () => {
    if (!id) return;
    fetch(`${apiUrl}/api/v1/books/${id}/`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (data) {
          if (data.cover && typeof data.cover === 'string' && data.cover.startsWith('/')) {
            data.cover = `${apiUrl}${data.cover}`;
          }
          setBook(data);
        }
      })
      .catch(() => {});
  };

  const handleSaveShelf = async () => {
    if (!token || !userBook) return;
    setSavingShelf(true);
    try {
      const res = await fetch(`${apiUrl}/api/v1/books/user/books/${userBook.id}/`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          status: readingStatus,
          progress: Number(progress) || 0,
          current_page: Number(currentPage) || 0,
          started_at: startedAt || null,
          finished_at: finishedAt || null,
          is_digital: isDigital,
          is_read: readingStatus === 'read',
          wishlist: readingStatus === 'want_to_read' ? true : wishlist,
          rating: rating === '' ? null : rating,
          notes,
        }),
      });
      if (res.ok) {
        const updated = await res.json();
        setUserBook(updated);
        setReadingStatus(updated.status || readingStatus);
        setProgress(updated.progress ?? progress);
        setCurrentPage(updated.current_page ?? currentPage);
        setStartedAt(updated.started_at || '');
        setFinishedAt(updated.finished_at || '');
        setIsEditing(false);
        refreshBookDetails();
      }
    } catch (e) {
      console.error(e);
    } finally {
      setSavingShelf(false);
    }
  };

  const handleAddToShelf = async (
    targetStatus: 'want_to_read' | 'reading' | 'read' = 'want_to_read'
  ) => {
    if (!token || !id) return;
    setSavingShelf(true);
    try {
      const todayStr = new Date().toISOString().split('T')[0];
      const res = await fetch(`${apiUrl}/api/v1/books/user/books/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          book_id: id,
          status: targetStatus,
          progress: targetStatus === 'read' ? 100 : 0,
          current_page: 0,
          started_at: targetStatus === 'reading' ? todayStr : null,
          finished_at: targetStatus === 'read' ? todayStr : null,
          is_read: targetStatus === 'read',
          wishlist: targetStatus === 'want_to_read',
          is_digital: false,
          owned: true,
        }),
      });
      if (res.ok) {
        const created = await res.json();
        setUserBook(created);
        setReadingStatus(created.status || targetStatus);
        setProgress(created.progress ?? (targetStatus === 'read' ? 100 : 0));
        setCurrentPage(created.current_page ?? 0);
        setStartedAt(created.started_at || '');
        setFinishedAt(created.finished_at || '');
        setIsRead(targetStatus === 'read');
        setWishlist(targetStatus === 'want_to_read');
        refreshBookDetails();
      }
    } catch (e) {
      console.error(e);
    } finally {
      setSavingShelf(false);
    }
  };

  const handleRemoveFromShelf = async () => {
    if (!token || !userBook) return;
    if (!window.confirm('¿Seguro que deseas quitar este libro de tu biblioteca?')) return;
    try {
      await fetch(`${apiUrl}/api/v1/books/user/books/${userBook.id}/`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      });
      setUserBook(null);
    } catch (e) {
      console.error(e);
    }
  };

  const handleFetchAiSummary = async () => {
    if (!token || !id) return;
    setLoadingAi(true);
    try {
      const res = await fetch(`${apiUrl}/api/v1/books/${id}/ai/summary/`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setAiSummary(data.summary);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoadingAi(false);
    }
  };

  const handleSendErrata = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token || !id || !errataText.trim()) return;
    try {
      await createErrata(token, {
        book_id: Number(id),
        type: errataType,
        text: errataText.trim(),
      });
      setErrataText('');
      setErrataSuccess(true);
      setTimeout(() => setErrataSuccess(false), 4000);
    } catch (e) {
      alert('Error al enviar el reporte.');
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-[50vh]">
        <Spinner size="xl" color="info" />
      </div>
    );
  }

  if (error || !book) {
    return (
      <div className="max-w-2xl mx-auto p-8 bg-white dark:bg-slate-800 rounded-3xl border border-slate-200 dark:border-slate-700 text-center">
        <span className="text-4xl">📚</span>
        <h3 className="text-lg font-bold text-slate-900 dark:text-white mt-2">
          {error || 'Libro no encontrado'}
        </h3>
        <button
          onClick={() => navigate(-1)}
          className="mt-4 text-teal-600 hover:underline text-sm font-semibold"
        >
          ← Volver
        </button>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto space-y-8">
      {/* Botón Volver */}
      <button
        onClick={() => navigate(-1)}
        className="inline-flex items-center gap-1.5 text-xs font-bold text-slate-500 hover:text-teal-600 transition-colors"
      >
        <span>←</span>
        <span>Volver al catálogo</span>
      </button>

      {/* ── Ficha Principal del Libro ── */}
      <div className="bg-white dark:bg-slate-800 rounded-3xl border border-slate-200/80 dark:border-slate-700 p-6 sm:p-8 shadow-sm">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {/* Columna Izquierda: Portada & Acciones */}
          <div className="space-y-4 flex flex-col items-center md:items-start">
            <div className="relative aspect-[2/3] w-56 sm:w-64 rounded-2xl overflow-hidden shadow-2xl border-4 border-white dark:border-slate-700 bg-slate-100 dark:bg-slate-700">
              {book.cover ? (
                <img
                  src={resolveMediaUrl(book.cover)}
                  alt={book.title}
                  className="w-full h-full object-cover"
                />
              ) : (
                <div className="w-full h-full flex items-center justify-center p-4 text-center font-bold text-slate-400 text-sm">
                  {book.title}
                </div>
              )}
            </div>

            {/* Widget de Biblioteca del Usuario */}
            <div className="w-full max-w-xs bg-slate-50 dark:bg-slate-700/50 p-4 rounded-2xl border border-slate-200/80 dark:border-slate-600 space-y-3">
              {userBook ? (
                <>
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-teal-700 dark:text-teal-300">
                      ✓ En tu biblioteca
                    </span>
                    <button
                      onClick={() => setIsEditing(!isEditing)}
                      className="text-xs font-semibold text-slate-600 hover:text-teal-600 underline"
                    >
                      {isEditing ? 'Cerrar' : 'Editar estado'}
                    </button>
                  </div>

                  {!isEditing ? (
                    <div className="space-y-2 text-xs text-slate-600 dark:text-slate-300">
                      {/* Badge de Estado de Lectura */}
                      <div className="flex items-center justify-between">
                        {readingStatus === 'reading' && (
                          <span className="px-2.5 py-1 rounded-xl text-xs font-bold bg-indigo-100 text-indigo-800 dark:bg-indigo-900/40 dark:text-indigo-300 border border-indigo-200/60 flex items-center gap-1.5">
                            <span className="animate-pulse">📖</span> Leyendo
                          </span>
                        )}
                        {readingStatus === 'read' && (
                          <span className="px-2.5 py-1 rounded-xl text-xs font-bold bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300 border border-emerald-200/60 flex items-center gap-1.5">
                            <span>✅</span> Leído
                          </span>
                        )}
                        {readingStatus === 'want_to_read' && (
                          <span className="px-2.5 py-1 rounded-xl text-xs font-bold bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300 border border-amber-200/60 flex items-center gap-1.5">
                            <span>⏳</span> Quiero leer
                          </span>
                        )}
                        {readingStatus === 'abandoned' && (
                          <span className="px-2.5 py-1 rounded-xl text-xs font-bold bg-slate-200 text-slate-700 dark:bg-slate-600 dark:text-slate-200 flex items-center gap-1.5">
                            <span>🚫</span> Abandonado
                          </span>
                        )}

                        <span className="text-[11px] font-semibold text-slate-500">
                          {isDigital ? '📱 Digital' : '📖 Físico'}
                        </span>
                      </div>

                      {/* Progreso de lectura con barra */}
                      {readingStatus === 'reading' && (
                        <div className="space-y-1 pt-1">
                          <div className="flex justify-between text-[11px] font-semibold text-indigo-700 dark:text-indigo-300">
                            <span>Progreso: {progress}%</span>
                            {currentPage > 0 && <span>Pág. {currentPage}</span>}
                          </div>
                          <div className="w-full bg-slate-200 dark:bg-slate-600 h-2 rounded-full overflow-hidden">
                            <div
                              className="bg-gradient-to-r from-indigo-500 to-teal-400 h-full rounded-full transition-all duration-300"
                              style={{ width: `${Math.min(100, Math.max(0, progress))}%` }}
                            />
                          </div>
                        </div>
                      )}

                      {/* Fechas */}
                      <div className="text-[11px] text-slate-400 space-y-0.5 pt-0.5">
                        {startedAt && <p>Iniciado: {startedAt}</p>}
                        {finishedAt && <p>Terminado: {finishedAt}</p>}
                      </div>

                      <div className="pt-1 border-t border-slate-200/60 dark:border-slate-600">
                        <p>
                          <strong>Mi nota privada:</strong> {rating ? `⭐ ${rating}/10` : 'Sin puntuar'}
                        </p>
                        {notes && (
                          <p className="pt-1 italic text-slate-500 dark:text-slate-400 line-clamp-2">
                            "{notes}"
                          </p>
                        )}
                      </div>
                    </div>
                  ) : (
                    <div className="space-y-3 pt-1 text-xs">
                      {/* Selector de Estado */}
                      <div>
                        <label className="block text-[11px] font-bold text-slate-700 dark:text-slate-300 mb-1">
                          Estado de lectura:
                        </label>
                        <select
                          value={readingStatus}
                          onChange={(e) => {
                            const st = e.target.value as any;
                            setReadingStatus(st);
                            if (st === 'read' && progress < 100) setProgress(100);
                            if (st === 'read' && !finishedAt) {
                              setFinishedAt(new Date().toISOString().split('T')[0]);
                            }
                            if (st === 'reading' && !startedAt) {
                              setStartedAt(new Date().toISOString().split('T')[0]);
                            }
                          }}
                          className="w-full text-xs rounded-xl border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-700 py-1.5 px-2"
                        >
                          <option value="want_to_read">⏳ Quiero leer (Pendiente)</option>
                          <option value="reading">📖 Leyendo actualmente</option>
                          <option value="read">✅ Leído (Terminado)</option>
                          <option value="abandoned">🚫 Abandonado</option>
                        </select>
                      </div>

                      {/* Controles de Progreso si está leyendo o abandonado */}
                      {(readingStatus === 'reading' || readingStatus === 'abandoned') && (
                        <div className="p-2.5 bg-indigo-50/50 dark:bg-indigo-900/20 rounded-xl space-y-2 border border-indigo-100 dark:border-indigo-900/40">
                          <div className="flex items-center justify-between text-[11px] font-semibold">
                            <span>Progreso:</span>
                            <span className="font-bold text-indigo-600 dark:text-indigo-400">{progress}%</span>
                          </div>
                          <input
                            type="range"
                            min="0"
                            max="100"
                            value={progress}
                            onChange={(e) => setProgress(Number(e.target.value))}
                            className="w-full accent-teal-600 cursor-pointer"
                          />
                          <div className="flex items-center gap-2">
                            <label className="text-[11px] text-slate-600 dark:text-slate-300 whitespace-nowrap">
                              Pág. actual:
                            </label>
                            <input
                              type="number"
                              min="0"
                              value={currentPage || ''}
                              onChange={(e) => setCurrentPage(Number(e.target.value) || 0)}
                              placeholder="Ej: 140"
                              className="w-full text-xs py-1 px-2 rounded-lg border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-700"
                            />
                          </div>
                        </div>
                      )}

                      {/* Fechas de Lectura */}
                      <div className="grid grid-cols-2 gap-2">
                        <div>
                          <label className="block text-[10px] text-slate-500 mb-0.5">Fecha inicio:</label>
                          <input
                            type="date"
                            value={startedAt}
                            onChange={(e) => setStartedAt(e.target.value)}
                            className="w-full text-[11px] py-1 px-1.5 rounded-lg border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-700"
                          />
                        </div>
                        <div>
                          <label className="block text-[10px] text-slate-500 mb-0.5">Fecha fin:</label>
                          <input
                            type="date"
                            value={finishedAt}
                            onChange={(e) => setFinishedAt(e.target.value)}
                            className="w-full text-[11px] py-1 px-1.5 rounded-lg border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-700"
                          />
                        </div>
                      </div>

                      {/* Formato y Wishlist */}
                      <div className="flex items-center justify-between gap-2 pt-1">
                        <label className="flex items-center gap-1.5 text-xs font-medium cursor-pointer">
                          <input
                            type="checkbox"
                            checked={isDigital}
                            onChange={(e) => setIsDigital(e.target.checked)}
                            className="rounded text-teal-600"
                          />
                          <span>📱 Digital</span>
                        </label>
                        <label className="flex items-center gap-1.5 text-xs font-medium cursor-pointer">
                          <input
                            type="checkbox"
                            checked={wishlist}
                            onChange={(e) => setWishlist(e.target.checked)}
                            className="rounded text-teal-600"
                          />
                          <span>⭐ Wishlist</span>
                        </label>
                      </div>

                      {/* Nota privada */}
                      <div>
                        <label className="block text-[11px] font-bold text-slate-700 dark:text-slate-300 mb-1">
                          Mi nota privada:
                        </label>
                        <select
                          value={rating}
                          onChange={(e) => setRating(e.target.value ? Number(e.target.value) : '')}
                          className="w-full text-xs rounded-xl border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-700 py-1.5 px-2"
                        >
                          <option value="">Sin puntuar</option>
                          {[10, 9, 8, 7, 6, 5, 4, 3, 2, 1].map((n) => (
                            <option key={n} value={n}>
                              ⭐ {n}/10
                            </option>
                          ))}
                        </select>
                      </div>

                      {/* Notas personales */}
                      <div>
                        <label className="block text-[11px] font-bold text-slate-700 dark:text-slate-300 mb-1">
                          Notas privadas:
                        </label>
                        <textarea
                          rows={2}
                          placeholder="Citas, pensamientos o notas privadas..."
                          value={notes}
                          onChange={(e) => setNotes(e.target.value)}
                          className="w-full text-xs rounded-xl border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-700 p-2"
                        />
                      </div>

                      <div className="flex gap-2 pt-1">
                        <button
                          onClick={handleSaveShelf}
                          disabled={savingShelf}
                          className="flex-1 bg-teal-600 hover:bg-teal-700 text-white font-bold py-2 rounded-xl text-xs shadow transition-all disabled:opacity-50"
                        >
                          {savingShelf ? 'Guardando...' : 'Guardar cambios'}
                        </button>
                        <button
                          onClick={handleRemoveFromShelf}
                          className="bg-rose-100 hover:bg-rose-200 text-rose-700 font-bold px-3 py-2 rounded-xl text-xs transition-colors"
                          title="Eliminar de mi estantería"
                        >
                          🗑
                        </button>
                      </div>
                    </div>
                  )}
                </>
              ) : (
                <div className="space-y-2">
                  <p className="text-xs text-slate-500 dark:text-slate-400">
                    Añade este libro para registrar tu progreso y lecturas.
                  </p>
                  <button
                    onClick={() => handleAddToShelf('reading')}
                    disabled={savingShelf}
                    className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-2 rounded-xl text-xs transition-all shadow flex items-center justify-center gap-1.5"
                  >
                    <span>📖</span>
                    <span>Empezar a leer</span>
                  </button>
                  <div className="grid grid-cols-2 gap-2">
                    <button
                      onClick={() => handleAddToShelf('want_to_read')}
                      disabled={savingShelf}
                      className="bg-slate-100 hover:bg-slate-200 dark:bg-slate-700 dark:hover:bg-slate-600 text-slate-700 dark:text-slate-200 font-semibold py-1.5 rounded-xl text-xs transition-colors"
                    >
                      ⏳ Quiero leer
                    </button>
                    <button
                      onClick={() => handleAddToShelf('read')}
                      disabled={savingShelf}
                      className="bg-emerald-600 hover:bg-emerald-700 text-white font-semibold py-1.5 rounded-xl text-xs transition-colors"
                    >
                      ✓ Ya lo leí
                    </button>
                  </div>
                </div>
              )}
            </div>

            {/* Botón Asistente BookAI */}
            <button
              onClick={() => setIsAiModalOpen(true)}
              className="w-full max-w-xs bg-gradient-to-r from-amber-400 to-orange-400 hover:from-amber-300 hover:to-orange-300 text-slate-900 font-bold py-2.5 px-4 rounded-2xl text-xs shadow-md shadow-amber-500/10 flex items-center justify-center gap-2"
            >
              <span>✨</span>
              <span>Preguntar a BookAI sobre este libro</span>
            </button>
          </div>

          {/* Columna Derecha: Información & Sinopsis */}
          <div className="md:col-span-2 space-y-5">
            <div>
              <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-white tracking-tight">
                {book.title}
              </h1>

              <div className="flex flex-wrap items-center gap-2 mt-2">
                {book.author ? (
                  <Link
                    to={`/authors/${book.author.id}`}
                    className="text-base font-semibold text-teal-600 hover:text-teal-700 hover:underline"
                  >
                    {book.author.name}
                  </Link>
                ) : (
                  <span className="text-slate-500">Autor desconocido</span>
                )}

                {book.published_date && (
                  <>
                    <span className="text-slate-300 dark:text-slate-600">•</span>
                    <span className="text-xs text-slate-500">
                      Publicado en {new Date(book.published_date).getFullYear() || book.published_date}
                    </span>
                  </>
                )}

                {book.isbn && (
                  <>
                    <span className="text-slate-300 dark:text-slate-600">•</span>
                    <span className="text-xs text-slate-400 font-mono">ISBN: {book.isbn}</span>
                  </>
                )}
              </div>

              {/* Puntuación Media y Desglose en Estrellas */}
              <div className="pt-2">
                <StarRating
                  rating={book.average_rating}
                  maxRating={10}
                  totalReviews={book.reviews_count}
                  distribution={book.rating_distribution}
                  size="md"
                />
              </div>
            </div>

            {/* Categorías / Géneros */}
            {book.categories && book.categories.length > 0 && (
              <div className="flex flex-wrap gap-1.5">
                {book.categories.map((c: any) => (
                  <span
                    key={c.id}
                    className="px-2.5 py-1 rounded-lg text-xs font-semibold bg-teal-50 text-teal-800 dark:bg-teal-900/30 dark:text-teal-300 border border-teal-200/50 dark:border-teal-800/40"
                  >
                    {c.name}
                  </span>
                ))}
              </div>
            )}

            {/* Sinopsis */}
            <div>
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">
                Sinopsis
              </h3>
              {book.description ? (
                <div
                  className="text-sm text-slate-600 dark:text-slate-300 leading-relaxed prose dark:prose-invert max-w-none"
                  dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(book.description) }}
                />
              ) : (
                <p className="text-xs text-slate-400 italic">
                  No hay sinopsis disponible actualmente para este título.
                </p>
              )}
            </div>

            {/* Tarjeta de Análisis con BookAI */}
            <div className="p-5 rounded-2xl bg-gradient-to-br from-teal-900 to-slate-900 text-white shadow-md space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="text-xl">✨</span>
                  <h4 className="text-sm font-bold">Análisis Literario BookAI</h4>
                </div>
                {!aiSummary && (
                  <button
                    onClick={handleFetchAiSummary}
                    disabled={loadingAi}
                    className="bg-white/20 hover:bg-white/30 text-white text-xs font-bold px-3 py-1.5 rounded-xl transition-colors backdrop-blur-sm flex items-center gap-1"
                  >
                    {loadingAi ? 'Analizando...' : 'Generar análisis'}
                  </button>
                )}
              </div>

              {loadingAi && (
                <div className="flex items-center gap-2 text-xs text-teal-200 py-2">
                  <Spinner size="sm" color="info" />
                  <span>Explorando temas y estilo de la obra...</span>
                </div>
              )}

              {aiSummary && (
                <div className="text-xs sm:text-sm text-teal-100/90 leading-relaxed whitespace-pre-line pt-2 border-t border-white/10">
                  {aiSummary}
                </div>
              )}

              {!aiSummary && !loadingAi && (
                <p className="text-xs text-teal-200/70">
                  Descubre los temas centrales, estilo narrativo y a quién va recomendada esta obra con inteligencia artificial.
                </p>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* ── Recomendación / Compra en Amazon (Afiliados) ── */}
      <AmazonAdSlot
        bookTitle={book.title}
        searchQuery={`${book.title} ${book.author?.name || ''}`}
        variant="banner"
      />

      {/* ── Sección de Reseñas Públicas de la Comunidad ── */}
      <BookReviewsSection
        bookId={book.id}
        bookTitle={book.title}
        token={token}
        currentUser={user}
        onReviewSaved={refreshBookDetails}
      />

      {/* ── Formulario de Erratas ── */}
      <div className="bg-white dark:bg-slate-800 rounded-3xl border border-slate-200/80 dark:border-slate-700 p-6 shadow-sm">
        <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-1.5 mb-2">
          <span>✍️</span>
          <span>¿Hay algún dato erróneo en este libro?</span>
        </h3>
        <p className="text-xs text-slate-500 dark:text-slate-400 mb-4">
          Reporta información faltante o incorrecta sobre la portada, fecha o edición.
        </p>

        {errataSuccess ? (
          <div className="p-3 bg-emerald-50 text-emerald-800 dark:bg-emerald-900/30 rounded-xl text-xs font-semibold">
            ✓ Reporte enviado correctamente a los editores.
          </div>
        ) : (
          <form onSubmit={handleSendErrata} className="space-y-3">
            <div className="flex gap-3 items-center">
              <label className="text-xs font-bold text-slate-700 dark:text-slate-300">
                Tipo:
              </label>
              <select
                value={errataType}
                onChange={(e) => setErrataType(e.target.value as any)}
                className="text-xs rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-700 py-1.5 px-3"
              >
                <option value="errata">Errata</option>
                <option value="suggestion">Sugerencia</option>
                <option value="other">Otro</option>
              </select>
            </div>
            <textarea
              rows={3}
              value={errataText}
              onChange={(e) => setErrataText(e.target.value)}
              placeholder="Explica qué dato está incorrecto..."
              className="w-full text-xs rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-700 p-3 focus:ring-teal-500"
            />
            <button
              type="submit"
              disabled={!errataText.trim()}
              className="bg-teal-600 hover:bg-teal-700 text-white font-bold text-xs px-4 py-2 rounded-xl transition-all disabled:opacity-50"
            >
              Enviar reporte
            </button>
          </form>
        )}
      </div>

      {/* ── Sección de Recomendaciones Contextuales (Fase 24) ── */}
      {relatedBooks.length > 0 && (
        <div className="bg-white dark:bg-slate-800 rounded-3xl p-6 border border-slate-100 dark:border-slate-700 shadow-sm space-y-4">
          <div>
            <h3 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
              <span>📚</span>
              <span>Lectores también disfrutaron</span>
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Títulos recomendados por afinidad de autor, temática y co-lecturas de la comunidad
            </p>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-4">
            {relatedBooks.map((rel) => (
              <div
                key={rel.id}
                onClick={() => navigate(`/books/${rel.id}`)}
                className="group bg-slate-50 dark:bg-slate-900/60 p-3 rounded-2xl border border-slate-200/60 dark:border-slate-700/60 hover:shadow-md hover:border-teal-400 transition-all cursor-pointer flex flex-col justify-between"
              >
                <div>
                  <div className="aspect-[2/3] w-full rounded-xl overflow-hidden bg-slate-200 dark:bg-slate-700 mb-2">
                    {rel.cover ? (
                      <img
                        src={resolveMediaUrl(rel.cover)}
                        alt={rel.title}
                        className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-200"
                        loading="lazy"
                      />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center p-2 text-center text-xs text-slate-400">
                        {rel.title}
                      </div>
                    )}
                  </div>
                  <h4 className="text-xs font-bold text-slate-900 dark:text-white truncate group-hover:text-teal-600 transition-colors">
                    {rel.title}
                  </h4>
                  <p className="text-[11px] text-slate-500 truncate">
                    {rel.author_name}
                  </p>
                  {rel.average_rating && (
                    <span className="text-[11px] text-amber-500 font-medium flex items-center gap-1 mt-0.5">
                      ★ {rel.average_rating.toFixed(1)}
                    </span>
                  )}
                </div>

                <div className="mt-2 pt-1.5 border-t border-slate-200/60 dark:border-slate-800">
                  <span className="inline-block text-[10px] text-teal-700 dark:text-teal-300 bg-teal-50 dark:bg-teal-950/40 px-1.5 py-0.5 rounded line-clamp-2">
                    💡 {rel.reason}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <AIAssistantModal
        isOpen={isAiModalOpen}
        onClose={() => setIsAiModalOpen(false)}
        contextBookId={book.id}
        contextBookTitle={book.title}
      />
    </div>
  );
}