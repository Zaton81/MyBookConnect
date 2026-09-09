import React, { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useAuthStore } from '../store/auth';
import { Spinner } from 'flowbite-react';
import DOMPurify from 'dompurify';
import { createErrata } from '../services/erratas';
import { AIAssistantModal } from '../components/AIAssistantModal';

export function BookDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { token, user } = useAuthStore();

  const [book, setBook] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Estado de estantería del usuario
  const [userBook, setUserBook] = useState<any | null>(null);
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
    if (!token || !id) return;
    setLoading(true);

    // Cargar detalles del libro
    fetch(`${apiUrl}/api/v1/books/${id}/`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(async (r) => {
        if (!r.ok) throw new Error('No se pudo cargar el libro');
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

    // Cargar entrada del usuario en su estantería
    fetch(`${apiUrl}/api/v1/books/user/books/by-book/${id}/`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(async (r) => {
        if (r.status === 404) return null;
        if (!r.ok) return null;
        return r.json();
      })
      .then((found) => {
        if (found) {
          setUserBook(found);
          setIsDigital(!!found.is_digital);
          setIsRead(!!found.is_read);
          setWishlist(!!found.wishlist);
          setRating(found.rating ?? '');
          setNotes(found.notes || '');
        }
      })
      .catch(() => {});
  }, [id, token, apiUrl]);

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
          is_digital: isDigital,
          is_read: isRead,
          wishlist: wishlist,
          rating: rating === '' ? null : rating,
          notes,
        }),
      });
      if (res.ok) {
        const updated = await res.json();
        setUserBook(updated);
        setIsEditing(false);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setSavingShelf(false);
    }
  };

  const handleAddToShelf = async (asRead = false, asWishlist = false) => {
    if (!token || !id) return;
    setSavingShelf(true);
    try {
      const res = await fetch(`${apiUrl}/api/v1/books/user/books/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          book_id: id,
          is_read: asRead,
          wishlist: asWishlist,
          is_digital: false,
          owned: true,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        setUserBook(data);
        setIsRead(data.is_read);
        setWishlist(data.wishlist);
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
                  src={book.cover}
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
                      {isEditing ? 'Cerrar' : 'Editar'}
                    </button>
                  </div>

                  {!isEditing ? (
                    <div className="space-y-1.5 text-xs text-slate-600 dark:text-slate-300">
                      <p>
                        <strong>Estado:</strong> {isRead ? '✅ Leído' : '⏳ Pendiente'}
                      </p>
                      <p>
                        <strong>Formato:</strong> {isDigital ? '📱 Digital' : '📖 Físico'}
                      </p>
                      <p>
                        <strong>Mi nota:</strong> {rating ? `⭐ ${rating}/10` : 'Sin puntuar'}
                      </p>
                      {wishlist && (
                        <span className="inline-block px-2 py-0.5 rounded-full bg-amber-100 text-amber-800 text-[10px] font-bold">
                          ⭐ En Wishlist
                        </span>
                      )}
                      {notes && (
                        <p className="pt-1 italic text-slate-500 line-clamp-2">
                          "{notes}"
                        </p>
                      )}
                    </div>
                  ) : (
                    <div className="space-y-2.5 pt-1">
                      <div className="flex gap-2 text-xs">
                        <label className="flex items-center gap-1 font-medium">
                          <input
                            type="checkbox"
                            checked={isRead}
                            onChange={(e) => setIsRead(e.target.checked)}
                            className="rounded text-teal-600"
                          />
                          <span>Leído</span>
                        </label>
                        <label className="flex items-center gap-1 font-medium">
                          <input
                            type="checkbox"
                            checked={wishlist}
                            onChange={(e) => setWishlist(e.target.checked)}
                            className="rounded text-teal-600"
                          />
                          <span>Wishlist</span>
                        </label>
                      </div>

                      <select
                        value={rating}
                        onChange={(e) => setRating(e.target.value ? Number(e.target.value) : '')}
                        className="w-full text-xs rounded-xl border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-700 py-1.5 px-2"
                      >
                        <option value="">Sin nota</option>
                        {[10, 9, 8, 7, 6, 5, 4, 3, 2, 1].map((n) => (
                          <option key={n} value={n}>
                            ⭐ {n}/10
                          </option>
                        ))}
                      </select>

                      <textarea
                        rows={2}
                        placeholder="Mis notas personales..."
                        value={notes}
                        onChange={(e) => setNotes(e.target.value)}
                        className="w-full text-xs rounded-xl border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-700 p-2"
                      />

                      <div className="flex gap-2">
                        <button
                          onClick={handleSaveShelf}
                          disabled={savingShelf}
                          className="flex-1 bg-teal-600 hover:bg-teal-700 text-white font-bold py-1.5 rounded-xl text-xs"
                        >
                          Guardar
                        </button>
                        <button
                          onClick={handleRemoveFromShelf}
                          className="bg-rose-100 hover:bg-rose-200 text-rose-700 font-bold px-2 py-1.5 rounded-xl text-xs"
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
                    Añade este libro para llevar el control de tus lecturas.
                  </p>
                  <button
                    onClick={() => handleAddToShelf(false, false)}
                    disabled={savingShelf}
                    className="w-full bg-teal-600 hover:bg-teal-700 text-white font-bold py-2 rounded-xl text-xs transition-all shadow"
                  >
                    + Añadir a mi estantería
                  </button>
                  <button
                    onClick={() => handleAddToShelf(true, false)}
                    className="w-full bg-slate-200 hover:bg-slate-300 dark:bg-slate-700 dark:hover:bg-slate-600 text-slate-700 dark:text-slate-200 font-semibold py-1.5 rounded-xl text-xs"
                  >
                    ✓ Ya lo he leído
                  </button>
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

      <AIAssistantModal
        isOpen={isAiModalOpen}
        onClose={() => setIsAiModalOpen(false)}
        contextBookId={book.id}
        contextBookTitle={book.title}
      />
    </div>
  );
}