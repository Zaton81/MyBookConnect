import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { StarRating } from './StarRating';

interface ReviewItem {
  id: number;
  user: number;
  username: string;
  avatar?: string | null;
  book: number;
  rating: number;
  title?: string | null;
  text?: string | null;
  created_at: string;
  updated_at: string;
}

interface BookReviewsSectionProps {
  bookId: number | string;
  bookTitle: string;
  token: string | null;
  currentUser: any | null;
  onReviewSaved?: () => void;
}

export function BookReviewsSection({
  bookId,
  bookTitle,
  token,
  currentUser,
  onReviewSaved,
}: BookReviewsSectionProps) {
  const [reviews, setReviews] = useState<ReviewItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Formulario de reseña
  const [rating, setRating] = useState<number>(10);
  const [reviewTitle, setReviewTitle] = useState('');
  const [reviewText, setReviewText] = useState('');
  const [myExistingReview, setMyExistingReview] = useState<ReviewItem | null>(null);

  const apiUrl = (import.meta as any).env.VITE_API_URL || 'http://localhost:8000';

  const fetchReviews = async () => {
    try {
      setLoading(true);
      const res = await fetch(`${apiUrl}/api/v1/books/reviews/?book=${bookId}`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (res.ok) {
        const data = await res.json();
        const results: ReviewItem[] = Array.isArray(data) ? data : data.results || [];
        setReviews(results);

        if (currentUser) {
          const found = results.find(
            (r: any) =>
              (r.user_id && r.user_id === currentUser.id) ||
              r.user === currentUser.id ||
              r.user === currentUser.username ||
              r.username === currentUser.username
          );
          if (found) {
            setMyExistingReview(found);
            setRating(found.rating);
            setReviewTitle(found.title || '');
            setReviewText(found.text || '');
          }
        }
      }
    } catch (e) {
      console.error('Error cargando reseñas:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (bookId) {
      fetchReviews();
    }
  }, [bookId, token, currentUser]);

  const handleSubmitReview = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token) {
      setErrorMessage('Debes iniciar sesión para publicar una reseña.');
      return;
    }
    setSubmitting(true);
    setErrorMessage(null);

    try {
      const res = await fetch(`${apiUrl}/api/v1/books/reviews/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          book_id: Number(bookId),
          book: Number(bookId),
          rating: rating,
          title: reviewTitle.trim() || null,
          text: reviewText.trim() || null,
        }),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'No se pudo guardar la reseña.');
      }

      setShowForm(false);
      await fetchReviews();
      if (onReviewSaved) {
        onReviewSaved();
      }
    } catch (err: any) {
      setErrorMessage(err.message || 'Error al enviar la reseña.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <section className="bg-white dark:bg-slate-800 rounded-3xl border border-slate-200/80 dark:border-slate-700 p-6 sm:p-8 shadow-sm space-y-6">
      {/* Encabezado de la sección */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-100 dark:border-slate-700/60">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xl">💬</span>
            <h2 className="text-lg sm:text-xl font-bold text-slate-900 dark:text-white">
              Reseñas de la comunidad
            </h2>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-teal-50 text-teal-700 dark:bg-teal-900/30 dark:text-teal-300">
              {reviews.length}
            </span>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Opiniones y críticas literarias públicas compartidas por los lectores.
          </p>
        </div>

        {token && (
          <button
            onClick={() => setShowForm(!showForm)}
            className="self-start sm:self-auto inline-flex items-center gap-2 bg-teal-600 hover:bg-teal-700 text-white text-xs font-bold px-4 py-2.5 rounded-2xl transition-all shadow-sm"
          >
            <span>✍️</span>
            <span>{myExistingReview ? (showForm ? 'Cancelar edición' : 'Editar mi reseña') : (showForm ? 'Cerrar formulario' : 'Escribir una reseña')}</span>
          </button>
        )}
      </div>

      {/* Formulario para publicar/editar reseña */}
      {showForm && (
        <form
          onSubmit={handleSubmitReview}
          className="p-5 bg-slate-50 dark:bg-slate-700/40 rounded-2xl border border-slate-200 dark:border-slate-600 space-y-4 animate-in fade-in duration-200"
        >
          <h3 className="text-sm font-bold text-slate-900 dark:text-white">
            {myExistingReview ? 'Editar tu reseña de ' : 'Tu reseña de '} "{bookTitle}"
          </h3>

          {errorMessage && (
            <div className="p-3 bg-rose-50 border border-rose-200 text-rose-700 rounded-xl text-xs font-semibold">
              {errorMessage}
            </div>
          )}

          {/* Selector de estrellas */}
          <div>
            <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1">
              Tu puntuación:
            </label>
            <div className="flex items-center gap-3">
              <StarRating
                rating={rating}
                maxRating={10}
                size="lg"
                interactive={true}
                onRatingChange={(newVal) => setRating(newVal)}
              />
              <span className="text-xs font-bold text-teal-700 dark:text-teal-300 bg-teal-50 dark:bg-teal-900/40 px-2 py-1 rounded-lg">
                {(rating / 2).toFixed(1)} / 5 ({rating}/10)
              </span>
            </div>
          </div>

          {/* Título de la reseña */}
          <div>
            <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1">
              Título de la reseña (opcional):
            </label>
            <input
              type="text"
              value={reviewTitle}
              onChange={(e) => setReviewTitle(e.target.value)}
              placeholder="Ej: Una obra maestra imprescindible..."
              maxLength={150}
              className="w-full text-xs rounded-xl border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-800 p-2.5 focus:ring-2 focus:ring-teal-500 focus:outline-none"
            />
          </div>

          {/* Texto de la reseña */}
          <div>
            <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1">
              Tu opinión o crítica literaria:
            </label>
            <textarea
              rows={4}
              value={reviewText}
              onChange={(e) => setReviewText(e.target.value)}
              placeholder="¿Qué te ha parecido la trama, el desarrollo de personajes o la prosa del autor?..."
              className="w-full text-xs rounded-xl border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-800 p-3 focus:ring-2 focus:ring-teal-500 focus:outline-none leading-relaxed"
            />
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={() => setShowForm(false)}
              className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-600 hover:bg-slate-200 dark:text-slate-300 dark:hover:bg-slate-600"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="bg-teal-600 hover:bg-teal-700 text-white text-xs font-bold px-5 py-2 rounded-xl shadow-md transition-all disabled:opacity-50"
            >
              {submitting ? 'Guardando...' : (myExistingReview ? 'Actualizar reseña' : 'Publicar reseña')}
            </button>
          </div>
        </form>
      )}

      {/* Listado de reseñas */}
      {loading ? (
        <div className="py-8 text-center text-xs text-slate-400">
          Cargando opiniones de la comunidad...
        </div>
      ) : reviews.length === 0 ? (
        <div className="py-10 text-center space-y-2 bg-slate-50/50 dark:bg-slate-800/50 rounded-2xl border border-dashed border-slate-200 dark:border-slate-700">
          <span className="text-3xl">📖</span>
          <h4 className="text-sm font-bold text-slate-700 dark:text-slate-200">
            Aún no hay reseñas públicas para este libro
          </h4>
          <p className="text-xs text-slate-400 max-w-sm mx-auto">
            ¡Sé el primer lector en compartir tu opinión y valoración con la comunidad!
          </p>
          {!token && (
            <p className="text-xs text-teal-600 pt-2 font-semibold">
              Inicia sesión para ser el primero en reseñar este libro.
            </p>
          )}
        </div>
      ) : (
        <div className="space-y-4 divide-y divide-slate-100 dark:divide-slate-700/60">
          {reviews.map((rev: any) => {
            const authorName = rev.username || (typeof rev.user === 'string' ? rev.user : '') || (rev.user?.username) || 'Lector';
            const rawAvatar = rev.avatar || rev.user_avatar || rev.user?.avatar;
            const avatarUrl = rawAvatar
              ? (rawAvatar.startsWith('http') ? rawAvatar : `${apiUrl}${rawAvatar}`)
              : null;
            const targetUserId = rev.user_id || (typeof rev.user === 'number' ? rev.user : rev.user?.id);
            const dateStr = rev.created_at
              ? new Date(rev.created_at).toLocaleDateString('es-ES', {
                  year: 'numeric',
                  month: 'short',
                  day: 'numeric',
                })
              : '';

            return (
              <article key={rev.id} className="pt-4 first:pt-0 space-y-2">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-center gap-3">
                    {avatarUrl ? (
                      <img
                        src={avatarUrl}
                        alt={authorName}
                        className="w-9 h-9 rounded-full object-cover border border-slate-200 dark:border-slate-600"
                      />
                    ) : (
                      <div className="w-9 h-9 rounded-full bg-gradient-to-tr from-teal-500 to-emerald-400 flex items-center justify-center text-white font-bold text-xs uppercase shadow-sm">
                        {(authorName || 'MB').slice(0, 2).toUpperCase()}
                      </div>
                    )}
                    <div>
                      {targetUserId ? (
                        <Link
                          to={`/users/${targetUserId}`}
                          className="text-xs font-bold text-slate-900 dark:text-white hover:text-teal-600 hover:underline"
                        >
                          {authorName}
                        </Link>
                      ) : (
                        <span className="text-xs font-bold text-slate-900 dark:text-white">
                          {authorName}
                        </span>
                      )}
                      <div className="text-[10px] text-slate-400">{dateStr}</div>
                    </div>
                  </div>

                  <div className="flex items-center">
                    <StarRating
                      rating={rev.rating}
                      maxRating={10}
                      size="sm"
                      interactive={false}
                      showBreakdownOnHover={false}
                    />
                  </div>
                </div>

                {rev.title && (
                  <h4 className="text-sm font-bold text-slate-800 dark:text-slate-100 pt-1">
                    {rev.title}
                  </h4>
                )}

                {rev.text && (
                  <p className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed whitespace-pre-line">
                    {rev.text}
                  </p>
                )}
              </article>
            );
          })}
        </div>
      )}
    </section>
  );
}
