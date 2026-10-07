import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuthStore } from '../../../store/auth';
import { createErrata } from '../../../services/erratas';
import { Spinner, Modal, Button } from 'flowbite-react';
import {
  HiBadgeCheck,
  HiOutlineGlobeAlt,
  HiOutlineBookOpen,
  HiOutlineStar,
  HiOutlineChatAlt2,
  HiOutlineUsers,
  HiOutlineShieldCheck,
} from 'react-icons/hi';
import { BsTwitterX, BsInstagram, BsWikipedia } from 'react-icons/bs';
import { AuthorEventsSection } from '../components/AuthorEventsSection';
import { AuthorPublicationsSection } from '../components/AuthorPublicationsSection';

interface AuthorData {
  id: number;
  name: string;
  bio?: string;
  biography?: string;
  photo?: string;
  birth_date?: string;
  death_date?: string;
  nationality?: string;
  website?: string;
  twitter?: string;
  instagram?: string;
  wikipedia_url?: string;
  goodreads_url?: string;
  is_verified?: boolean;
  is_claimed?: boolean;
  can_claim?: boolean;
  claimed_by?: number;
  published_books_count?: number;
  average_rating?: number;
  total_reviews_count?: number;
  total_readers_count?: number;
}

interface AuthorBookItem {
  id: number;
  title: string;
  cover?: string;
  published_date?: string;
  average_rating?: number;
}

export function Author() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { token, user } = useAuthStore();
  const [author, setAuthor] = useState<AuthorData | null>(null);
  const [localBooks, setLocalBooks] = useState<AuthorBookItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Erratas
  const [errataText, setErrataText] = useState('');
  const [errataType, setErrataType] = useState<'errata' | 'suggestion' | 'other'>('errata');
  const [reportSent, setReportSent] = useState(false);

  // Reclamación de autor
  const [isClaimModalOpen, setIsClaimModalOpen] = useState(false);
  const [claimContactEmail, setClaimContactEmail] = useState('');
  const [claimProofDesc, setClaimProofDesc] = useState('');
  const [claimSupportingLink, setClaimSupportingLink] = useState('');
  const [submittingClaim, setSubmittingClaim] = useState(false);
  const [claimSuccessMessage, setClaimSuccessMessage] = useState<string | null>(null);
  const [claimErrorMessage, setClaimErrorMessage] = useState<string | null>(null);
  const [userClaimStatus, setUserClaimStatus] = useState<string | null>(null);

  const apiUrl = (import.meta as any).env.VITE_API_URL || 'http://localhost:8000';

  const loadAuthorData = async () => {
    if (!id) return;
    try {
      setLoading(true);
      setError(null);
      const headers: Record<string, string> = {};
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const res = await fetch(`${apiUrl}/api/v1/books/authors/${id}/`, { headers });
      if (!res.ok) throw new Error('No se pudo cargar la información del autor');

      const data = await res.json();
      if (data?.photo && typeof data.photo === 'string' && data.photo.startsWith('/')) {
        data.photo = `${apiUrl}${data.photo}`;
      }
      setAuthor(data);

      // Cargar libros del autor
      const booksRes = await fetch(`${apiUrl}/api/v1/books/authors/${id}/books/`, { headers });
      if (booksRes.ok) {
        const bData = await booksRes.json();
        const bList = Array.isArray(bData) ? bData : bData.local || [];
        setLocalBooks(bList);
      }

      // Si el usuario está autenticado, consultar si ya tiene una reclamación pendiente
      if (token) {
        try {
          const claimRes = await fetch(`${apiUrl}/api/v1/books/authors/${id}/claim-status/`, {
            headers: { Authorization: `Bearer ${token}` },
          });
          if (claimRes.ok) {
            const claimData = await claimRes.json();
            setUserClaimStatus(claimData.claim ? claimData.claim.status : null);
          }
        } catch {
          // silent
        }
      }
    } catch (e: any) {
      console.error(e);
      setError(e.message || 'Error al obtener datos');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAuthorData();
  }, [id, token]);

  const handleRefreshAuthor = async () => {
    if (!token || !id) return;
    setRefreshing(true);
    try {
      await fetch(`${apiUrl}/api/v1/books/authors/${id}/refresh-books/`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
      await loadAuthorData();
    } catch (e) {
      console.error(e);
    } finally {
      setRefreshing(false);
    }
  };

  const handleSendErrata = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token || !id || !errataText.trim()) return;
    try {
      await createErrata(token, {
        author_id: Number(id),
        type: errataType,
        text: errataText.trim(),
      });
      setErrataText('');
      setReportSent(true);
      setTimeout(() => setReportSent(false), 4000);
    } catch (e) {
      alert('No se pudo enviar el reporte.');
    }
  };

  const handleOpenClaimModal = () => {
    setClaimContactEmail(user?.email || '');
    setClaimProofDesc('');
    setClaimSupportingLink('');
    setClaimSuccessMessage(null);
    setClaimErrorMessage(null);
    setIsClaimModalOpen(true);
  };

  const handleSubmitClaim = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token || !id) return;

    if (!claimProofDesc.trim()) {
      setClaimErrorMessage('Por favor incluye una descripción detallada o acreditación.');
      return;
    }

    try {
      setSubmittingClaim(true);
      setClaimErrorMessage(null);

      const res = await fetch(`${apiUrl}/api/v1/books/authors/${id}/claim/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          contact_email: claimContactEmail.trim() || user?.email,
          proof_description: claimProofDesc.trim(),
          supporting_link: claimSupportingLink.trim(),
        }),
      });

      const resData = await res.json();

      if (!res.ok) {
        throw new Error(resData.detail || resData.error || 'Error al enviar la solicitud');
      }

      setClaimSuccessMessage(
        '¡Solicitud enviada con éxito! Nuestro equipo editorial la revisará y recibirás una notificación cuando sea resuelta.'
      );
      setUserClaimStatus('pending');
      setTimeout(() => {
        setIsClaimModalOpen(false);
      }, 3500);
    } catch (err: any) {
      setClaimErrorMessage(err.message || 'Error al procesar la reclamación');
    } finally {
      setSubmittingClaim(false);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-[50vh]">
        <Spinner size="xl" className="fill-teal-600" />
      </div>
    );
  }

  if (error || !author) {
    return (
      <div className="max-w-2xl mx-auto p-8 bg-white dark:bg-slate-800 rounded-3xl border border-slate-200 dark:border-slate-700 text-center space-y-3">
        <span className="text-4xl">⚠️</span>
        <h3 className="text-lg font-bold text-slate-900 dark:text-white">
          {error || 'Autor no encontrado'}
        </h3>
        <button
          onClick={() => navigate(-1)}
          className="mt-2 text-teal-600 dark:text-teal-400 hover:underline text-sm font-semibold cursor-pointer"
        >
          ← Volver atrás
        </button>
      </div>
    );
  }

  const booksCount = author.published_books_count ?? localBooks.length;
  const avgRating = author.average_rating ? Number(author.average_rating).toFixed(1) : null;
  const reviewsCount = author.total_reviews_count ?? 0;
  const readersCount = author.total_readers_count ?? 0;

  return (
    <div className="max-w-5xl mx-auto space-y-8 pb-12">
      {/* Botón Volver */}
      <button
        onClick={() => navigate(-1)}
        className="inline-flex items-center gap-1.5 text-xs font-bold text-slate-500 hover:text-teal-600 dark:hover:text-teal-400 transition-colors cursor-pointer"
      >
        <span>←</span>
        <span>Volver</span>
      </button>

      {/* Hero del Autor */}
      <div className="bg-white dark:bg-slate-900 rounded-3xl border border-slate-200/80 dark:border-slate-800 p-6 sm:p-8 shadow-sm relative overflow-hidden space-y-6">
        <div className="flex flex-col sm:flex-row items-center sm:items-start gap-6">
          {/* Foto de Autor */}
          <div className="relative shrink-0">
            {author.photo ? (
              <img
                src={author.photo}
                alt={author.name}
                className="w-32 h-32 sm:w-44 sm:h-44 rounded-3xl object-cover shadow-lg border-4 border-white dark:border-slate-800"
              />
            ) : (
              <div className="w-32 h-32 sm:w-44 sm:h-44 rounded-3xl bg-gradient-to-tr from-teal-600 to-emerald-700 text-white flex items-center justify-center text-4xl font-extrabold shadow-lg border-4 border-white dark:border-slate-800">
                {author.name[0]?.toUpperCase() || 'A'}
              </div>
            )}

            {author.is_verified && (
              <div
                className="absolute -bottom-2 -right-2 bg-sky-500 text-white p-1.5 rounded-full shadow-md border-2 border-white dark:border-slate-900"
                title="Autor Oficial Verificado"
              >
                <HiBadgeCheck className="w-5 h-5" />
              </div>
            )}
          </div>

          {/* Información Principal */}
          <div className="flex-1 text-center sm:text-left space-y-3">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <div className="flex items-center justify-center sm:justify-start gap-2 flex-wrap">
                  <span className="text-xs font-bold uppercase tracking-wider text-teal-600 dark:text-teal-400">
                    Escritor / Autor
                  </span>
                  {author.is_verified && (
                    <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-sky-50 dark:bg-sky-950/60 text-sky-700 dark:text-sky-300 border border-sky-200 dark:border-sky-800">
                      <HiBadgeCheck className="w-4 h-4 text-sky-500" />
                      Oficial Verificado
                    </span>
                  )}
                  {author.nationality && (
                    <span className="text-xs text-slate-500 dark:text-slate-400">
                      • {author.nationality}
                    </span>
                  )}
                </div>

                <h1 className="text-2xl sm:text-4xl font-black text-slate-900 dark:text-white tracking-tight mt-1">
                  {author.name}
                </h1>

                {(author.birth_date || author.death_date) && (
                  <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                    {author.birth_date && `Nacimiento: ${author.birth_date}`}
                    {author.birth_date && author.death_date && ' — '}
                    {author.death_date && `Fallecimiento: ${author.death_date}`}
                  </p>
                )}
              </div>

              {/* Botones de acción (Buscar más obras / Reclamar) */}
              <div className="flex flex-wrap items-center justify-center sm:justify-end gap-2">
                <button
                  onClick={handleRefreshAuthor}
                  disabled={refreshing}
                  className="bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 font-semibold px-3.5 py-2 rounded-xl text-xs transition-colors flex items-center gap-1.5 cursor-pointer"
                >
                  <span>{refreshing ? '⏳' : '🔄'}</span>
                  <span>{refreshing ? 'Buscando...' : 'Actualizar catálogo'}</span>
                </button>

                {!author.is_verified && !author.is_claimed && (
                  <>
                    {userClaimStatus === 'pending' ? (
                      <span className="inline-flex items-center gap-1 px-3 py-2 rounded-xl text-xs font-bold bg-amber-50 dark:bg-amber-950/50 text-amber-700 dark:text-amber-300 border border-amber-200 dark:border-amber-800">
                        <span>⏳</span> Solicitud de autoría en revisión
                      </span>
                    ) : (
                      <button
                        onClick={handleOpenClaimModal}
                        className="bg-gradient-to-r from-teal-600 to-emerald-600 hover:from-teal-700 hover:to-emerald-700 text-white font-bold px-3.5 py-2 rounded-xl text-xs transition-all shadow-sm hover:shadow flex items-center gap-1.5 cursor-pointer"
                      >
                        <HiOutlineShieldCheck className="w-4 h-4" />
                        <span>Reclamar perfil</span>
                      </button>
                    )}
                  </>
                )}
              </div>
            </div>

            {/* Biografía */}
            {author.biography ? (
              <div className="text-sm text-slate-600 dark:text-slate-300 leading-relaxed max-w-3xl whitespace-pre-line pt-1">
                {author.biography}
              </div>
            ) : (
              <p className="text-xs text-slate-400 italic pt-1">
                Biografía en proceso de recopilación bibliográfica.
              </p>
            )}

            {/* Enlaces y Redes Sociales */}
            <div className="flex flex-wrap items-center justify-center sm:justify-start gap-3 pt-3 border-t border-slate-100 dark:border-slate-800">
              {author.website && (
                <a
                  href={author.website}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 text-xs text-teal-600 dark:text-teal-400 hover:underline"
                >
                  <HiOutlineGlobeAlt className="w-4 h-4" />
                  <span>Sitio Oficial</span>
                </a>
              )}
              {author.wikipedia_url && (
                <a
                  href={author.wikipedia_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 text-xs text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white"
                >
                  <BsWikipedia className="w-3.5 h-3.5" />
                  <span>Wikipedia</span>
                </a>
              )}
              {author.twitter && (
                <a
                  href={author.twitter.startsWith('http') ? author.twitter : `https://x.com/${author.twitter}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 text-xs text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white"
                >
                  <BsTwitterX className="w-3.5 h-3.5" />
                  <span>X (Twitter)</span>
                </a>
              )}
              {author.instagram && (
                <a
                  href={author.instagram.startsWith('http') ? author.instagram : `https://instagram.com/${author.instagram}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 text-xs text-slate-600 dark:text-slate-400 hover:text-rose-500"
                >
                  <BsInstagram className="w-3.5 h-3.5" />
                  <span>Instagram</span>
                </a>
              )}
            </div>
          </div>
        </div>

        {/* Barra de Estadísticas de Impacto Editorial */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-4 border-t border-slate-100 dark:border-slate-800">
          <div className="p-3.5 rounded-2xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200/60 dark:border-slate-800 text-center">
            <div className="text-xl font-black text-slate-900 dark:text-white flex items-center justify-center gap-1.5">
              <HiOutlineBookOpen className="w-5 h-5 text-teal-600 dark:text-teal-400" />
              <span>{booksCount}</span>
            </div>
            <div className="text-[11px] font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider mt-1">
              Libros Publicados
            </div>
          </div>

          <div className="p-3.5 rounded-2xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200/60 dark:border-slate-800 text-center">
            <div className="text-xl font-black text-amber-500 flex items-center justify-center gap-1.5">
              <HiOutlineStar className="w-5 h-5 fill-amber-400" />
              <span>{avgRating ? `${avgRating} / 5` : 'N/A'}</span>
            </div>
            <div className="text-[11px] font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider mt-1">
              Calificación Media
            </div>
          </div>

          <div className="p-3.5 rounded-2xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200/60 dark:border-slate-800 text-center">
            <div className="text-xl font-black text-slate-900 dark:text-white flex items-center justify-center gap-1.5">
              <HiOutlineChatAlt2 className="w-5 h-5 text-sky-500" />
              <span>{reviewsCount}</span>
            </div>
            <div className="text-[11px] font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider mt-1">
              Reseñas Recibidas
            </div>
          </div>

          <div className="p-3.5 rounded-2xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200/60 dark:border-slate-800 text-center">
            <div className="text-xl font-black text-slate-900 dark:text-white flex items-center justify-center gap-1.5">
              <HiOutlineUsers className="w-5 h-5 text-indigo-500" />
              <span>{readersCount}</span>
            </div>
            <div className="text-[11px] font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider mt-1">
              Lectores en Comunidad
            </div>
          </div>
        </div>
      </div>

      {/* Obras del Autor */}
      <div className="space-y-4">
        <h2 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
          <span>📚</span>
          <span>Catálogo de Obras de {author.name}</span>
          <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-teal-100 text-teal-800 dark:bg-teal-900/40 dark:text-teal-300">
            {localBooks.length}
          </span>
        </h2>

        {localBooks.length === 0 ? (
          <div className="p-8 text-center bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 text-slate-500 text-sm">
            Aún no hay libros catalogados de este autor en MyBookSocial. Pulsa en "Actualizar catálogo" para sincronizar.
          </div>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4 sm:gap-6">
            {localBooks.map((book: any) => {
              const coverUrl =
                book.cover && typeof book.cover === 'string' && book.cover.startsWith('/')
                  ? `${apiUrl}${book.cover}`
                  : book.cover;

              return (
                <div
                  key={book.id}
                  onClick={() => navigate(`/books/${book.id}`)}
                  className="group bg-white dark:bg-slate-900 rounded-2xl p-3 border border-slate-200/80 dark:border-slate-800 shadow-sm hover:shadow-lg transition-all duration-200 cursor-pointer flex flex-col justify-between"
                >
                  <div className="relative aspect-[2/3] w-full rounded-xl overflow-hidden bg-slate-100 dark:bg-slate-800 mb-2 shadow-inner">
                    {coverUrl ? (
                      <img
                        src={coverUrl}
                        alt={book.title}
                        className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                        loading="lazy"
                      />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center p-2 text-center text-xs font-semibold text-slate-400">
                        {book.title}
                      </div>
                    )}
                  </div>

                  <div>
                    <h4 className="font-bold text-xs sm:text-sm text-slate-900 dark:text-white truncate group-hover:text-teal-600 transition-colors">
                      {book.title}
                    </h4>
                    {book.published_date && (
                      <p className="text-[11px] text-slate-400 mt-0.5">
                        {new Date(book.published_date).getFullYear() || book.published_date}
                      </p>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Encuentros y Eventos Literarios del Autor */}
      <AuthorEventsSection
        authorId={author.id}
        authorName={author.name}
        isAuthorOwner={Boolean(
          (user && (author.claimed_by === user.id || (user as any).role === 'ADMIN' || (user as any).role === 'MODERATOR' || user.is_staff))
        )}
        books={localBooks}
      />

      {/* Publicaciones y Adelantos del Autor */}
      <AuthorPublicationsSection
        authorId={author.id}
        authorName={author.name}
        isAuthorOwner={Boolean(
          (user && (author.claimed_by === user.id || (user as any).role === 'ADMIN' || (user as any).role === 'MODERATOR' || user.is_staff))
        )}
        books={localBooks}
      />

      {/* Formulario de Erratas / Sugerencias */}
      <div className="bg-white dark:bg-slate-900 rounded-3xl border border-slate-200/80 dark:border-slate-800 p-6 shadow-sm">
        <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-1.5 mb-2">
          <span>✍️</span>
          <span>¿Algún dato de {author.name} es incorrecto?</span>
        </h3>
        <p className="text-xs text-slate-500 dark:text-slate-400 mb-4">
          Nuestra comunidad cuida los datos bibliográficos. Envía una sugerencia o corrección a nuestro equipo editorial.
        </p>

        {reportSent ? (
          <div className="p-4 bg-emerald-50 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-300 rounded-xl text-xs font-semibold">
            ✓ ¡Gracias! Tu reporte ha sido recibido por los moderadores.
          </div>
        ) : (
          <form onSubmit={handleSendErrata} className="space-y-3">
            <div className="flex gap-3 items-center">
              <label className="text-xs font-bold text-slate-700 dark:text-slate-300">
                Tipo de reporte:
              </label>
              <select
                value={errataType}
                onChange={(e) => setErrataType(e.target.value as any)}
                className="text-xs rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 py-1.5 px-3 text-slate-900 dark:text-white focus:ring-teal-500"
              >
                <option value="errata">Errata bibliográfica</option>
                <option value="suggestion">Sugerencia de biografía</option>
                <option value="other">Otro motivo</option>
              </select>
            </div>

            <textarea
              rows={3}
              value={errataText}
              onChange={(e) => setErrataText(e.target.value)}
              placeholder="Describe el dato que consideras incorrecto o la corrección sugerida..."
              className="w-full text-xs rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 p-3 text-slate-900 dark:text-white focus:ring-teal-500"
            />

            <button
              type="submit"
              disabled={!errataText.trim()}
              className="bg-teal-600 hover:bg-teal-700 text-white font-bold text-xs px-4 py-2 rounded-xl transition-all disabled:opacity-50 cursor-pointer"
            >
              Enviar reporte
            </button>
          </form>
        )}
      </div>

      {/* Modal Reclamar Perfil de Autor */}
      <Modal show={isClaimModalOpen} onClose={() => setIsClaimModalOpen(false)} size="md">
        <Modal.Header>
          <span className="font-bold text-slate-900 dark:text-white flex items-center gap-2">
            <HiOutlineShieldCheck className="w-5 h-5 text-teal-600" />
            Reclamar perfil de {author.name}
          </span>
        </Modal.Header>
        <form onSubmit={handleSubmitClaim}>
          <Modal.Body className="space-y-4">
            <p className="text-xs sm:text-sm text-slate-600 dark:text-slate-300 leading-relaxed">
              Si eres el autor o su representante legal formal, puedes solicitar la verificación y vinculación
              de esta página oficial a tu cuenta de MyBookSocial.
            </p>

            {claimSuccessMessage && (
              <div className="p-3.5 rounded-xl bg-emerald-50 dark:bg-emerald-950/40 text-emerald-800 dark:text-emerald-300 text-xs font-semibold">
                {claimSuccessMessage}
              </div>
            )}

            {claimErrorMessage && (
              <div className="p-3.5 rounded-xl bg-red-50 dark:bg-red-950/40 text-red-800 dark:text-red-300 text-xs font-semibold">
                {claimErrorMessage}
              </div>
            )}

            <div>
              <label className="block text-xs font-bold uppercase text-slate-600 dark:text-slate-300 mb-1">
                Correo Electrónico de Contacto *
              </label>
              <input
                type="email"
                required
                value={claimContactEmail}
                onChange={(e) => setClaimContactEmail(e.target.value)}
                placeholder="tu-correo-oficial@editorial.com"
                className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm text-slate-900 dark:text-white focus:ring-2 focus:ring-teal-500"
              />
            </div>

            <div>
              <label className="block text-xs font-bold uppercase text-slate-600 dark:text-slate-300 mb-1">
                Enlace de Acreditación / Sitio Web Oficial
              </label>
              <input
                type="url"
                value={claimSupportingLink}
                onChange={(e) => setClaimSupportingLink(e.target.value)}
                placeholder="https://tupaginaweb.com o enlace a perfil en redes verificado"
                className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm text-slate-900 dark:text-white focus:ring-2 focus:ring-teal-500"
              />
            </div>

            <div>
              <label className="block text-xs font-bold uppercase text-slate-600 dark:text-slate-300 mb-1">
                Motivo y Prueba de Autoría *
              </label>
              <textarea
                required
                rows={4}
                value={claimProofDesc}
                onChange={(e) => setClaimProofDesc(e.target.value)}
                placeholder="Indica cómo podemos verificar que eres el autor (editorial que te publica, perfil oficial en redes, ISBN de tus obras, etc.)..."
                className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm text-slate-900 dark:text-white focus:ring-2 focus:ring-teal-500"
              />
            </div>
          </Modal.Body>
          <Modal.Footer className="flex justify-end gap-2">
            <Button color="gray" onClick={() => setIsClaimModalOpen(false)} disabled={submittingClaim}>
              Cancelar
            </Button>
            <Button
              type="submit"
              className="bg-teal-600 hover:bg-teal-700 text-white"
              disabled={submittingClaim || !!claimSuccessMessage}
            >
              {submittingClaim ? <Spinner size="sm" className="mr-2" /> : null}
              Enviar Solicitud
            </Button>
          </Modal.Footer>
        </form>
      </Modal>
    </div>
  );
}

export default Author;
