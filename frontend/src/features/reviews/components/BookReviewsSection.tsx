import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { StarRating } from '../../../components/ui';
import { ReportModal } from '../../moderation';
import { reviewSchema, ReviewFormData } from '../schemas/reviewSchemas';

interface ReviewItem {
  id: number;
  user: number;
  username: string;
  avatar?: string | null;
  book: number;
  rating: number;
  title?: string | null;
  text?: string | null;
  image?: string | null;
  created_at: string;
  updated_at: string;
  likes_count?: number;
  user_has_liked?: boolean;
  comments_count?: number;
}

function renderFormattedInline(
  content: string,
  keyPrefix: string | number,
  revealedSpoilers: Record<string, boolean>,
  toggleSpoiler: (spoilerId: string) => void
): React.ReactNode {
  const tokens = content.split(/(\[spoiler\].*?\[\/spoiler\]|\*\*.*?\*\*|\*.*?\*)/g);

  return tokens.map((part, i) => {
    if (!part) return null;
    const tokenKey = `${keyPrefix}-${i}`;

    if (part.startsWith('[spoiler]') && part.endsWith('[/spoiler]')) {
      const inner = part.slice(9, -10);
      const isRevealed = !!revealedSpoilers[tokenKey];
      return (
        <span
          key={tokenKey}
          onClick={() => toggleSpoiler(tokenKey)}
          className={`cursor-pointer inline-block rounded px-1.5 py-0.5 text-xs font-medium transition-all ${
            isRevealed
              ? 'bg-amber-100 dark:bg-amber-950/60 text-amber-900 dark:text-amber-200 border border-amber-300 dark:border-amber-700/50'
              : 'bg-slate-300 dark:bg-slate-700 text-transparent select-none hover:bg-slate-400 dark:hover:bg-slate-600'
          }`}
          title={isRevealed ? 'Haz clic para ocultar spoiler' : 'Spoiler oculto - Haz clic para ver'}
        >
          {isRevealed ? `⚠️ ${inner}` : '⚠️ SPOILER (Click para ver)'}
        </span>
      );
    }

    if (part.startsWith('**') && part.endsWith('**') && part.length >= 4) {
      return (
        <strong key={tokenKey} className="font-semibold text-slate-900 dark:text-white">
          {part.slice(2, -2)}
        </strong>
      );
    }

    if (part.startsWith('*') && part.endsWith('*') && part.length >= 2) {
      return (
        <em key={tokenKey} className="italic text-slate-800 dark:text-slate-200">
          {part.slice(1, -1)}
        </em>
      );
    }

    return <React.Fragment key={tokenKey}>{part}</React.Fragment>;
  });
}

function RichReviewText({ text }: { text: string }) {
  const [revealedSpoilers, setRevealedSpoilers] = useState<Record<string, boolean>>({});

  const toggleSpoiler = (id: string) => {
    setRevealedSpoilers((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  if (!text) return null;

  const lines = text.split('\n');

  return (
    <div className="text-xs text-slate-700 dark:text-slate-200 leading-relaxed space-y-1.5">
      {lines.map((line, idx) => {
        const trimmed = line.trim();
        if (!trimmed) {
          return <div key={idx} className="h-1.5" />;
        }

        if (line.startsWith('> ')) {
          return (
            <blockquote
              key={idx}
              className="border-l-4 border-teal-500 pl-3 py-1 italic text-slate-600 dark:text-slate-400 bg-slate-50 dark:bg-slate-800/60 rounded-r-lg my-1"
            >
              {renderFormattedInline(line.slice(2), idx, revealedSpoilers, toggleSpoiler)}
            </blockquote>
          );
        }

        if (line.startsWith('### ')) {
          return (
            <h5 key={idx} className="font-bold text-sm text-slate-900 dark:text-white pt-1">
              {renderFormattedInline(line.slice(4), idx, revealedSpoilers, toggleSpoiler)}
            </h5>
          );
        }

        if (line.startsWith('- ') || line.startsWith('* ')) {
          return (
            <div key={idx} className="flex items-start gap-2 pl-2">
              <span className="text-teal-500 font-bold">•</span>
              <span>
                {renderFormattedInline(line.slice(2), idx, revealedSpoilers, toggleSpoiler)}
              </span>
            </div>
          );
        }

        return (
          <p key={idx}>
            {renderFormattedInline(line, idx, revealedSpoilers, toggleSpoiler)}
          </p>
        );
      })}
    </div>
  );
}

interface CommentItem {
  id: number;
  review: number;
  user: {
    id: number;
    username: string;
    avatar?: string | null;
  };
  content: string;
  created_at: string;
  is_owner: boolean;
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

  // Likes y Comentarios
  const [expandedComments, setExpandedComments] = useState<Record<number, boolean>>({});
  const [commentsData, setCommentsData] = useState<Record<number, CommentItem[]>>({});
  const [loadingComments, setLoadingComments] = useState<Record<number, boolean>>({});
  const [newCommentText, setNewCommentText] = useState<Record<number, string>>({});
  const [submittingComment, setSubmittingComment] = useState<Record<number, boolean>>({});
  const [likePending, setLikePending] = useState<Record<number, boolean>>({});
  const [reportingTarget, setReportingTarget] = useState<{
    type: 'review' | 'comment';
    id: number;
    title?: string;
  } | null>(null);

  // Formulario de reseña con React Hook Form y Zod
  const [myExistingReview, setMyExistingReview] = useState<ReviewItem | null>(null);
  const [selectedImage, setSelectedImage] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [activeEditorTab, setActiveEditorTab] = useState<'write' | 'preview'>('write');
  const fileInputRef = React.useRef<HTMLInputElement | null>(null);
  const textareaRef = React.useRef<HTMLTextAreaElement | null>(null);

  const {
    register: registerReview,
    handleSubmit: handleSubmitReview,
    setValue: setReviewValue,
    watch: watchReview,
    reset: resetReview,
    formState: { errors: reviewErrors },
  } = useForm<ReviewFormData>({
    resolver: zodResolver(reviewSchema),
    defaultValues: {
      rating: 5,
      title: '',
      text: '',
    },
  });

  const currentRating = watchReview('rating');
  const watchedText = watchReview('text') || '';

  const apiUrl = (import.meta as any).env.VITE_API_URL || 'http://localhost:8000';

  const insertFormatting = (prefix: string, suffix: string = '') => {
    const textarea = textareaRef.current;
    if (!textarea) return;

    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const current = textarea.value || '';
    const selected = current.substring(start, end);

    const replacement = selected ? `${prefix}${selected}${suffix}` : `${prefix}${suffix}`;
    const nextVal = current.substring(0, start) + replacement + current.substring(end);

    setReviewValue('text', nextVal, { shouldValidate: true });

    setTimeout(() => {
      textarea.focus();
      const cursor = selected
        ? start + prefix.length + selected.length + suffix.length
        : start + prefix.length;
      textarea.setSelectionRange(cursor, cursor);
    }, 10);
  };

  const handleImageChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (file.size > 5 * 1024 * 1024) {
      setErrorMessage('La fotografía no puede superar 5 MB.');
      return;
    }
    if (!file.type.startsWith('image/')) {
      setErrorMessage('Por favor selecciona una imagen válida (JPG, PNG o WebP).');
      return;
    }

    setSelectedImage(file);
    const reader = new FileReader();
    reader.onloadend = () => {
      setImagePreview(reader.result as string);
    };
    reader.readAsDataURL(file);
  };

  const handleRemoveImage = () => {
    setSelectedImage(null);
    setImagePreview(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const fetchReviews = async () => {
    try {
      setLoading(true);
      const res = await fetch(`${apiUrl}/api/v1/reviews/?book=${bookId}`, {
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
            setReviewValue('rating', found.rating);
            setReviewValue('title', found.title || '');
            setReviewValue('text', found.text || '');
            if (found.image) {
              setImagePreview(
                found.image.startsWith('http') ? found.image : `${apiUrl}${found.image}`
              );
            }
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

  const toggleLike = async (reviewId: number) => {
    if (!token) {
      alert('Inicia sesión para indicar que te gusta esta reseña.');
      return;
    }
    if (likePending[reviewId]) return;

    setLikePending((prev) => ({ ...prev, [reviewId]: true }));
    try {
      const res = await fetch(`${apiUrl}/api/v1/reviews/${reviewId}/like/`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });
      if (res.ok) {
        const data = await res.json();
        setReviews((prev) =>
          prev.map((r) =>
            r.id === reviewId
              ? { ...r, likes_count: data.likes_count, user_has_liked: data.liked }
              : r
          )
        );
      }
    } catch (err) {
      console.error('Error toggling like:', err);
    } finally {
      setLikePending((prev) => ({ ...prev, [reviewId]: false }));
    }
  };

  const loadComments = async (reviewId: number) => {
    setLoadingComments((prev) => ({ ...prev, [reviewId]: true }));
    try {
      const res = await fetch(`${apiUrl}/api/v1/reviews/${reviewId}/comments/`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (res.ok) {
        const data = await res.json();
        setCommentsData((prev) => ({ ...prev, [reviewId]: Array.isArray(data) ? data : [] }));
      }
    } catch (err) {
      console.error('Error loading comments:', err);
    } finally {
      setLoadingComments((prev) => ({ ...prev, [reviewId]: false }));
    }
  };

  const toggleComments = (reviewId: number) => {
    const nextState = !expandedComments[reviewId];
    setExpandedComments((prev) => ({ ...prev, [reviewId]: nextState }));
    if (nextState && !commentsData[reviewId]) {
      loadComments(reviewId);
    }
  };

  const handleAddComment = async (reviewId: number, e: React.FormEvent) => {
    e.preventDefault();
    const content = (newCommentText[reviewId] || '').trim();
    if (!content || !token) return;

    setSubmittingComment((prev) => ({ ...prev, [reviewId]: true }));
    try {
      const res = await fetch(`${apiUrl}/api/v1/reviews/${reviewId}/comments/`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ content }),
      });
      if (res.ok) {
        const newC = await res.json();
        setCommentsData((prev) => ({
          ...prev,
          [reviewId]: [...(prev[reviewId] || []), newC],
        }));
        setNewCommentText((prev) => ({ ...prev, [reviewId]: '' }));
        setReviews((prev) =>
          prev.map((r) =>
            r.id === reviewId ? { ...r, comments_count: (r.comments_count || 0) + 1 } : r
          )
        );
      }
    } catch (err) {
      console.error('Error adding comment:', err);
    } finally {
      setSubmittingComment((prev) => ({ ...prev, [reviewId]: false }));
    }
  };

  const handleDeleteComment = async (reviewId: number, commentId: number) => {
    if (!token || !window.confirm('¿Deseas eliminar tu comentario?')) return;

    try {
      const res = await fetch(`${apiUrl}/api/v1/reviews/${reviewId}/comments/${commentId}/`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok || res.status === 204) {
        setCommentsData((prev) => ({
          ...prev,
          [reviewId]: (prev[reviewId] || []).filter((c) => c.id !== commentId),
        }));
        setReviews((prev) =>
          prev.map((r) =>
            r.id === reviewId
              ? { ...r, comments_count: Math.max(0, (r.comments_count || 1) - 1) }
              : r
          )
        );
      }
    } catch (err) {
      console.error('Error deleting comment:', err);
    }
  };

  const onSubmitReview = async (data: ReviewFormData) => {
    if (!token) {
      setErrorMessage('Debes iniciar sesión para publicar una reseña.');
      return;
    }
    setSubmitting(true);
    setErrorMessage(null);

    try {
      let res: Response;
      if (selectedImage) {
        const formData = new FormData();
        formData.append('book_id', String(bookId));
        formData.append('book', String(bookId));
        formData.append('rating', String(data.rating));
        if (data.title?.trim()) formData.append('title', data.title.trim());
        if (data.text?.trim()) formData.append('text', data.text.trim());
        formData.append('image', selectedImage);

        res = await fetch(`${apiUrl}/api/v1/reviews/`, {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${token}`,
          },
          body: formData,
        });
      } else {
        res = await fetch(`${apiUrl}/api/v1/reviews/`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            book_id: Number(bookId),
            book: Number(bookId),
            rating: data.rating,
            title: data.title?.trim() || null,
            text: data.text?.trim() || null,
          }),
        });
      }

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || (err.image && err.image[0]) || 'No se pudo guardar la reseña.');
      }

      setShowForm(false);
      setSelectedImage(null);
      setImagePreview(null);
      setActiveEditorTab('write');
      resetReview({
        rating: 5,
        title: '',
        text: '',
      });
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

  const { ref: textFormRef, ...textFormProps } = registerReview('text');

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
            onClick={() => {
              if (showForm) {
                handleRemoveImage();
                setActiveEditorTab('write');
              }
              setShowForm(!showForm);
            }}
            className="self-start sm:self-auto inline-flex items-center gap-2 bg-teal-600 hover:bg-teal-700 text-white text-xs font-bold px-4 py-2.5 rounded-2xl transition-all shadow-sm"
          >
            <span>✍️</span>
            <span>
              {myExistingReview
                ? showForm
                  ? 'Cancelar edición'
                  : 'Editar mi reseña'
                : showForm
                  ? 'Cerrar formulario'
                  : 'Escribir una reseña'}
            </span>
          </button>
        )}
      </div>

      {/* Formulario para publicar/editar reseña */}
      {showForm && (
        <form
          onSubmit={handleSubmitReview(onSubmitReview)}
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
                rating={currentRating}
                maxRating={5}
                size="lg"
                interactive={true}
                onRatingChange={(newVal) =>
                  setReviewValue('rating', newVal, { shouldValidate: true })
                }
              />
              <span className="text-xs font-bold text-teal-700 dark:text-teal-300 bg-teal-50 dark:bg-teal-900/40 px-2 py-1 rounded-lg">
                {currentRating} / 5
              </span>
            </div>
            {reviewErrors.rating && (
              <p className="text-xs text-rose-500 mt-1">{reviewErrors.rating.message}</p>
            )}
          </div>

          {/* Título de la reseña */}
          <div>
            <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1">
              Título de la reseña (opcional):
            </label>
            <input
              type="text"
              {...registerReview('title')}
              placeholder="Ej: Una obra maestra imprescindible..."
              maxLength={150}
              className="w-full text-xs rounded-xl border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-800 p-2.5 focus:ring-2 focus:ring-teal-500 focus:outline-none"
            />
            {reviewErrors.title && (
              <p className="text-xs text-rose-500 mt-1">{reviewErrors.title.message}</p>
            )}
          </div>

          {/* Editor de texto enriquecido */}
          <div>
            <div className="flex items-center justify-between pb-1">
              <label className="block text-xs font-bold text-slate-700 dark:text-slate-300">
                Tu opinión o crítica literaria:
              </label>
              <div className="flex items-center gap-1 bg-slate-200/70 dark:bg-slate-800/80 p-0.5 rounded-lg text-[11px] font-semibold">
                <button
                  type="button"
                  onClick={() => setActiveEditorTab('write')}
                  className={`px-2.5 py-1 rounded-md transition-all ${
                    activeEditorTab === 'write'
                      ? 'bg-white dark:bg-slate-700 text-teal-600 dark:text-teal-300 shadow-xs'
                      : 'text-slate-500 hover:text-slate-800 dark:text-slate-400'
                  }`}
                >
                  ✏️ Escribir
                </button>
                <button
                  type="button"
                  onClick={() => setActiveEditorTab('preview')}
                  className={`px-2.5 py-1 rounded-md transition-all ${
                    activeEditorTab === 'preview'
                      ? 'bg-white dark:bg-slate-700 text-teal-600 dark:text-teal-300 shadow-xs'
                      : 'text-slate-500 hover:text-slate-800 dark:text-slate-400'
                  }`}
                >
                  👁️ Vista previa
                </button>
              </div>
            </div>

            {/* Barra de herramientas para formatear */}
            {activeEditorTab === 'write' && (
              <div className="flex flex-wrap items-center gap-1 p-1.5 mb-1.5 bg-slate-100 dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-600 text-xs">
                <button
                  type="button"
                  onClick={() => insertFormatting('**', '**')}
                  className="px-2 py-1 font-bold rounded-lg hover:bg-white dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 transition-colors"
                  title="Negrita (**texto**)"
                >
                  B
                </button>
                <button
                  type="button"
                  onClick={() => insertFormatting('*', '*')}
                  className="px-2 py-1 italic rounded-lg hover:bg-white dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 transition-colors"
                  title="Cursiva (*texto*)"
                >
                  I
                </button>
                <button
                  type="button"
                  onClick={() => insertFormatting('### ')}
                  className="px-2 py-1 font-bold text-xs rounded-lg hover:bg-white dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 transition-colors"
                  title="Encabezado (### Título)"
                >
                  H
                </button>
                <button
                  type="button"
                  onClick={() => insertFormatting('> ')}
                  className="px-2 py-1 rounded-lg hover:bg-white dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 transition-colors"
                  title="Cita literaria (> Cita)"
                >
                  ❝ Cita
                </button>
                <button
                  type="button"
                  onClick={() => insertFormatting('- ')}
                  className="px-2 py-1 rounded-lg hover:bg-white dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 transition-colors"
                  title="Elemento de lista (- Item)"
                >
                  • Lista
                </button>
                <button
                  type="button"
                  onClick={() => insertFormatting('[spoiler]', '[/spoiler]')}
                  className="px-2.5 py-1 font-semibold rounded-lg bg-amber-100 hover:bg-amber-200 text-amber-900 dark:bg-amber-950/60 dark:hover:bg-amber-900/80 dark:text-amber-200 transition-colors text-[11px]"
                  title="Ocultar spoiler para otros lectores"
                >
                  ⚠️ Spoiler
                </button>
                <div className="ml-auto text-[10px] text-slate-400 font-mono pr-1">
                  {watchedText.length}/5000
                </div>
              </div>
            )}

            {/* Pestaña de escritura */}
            {activeEditorTab === 'write' ? (
              <textarea
                rows={5}
                ref={(el) => {
                  textFormRef(el);
                  textareaRef.current = el;
                }}
                {...textFormProps}
                placeholder="Comparte tus impresiones detalladas, reflexiones sobre los personajes, citas favoritas o advertencias de spoiler..."
                className="w-full text-xs rounded-xl border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-800 p-3 focus:ring-2 focus:ring-teal-500 focus:outline-none leading-relaxed"
              />
            ) : (
              /* Pestaña de vista previa */
              <div className="min-h-[120px] p-3 rounded-xl border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-800">
                {watchedText.trim() ? (
                  <RichReviewText text={watchedText} />
                ) : (
                  <p className="text-xs italic text-slate-400 text-center py-4">
                    Tu vista previa aparecerá aquí cuando escribas tu reseña...
                  </p>
                )}
              </div>
            )}

            {reviewErrors.text && (
              <p className="text-xs text-rose-500 mt-1">{reviewErrors.text.message}</p>
            )}
          </div>

          {/* Subida de foto o imagen de la reseña */}
          <div className="space-y-2 pt-1 border-t border-slate-200/60 dark:border-slate-600/60">
            <div className="flex items-center justify-between">
              <label className="block text-xs font-bold text-slate-700 dark:text-slate-300">
                📸 Adjuntar fotografía (opcional):
              </label>
              <span className="text-[10px] text-slate-400">JPG, PNG o WebP hasta 5 MB</span>
            </div>

            <input
              type="file"
              ref={fileInputRef}
              accept="image/*"
              onChange={handleImageChange}
              className="hidden"
            />

            {!imagePreview ? (
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                className="w-full py-3 px-4 border border-dashed border-slate-300 dark:border-slate-600 hover:border-teal-500 rounded-xl bg-white dark:bg-slate-800 text-xs text-slate-600 dark:text-slate-300 font-medium flex items-center justify-center gap-2 hover:bg-teal-50/50 dark:hover:bg-slate-700/50 transition-colors"
              >
                <span>📷</span>
                <span>Haz clic para añadir una foto de tu ejemplar, cita o ilustración</span>
              </button>
            ) : (
              <div className="relative inline-block border border-slate-200 dark:border-slate-600 rounded-xl p-1 bg-white dark:bg-slate-800">
                <img
                  src={imagePreview}
                  alt="Vista previa de la fotografía"
                  className="h-28 w-auto rounded-lg object-cover"
                />
                <button
                  type="button"
                  onClick={handleRemoveImage}
                  className="absolute -top-2 -right-2 bg-rose-600 text-white rounded-full w-6 h-6 flex items-center justify-center text-xs font-bold shadow-md hover:bg-rose-700 transition-colors"
                  title="Eliminar imagen"
                >
                  ✕
                </button>
              </div>
            )}
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={() => {
                handleRemoveImage();
                setActiveEditorTab('write');
                setShowForm(false);
              }}
              className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-600 hover:bg-slate-200 dark:text-slate-300 dark:hover:bg-slate-600"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="bg-teal-600 hover:bg-teal-700 text-white text-xs font-bold px-5 py-2 rounded-xl shadow-md transition-all disabled:opacity-50"
            >
              {submitting
                ? 'Guardando...'
                : myExistingReview
                  ? 'Actualizar reseña'
                  : 'Publicar reseña'}
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
            const authorName =
              rev.username ||
              (typeof rev.user === 'string' ? rev.user : '') ||
              rev.user?.username ||
              'Lector';
            const rawAvatar = rev.avatar || rev.user_avatar || rev.user?.avatar;
            const avatarUrl = rawAvatar
              ? rawAvatar.startsWith('http')
                ? rawAvatar
                : `${apiUrl}${rawAvatar}`
              : null;
            const targetUserId =
              rev.user_id || (typeof rev.user === 'number' ? rev.user : rev.user?.id);
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
                      maxRating={5}
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
                  <div className="pt-1">
                    <RichReviewText text={rev.text} />
                  </div>
                )}

                {rev.image && (
                  <div className="pt-2">
                    <a
                      href={rev.image.startsWith('http') ? rev.image : `${apiUrl}${rev.image}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-block"
                    >
                      <img
                        src={rev.image.startsWith('http') ? rev.image : `${apiUrl}${rev.image}`}
                        alt={`Fotografía adjunta por ${authorName}`}
                        className="max-h-72 w-auto max-w-full rounded-2xl object-cover border border-slate-200 dark:border-slate-700 shadow-xs hover:opacity-95 transition-opacity"
                        loading="lazy"
                      />
                    </a>
                  </div>
                )}

                {/* Barra de interacción social: Likes y Comentarios */}
                <div className="flex items-center gap-4 pt-2 border-t border-slate-100 dark:border-slate-700/50 text-xs">
                  <button
                    type="button"
                    onClick={() => toggleLike(rev.id)}
                    disabled={likePending[rev.id]}
                    className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-xl font-medium transition-all ${
                      rev.user_has_liked
                        ? 'bg-rose-50 text-rose-600 dark:bg-rose-950/40 dark:text-rose-400 font-bold'
                        : 'text-slate-500 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-700/50'
                    }`}
                    title={rev.user_has_liked ? 'Ya no me gusta' : 'Me gusta'}
                  >
                    <span>{rev.user_has_liked ? '❤️' : '🤍'}</span>
                    <span>{rev.likes_count || 0}</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => toggleComments(rev.id)}
                    className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-xl text-slate-500 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-700/50 transition-all font-medium"
                  >
                    <span>💬</span>
                    <span>
                      {rev.comments_count || 0}{' '}
                      {rev.comments_count === 1 ? 'comentario' : 'comentarios'}
                    </span>
                  </button>

                  {token && (
                    <button
                      type="button"
                      onClick={() =>
                        setReportingTarget({
                          type: 'review',
                          id: rev.id,
                          title: rev.title || `Reseña de ${authorName}`,
                        })
                      }
                      className="inline-flex items-center gap-1 px-2 py-1 rounded-xl text-slate-400 hover:text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/30 transition-all font-medium ml-auto"
                      title="Denunciar reseña"
                    >
                      <span>🚩</span>
                      <span className="hidden sm:inline">Denunciar</span>
                    </button>
                  )}
                </div>

                {/* Hilo de comentarios expandible */}
                {expandedComments[rev.id] && (
                  <div className="mt-3 pl-3 sm:pl-4 border-l-2 border-teal-500/40 dark:border-teal-400/30 space-y-3 animate-in fade-in duration-200">
                    {loadingComments[rev.id] ? (
                      <div className="text-[11px] text-slate-400 py-2">Cargando comentarios...</div>
                    ) : (commentsData[rev.id] || []).length === 0 ? (
                      <div className="text-[11px] text-slate-400 italic py-1">
                        No hay comentarios todavía en esta reseña. ¡Sé el primero en responder!
                      </div>
                    ) : (
                      <div className="space-y-2 pt-1">
                        {(commentsData[rev.id] || []).map((c) => {
                          const cAvatar = c.user?.avatar
                            ? c.user.avatar.startsWith('http')
                              ? c.user.avatar
                              : `${apiUrl}${c.user.avatar}`
                            : null;
                          const cDate = c.created_at
                            ? new Date(c.created_at).toLocaleDateString('es-ES', {
                                month: 'short',
                                day: 'numeric',
                                hour: '2-digit',
                                minute: '2-digit',
                              })
                            : '';

                          return (
                            <div
                              key={c.id}
                              className="p-2.5 rounded-xl bg-slate-50/80 dark:bg-slate-700/30 border border-slate-100 dark:border-slate-700/60 text-xs flex items-start justify-between gap-2"
                            >
                              <div className="flex items-start gap-2.5">
                                {cAvatar ? (
                                  <img
                                    src={cAvatar}
                                    alt={c.user?.username || ''}
                                    className="w-6 h-6 rounded-full object-cover border border-slate-200 dark:border-slate-600 mt-0.5"
                                  />
                                ) : (
                                  <div className="w-6 h-6 rounded-full bg-teal-600/80 text-white font-bold text-[10px] flex items-center justify-center mt-0.5">
                                    {(c.user?.username || 'U').slice(0, 1).toUpperCase()}
                                  </div>
                                )}
                                <div className="space-y-0.5">
                                  <div className="flex items-center gap-2">
                                    <Link
                                      to={`/users/${c.user?.id}`}
                                      className="font-bold text-slate-800 dark:text-slate-200 hover:text-teal-600 text-[11px]"
                                    >
                                      {c.user?.username}
                                    </Link>
                                    <span className="text-[10px] text-slate-400">{cDate}</span>
                                  </div>
                                  <p className="text-slate-600 dark:text-slate-300 leading-snug text-xs">
                                    {c.content}
                                  </p>
                                </div>
                              </div>

                              <div className="flex items-center gap-1 shrink-0">
                                {token && (
                                  <button
                                    type="button"
                                    onClick={() =>
                                      setReportingTarget({
                                        type: 'comment',
                                        id: c.id,
                                        title: `Comentario de @${c.user?.username}`,
                                      })
                                    }
                                    className="text-slate-400 hover:text-rose-500 p-1 text-[11px] transition-colors"
                                    title="Denunciar comentario"
                                  >
                                    🚩
                                  </button>
                                )}
                                {c.is_owner && (
                                  <button
                                    type="button"
                                    onClick={() => handleDeleteComment(rev.id, c.id)}
                                    className="text-slate-400 hover:text-rose-500 p-1 text-[11px] transition-colors"
                                    title="Eliminar comentario"
                                  >
                                    🗑️
                                  </button>
                                )}
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    )}

                    {/* Formulario para añadir comentario */}
                    {token ? (
                      <form
                        onSubmit={(e) => handleAddComment(rev.id, e)}
                        className="flex items-center gap-2 pt-1"
                      >
                        <input
                          type="text"
                          value={newCommentText[rev.id] || ''}
                          onChange={(e) =>
                            setNewCommentText((prev) => ({ ...prev, [rev.id]: e.target.value }))
                          }
                          placeholder="Escribe una respuesta o comentario..."
                          maxLength={500}
                          className="flex-1 text-xs rounded-xl border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-800 px-3 py-2 focus:ring-2 focus:ring-teal-500 focus:outline-none"
                        />
                        <button
                          type="submit"
                          disabled={
                            submittingComment[rev.id] || !(newCommentText[rev.id] || '').trim()
                          }
                          className="px-3 py-2 rounded-xl text-xs font-bold bg-teal-600 hover:bg-teal-700 text-white disabled:opacity-50 transition-all shadow-sm shrink-0"
                        >
                          {submittingComment[rev.id] ? '...' : 'Comentar'}
                        </button>
                      </form>
                    ) : (
                      <div className="text-[11px] text-slate-400 pt-1">
                        Inicia sesión para dejar un comentario en esta reseña.
                      </div>
                    )}
                  </div>
                )}
              </article>
            );
          })}
        </div>
      )}

      {/* Modal universal de denuncia de contenido */}
      <ReportModal
        isOpen={!!reportingTarget}
        onClose={() => setReportingTarget(null)}
        targetType={reportingTarget?.type || 'review'}
        targetId={reportingTarget?.id || 0}
        targetTitle={reportingTarget?.title}
      />
    </section>
  );
}
export default BookReviewsSection;
