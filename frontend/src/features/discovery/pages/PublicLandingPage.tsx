import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuthStore } from '../../../store/auth';
import { AuthModal } from '../../auth';

interface DiscoveryBook {
  id: number;
  title: string;
  author_name: string;
  author_id?: number;
  cover?: string | null;
  average_rating: number;
  ratings_count: number;
  categories: string[];
  description: string;
  published_year?: number | null;
}

interface DiscoveryData {
  trending: DiscoveryBook[];
  popular: DiscoveryBook[];
  newest: DiscoveryBook[];
  categories: { id: number; name: string; slug: string; books_count: number }[];
  genre_books?: DiscoveryBook[];
  active_genre?: string | null;
  stats?: { total_books: number; total_reviews: number };
}

export function PublicLandingPage() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  // Estados de AuthModal
  const [isAuthOpen, setIsAuthOpen] = useState(false);
  const [authMode, setAuthMode] = useState<'login' | 'register'>('register');

  // Estados de datos de descubrimiento
  const [activeTab, setActiveTab] = useState<'trending' | 'popular' | 'newest'>('trending');
  const [selectedGenre, setSelectedGenre] = useState<string | null>(null);
  const [discoveryData, setDiscoveryData] = useState<DiscoveryData | null>(null);
  const [loadingDiscovery, setLoadingDiscovery] = useState(true);

  const apiUrl = (import.meta as any).env.VITE_API_URL || 'http://localhost:8000';

  // Si el usuario ya está autenticado, redirigir a /home
  useEffect(() => {
    if (isAuthenticated) {
      navigate('/home', { replace: true });
    }
  }, [isAuthenticated, navigate]);

  // Si la URL viene con ?auth=login o ?auth=register, abrir modal
  useEffect(() => {
    const authParam = searchParams.get('auth');
    if (authParam === 'login' || authParam === 'register') {
      setAuthMode(authParam);
      setIsAuthOpen(true);
    }
  }, [searchParams]);

  // Cargar datos de descubrimiento desde el backend
  useEffect(() => {
    let isMounted = true;
    const fetchDiscovery = async () => {
      try {
        setLoadingDiscovery(true);
        const url = selectedGenre
          ? `${apiUrl}/api/v1/books/discover/?genre=${encodeURIComponent(selectedGenre)}&limit=8`
          : `${apiUrl}/api/v1/books/discover/?limit=8`;
        const res = await fetch(url);
        if (res.ok) {
          const data = await res.json();
          if (isMounted) setDiscoveryData(data);
        }
      } catch (err) {
        console.error('Error al cargar datos de descubrimiento:', err);
      } finally {
        if (isMounted) setLoadingDiscovery(false);
      }
    };
    fetchDiscovery();
    return () => {
      isMounted = false;
    };
  }, [selectedGenre, apiUrl]);

  const openAuth = (mode: 'login' | 'register') => {
    setAuthMode(mode);
    setIsAuthOpen(true);
  };

  // Libros actuales a mostrar
  const currentBooks: DiscoveryBook[] = selectedGenre && discoveryData?.genre_books && discoveryData.genre_books.length > 0
    ? discoveryData.genre_books
    : discoveryData
    ? discoveryData[activeTab] || []
    : [];

  return (
    <div className="w-full flex flex-col gap-16 sm:gap-24 pb-16">
      {/* 1. HERO SECTION */}
      <section className="relative pt-6 sm:pt-12 pb-12 overflow-hidden">
        {/* Luces y gradientes de fondo decorativos */}
        <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-3/4 max-w-4xl h-96 bg-gradient-to-tr from-teal-500/15 via-emerald-500/10 to-cyan-500/10 rounded-full blur-3xl pointer-events-none" />

        <div className="relative max-w-5xl mx-auto px-4 text-center flex flex-col items-center">
          {/* Badge con pill animado */}
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-teal-50 dark:bg-teal-950/60 border border-teal-200 dark:border-teal-800/80 text-teal-800 dark:text-teal-300 text-xs sm:text-sm font-semibold mb-6 shadow-sm">
            <span className="flex h-2 w-2 rounded-full bg-emerald-500 animate-ping" />
            <span>Plataforma social de lectura • Beta abierta sin algoritmos invasivos</span>
          </div>

          {/* Título principal */}
          <h1 className="text-4xl sm:text-5xl md:text-6xl font-black text-slate-900 dark:text-white tracking-tight leading-tight max-w-4xl">
            Tu universo literario conectado en{' '}
            <span className="bg-gradient-to-r from-teal-600 via-emerald-600 to-teal-500 dark:from-teal-300 dark:via-emerald-400 dark:to-cyan-300 bg-clip-text text-transparent">
              un solo lugar
            </span>
          </h1>

          {/* Subtítulo inspirador */}
          <p className="mt-6 text-base sm:text-lg md:text-xl text-slate-600 dark:text-slate-300 max-w-2xl leading-relaxed">
            Organiza tus lecturas, descubre tu próximo libro favorito con algoritmos transparentes
            y comparte notas y reseñas sinceras con una comunidad viva y respetuosa.
          </p>

          {/* Botones de acción principales */}
          <div className="mt-8 flex flex-col sm:flex-row items-center justify-center gap-4 w-full sm:w-auto">
            <button
              onClick={() => openAuth('register')}
              className="w-full sm:w-auto px-8 py-3.5 rounded-2xl font-bold text-base text-slate-950 bg-gradient-to-r from-teal-300 via-emerald-300 to-teal-200 hover:from-teal-200 hover:to-emerald-200 shadow-xl shadow-teal-900/20 hover:shadow-teal-900/40 transition-all transform hover:-translate-y-0.5 cursor-pointer"
            >
              Comenzar gratis en 1 minuto
            </button>
            <button
              onClick={() => openAuth('login')}
              className="w-full sm:w-auto px-7 py-3.5 rounded-2xl font-bold text-base text-slate-700 dark:text-slate-200 bg-white dark:bg-slate-800/80 hover:bg-slate-50 dark:hover:bg-slate-800 border border-slate-200 dark:border-slate-700/80 shadow-sm transition-all cursor-pointer"
            >
              Ya soy miembro • Iniciar sesión
            </button>
          </div>

          {/* Ventajas rápidas */}
          <div className="mt-10 flex flex-wrap items-center justify-center gap-6 sm:gap-8 text-xs sm:text-sm text-slate-500 dark:text-slate-400 font-medium">
            <span className="flex items-center gap-1.5">
              <span className="text-emerald-500">✓</span> Importa de Goodreads/StoryGraph
            </span>
            <span className="flex items-center gap-1.5">
              <span className="text-emerald-500">✓</span> 100% Privacidad (RGPD Art. 17 & 20)
            </span>
            <span className="flex items-center gap-1.5">
              <span className="text-emerald-500">✓</span> Sin publicidad intrusiva
            </span>
          </div>
        </div>
      </section>

      {/* 2. SECCIÓN DE DESCUBRIMIENTO LITERARIO (Fase 20) */}
      <section id="descubrimiento" className="scroll-mt-20">
        <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 mb-8">
          <div>
            <div className="inline-flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-teal-600 dark:text-teal-400 mb-1">
              <span>✨</span>
              <span>Explora el Catálogo</span>
            </div>
            <h2 className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-white">
              Descubrimiento de Libros
            </h2>
            <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400 mt-1">
              Libros en tendencia, más leídos por la comunidad y últimas incorporaciones.
            </p>
          </div>

          {/* Pestañas de selección rápida */}
          <div className="flex p-1 bg-slate-200/70 dark:bg-slate-800/80 rounded-2xl border border-slate-300/40 dark:border-slate-700/60 self-start sm:self-auto">
            <button
              onClick={() => {
                setSelectedGenre(null);
                setActiveTab('trending');
              }}
              className={`px-4 py-2 text-xs font-bold rounded-xl transition-all cursor-pointer ${
                activeTab === 'trending' && !selectedGenre
                  ? 'bg-white dark:bg-slate-900 text-teal-600 dark:text-teal-400 shadow-sm'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
              }`}
            >
              🌟 Tendencias
            </button>
            <button
              onClick={() => {
                setSelectedGenre(null);
                setActiveTab('popular');
              }}
              className={`px-4 py-2 text-xs font-bold rounded-xl transition-all cursor-pointer ${
                activeTab === 'popular' && !selectedGenre
                  ? 'bg-white dark:bg-slate-900 text-teal-600 dark:text-teal-400 shadow-sm'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
              }`}
            >
              🔥 Populares
            </button>
            <button
              onClick={() => {
                setSelectedGenre(null);
                setActiveTab('newest');
              }}
              className={`px-4 py-2 text-xs font-bold rounded-xl transition-all cursor-pointer ${
                activeTab === 'newest' && !selectedGenre
                  ? 'bg-white dark:bg-slate-900 text-teal-600 dark:text-teal-400 shadow-sm'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
              }`}
            >
              🆕 Novedades
            </button>
          </div>
        </div>

        {/* Chips de Categorías/Géneros */}
        {discoveryData?.categories && discoveryData.categories.length > 0 && (
          <div className="flex items-center gap-2 overflow-x-auto pb-4 mb-6 scrollbar-none">
            <button
              onClick={() => setSelectedGenre(null)}
              className={`px-3 py-1.5 rounded-full text-xs font-semibold whitespace-nowrap transition-all cursor-pointer ${
                selectedGenre === null
                  ? 'bg-teal-600 text-white shadow-sm'
                  : 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700'
              }`}
            >
              Todos los géneros
            </button>
            {discoveryData.categories.map((c) => (
              <button
                key={c.id}
                onClick={() => setSelectedGenre(c.slug)}
                className={`px-3 py-1.5 rounded-full text-xs font-semibold whitespace-nowrap transition-all cursor-pointer flex items-center gap-1.5 ${
                  selectedGenre === c.slug
                    ? 'bg-teal-600 text-white shadow-sm'
                    : 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700'
                }`}
              >
                <span>{c.name}</span>
                <span className="text-[10px] opacity-75">({c.books_count})</span>
              </button>
            ))}
          </div>
        )}

        {/* Grid de Libros */}
        {loadingDiscovery ? (
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4 sm:gap-6 animate-pulse">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="h-72 bg-slate-200 dark:bg-slate-800 rounded-3xl" />
            ))}
          </div>
        ) : currentBooks.length === 0 ? (
          <div className="p-8 text-center bg-white dark:bg-slate-900 rounded-3xl border border-slate-200 dark:border-slate-800">
            <p className="text-slate-500 dark:text-slate-400 text-sm">
              No se encontraron libros para esta categoría actualmente.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4 sm:gap-6">
            {currentBooks.map((book) => (
              <div
                key={book.id}
                onClick={() => openAuth('register')}
                className="group relative flex flex-col rounded-3xl bg-white dark:bg-slate-900 border border-slate-100 dark:border-slate-800/80 shadow-md hover:shadow-xl transition-all duration-300 p-3 sm:p-4 hover:-translate-y-1 cursor-pointer overflow-hidden"
              >
                {/* Contenedor de Portada */}
                <div className="w-full aspect-[2/3] rounded-2xl bg-slate-100 dark:bg-slate-800 overflow-hidden relative mb-3">
                  {book.cover ? (
                    <img
                      src={book.cover}
                      alt={book.title}
                      loading="lazy"
                      className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                    />
                  ) : (
                    <div className="w-full h-full flex flex-col items-center justify-center text-center p-3 bg-gradient-to-br from-teal-50 to-slate-100 dark:from-slate-800 dark:to-slate-900">
                      <span className="text-3xl mb-1">📖</span>
                      <span className="text-[11px] font-bold text-slate-700 dark:text-slate-300 line-clamp-3">
                        {book.title}
                      </span>
                    </div>
                  )}

                  {/* Rating Badge flotante */}
                  {book.average_rating > 0 && (
                    <div className="absolute top-2 right-2 px-2 py-0.5 rounded-lg bg-black/70 backdrop-blur-sm text-amber-300 font-bold text-[11px] flex items-center gap-1 shadow">
                      <span>★</span>
                      <span>{book.average_rating.toFixed(1)}</span>
                    </div>
                  )}
                </div>

                {/* Info del libro */}
                <div className="flex-1 flex flex-col justify-between">
                  <div>
                    <h3 className="font-bold text-sm text-slate-900 dark:text-white line-clamp-1 group-hover:text-teal-600 dark:group-hover:text-teal-400 transition-colors">
                      {book.title}
                    </h3>
                    <p className="text-xs text-slate-500 dark:text-slate-400 line-clamp-1 mt-0.5 font-medium">
                      {book.author_name}
                    </p>
                  </div>

                  {book.categories && book.categories.length > 0 && (
                    <div className="mt-2.5 flex items-center gap-1 overflow-hidden">
                      <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 truncate">
                        {book.categories[0]}
                      </span>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* 3. SECCIÓN POR QUÉ ELEGIRNOS */}
      <section id="caracteristicas" className="scroll-mt-20">
        <div className="text-center max-w-2xl mx-auto mb-12">
          <div className="inline-flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-teal-600 dark:text-teal-400 mb-2">
            <span>🛡️</span>
            <span>Experiencia de Usuario</span>
          </div>
          <h2 className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-white">
            Diseñado para personas que aman leer
          </h2>
          <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
            Una plataforma construida sobre la honestidad, la privacidad y el placer de la lectura.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {/* Card 1 */}
          <div className="rounded-3xl p-6 bg-white dark:bg-slate-900 border border-slate-100 dark:border-slate-800 shadow-sm hover:shadow-md transition-shadow">
            <div className="w-12 h-12 rounded-2xl bg-teal-50 dark:bg-teal-950/60 border border-teal-200/60 dark:border-teal-800/60 flex items-center justify-center text-2xl mb-4">
              📚
            </div>
            <h3 className="font-bold text-base text-slate-900 dark:text-white mb-2">
              Estanterías Inteligentes
            </h3>
            <p className="text-xs sm:text-sm text-slate-600 dark:text-slate-400 leading-relaxed">
              Organiza tus lecturas por "Leyendo", "Leídos" o "Por leer". Importa tu historial de Goodreads
              o StoryGraph en un clic sin perder ni una reseña.
            </p>
          </div>

          {/* Card 2 */}
          <div className="rounded-3xl p-6 bg-white dark:bg-slate-900 border border-slate-100 dark:border-slate-800 shadow-sm hover:shadow-md transition-shadow">
            <div className="w-12 h-12 rounded-2xl bg-emerald-50 dark:bg-emerald-950/60 border border-emerald-200/60 dark:border-emerald-800/60 flex items-center justify-center text-2xl mb-4">
              🛡️
            </div>
            <h3 className="font-bold text-base text-slate-900 dark:text-white mb-2">
              Privacidad Incondicional
            </h3>
            <p className="text-xs sm:text-sm text-slate-600 dark:text-slate-400 leading-relaxed">
              Tus datos nunca se venden ni se emplean para entrenar modelos de IA de terceros.
              Total cumplimiento de RGPD con derecho al olvido y exportación instantánea.
            </p>
          </div>

          {/* Card 3 */}
          <div className="rounded-3xl p-6 bg-white dark:bg-slate-900 border border-slate-100 dark:border-slate-800 shadow-sm hover:shadow-md transition-shadow">
            <div className="w-12 h-12 rounded-2xl bg-cyan-50 dark:bg-cyan-950/60 border border-cyan-200/60 dark:border-cyan-800/60 flex items-center justify-center text-2xl mb-4">
              💬
            </div>
            <h3 className="font-bold text-base text-slate-900 dark:text-white mb-2">
              Comunidad Literaria Real
            </h3>
            <p className="text-xs sm:text-sm text-slate-600 dark:text-slate-400 leading-relaxed">
              Descubre qué leen tus amigos, intercambia impresiones, crea listas colaborativas
              y conversa en tiempo real sin algoritmos adictivos ni clickbait.
            </p>
          </div>

          {/* Card 4 */}
          <div className="rounded-3xl p-6 bg-white dark:bg-slate-900 border border-slate-100 dark:border-slate-800 shadow-sm hover:shadow-md transition-shadow">
            <div className="w-12 h-12 rounded-2xl bg-purple-50 dark:bg-purple-950/60 border border-purple-200/60 dark:border-purple-800/60 flex items-center justify-center text-2xl mb-4">
              ✨
            </div>
            <h3 className="font-bold text-base text-slate-900 dark:text-white mb-2">
              BookAI Asistente Ético
            </h3>
            <p className="text-xs sm:text-sm text-slate-600 dark:text-slate-400 leading-relaxed">
              Encuentra libros con temáticas complejas, conexiones literarias inesperadas o resúmenes
              temáticos utilizando inteligencia artificial privada y controlada.
            </p>
          </div>
        </div>
      </section>

      {/* 4. BANNER FINAL CTA */}
      <section className="rounded-3xl p-8 sm:p-12 bg-gradient-to-r from-teal-800 via-emerald-800 to-teal-900 text-white shadow-2xl relative overflow-hidden text-center">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,_var(--tw-gradient-stops))] from-white/10 via-transparent to-transparent pointer-events-none" />
        <div className="relative max-w-2xl mx-auto flex flex-col items-center">
          <span className="text-4xl mb-4">📖</span>
          <h2 className="text-2xl sm:text-4xl font-extrabold tracking-tight">
            ¿Listo para empezar tu próxima aventura de lectura?
          </h2>
          <p className="mt-4 text-teal-100 text-sm sm:text-base leading-relaxed">
            Únete a la comunidad de MyBookConnect. Crea tu cuenta en menos de un minuto
            y organiza tu biblioteca personal hoy mismo.
          </p>
          <div className="mt-8 flex flex-col sm:flex-row items-center gap-4">
            <button
              onClick={() => openAuth('register')}
              className="w-full sm:w-auto px-8 py-3.5 rounded-2xl font-bold text-base text-slate-950 bg-gradient-to-r from-teal-300 via-emerald-300 to-teal-200 hover:from-teal-200 hover:to-emerald-200 shadow-xl transition-all cursor-pointer"
            >
              Crear cuenta gratis
            </button>
            <button
              onClick={() => openAuth('login')}
              className="w-full sm:w-auto px-7 py-3.5 rounded-2xl font-bold text-base text-white hover:bg-white/10 border border-white/20 transition-all cursor-pointer"
            >
              Iniciar sesión
            </button>
          </div>
        </div>
      </section>

      {/* MODAL GLOBAL DE LOGIN Y REGISTRO */}
      <AuthModal
        isOpen={isAuthOpen}
        initialMode={authMode}
        onClose={() => setIsAuthOpen(false)}
      />
    </div>
  );
}

export default PublicLandingPage;
