import React, { useEffect, useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { clubService } from '../services/clubService';
import { ReadingClub, ClubMember, ClubDiscussion } from '../types';

export const ClubDetailPage: React.FC = () => {
  const { slug } = useParams<{ slug: string }>();
  const navigate = useNavigate();

  const [club, setClub] = useState<ReadingClub | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'readings' | 'discussions' | 'members'>('readings');

  // Members and Discussions state
  const [members, setMembers] = useState<ClubMember[]>([]);
  const [discussions, setDiscussions] = useState<ClubDiscussion[]>([]);
  const [actionLoading, setActionLoading] = useState(false);

  // New discussion modal state
  const [isDiscussionModalOpen, setIsDiscussionModalOpen] = useState(false);
  const [discTitle, setDiscTitle] = useState('');
  const [discContent, setDiscContent] = useState('');
  const [discHasSpoilers, setDiscHasSpoilers] = useState(false);

  // Comments toggle per discussion
  const [expandedDiscussionId, setExpandedDiscussionId] = useState<number | null>(null);
  const [commentContent, setCommentContent] = useState('');
  const [commentHasSpoilers, setCommentHasSpoilers] = useState(false);

  // Spoilers revealed state
  const [revealedSpoilers, setRevealedSpoilers] = useState<Record<number, boolean>>({});

  const fetchClubDetails = async () => {
    if (!slug) return;
    try {
      setLoading(true);
      setError(null);
      const data = await clubService.getClub(slug);
      setClub(data);
    } catch (err: any) {
      setError(err?.message || 'Error al cargar el club de lectura');
    } finally {
      setLoading(false);
    }
  };

  const fetchMembers = async () => {
    if (!slug) return;
    try {
      const data = await clubService.getMembers(slug);
      setMembers(data);
    } catch (err) {
      console.error(err);
    }
  };

  const fetchDiscussions = async () => {
    if (!slug) return;
    try {
      const data = await clubService.getDiscussions(slug);
      setDiscussions(data);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    fetchClubDetails();
  }, [slug]);

  useEffect(() => {
    if (activeTab === 'members') fetchMembers();
    if (activeTab === 'discussions') fetchDiscussions();
  }, [activeTab, slug]);

  const handleJoin = async () => {
    if (!slug) return;
    try {
      setActionLoading(true);
      const res = await clubService.joinClub(slug);
      alert(res.detail);
      await fetchClubDetails();
    } catch (err: any) {
      alert(err?.message || 'Error al solicitar unión');
    } finally {
      setActionLoading(false);
    }
  };

  const handleLeave = async () => {
    if (!slug || !window.confirm('¿Seguro que deseas abandonar el club?')) return;
    try {
      setActionLoading(true);
      await clubService.leaveClub(slug);
      alert('Has salido del club.');
      navigate('/clubs');
    } catch (err: any) {
      alert(err?.message || 'Error al salir del club');
    } finally {
      setActionLoading(false);
    }
  };

  const handleCreateDiscussion = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!slug || !discTitle.trim() || !discContent.trim()) return;

    try {
      setActionLoading(true);
      const newDisc = await clubService.createDiscussion(slug, {
        title: discTitle.trim(),
        content: discContent.trim(),
        has_spoilers: discHasSpoilers,
      });
      setDiscussions((prev) => [newDisc, ...prev]);
      setIsDiscussionModalOpen(false);
      setDiscTitle('');
      setDiscContent('');
      setDiscHasSpoilers(false);
    } catch (err: any) {
      alert(err?.message || 'Error al publicar el debate');
    } finally {
      setActionLoading(false);
    }
  };

  const handleAddComment = async (discussionId: number) => {
    if (!slug || !commentContent.trim()) return;
    try {
      setActionLoading(true);
      const newComment = await clubService.addComment(slug, discussionId, {
        content: commentContent.trim(),
        has_spoilers: commentHasSpoilers,
      });
      setDiscussions((prev) =>
        prev.map((d) =>
          d.id === discussionId
            ? {
                ...d,
                comments_count: d.comments_count + 1,
                recent_comments: [...(d.recent_comments || []), newComment],
              }
            : d
        )
      );
      setCommentContent('');
      setCommentHasSpoilers(false);
    } catch (err: any) {
      alert(err?.message || 'Error al enviar comentario');
    } finally {
      setActionLoading(false);
    }
  };

  const toggleSpoiler = (id: number) => {
    setRevealedSpoilers((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  if (loading) {
    return (
      <div className="max-w-6xl mx-auto px-4 py-16 text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto"></div>
        <p className="mt-4 text-sm text-gray-500">Cargando club de lectura...</p>
      </div>
    );
  }

  if (error || !club) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-12">
        <div className="p-6 rounded-2xl bg-red-50 dark:bg-red-900/30 text-red-700 dark:text-red-300">
          <h2 className="text-lg font-bold">No fue posible cargar el club</h2>
          <p className="mt-1 text-sm">{error || 'El club solicitado no existe o no tienes acceso.'}</p>
          <Link
            to="/clubs"
            className="mt-4 inline-block text-sm font-semibold text-indigo-600 hover:underline"
          >
            ← Volver al catálogo de clubs
          </Link>
        </div>
      </div>
    );
  }

  const isMemberActive = club.membership?.status === 'ACTIVE';
  const isMemberPending = club.membership?.status === 'PENDING';

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Volver */}
      <div className="mb-4">
        <Link
          to="/clubs"
          className="text-sm font-medium text-gray-500 hover:text-indigo-600 dark:hover:text-indigo-400 inline-flex items-center gap-1 transition"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 19l-7-7 7-7" />
          </svg>
          Todos los Clubs
        </Link>
      </div>

      {/* Hero / Cabecera del Club */}
      <div className="bg-white dark:bg-gray-800 rounded-3xl p-6 sm:p-8 border border-gray-200 dark:border-gray-700/80 shadow-sm">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="space-y-3 max-w-2xl">
            <div className="flex items-center gap-3">
              <span
                className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold ${
                  club.is_private
                    ? 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300'
                    : 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300'
                }`}
              >
                {club.is_private ? 'Club Privado' : 'Club Público'}
              </span>
              {club.membership && (
                <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-indigo-100 text-indigo-800 dark:bg-indigo-900/40 dark:text-indigo-300">
                  {club.membership.role === 'ADMIN'
                    ? 'Administrador'
                    : club.membership.role === 'MODERATOR'
                    ? 'Moderador'
                    : 'Miembro'}
                </span>
              )}
            </div>

            <h1 className="text-3xl sm:text-4xl font-extrabold text-gray-900 dark:text-white tracking-tight">
              {club.name}
            </h1>

            <p className="text-base text-gray-600 dark:text-gray-300 leading-relaxed">
              {club.description || 'Comunidad literaria de MyBookConnect.'}
            </p>

            <div className="flex items-center gap-4 text-xs text-gray-500 dark:text-gray-400 pt-1">
              <span>Fundado por @{club.creator.username}</span>
              <span>•</span>
              <span>{club.members_count} miembros activos</span>
            </div>
          </div>

          {/* Acciones de membresía */}
          <div className="flex flex-col sm:flex-row gap-3">
            {!club.membership ? (
              <button
                type="button"
                disabled={actionLoading}
                onClick={handleJoin}
                className="px-6 py-2.5 rounded-xl font-semibold text-white bg-indigo-600 hover:bg-indigo-700 transition shadow disabled:opacity-50"
              >
                {club.is_private ? 'Solicitar Ingreso' : 'Unirse al Club'}
              </button>
            ) : isMemberPending ? (
              <span className="px-4 py-2 bg-amber-50 dark:bg-amber-900/20 text-amber-700 dark:text-amber-400 rounded-xl text-sm font-semibold text-center border border-amber-200 dark:border-amber-800">
                Solicitud Pendiente de Aprobación
              </span>
            ) : (
              <button
                type="button"
                disabled={actionLoading}
                onClick={handleLeave}
                className="px-4 py-2 text-sm font-medium text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-950/30 rounded-xl transition border border-red-200 dark:border-red-900"
              >
                Abandonar Club
              </button>
            )}
          </div>
        </div>

        {/* Reglas si existen */}
        {club.rules && (
          <div className="mt-6 pt-6 border-t border-gray-100 dark:border-gray-700/60">
            <h2 className="text-xs font-bold uppercase tracking-wider text-gray-400">
              Reglas de convivencia
            </h2>
            <p className="mt-1 text-sm text-gray-600 dark:text-gray-300 whitespace-pre-line">
              {club.rules}
            </p>
          </div>
        )}
      </div>

      {/* Pestañas del Club */}
      <div className="mt-8 border-b border-gray-200 dark:border-gray-800">
        <nav role="tablist" aria-label="Secciones del club" className="flex gap-8">
          <button
            role="tab"
            aria-selected={activeTab === 'readings'}
            onClick={() => setActiveTab('readings')}
            className={`pb-4 text-sm font-bold border-b-2 transition ${
              activeTab === 'readings'
                ? 'border-indigo-600 text-indigo-600 dark:text-indigo-400'
                : 'border-transparent text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'
            }`}
          >
            Lecturas Conjuntas
          </button>
          <button
            role="tab"
            aria-selected={activeTab === 'discussions'}
            onClick={() => setActiveTab('discussions')}
            className={`pb-4 text-sm font-bold border-b-2 transition ${
              activeTab === 'discussions'
                ? 'border-indigo-600 text-indigo-600 dark:text-indigo-400'
                : 'border-transparent text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'
            }`}
          >
            Debates y Foros
          </button>
          <button
            role="tab"
            aria-selected={activeTab === 'members'}
            onClick={() => setActiveTab('members')}
            className={`pb-4 text-sm font-bold border-b-2 transition ${
              activeTab === 'members'
                ? 'border-indigo-600 text-indigo-600 dark:text-indigo-400'
                : 'border-transparent text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'
            }`}
          >
            Miembros ({club.members_count})
          </button>
        </nav>
      </div>

      {/* Panel: Lecturas Conjuntas */}
      {activeTab === 'readings' && (
        <div className="mt-8 space-y-6">
          {/* Lectura actual */}
          <div className="bg-white dark:bg-gray-800 rounded-2xl p-6 border border-gray-200 dark:border-gray-700">
            <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-4">
              Lectura en Curso
            </h2>
            {club.current_book ? (
              <div className="flex flex-col sm:flex-row items-start gap-6">
                {club.current_book.cover_image_url ? (
                  <img
                    src={club.current_book.cover_image_url}
                    alt={club.current_book.title}
                    className="w-28 h-40 object-cover rounded-xl shadow-md"
                  />
                ) : (
                  <div className="w-28 h-40 bg-indigo-50 dark:bg-indigo-900/30 flex items-center justify-center rounded-xl text-indigo-500 font-bold text-lg">
                    Sin portada
                  </div>
                )}
                <div className="flex-1 space-y-2">
                  <h3 className="text-2xl font-bold text-gray-900 dark:text-white">
                    {club.current_book.title}
                  </h3>
                  {club.current_book.author_name && (
                    <p className="text-base text-gray-600 dark:text-gray-300">
                      de {club.current_book.author_name}
                    </p>
                  )}
                  {club.current_book.average_rating && (
                    <div className="flex items-center gap-1 text-amber-500 text-sm font-semibold">
                      ★ {club.current_book.average_rating.toFixed(1)} / 5.0
                    </div>
                  )}
                  <div className="pt-2">
                    <Link
                      to={`/books/${club.current_book.id}`}
                      className="inline-flex items-center text-sm font-semibold text-indigo-600 dark:text-indigo-400 hover:underline"
                    >
                      Ver ficha completa del libro →
                    </Link>
                  </div>
                </div>
              </div>
            ) : (
              <p className="text-sm text-gray-500 dark:text-gray-400 italic">
                El club no tiene una lectura activa en este momento.
              </p>
            )}
          </div>

          {/* Historial o Plan */}
          {club.reading_plan && club.reading_plan.length > 0 && (
            <div className="bg-white dark:bg-gray-800 rounded-2xl p-6 border border-gray-200 dark:border-gray-700">
              <h2 className="text-lg font-bold text-gray-900 dark:text-white mb-4">
                Plan de Lecturas Conjuntas
              </h2>
              <div className="divide-y divide-gray-100 dark:divide-gray-700">
                {club.reading_plan.map((item) => (
                  <div key={item.id} className="py-4 flex items-center justify-between gap-4">
                    <div>
                      <h4 className="font-semibold text-gray-900 dark:text-white text-base">
                        {item.book.title}
                      </h4>
                      {item.target_milestones && (
                        <p className="text-xs text-indigo-600 dark:text-indigo-400 mt-0.5">
                          Hitos: {item.target_milestones}
                        </p>
                      )}
                    </div>
                    <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300">
                      {item.status}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Panel: Debates */}
      {activeTab === 'discussions' && (
        <div className="mt-8 space-y-6">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-bold text-gray-900 dark:text-white">
              Hilos de Discusión
            </h2>
            {isMemberActive && (
              <button
                type="button"
                onClick={() => setIsDiscussionModalOpen(true)}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-semibold rounded-xl shadow transition"
              >
                + Nuevo Debate
              </button>
            )}
          </div>

          {discussions.length === 0 ? (
            <div className="text-center py-12 bg-gray-50 dark:bg-gray-800/40 rounded-2xl border border-dashed border-gray-300 dark:border-gray-700">
              <p className="text-sm text-gray-500">Aún no hay debates en este club. ¡Inicia el primero!</p>
            </div>
          ) : (
            <div className="space-y-4">
              {discussions.map((disc) => (
                <div
                  key={disc.id}
                  className="bg-white dark:bg-gray-800 rounded-2xl p-6 border border-gray-200 dark:border-gray-700 space-y-4"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <div className="flex items-center gap-2">
                        {disc.is_pinned && (
                          <span className="text-xs font-bold text-indigo-600 dark:text-indigo-400 uppercase tracking-wide">
                            📌 Fijado
                          </span>
                        )}
                        {disc.has_spoilers && (
                          <span className="text-xs font-bold px-2 py-0.5 rounded bg-rose-100 text-rose-800 dark:bg-rose-900/40 dark:text-rose-300">
                            ⚠️ Spoilers
                          </span>
                        )}
                      </div>
                      <h3 className="text-lg font-bold text-gray-900 dark:text-white mt-1">
                        {disc.title}
                      </h3>
                      <p className="text-xs text-gray-400">
                        Por @{disc.author.username} • {new Date(disc.created_at).toLocaleDateString()}
                      </p>
                    </div>
                    <span className="text-xs font-medium text-gray-500">
                      {disc.comments_count} {disc.comments_count === 1 ? 'comentario' : 'comentarios'}
                    </span>
                  </div>

                  {/* Contenido con soporte de spoiler blur */}
                  {disc.has_spoilers && !revealedSpoilers[disc.id] ? (
                    <div className="p-4 bg-gray-50 dark:bg-gray-750 rounded-xl text-center">
                      <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">
                        Este debate contiene revelaciones de la trama (spoilers).
                      </p>
                      <button
                        type="button"
                        onClick={() => toggleSpoiler(disc.id)}
                        className="text-xs font-semibold text-indigo-600 dark:text-indigo-400 hover:underline"
                      >
                        Mostrar contenido
                      </button>
                    </div>
                  ) : (
                    <div className="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-line">
                      {disc.content}
                    </div>
                  )}

                  {/* Comentarios Toggle */}
                  <div className="pt-2 border-t border-gray-100 dark:border-gray-700">
                    <button
                      type="button"
                      onClick={() =>
                        setExpandedDiscussionId(expandedDiscussionId === disc.id ? null : disc.id)
                      }
                      className="text-xs font-bold text-indigo-600 dark:text-indigo-400 hover:underline"
                    >
                      {expandedDiscussionId === disc.id ? 'Ocultar comentarios' : 'Ver y responder comentarios'}
                    </button>

                    {expandedDiscussionId === disc.id && (
                      <div className="mt-4 space-y-3">
                        {disc.recent_comments && disc.recent_comments.length > 0 && (
                          <div className="space-y-2">
                            {disc.recent_comments.map((comm) => (
                              <div
                                key={comm.id}
                                className="p-3 bg-gray-50 dark:bg-gray-750 rounded-xl text-xs space-y-1"
                              >
                                <span className="font-bold text-gray-900 dark:text-white">
                                  @{comm.author.username}
                                </span>
                                <p className="text-gray-700 dark:text-gray-300">{comm.content}</p>
                              </div>
                            ))}
                          </div>
                        )}

                        {isMemberActive && (
                          <div className="flex gap-2 mt-2">
                            <input
                              type="text"
                              value={commentContent}
                              onChange={(e) => setCommentContent(e.target.value)}
                              placeholder="Escribe tu opinión en el debate..."
                              className="flex-1 px-3 py-1.5 text-xs bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-indigo-500"
                            />
                            <button
                              type="button"
                              onClick={() => handleAddComment(disc.id)}
                              className="px-3 py-1.5 bg-indigo-600 text-white rounded-lg text-xs font-semibold hover:bg-indigo-700 transition"
                            >
                              Comentar
                            </button>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Panel: Miembros */}
      {activeTab === 'members' && (
        <div className="mt-8 bg-white dark:bg-gray-800 rounded-2xl p-6 border border-gray-200 dark:border-gray-700">
          <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-4">
            Miembros de la Comunidad
          </h2>
          <div className="divide-y divide-gray-100 dark:divide-gray-700">
            {members.map((m) => (
              <div key={m.id} className="py-3 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-full bg-indigo-100 dark:bg-indigo-900/40 text-indigo-600 flex items-center justify-center font-bold text-sm">
                    {m.user.username.charAt(0).toUpperCase()}
                  </div>
                  <div>
                    <h4 className="text-sm font-semibold text-gray-900 dark:text-white">
                      @{m.user.username}
                    </h4>
                    <span className="text-xs text-gray-400">
                      Ingreso: {new Date(m.joined_at).toLocaleDateString()}
                    </span>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span
                    className={`text-xs font-semibold px-2.5 py-0.5 rounded-full ${
                      m.role === 'ADMIN'
                        ? 'bg-purple-100 text-purple-800 dark:bg-purple-900/40 dark:text-purple-300'
                        : m.role === 'MODERATOR'
                        ? 'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300'
                        : 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300'
                    }`}
                  >
                    {m.role}
                  </span>
                  {m.status === 'PENDING' && (
                    <span className="text-xs font-semibold px-2 py-0.5 rounded bg-amber-100 text-amber-800">
                      Pendiente
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Modal Nuevo Debate */}
      {isDiscussionModalOpen && (
        <div
          role="dialog"
          aria-modal="true"
          className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4"
        >
          <div className="bg-white dark:bg-gray-800 rounded-2xl max-w-lg w-full p-6 border border-gray-200 dark:border-gray-700 shadow-xl">
            <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-4">
              Iniciar Hilo de Debate
            </h3>
            <form onSubmit={handleCreateDiscussion} className="space-y-4">
              <div>
                <label className="block text-xs font-bold text-gray-700 dark:text-gray-300 uppercase">
                  Título del Debate *
                </label>
                <input
                  type="text"
                  required
                  value={discTitle}
                  onChange={(e) => setDiscTitle(e.target.value)}
                  placeholder="Ej. Análisis del desenlace del capítulo 10"
                  className="mt-1 w-full px-3 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-xl text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-gray-700 dark:text-gray-300 uppercase">
                  Pregunta o Contenido *
                </label>
                <textarea
                  rows={4}
                  required
                  value={discContent}
                  onChange={(e) => setDiscContent(e.target.value)}
                  placeholder="Comparte tus reflexiones, preguntas o citas..."
                  className="mt-1 w-full px-3 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-xl text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="has-spoilers"
                  checked={discHasSpoilers}
                  onChange={(e) => setDiscHasSpoilers(e.target.checked)}
                  className="rounded text-indigo-600"
                />
                <label htmlFor="has-spoilers" className="text-xs font-medium text-gray-700 dark:text-gray-300">
                  Advertir que este debate contiene spoilers de la obra
                </label>
              </div>

              <div className="flex justify-end gap-3 pt-4 border-t border-gray-100 dark:border-gray-700">
                <button
                  type="button"
                  onClick={() => setIsDiscussionModalOpen(false)}
                  className="px-4 py-2 text-xs font-semibold text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-xl"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={actionLoading || !discTitle.trim() || !discContent.trim()}
                  className="px-5 py-2 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-xl shadow disabled:opacity-50"
                >
                  Publicar Debate
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
