import { useEffect, useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuthStore } from '../../../store/auth';
import { Spinner } from 'flowbite-react';
import { AIAssistantModal } from '../../ai';
import { OnboardingModal } from '../../onboarding';
import { resolveMediaUrl } from '../../../utils/media';
import { FeedActivityCard } from '../components/FeedActivityCard';
import { FeedFilterTabs } from '../components/FeedFilterTabs';
import { TrendingSidebar } from '../components/TrendingSidebar';

interface TrendingBook {
  id: number;
  title: string;
  cover?: string;
  author_name: string;
  average_rating?: number;
  readers_count: number;
  reviews_count: number;
  trending_score?: number;
}

interface RecommendedBook {
  id: number;
  title: string;
  cover?: string;
  author_name: string;
  average_rating?: number;
  score: number;
  reason: string;
  categories?: Array<{ id: number; name: string }>;
}

interface FeedItem {
  id: string | number;
  type: string;
  type_display?: string;
  timestamp?: string;
  created_at?: string;
  score?: number;
  feed_signal?: string;
  user: {
    id: number;
    username: string;
    avatar?: string;
  };
  target_user?: {
    id: number;
    username: string;
    avatar?: string;
  };
  metadata?: {
    list_id?: number;
    name?: string;
    privacy?: string;
    rating?: number;
    comment_id?: number;
    review_id?: number;
    status?: string;
    progress?: number;
  };
  book?: {
    id: number;
    title: string;
    cover?: string;
    author_name?: string;
  };
  review?: {
    id: number;
    rating?: number;
    title?: string;
    text?: string;
  };
  rating?: number;
  comment?: string;
}

export const Home = () => {
  const { user, token } = useAuthStore();
  const navigate = useNavigate();

  const [recommendations, setRecommendations] = useState<RecommendedBook[]>([]);
  const [trending, setTrending] = useState<TrendingBook[]>([]);
  const [trendingPeriod, setTrendingPeriod] = useState<'week' | 'month' | 'all'>('week');
  const [trendingLoading, setTrendingLoading] = useState(false);
  const [feed, setFeed] = useState<FeedItem[]>([]);
  const [feedMode, setFeedMode] = useState<'smart' | 'chronological'>('smart');
  const [feedCategory, setFeedCategory] = useState<
    'all' | 'reads' | 'reviews' | 'lists' | 'social'
  >('all');
  const [activeMenuId, setActiveMenuId] = useState<string | number | null>(null);
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [feedLoading, setFeedLoading] = useState(false);
  const [loading, setLoading] = useState(true);
  const [isAiModalOpen, setIsAiModalOpen] = useState(false);
  const [isOnboardingOpen, setIsOnboardingOpen] = useState(false);

  const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';

  // Detección de primer login para lanzar el asistente de bienvenida (Fase 19)
  useEffect(() => {
    if (user && user.onboarding_completed === false) {
      setIsOnboardingOpen(true);
    }
  }, [user]);

  // Carga inicial del dashboard: recomendaciones, feed y tendencias
  useEffect(() => {
    if (!user) {
      navigate('/');
      return;
    }

    const loadDashboardData = async () => {
      try {
        setLoading(true);
        const headers: HeadersInit = token ? { Authorization: `Bearer ${token}` } : {};

        const [recsRes, trendingRes, feedRes] = await Promise.all([
          fetch(`${apiUrl}/api/v1/books/recommendations/?limit=6`, { headers }),
          fetch(`${apiUrl}/api/v1/books/trending/?period=week`, { headers }),
          fetch(`${apiUrl}/api/v1/users/feed/?mode=smart`, { headers }),
        ]);

        if (recsRes.ok) {
          const rData = await recsRes.json();
          const recResults = rData.results || [];
          setRecommendations(recResults);

          // Feedback de recomendaciones (Fase 25): registrar impresiones (recommendation_shown)
          if (recResults.length > 0 && token) {
            const shownEvents = recResults.map((b: RecommendedBook, index: number) => ({
              book_id: b.id,
              action: 'recommendation_shown',
              strategy: rData.strategy || 'hybrid',
              algorithm_version: 'v1.0',
              metadata: { position: index + 1, score: b.score, reason: b.reason },
            }));
            fetch(`${apiUrl}/api/v1/books/recommendations/feedback/`, {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
                Authorization: `Bearer ${token}`,
              },
              body: JSON.stringify(shownEvents),
            }).catch((err) => console.error('Error tracking recommendation impressions', err));
          }
        }

        if (trendingRes.ok) {
          const tData = await trendingRes.json();
          setTrending(tData.results || []);
        }

        if (feedRes.ok) {
          const fData = await feedRes.json();
          setFeed(fData.results || []);
        }
      } catch (e) {
        console.error('Error loading dashboard data', e);
      } finally {
        setLoading(false);
      }
    };

    loadDashboardData();
  }, [user, token, navigate, apiUrl]);

  // Cambio interactivo del periodo de tendencias
  const handlePeriodChange = async (period: 'week' | 'month' | 'all') => {
    if (period === trendingPeriod) return;
    setTrendingPeriod(period);
    try {
      setTrendingLoading(true);
      const headers: HeadersInit = token ? { Authorization: `Bearer ${token}` } : {};
      const res = await fetch(`${apiUrl}/api/v1/books/trending/?period=${period}`, { headers });
      if (res.ok) {
        const data = await res.json();
        setTrending(data.results || []);
      }
    } catch (e) {
      console.error('Error switching trending period', e);
    } finally {
      setTrendingLoading(false);
    }
  };

  // Cierre de menús contextuales al hacer clic en el documento
  useEffect(() => {
    const handleOutsideClick = () => setActiveMenuId(null);
    window.addEventListener('click', handleOutsideClick);
    return () => window.removeEventListener('click', handleOutsideClick);
  }, []);

  // Carga reactiva de elementos del feed según modo y categoría
  const fetchFeedItems = async (
    mode: 'smart' | 'chronological',
    category: 'all' | 'reads' | 'reviews' | 'lists' | 'social'
  ) => {
    try {
      setFeedLoading(true);
      const headers: HeadersInit = token ? { Authorization: `Bearer ${token}` } : {};
      const params = new URLSearchParams();
      params.append('mode', mode);
      if (category !== 'all') {
        params.append('category', category);
      }
      const res = await fetch(`${apiUrl}/api/v1/users/feed/?${params.toString()}`, { headers });
      if (res.ok) {
        const data = await res.json();
        setFeed(data.results || []);
      }
    } catch (e) {
      console.error('Error fetching feed', e);
    } finally {
      setFeedLoading(false);
    }
  };

  const handleFeedModeChange = (mode: 'smart' | 'chronological') => {
    if (mode === feedMode) return;
    setFeedMode(mode);
    fetchFeedItems(mode, feedCategory);
  };

  const handleFeedCategoryChange = (category: 'all' | 'reads' | 'reviews' | 'lists' | 'social') => {
    if (category === feedCategory) return;
    setFeedCategory(category);
    fetchFeedItems(feedMode, category);
  };

  // Acciones de control de feed para el usuario (Fase 22 - Roadmap 27)
  const handleHideActivity = async (activityId: string | number) => {
    setActiveMenuId(null);
    try {
      const headers: HeadersInit = token ? { Authorization: `Bearer ${token}` } : {};
      const res = await fetch(`${apiUrl}/api/v1/auth/feed/${activityId}/hide/`, {
        method: 'POST',
        headers,
      });
      if (res.ok) {
        setFeed((prev) => prev.filter((item) => item.id !== activityId));
        setToastMessage('Publicación descartada de tu feed.');
        setTimeout(() => setToastMessage(null), 3500);
      }
    } catch (e) {
      console.error('Error hiding activity', e);
    }
  };

  const handleMuteUser = async (userId: number, username: string) => {
    setActiveMenuId(null);
    try {
      const headers: HeadersInit = token ? { Authorization: `Bearer ${token}` } : {};
      const res = await fetch(`${apiUrl}/api/v1/auth/users/${userId}/mute/`, {
        method: 'POST',
        headers,
      });
      if (res.ok) {
        setFeed((prev) => prev.filter((item) => item.user.id !== userId));
        setToastMessage(
          `Has silenciado a @${username}. Sus publicaciones no aparecerán en tu feed.`
        );
        setTimeout(() => setToastMessage(null), 4000);
      }
    } catch (e) {
      console.error('Error muting user', e);
    }
  };

  const handleUnfollowUser = async (userId: number, username: string) => {
    setActiveMenuId(null);
    try {
      const headers: HeadersInit = token ? { Authorization: `Bearer ${token}` } : {};
      const res = await fetch(`${apiUrl}/api/v1/auth/users/${userId}/unfollow/`, {
        method: 'POST',
        headers,
      });
      if (res.ok) {
        setFeed((prev) => prev.filter((item) => item.user.id !== userId));
        setToastMessage(`Has dejado de seguir a @${username}.`);
        setTimeout(() => setToastMessage(null), 3500);
      }
    } catch (e) {
      console.error('Error unfollowing user', e);
    }
  };

  const handleBlockUser = async (userId: number, username: string) => {
    setActiveMenuId(null);
    if (
      !window.confirm(
        `¿Estás seguro de que deseas bloquear a @${username}? No podréis interactuar ni ver vuestro contenido mutuamente.`
      )
    ) {
      return;
    }
    try {
      const headers: HeadersInit = token ? { Authorization: `Bearer ${token}` } : {};
      const res = await fetch(`${apiUrl}/api/v1/auth/users/${userId}/block/`, {
        method: 'POST',
        headers,
      });
      if (res.ok) {
        setFeed((prev) => prev.filter((item) => item.user.id !== userId));
        setToastMessage(`Has bloqueado a @${username}.`);
        setTimeout(() => setToastMessage(null), 4000);
      }
    } catch (e) {
      console.error('Error blocking user', e);
    }
  };

  const getActivityActionText = (item: FeedItem) => {
    if (item.type_display) return item.type_display.toLowerCase();
    switch (item.type) {
      case 'REVIEW_CREATED':
      case 'review':
        return 'ha publicado una reseña de';
      case 'BOOK_FINISHED':
      case 'finished_reading':
        return 'ha terminado de leer';
      case 'BOOK_STARTED':
        return 'ha empezado a leer';
      case 'BOOK_RATED':
        return 'ha calificado';
      case 'BOOK_ADDED':
        return 'ha añadido a su biblioteca';
      case 'LIST_CREATED':
        return 'ha creado una lista de lectura';
      case 'USER_FOLLOWED':
        return 'ha comenzado a seguir a un lector';
      case 'REVIEW_LIKED':
        return 'ha reaccionado a la reseña de';
      case 'COMMENT_ADDED':
        return 'ha comentado en la reseña de';
      default:
        return 'ha compartido una novedad sobre';
    }
  };

  if (!user) return null;

  const renderStars = (rating?: number) => {
    if (!rating) return null;
    return (
      <div className="flex items-center text-amber-400 text-xs">
        {Array.from({ length: 5 }).map((_, i) => (
          <span key={i}>{i < Math.round(rating) ? '★' : '☆'}</span>
        ))}
        <span className="ml-1 text-gray-500 font-medium">{rating.toFixed(1)}</span>
      </div>
    );
  };

  const formatRelativeTime = (timestamp?: string) => {
    if (!timestamp) return 'Reciente';
    const diffMs = Date.now() - new Date(timestamp).getTime();
    if (isNaN(diffMs)) return 'Reciente';
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    if (diffHours < 1) return 'Hace unos minutos';
    if (diffHours < 24) return `Hace ${diffHours} h`;
    const diffDays = Math.floor(diffHours / 24);
    return `Hace ${diffDays} d`;
  };

  const handleRecommendationClick = (book: RecommendedBook, index: number) => {
    if (token) {
      fetch(`${apiUrl}/api/v1/books/recommendations/feedback/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          book_id: book.id,
          action: 'recommendation_clicked',
          strategy: 'hybrid',
          algorithm_version: 'v1.0',
          metadata: { position: index + 1, score: book.score },
        }),
      }).catch((err) => console.error('Error tracking recommendation click', err));
    }
    navigate(`/books/${book.id}`);
  };

  const getRankBadge = (index: number) => {
    if (index === 0) return { label: '#1 🥇', bg: 'bg-amber-500 text-white shadow-amber-500/40' };
    if (index === 1) return { label: '#2 🥈', bg: 'bg-slate-400 text-white shadow-slate-400/40' };
    if (index === 2) return { label: '#3 🥉', bg: 'bg-amber-700 text-white shadow-amber-700/40' };
    return { label: `#${index + 1}`, bg: 'bg-gray-900/80 backdrop-blur-sm text-white' };
  };

  return (
    <div className="space-y-8">
      <div className="max-w-7xl mx-auto space-y-8">
        {/* ── Hero Banner ── */}
        <div className="relative overflow-hidden rounded-3xl bg-gradient-to-r from-teal-700 via-teal-600 to-emerald-700 text-white p-6 sm:p-10 shadow-xl shadow-teal-900/10">
          <div className="relative z-10 max-w-2xl">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/20 backdrop-blur-md text-xs font-semibold uppercase tracking-wider mb-4">
              <span>📖</span>
              <span>Comunidad de Lectores</span>
            </div>
            <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight">
              ¡Qué bueno verte de nuevo, {user.username}!
            </h1>
            <p className="mt-3 text-teal-100 text-sm sm:text-base leading-relaxed">
              Explora las novedades literarias de tus amigos, descubre qué libros son tendencia hoy
              o consulta a tu asistente de lectura inteligente.
            </p>

            <div className="mt-6 flex flex-wrap items-center gap-3">
              <button
                onClick={() => navigate('/library')}
                className="bg-white text-teal-800 hover:bg-teal-50 font-bold px-5 py-2.5 rounded-xl text-sm transition-all shadow-md transform hover:-translate-y-0.5"
              >
                Mi Biblioteca
              </button>
              <button
                onClick={() => setIsAiModalOpen(true)}
                className="bg-amber-400 hover:bg-amber-300 text-gray-900 font-bold px-5 py-2.5 rounded-xl text-sm transition-all shadow-md flex items-center gap-2 transform hover:-translate-y-0.5"
              >
                <span>✨</span>
                <span>Descubrir con BookAI</span>
              </button>
              <button
                onClick={() => navigate('/books/add')}
                className="bg-white/10 hover:bg-white/20 border border-white/30 text-white font-medium px-4 py-2.5 rounded-xl text-sm transition-all backdrop-blur-sm"
              >
                + Añadir Libro
              </button>
            </div>
          </div>

          <div className="hidden lg:block absolute right-10 bottom-6 opacity-20 text-9xl pointer-events-none select-none">
            📚
          </div>
        </div>

        {/* ── Sección de Recomendados para ti (Fase 24) ── */}
        {recommendations.length > 0 && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
                  <span>✨</span>
                  <span>Recomendados para ti</span>
                </h2>
                <p className="text-xs sm:text-sm text-gray-500 dark:text-gray-400">
                  Sugerencias personalizadas basadas en tus afinidades, lecturas y amigos
                </p>
              </div>
              <Link
                to="/recommendations"
                className="text-xs sm:text-sm font-semibold text-teal-600 dark:text-teal-400 hover:text-teal-700 dark:hover:text-teal-300 hover:underline flex items-center gap-1"
              >
                <span>Ver todas</span>
                <span>→</span>
              </Link>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4 sm:gap-6">
              {recommendations.map((book, index) => (
                <div
                  key={book.id}
                  onClick={() => handleRecommendationClick(book, index)}
                  className="group bg-white dark:bg-gray-800 rounded-2xl p-3 border border-teal-100 dark:border-teal-900/40 shadow-sm hover:shadow-lg hover:border-teal-300 dark:hover:border-teal-600 transition-all duration-200 cursor-pointer flex flex-col justify-between"
                >
                  <div>
                    <div className="relative aspect-[2/3] w-full overflow-hidden rounded-xl bg-gray-100 dark:bg-gray-700 mb-3 shadow-inner">
                      {book.cover ? (
                        <img
                          src={resolveMediaUrl(book.cover)}
                          alt={book.title}
                          className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                          loading="lazy"
                        />
                      ) : (
                        <div className="w-full h-full flex items-center justify-center p-2 text-center text-xs font-semibold text-gray-400 dark:text-gray-500">
                          {book.title}
                        </div>
                      )}
                    </div>

                    <h3 className="font-bold text-sm text-gray-900 dark:text-white truncate group-hover:text-teal-600 dark:group-hover:text-teal-400 transition-colors">
                      {book.title}
                    </h3>
                    <p className="text-xs text-gray-500 dark:text-gray-400 truncate">
                      {book.author_name || 'Autor desconocido'}
                    </p>
                    {book.categories && book.categories.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-1">
                        {book.categories.slice(0, 1).map((c) => (
                          <span
                            key={c.id}
                            className="inline-block text-[9px] font-semibold text-teal-700 dark:text-teal-300 bg-teal-50 dark:bg-teal-900/30 px-1.5 py-0.5 rounded border border-teal-200/50 dark:border-teal-800/40 truncate max-w-[110px]"
                          >
                            {c.name}
                          </span>
                        ))}
                      </div>
                    )}
                    <div className="mt-1">
                      {book.average_rating ? (
                        renderStars(book.average_rating)
                      ) : (
                        <span className="text-[11px] text-gray-400">Sin reseñas aún</span>
                      )}
                    </div>
                  </div>

                  <div className="mt-2.5 pt-2 border-t border-gray-100 dark:border-gray-700/60">
                    <span className="inline-block text-[10px] font-medium text-teal-800 dark:text-teal-300 bg-teal-50 dark:bg-teal-950/60 px-2 py-0.5 rounded-md border border-teal-200/60 dark:border-teal-800/40 line-clamp-2">
                      💡 {book.reason}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ── Sección de Libros en Tendencia ── */}
        <div className="space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
            <div>
              <h2 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
                <span>🔥</span>
                <span>Tendencias de la Comunidad</span>
              </h2>
              <p className="text-xs sm:text-sm text-gray-500 dark:text-gray-400">
                Los libros con mayor actividad, lecturas y valoración comunitaria
              </p>
            </div>

            {/* Selector de periodo */}
            <div className="inline-flex p-1 bg-gray-100 dark:bg-gray-800 rounded-xl self-start sm:self-auto border border-gray-200 dark:border-gray-700 shadow-inner text-xs font-semibold">
              <button
                type="button"
                onClick={() => handlePeriodChange('week')}
                className={`px-3 py-1.5 rounded-lg transition-all ${
                  trendingPeriod === 'week'
                    ? 'bg-white dark:bg-gray-700 text-teal-700 dark:text-teal-400 shadow-sm font-bold'
                    : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
                }`}
              >
                Esta semana
              </button>
              <button
                type="button"
                onClick={() => handlePeriodChange('month')}
                className={`px-3 py-1.5 rounded-lg transition-all ${
                  trendingPeriod === 'month'
                    ? 'bg-white dark:bg-gray-700 text-teal-700 dark:text-teal-400 shadow-sm font-bold'
                    : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
                }`}
              >
                Este mes
              </button>
              <button
                type="button"
                onClick={() => handlePeriodChange('all')}
                className={`px-3 py-1.5 rounded-lg transition-all ${
                  trendingPeriod === 'all'
                    ? 'bg-white dark:bg-gray-700 text-teal-700 dark:text-teal-400 shadow-sm font-bold'
                    : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
                }`}
              >
                Histórico
              </button>
            </div>
          </div>

          {loading || trendingLoading ? (
            <div className="flex justify-center items-center py-12">
              <Spinner size="xl" color="info" />
            </div>
          ) : trending.length === 0 ? (
            <div className="text-center py-8 bg-white dark:bg-gray-800 rounded-2xl border border-gray-100 dark:border-gray-700 text-gray-500 text-sm">
              Aún no hay suficientes actividades registradas en este periodo para calcular
              tendencias. ¡Sé el primero en interactuar con tus libros!
            </div>
          ) : (
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4 sm:gap-6">
              {trending.map((book, index) => {
                const rank = getRankBadge(index);
                return (
                  <div
                    key={book.id}
                    onClick={() => navigate(`/books/${book.id}`)}
                    className="group bg-white dark:bg-gray-800 rounded-2xl p-3 border border-gray-100 dark:border-gray-700 shadow-sm hover:shadow-lg transition-all duration-200 cursor-pointer flex flex-col justify-between"
                  >
                    <div className="relative aspect-[2/3] w-full overflow-hidden rounded-xl bg-gray-100 dark:bg-gray-700 mb-3 shadow-inner">
                      {book.cover ? (
                        <img
                          src={resolveMediaUrl(book.cover)}
                          alt={book.title}
                          className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                          loading="lazy"
                        />
                      ) : (
                        <div className="w-full h-full flex items-center justify-center p-2 text-center text-xs font-semibold text-gray-400 dark:text-gray-500">
                          {book.title}
                        </div>
                      )}

                      {/* Medalla de ranking */}
                      <span
                        className={`absolute top-2 left-2 ${rank.bg} text-[10px] font-extrabold px-2 py-0.5 rounded-md shadow`}
                      >
                        {rank.label}
                      </span>

                      {/* Score de tendencia si existe */}
                      {book.trending_score !== undefined && book.trending_score > 0 && (
                        <span
                          className="absolute top-2 right-2 bg-rose-600/90 backdrop-blur-sm text-white text-[10px] font-bold px-1.5 py-0.5 rounded-md shadow flex items-center gap-0.5"
                          title={`Score de tendencia: ${book.trending_score}`}
                        >
                          <span>🔥</span>
                          <span>{book.trending_score}</span>
                        </span>
                      )}

                      {book.readers_count > 0 && (
                        <span className="absolute bottom-2 left-2 bg-gray-900/80 backdrop-blur-sm text-white text-[10px] font-bold px-2 py-0.5 rounded-md shadow">
                          {book.readers_count} {book.readers_count === 1 ? 'lector' : 'lectores'}
                        </span>
                      )}
                    </div>

                    <div>
                      <h3 className="font-bold text-sm text-gray-900 dark:text-white truncate group-hover:text-teal-600 dark:group-hover:text-teal-400 transition-colors">
                        {book.title}
                      </h3>
                      <p className="text-xs text-gray-500 dark:text-gray-400 truncate">
                        {book.author_name || 'Autor desconocido'}
                      </p>
                      <div className="mt-1">
                        {book.average_rating ? (
                          renderStars(book.average_rating)
                        ) : (
                          <span className="text-[11px] text-gray-400">Sin reseñas aún</span>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* ── Muro Social de Actividad ── */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <div className="lg:col-span-2 space-y-4">
            <FeedFilterTabs
              feedMode={feedMode}
              feedCategory={feedCategory}
              feedLoading={feedLoading}
              onFeedModeChange={handleFeedModeChange}
              onFeedCategoryChange={handleFeedCategoryChange}
            />

            {loading || feedLoading ? (
              <div className="flex justify-center items-center py-12">
                <Spinner size="lg" color="info" />
              </div>
            ) : feed.length === 0 ? (
              <div className="text-center py-12 bg-white dark:bg-gray-800 rounded-2xl border border-gray-100 dark:border-gray-700 p-8">
                <p className="text-gray-500 text-sm">
                  {feedCategory !== 'all'
                    ? 'No hay actividades en esta categoría para tu feed actual.'
                    : 'Aún no hay actividad social reciente. ¡Conecta con amigos para ver sus lecturas aquí!'}
                </p>
                <button
                  onClick={() => navigate('/friends')}
                  className="mt-4 inline-flex items-center text-teal-600 font-bold text-sm hover:underline cursor-pointer"
                >
                  Explorar usuarios y amigos ➔
                </button>
              </div>
            ) : (
              <div className="space-y-4">
                {feed.map((item) => (
                  <FeedActivityCard
                    key={item.id}
                    item={item}
                    currentUserId={user?.id}
                    activeMenuId={activeMenuId}
                    setActiveMenuId={setActiveMenuId}
                    onHideActivity={handleHideActivity}
                    onMuteUser={handleMuteUser}
                    onUnfollowUser={handleUnfollowUser}
                    onBlockUser={handleBlockUser}
                    renderStars={renderStars}
                    formatRelativeTime={formatRelativeTime}
                    getActivityActionText={getActivityActionText}
                  />
                ))}
              </div>
            )}
          </div>

          {/* ── Sidebar de BookAI & Enlaces Rápidos ── */}
          <TrendingSidebar onOpenAiModal={() => setIsAiModalOpen(true)} />
        </div>
      </div>

      {toastMessage && (
        <div className="fixed bottom-6 right-6 z-50 bg-gray-900/95 dark:bg-gray-100/95 text-white dark:text-gray-900 text-xs font-semibold px-4 py-3 rounded-2xl shadow-2xl flex items-center gap-3 backdrop-blur-md border border-gray-700/50 dark:border-gray-300/50">
          <span>✨</span>
          <span>{toastMessage}</span>
          <button
            type="button"
            onClick={() => setToastMessage(null)}
            className="ml-2 text-gray-400 hover:text-white dark:hover:text-black font-bold text-sm"
          >
            ✕
          </button>
        </div>
      )}

      <AIAssistantModal isOpen={isAiModalOpen} onClose={() => setIsAiModalOpen(false)} />
      <OnboardingModal isOpen={isOnboardingOpen} onClose={() => setIsOnboardingOpen(false)} />
    </div>
  );
};

export default Home;
