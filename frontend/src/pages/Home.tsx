import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/auth';
import { Spinner } from 'flowbite-react';
import { AIAssistantModal } from '../components/AIAssistantModal';

interface TrendingBook {
  id: number;
  title: string;
  cover?: string;
  author_name: string;
  average_rating?: number;
  readers_count: number;
  reviews_count: number;
}

interface FeedItem {
  id: string;
  type: 'review' | 'finished_reading';
  timestamp: string;
  user: {
    id: number;
    username: string;
    avatar?: string;
  };
  book: {
    id: number;
    title: string;
    cover?: string;
    author_name: string;
  };
  rating?: number;
  comment?: string;
}

export const Home = () => {
  const { user, token } = useAuthStore();
  const navigate = useNavigate();

  const [trending, setTrending] = useState<TrendingBook[]>([]);
  const [feed, setFeed] = useState<FeedItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [isAiModalOpen, setIsAiModalOpen] = useState(false);

  const apiUrl = (import.meta as any).env.VITE_API_URL || 'http://localhost:8000';

  useEffect(() => {
    if (!user) {
      navigate('/');
      return;
    }

    const loadDashboardData = async () => {
      try {
        setLoading(true);
        const headers = token ? { Authorization: `Bearer ${token}` } : {};

        const [trendingRes, feedRes] = await Promise.all([
          fetch(`${apiUrl}/api/v1/books/trending/`, { headers }),
          fetch(`${apiUrl}/api/v1/books/feed/`, { headers }),
        ]);

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

  const formatRelativeTime = (timestamp: string) => {
    const diffMs = Date.now() - new Date(timestamp).getTime();
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    if (diffHours < 1) return 'Hace unos minutos';
    if (diffHours < 24) return `Hace ${diffHours} h`;
    const diffDays = Math.floor(diffHours / 24);
    return `Hace ${diffDays} d`;
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
              Explora las novedades literarias de tus amigos, descubre qué libros son tendencia hoy o consulta a tu asistente de lectura inteligente.
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

        {/* ── Sección de Libros en Tendencia ── */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
                <span>🔥</span>
                <span>Tendencias de la Comunidad</span>
              </h2>
              <p className="text-xs sm:text-sm text-gray-500 dark:text-gray-400">
                Los libros más leídos y valorados por la comunidad
              </p>
            </div>
          </div>

          {loading ? (
            <div className="flex justify-center items-center py-12">
              <Spinner size="xl" color="info" />
            </div>
          ) : trending.length === 0 ? (
            <div className="text-center py-8 bg-white dark:bg-gray-800 rounded-2xl border border-gray-100 dark:border-gray-700 text-gray-500 text-sm">
              Aún no hay suficientes lecturas registradas para calcular tendencias. ¡Sé el primero en calificar tus libros!
            </div>
          ) : (
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4 sm:gap-6">
              {trending.map((book) => (
                <div
                  key={book.id}
                  onClick={() => navigate(`/books/${book.id}`)}
                  className="group bg-white dark:bg-gray-800 rounded-2xl p-3 border border-gray-100 dark:border-gray-700 shadow-sm hover:shadow-lg transition-all duration-200 cursor-pointer flex flex-col justify-between"
                >
                  <div className="relative aspect-[2/3] w-full overflow-hidden rounded-xl bg-gray-100 dark:bg-gray-700 mb-3 shadow-inner">
                    {book.cover ? (
                      <img
                        src={book.cover}
                        alt={book.title}
                        className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                        loading="lazy"
                      />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center p-2 text-center text-xs font-semibold text-gray-400 dark:text-gray-500">
                        {book.title}
                      </div>
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
                      {book.average_rating ? renderStars(book.average_rating) : (
                        <span className="text-[11px] text-gray-400">Sin reseñas aún</span>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* ── Muro Social de Actividad ── */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <div className="lg:col-span-2 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
                  <span>✨</span>
                  <span>Muro Social de Lecturas</span>
                </h2>
                <p className="text-xs sm:text-sm text-gray-500 dark:text-gray-400">
                  Actividad reciente de amigos y lectores de la plataforma
                </p>
              </div>
            </div>

            {loading ? (
              <div className="flex justify-center items-center py-12">
                <Spinner size="lg" color="info" />
              </div>
            ) : feed.length === 0 ? (
              <div className="text-center py-12 bg-white dark:bg-gray-800 rounded-2xl border border-gray-100 dark:border-gray-700 p-8">
                <p className="text-gray-500 text-sm">
                  Aún no hay actividad social reciente. ¡Conecta con amigos para ver sus lecturas aquí!
                </p>
                <button
                  onClick={() => navigate('/friends')}
                  className="mt-4 inline-flex items-center text-teal-600 font-bold text-sm hover:underline"
                >
                  Explorar usuarios y amigos ➔
                </button>
              </div>
            ) : (
              <div className="space-y-4">
                {feed.map((item) => (
                  <div
                    key={item.id}
                    className="bg-white dark:bg-gray-800 rounded-2xl p-5 border border-gray-100 dark:border-gray-700 shadow-sm hover:shadow-md transition-shadow"
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex items-center space-x-3">
                        {item.user.avatar ? (
                          <img
                            src={item.user.avatar}
                            alt={item.user.username}
                            className="w-10 h-10 rounded-full object-cover cursor-pointer hover:opacity-80"
                            onClick={() => navigate(`/users/${item.user.id}`)}
                          />
                        ) : (
                          <div
                            onClick={() => navigate(`/users/${item.user.id}`)}
                            className="w-10 h-10 rounded-full bg-teal-600 text-white flex items-center justify-center font-bold cursor-pointer hover:bg-teal-700"
                          >
                            {item.user.username[0]?.toUpperCase()}
                          </div>
                        )}
                        <div>
                          <p className="text-sm text-gray-900 dark:text-white">
                            <strong
                              onClick={() => navigate(`/users/${item.user.id}`)}
                              className="cursor-pointer hover:text-teal-600 font-bold"
                            >
                              @{item.user.username}
                            </strong>{' '}
                            <span className="text-gray-500 dark:text-gray-400">
                              {item.type === 'review'
                                ? 'ha publicado una reseña de'
                                : 'ha terminado de leer'}
                            </span>
                          </p>
                          <span className="text-[11px] text-gray-400">
                            {formatRelativeTime(item.timestamp)}
                          </span>
                        </div>
                      </div>

                      {item.rating && renderStars(item.rating)}
                    </div>

                    <div
                      onClick={() => navigate(`/books/${item.book.id}`)}
                      className="mt-4 p-3 rounded-xl bg-gray-50 dark:bg-gray-700/50 hover:bg-teal-50/50 dark:hover:bg-gray-700 cursor-pointer flex items-center space-x-3 border border-gray-100 dark:border-gray-600/50 transition-colors"
                    >
                      {item.book.cover ? (
                        <img
                          src={item.book.cover}
                          alt={item.book.title}
                          className="w-12 h-16 object-cover rounded shadow shrink-0"
                        />
                      ) : (
                        <div className="w-12 h-16 bg-teal-700 text-white rounded flex items-center justify-center text-[10px] text-center font-medium shrink-0 p-1">
                          {item.book.title}
                        </div>
                      )}
                      <div className="min-w-0 flex-1">
                        <h4 className="font-bold text-sm text-gray-900 dark:text-white truncate">
                          {item.book.title}
                        </h4>
                        <p className="text-xs text-gray-500 dark:text-gray-400 truncate">
                          {item.book.author_name}
                        </p>
                      </div>
                    </div>

                    {item.comment && (
                      <div className="mt-3 text-sm text-gray-700 dark:text-gray-300 italic bg-gray-50/70 dark:bg-gray-700/30 p-3 rounded-xl border-l-2 border-teal-500">
                        "{item.comment}"
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* ── Sidebar de BookAI & Enlaces Rápidos ── */}
          <div className="space-y-6">
            <div className="rounded-3xl bg-gradient-to-br from-teal-900 via-teal-800 to-emerald-950 text-white p-6 shadow-xl relative overflow-hidden">
              <div className="w-12 h-12 rounded-2xl bg-white/10 backdrop-blur-md flex items-center justify-center text-2xl mb-4 shadow-inner">
                ✨
              </div>
              <h3 className="text-lg font-bold">Asistente Literario BookAI</h3>
              <p className="mt-2 text-xs sm:text-sm text-teal-100/90 leading-relaxed">
                ¿No sabes qué leer a continuación? Pídele recomendaciones a BookAI basadas en tu biblioteca o consulta por géneros y autores.
              </p>
              <button
                onClick={() => setIsAiModalOpen(true)}
                className="mt-5 w-full bg-gradient-to-r from-amber-400 to-orange-400 hover:from-amber-300 hover:to-orange-300 text-slate-900 font-bold py-2.5 px-4 rounded-xl text-sm transition-all shadow-md transform hover:-translate-y-0.5"
              >
                Abrir BookAI
              </button>
            </div>

            <div className="bg-white dark:bg-gray-800 rounded-3xl p-6 border border-gray-100 dark:border-gray-700 shadow-sm space-y-4">
              <h3 className="font-bold text-gray-900 dark:text-white text-base">
                Comunidad & Conexiones
              </h3>
              <p className="text-xs text-gray-500 dark:text-gray-400 leading-relaxed">
                Encuentra amigos lectores, compara vuestras estanterías y chatea en tiempo real sobre vuestras novelas favoritas.
              </p>
              <div className="pt-2 flex flex-col gap-2">
                <button
                  onClick={() => navigate('/friends')}
                  className="w-full text-left px-4 py-2.5 rounded-xl text-xs font-semibold bg-gray-50 dark:bg-gray-700 hover:bg-teal-50 dark:hover:bg-teal-900/30 text-gray-700 dark:text-gray-200 hover:text-teal-700 transition-colors flex items-center justify-between"
                >
                  <span>👥 Ver Lista de Amigos</span>
                  <span>➔</span>
                </button>
                <button
                  onClick={() => navigate('/chat')}
                  className="w-full text-left px-4 py-2.5 rounded-xl text-xs font-semibold bg-gray-50 dark:bg-gray-700 hover:bg-teal-50 dark:hover:bg-teal-900/30 text-gray-700 dark:text-gray-200 hover:text-teal-700 transition-colors flex items-center justify-between"
                >
                  <span>💬 Bandeja de Mensajes</span>
                  <span>➔</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <AIAssistantModal
        isOpen={isAiModalOpen}
        onClose={() => setIsAiModalOpen(false)}
      />
    </div>
  );
};