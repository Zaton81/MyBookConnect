import { useEffect, useState } from 'react';
import { useSearchParams, useNavigate, Link } from 'react-router-dom';
import { Button, Spinner } from 'flowbite-react';
import {
  HiOutlineLightningBolt,
  HiOutlineChartBar,
  HiOutlineBookOpen,
  HiOutlineSparkles,
  HiOutlineArrowSmUp,
  HiOutlineArrowSmDown,
} from 'react-icons/hi';
import { useAuthStore } from '../../../store/auth';
import {
  ActiveChallengesCard,
  BadgesGrid,
  GamificationOverviewData,
  ReadingGoalCard,
  ReadingStreakCard,
} from '../components/gamification';

interface TopGenre {
  name: string;
  count: number;
  percentage: number;
}

interface TopAuthor {
  id: number;
  name: string;
  count: number;
}

interface MonthlyStat {
  key: string;
  label: string;
  month?: number;
  year?: number;
  count: number;
  pages?: number;
}

interface ReadingPaceData {
  avg_days_per_book: number | null;
  fastest_book: {
    book_id: number;
    title: string;
    author: string;
    cover: string | null;
    days: number;
    pages: number;
  } | null;
  slowest_book: {
    book_id: number;
    title: string;
    author: string;
    cover: string | null;
    days: number;
    pages: number;
  } | null;
  avg_pages_per_day: number;
  avg_pages_per_month: number;
  highest_reading_month: {
    label: string;
    count: number;
  };
}

interface LengthCategory {
  label: string;
  count: number;
  percentage: number;
}

interface LengthDistributionData {
  short: LengthCategory;
  medium: LengthCategory;
  long: LengthCategory;
  epic: LengthCategory;
  longest_book: {
    book_id: number;
    title: string;
    author: string;
    pages: number;
    cover: string | null;
  } | null;
  shortest_book: {
    book_id: number;
    title: string;
    author: string;
    pages: number;
    cover: string | null;
  } | null;
}

interface FormatDistributionData {
  physical_count: number;
  physical_percentage: number;
  digital_count: number;
  digital_percentage: number;
  owned_count: number;
  owned_percentage: number;
  borrowed_count: number;
  borrowed_percentage: number;
}

interface YearInReviewData {
  year: number;
  total_books: number;
  total_pages: number;
  highest_rated_book: {
    book_id: number;
    title: string;
    author: string;
    rating: number;
    cover: string | null;
  } | null;
  favorite_genre: string | null;
  favorite_author: string | null;
  comparison_previous_year: {
    previous_year: number;
    previous_year_books: number;
    previous_year_pages: number;
    books_difference: number;
    books_percentage_change: number | null;
  };
}

interface ReadingStatsData {
  total_books: number;
  total_read: number;
  currently_reading: number;
  want_to_read: number;
  abandoned: number;
  total_pages_read: number;
  average_rating: number | null;
  ratings_distribution: Record<string | number, number>;
  top_genres: TopGenre[];
  top_authors: TopAuthor[];
  books_this_year: number;
  books_per_month: MonthlyStat[];
  selected_year?: number | null;
  available_years?: number[];
  reading_pace?: ReadingPaceData;
  length_distribution?: LengthDistributionData;
  format_distribution?: FormatDistributionData;
  year_in_review?: YearInReviewData;
}

type StatsTab = 'overview' | 'pace' | 'length' | 'review';

export function ReadingStats() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { token, user } = useAuthStore();

  const userIdParam = searchParams.get('user_id');
  const isOwnStats = !userIdParam || (user && String(user.id) === userIdParam);

  const [stats, setStats] = useState<ReadingStatsData | null>(null);
  const [gamification, setGamification] = useState<GamificationOverviewData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Estados avanzados del Sprint 15
  const [activeTab, setActiveTab] = useState<StatsTab>('overview');
  const [selectedYear, setSelectedYear] = useState<string>('all');
  const [chartMetric, setChartMetric] = useState<'books' | 'pages'>('books');

  const apiUrl = (import.meta as any).env.VITE_API_URL || 'http://localhost:8000';

  const fetchGamification = async () => {
    try {
      const query = userIdParam ? `?user_id=${encodeURIComponent(userIdParam)}` : '';
      const res = await fetch(`${apiUrl}/api/v1/gamification/overview/${query}`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (res.ok) {
        const data = await res.json();
        setGamification(data);
      }
    } catch (e) {
      console.warn('Error fetching gamification overview', e);
    }
  };

  const fetchStats = async (yearFilter: string) => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      if (userIdParam) params.set('user_id', userIdParam);
      if (yearFilter && yearFilter !== 'all') params.set('year', yearFilter);

      const queryStr = params.toString() ? `?${params.toString()}` : '';
      const res = await fetch(`${apiUrl}/api/v1/books/statistics/${queryStr}`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });

      if (res.status === 403) {
        const errData = await res.json().catch(() => ({}));
        setError(errData.detail || 'Este perfil es privado o solo está disponible para amigos.');
        setStats(null);
        return;
      }

      if (!res.ok) {
        throw new Error('No se pudieron cargar las estadísticas de lectura.');
      }

      const data: ReadingStatsData = await res.json();
      setStats(data);
    } catch (err: any) {
      setError(err.message || 'Error al obtener estadísticas.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStats(selectedYear);
    fetchGamification();
  }, [apiUrl, token, userIdParam, selectedYear]);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[50vh] gap-3">
        <Spinner size="xl" color="teal" />
        <p className="text-sm font-medium text-slate-600 dark:text-slate-400">
          Analizando biblioteca y calculando estadísticas avanzadas...
        </p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-2xl mx-auto my-12 p-8 text-center bg-white dark:bg-slate-900 rounded-3xl shadow-sm border border-slate-200 dark:border-slate-800">
        <div className="text-4xl mb-4">🔒</div>
        <h2 className="text-xl font-bold text-slate-800 dark:text-slate-100 mb-2">
          Acceso Restringido
        </h2>
        <p className="text-slate-600 dark:text-slate-400 text-sm mb-6">{error}</p>
        <Button color="light" onClick={() => navigate(-1)} className="mx-auto">
          Volver atrás
        </Button>
      </div>
    );
  }

  if (!stats) {
    return null;
  }

  const maxMonthValue = Math.max(
    ...(stats.books_per_month.map((m) =>
      chartMetric === 'books' ? m.count : m.pages || 0
    ) || [1]),
    1
  );

  return (
    <div className="max-w-6xl mx-auto space-y-8 pb-16 px-3 sm:px-4">
      {/* ── Encabezado Principal y Selector de Años ── */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 border-b border-slate-200 dark:border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-3">
            <span className="text-3xl">📊</span>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-white tracking-tight">
              {isOwnStats ? 'Mis Estadísticas de Lectura' : 'Estadísticas de Lectura'}
            </h1>
          </div>
          <p className="text-slate-500 dark:text-slate-400 text-sm mt-1">
            {isOwnStats
              ? 'Análisis profundo de tu velocidad, longitudes, géneros y memoria anual.'
              : 'Exploración de hábitos y trayectoria lectora de este usuario.'}
          </p>
        </div>

        {/* Selector de Periodo Temporal / Año */}
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider mr-1">
            Año:
          </span>
          <button
            type="button"
            onClick={() => setSelectedYear('all')}
            className={`px-3 py-1.5 rounded-full text-xs font-bold transition-all ${
              selectedYear === 'all'
                ? 'bg-teal-600 text-white shadow-sm'
                : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700'
            }`}
          >
            Histórico
          </button>
          {stats.available_years &&
            stats.available_years.map((y) => (
              <button
                key={y}
                type="button"
                onClick={() => setSelectedYear(String(y))}
                className={`px-3 py-1.5 rounded-full text-xs font-bold transition-all ${
                  selectedYear === String(y)
                    ? 'bg-teal-600 text-white shadow-sm'
                    : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700'
                }`}
              >
                {y}
              </button>
            ))}
          {isOwnStats && (
            <Link to="/library" className="ml-2">
              <Button size="xs" color="light">
                📚 Biblioteca
              </Button>
            </Link>
          )}
        </div>
      </div>

      {/* ── Tarjetas de Resumen KPI ── */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 sm:gap-4">
        {/* Total Leídos */}
        <div className="p-4 sm:p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 shadow-sm flex flex-col justify-between transition-all hover:border-teal-500/40">
          <span className="text-2xl">📚</span>
          <div className="mt-2">
            <div className="text-2xl sm:text-3xl font-black text-teal-600 dark:text-teal-400">
              {stats.total_read}
            </div>
            <div className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mt-0.5">
              Leídos {selectedYear !== 'all' ? selectedYear : ''}
            </div>
          </div>
        </div>

        {/* Calificación Media */}
        <div className="p-4 sm:p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 shadow-sm flex flex-col justify-between transition-all hover:border-amber-500/40">
          <span className="text-2xl">⭐</span>
          <div className="mt-2">
            <div className="text-2xl sm:text-3xl font-black text-amber-500">
              {stats.average_rating !== null ? stats.average_rating : '—'}
            </div>
            <div className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mt-0.5">
              Nota Media
            </div>
          </div>
        </div>

        {/* Páginas Leídas */}
        <div className="p-4 sm:p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 shadow-sm flex flex-col justify-between transition-all hover:border-blue-500/40">
          <span className="text-2xl">📄</span>
          <div className="mt-2">
            <div className="text-2xl sm:text-3xl font-black text-blue-600 dark:text-blue-400 truncate">
              {stats.total_pages_read.toLocaleString()}
            </div>
            <div className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mt-0.5">
              Páginas
            </div>
          </div>
        </div>

        {/* Ritmo Días/Libro */}
        <div className="p-4 sm:p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 shadow-sm flex flex-col justify-between transition-all hover:border-emerald-500/40">
          <span className="text-2xl">⚡</span>
          <div className="mt-2">
            <div className="text-2xl sm:text-3xl font-black text-emerald-600 dark:text-emerald-400">
              {stats.reading_pace?.avg_days_per_book !== null && stats.reading_pace?.avg_days_per_book !== undefined
                ? `${stats.reading_pace.avg_days_per_book}d`
                : '—'}
            </div>
            <div className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mt-0.5">
              Media / Libro
            </div>
          </div>
        </div>

        {/* Páginas al Día */}
        <div className="p-4 sm:p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 shadow-sm flex flex-col justify-between transition-all hover:border-purple-500/40">
          <span className="text-2xl">🔥</span>
          <div className="mt-2">
            <div className="text-2xl sm:text-3xl font-black text-purple-600 dark:text-purple-400">
              {stats.reading_pace?.avg_pages_per_day || 0}
            </div>
            <div className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mt-0.5">
              Págs / Día
            </div>
          </div>
        </div>

        {/* Mes Cumbre */}
        <div className="p-4 sm:p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 shadow-sm flex flex-col justify-between transition-all hover:border-orange-500/40">
          <span className="text-2xl">🏆</span>
          <div className="mt-2">
            <div className="text-sm font-bold text-orange-600 dark:text-orange-400 truncate">
              {stats.reading_pace?.highest_reading_month?.label || '—'}
            </div>
            <div className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mt-1">
              Pico ({stats.reading_pace?.highest_reading_month?.count || 0} lib.)
            </div>
          </div>
        </div>
      </div>

      {/* ── Navegación WAI-ARIA por Pestañas ── */}
      <div className="border-b border-slate-200 dark:border-slate-800">
        <nav
          className="flex space-x-2 sm:space-x-6 overflow-x-auto"
          aria-label="Pestañas de estadísticas"
          role="tablist"
        >
          <button
            role="tab"
            aria-selected={activeTab === 'overview'}
            onClick={() => setActiveTab('overview')}
            className={`pb-3 pt-2 text-sm font-bold border-b-2 flex items-center gap-2 transition-colors whitespace-nowrap ${
              activeTab === 'overview'
                ? 'border-teal-500 text-teal-600 dark:text-teal-400'
                : 'border-transparent text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'
            }`}
          >
            <HiOutlineChartBar className="w-4 h-4" />
            <span>Resumen General</span>
          </button>

          <button
            role="tab"
            aria-selected={activeTab === 'pace'}
            onClick={() => setActiveTab('pace')}
            className={`pb-3 pt-2 text-sm font-bold border-b-2 flex items-center gap-2 transition-colors whitespace-nowrap ${
              activeTab === 'pace'
                ? 'border-teal-500 text-teal-600 dark:text-teal-400'
                : 'border-transparent text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'
            }`}
          >
            <HiOutlineLightningBolt className="w-4 h-4" />
            <span>Ritmo & Velocidad</span>
          </button>

          <button
            role="tab"
            aria-selected={activeTab === 'length'}
            onClick={() => setActiveTab('length')}
            className={`pb-3 pt-2 text-sm font-bold border-b-2 flex items-center gap-2 transition-colors whitespace-nowrap ${
              activeTab === 'length'
                ? 'border-teal-500 text-teal-600 dark:text-teal-400'
                : 'border-transparent text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'
            }`}
          >
            <HiOutlineBookOpen className="w-4 h-4" />
            <span>Longitud & Formatos</span>
          </button>

          <button
            role="tab"
            aria-selected={activeTab === 'review'}
            onClick={() => setActiveTab('review')}
            className={`pb-3 pt-2 text-sm font-bold border-b-2 flex items-center gap-2 transition-colors whitespace-nowrap ${
              activeTab === 'review'
                ? 'border-teal-500 text-teal-600 dark:text-teal-400'
                : 'border-transparent text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'
            }`}
          >
            <HiOutlineSparkles className="w-4 h-4" />
            <span>Memoria Anual</span>
          </button>
        </nav>
      </div>

      {/* ── PESTAÑA 1: RESUMEN GENERAL ── */}
      {activeTab === 'overview' && (
        <div className="space-y-8 animate-fadeIn">
          {/* Gráfico de Evolución Mensual */}
          <div className="p-6 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 shadow-sm">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-6">
              <div>
                <h2 className="text-lg font-bold text-slate-900 dark:text-white flex items-center gap-2">
                  <span>📈</span> Evolución de Lectura Mensual
                </h2>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                  {selectedYear !== 'all'
                    ? `Distribución durante el año ${selectedYear}.`
                    : 'Historial de los últimos 12 meses.'}
                </p>
              </div>

              {/* Selector de Métrica (Libros vs Páginas) */}
              <div className="flex items-center gap-2 bg-slate-100 dark:bg-slate-800 p-1 rounded-xl text-xs font-semibold">
                <button
                  type="button"
                  onClick={() => setChartMetric('books')}
                  className={`px-3 py-1 rounded-lg transition-all ${
                    chartMetric === 'books'
                      ? 'bg-white dark:bg-slate-700 text-teal-600 dark:text-teal-300 shadow-xs'
                      : 'text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'
                  }`}
                >
                  Libros
                </button>
                <button
                  type="button"
                  onClick={() => setChartMetric('pages')}
                  className={`px-3 py-1 rounded-lg transition-all ${
                    chartMetric === 'pages'
                      ? 'bg-white dark:bg-slate-700 text-teal-600 dark:text-teal-300 shadow-xs'
                      : 'text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'
                  }`}
                >
                  Páginas
                </button>
              </div>
            </div>

            {/* Barras mensuales interactivas */}
            <div className="grid grid-cols-6 sm:grid-cols-12 gap-2 sm:gap-3 items-end h-48 pt-6 border-b border-slate-100 dark:border-slate-800 pb-2">
              {stats.books_per_month.map((item) => {
                const val = chartMetric === 'books' ? item.count : item.pages || 0;
                const heightPercent = maxMonthValue > 0 ? (val / maxMonthValue) * 100 : 0;
                return (
                  <div
                    key={item.key}
                    className="flex flex-col items-center h-full justify-end group relative"
                  >
                    {/* Tooltip flotante */}
                    <div className="absolute -top-8 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none bg-slate-900 text-white text-[10px] py-1 px-2 rounded-lg font-medium whitespace-nowrap z-10 shadow-lg">
                      {item.label}: {item.count} lib. ({item.pages || 0} pág.)
                    </div>

                    {/* Valor numérico encima de la barra */}
                    <span className="text-[10px] font-bold text-slate-600 dark:text-slate-400 mb-1 truncate max-w-full">
                      {val > 0 ? (chartMetric === 'pages' ? `${val}` : val) : ''}
                    </span>

                    {/* Barra con gradiente */}
                    <div
                      className={`w-full max-w-[28px] rounded-t-lg transition-all duration-300 group-hover:brightness-110 shadow-sm ${
                        chartMetric === 'books'
                          ? 'bg-gradient-to-t from-teal-600 to-teal-400 dark:from-teal-700 dark:to-teal-500'
                          : 'bg-gradient-to-t from-blue-600 to-cyan-400 dark:from-blue-700 dark:to-cyan-500'
                      }`}
                      style={{ height: `${Math.max(heightPercent, 4)}%` }}
                    />

                    {/* Etiqueta del mes */}
                    <span className="text-[10px] sm:text-[11px] font-medium text-slate-500 dark:text-slate-400 mt-2 truncate max-w-full">
                      {item.label.split(' ')[0]}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Grid de Distribución de Notas y Géneros */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            {/* Calificaciones (1 a 5) */}
            <div className="p-6 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 shadow-sm">
              <h2 className="text-lg font-bold text-slate-900 dark:text-white flex items-center gap-2 mb-1">
                <span>⭐</span> Distribución de Calificaciones
              </h2>
              <p className="text-xs text-slate-500 dark:text-slate-400 mb-6">
                Frecuencia de valoraciones otorgadas (escala de 1 a 5 estrellas).
              </p>

              <div className="space-y-2.5">
                {[5, 4, 3, 2, 1].map((score) => {
                  const count = stats.ratings_distribution[score] || 0;
                  const totalRatings = Object.values(stats.ratings_distribution).reduce(
                    (a, b) => a + b,
                    0
                  );
                  const percentage = totalRatings > 0 ? Math.round((count / totalRatings) * 100) : 0;

                  return (
                    <div key={score} className="flex items-center gap-3 text-xs">
                      <span className="w-8 font-bold text-slate-700 dark:text-slate-300 text-right">
                        {score} ★
                      </span>
                      <div className="flex-1 h-3.5 bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full transition-all duration-500 ${
                            score >= 4 ? 'bg-amber-400' : score === 3 ? 'bg-teal-500' : 'bg-slate-400'
                          }`}
                          style={{ width: `${percentage}%` }}
                        />
                      </div>
                      <span className="w-12 text-right font-semibold text-slate-600 dark:text-slate-400">
                        {count} ({percentage}%)
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Top Géneros Literarios */}
            <div className="p-6 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 shadow-sm">
              <h2 className="text-lg font-bold text-slate-900 dark:text-white flex items-center gap-2 mb-1">
                <span>🎭</span> Preferencias Literarias
              </h2>
              <p className="text-xs text-slate-500 dark:text-slate-400 mb-6">
                Géneros y temáticas predominantes en tus lecturas.
              </p>

              {stats.top_genres.length === 0 ? (
                <div className="text-center py-10 text-slate-400 dark:text-slate-500 text-sm">
                  No hay suficientes datos de géneros registrados en este periodo.
                </div>
              ) : (
                <div className="space-y-4">
                  {stats.top_genres.map((genre, idx) => (
                    <div key={genre.name} className="space-y-1">
                      <div className="flex justify-between text-xs font-semibold text-slate-700 dark:text-slate-300">
                        <span className="flex items-center gap-1.5 truncate">
                          <span className="text-teal-600 dark:text-teal-400 font-bold">
                            #{idx + 1}
                          </span>
                          <span className="truncate">{genre.name}</span>
                        </span>
                        <span className="text-slate-500 dark:text-slate-400 ml-2">
                          {genre.count} {genre.count === 1 ? 'libro' : 'libros'} ({genre.percentage}%)
                        </span>
                      </div>
                      <div className="h-3 bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
                        <div
                          className="h-full rounded-full bg-gradient-to-r from-teal-500 to-emerald-400 transition-all duration-500"
                          style={{ width: `${Math.min(genre.percentage, 100)}%` }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Autores más leídos */}
          <div className="p-6 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 shadow-sm">
            <h2 className="text-lg font-bold text-slate-900 dark:text-white flex items-center gap-2 mb-1">
              <span>✍️</span> Autores más leídos
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400 mb-6">
              Escritores con mayor presencia en tus lecturas.
            </p>

            {stats.top_authors.length === 0 ? (
              <div className="text-center py-8 text-slate-400 dark:text-slate-500 text-sm">
                Aún no hay autores asociados a las lecturas de este periodo.
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
                {stats.top_authors.map((author, index) => (
                  <Link
                    key={author.id}
                    to={`/authors/${author.id}`}
                    className="p-4 rounded-2xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200/60 dark:border-slate-700/60 hover:border-teal-500/60 transition-all group flex flex-col justify-between"
                  >
                    <div className="flex items-center gap-2.5">
                      <div className="w-8 h-8 rounded-full bg-teal-100 dark:bg-teal-900/50 text-teal-700 dark:text-teal-300 font-bold flex items-center justify-center text-xs">
                        #{index + 1}
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="font-bold text-sm text-slate-900 dark:text-slate-100 truncate group-hover:text-teal-600 dark:group-hover:text-teal-400 transition-colors">
                          {author.name}
                        </div>
                      </div>
                    </div>
                    <div className="mt-3 pt-2 border-t border-slate-200/50 dark:border-slate-700/50 flex justify-between items-center text-xs text-slate-500 dark:text-slate-400">
                      <span>Libros</span>
                      <span className="font-bold text-slate-700 dark:text-slate-200">
                        {author.count}
                      </span>
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </div>

          {/* Gamificación Opcional */}
          {gamification && gamification.gamification_enabled && (
            <div className="space-y-6 pt-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <ReadingGoalCard
                  goal={gamification.goal}
                  isOwn={!!isOwnStats}
                  onGoalUpdated={fetchGamification}
                />
                <ReadingStreakCard
                  streak={gamification.streak}
                  isOwn={!!isOwnStats}
                  onStreakUpdated={fetchGamification}
                />
              </div>
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <div className="lg:col-span-2">
                  <BadgesGrid badges={gamification.badges} />
                </div>
                <div>
                  <ActiveChallengesCard
                    challenges={gamification.challenges}
                    isOwn={!!isOwnStats}
                    onChallengeUpdated={fetchGamification}
                  />
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── PESTAÑA 2: RITMO & VELOCIDAD ── */}
      {activeTab === 'pace' && (
        <div className="space-y-8 animate-fadeIn">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {/* Días Promedio por Libro */}
            <div className="p-6 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 shadow-sm flex flex-col justify-between">
              <div>
                <div className="w-10 h-10 rounded-2xl bg-teal-100 dark:bg-teal-900/40 text-teal-600 dark:text-teal-300 flex items-center justify-center text-xl mb-4">
                  ⏱️
                </div>
                <h3 className="text-base font-bold text-slate-900 dark:text-white">
                  Duración Media por Libro
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                  Tiempo medio transcurrido entre la fecha de inicio y finalización.
                </p>
              </div>
              <div className="mt-6 pt-4 border-t border-slate-100 dark:border-slate-800">
                <div className="text-4xl font-black text-teal-600 dark:text-teal-400">
                  {stats.reading_pace?.avg_days_per_book !== null &&
                  stats.reading_pace?.avg_days_per_book !== undefined
                    ? `${stats.reading_pace.avg_days_per_book} días`
                    : 'Sin registros'}
                </div>
              </div>
            </div>

            {/* Páginas Diarias y Mensuales */}
            <div className="p-6 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 shadow-sm flex flex-col justify-between">
              <div>
                <div className="w-10 h-10 rounded-2xl bg-blue-100 dark:bg-blue-900/40 text-blue-600 dark:text-blue-300 flex items-center justify-center text-xl mb-4">
                  📖
                </div>
                <h3 className="text-base font-bold text-slate-900 dark:text-white">
                  Velocidad de Páginas
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                  Volumen promedio de páginas leídas por día y por mes.
                </p>
              </div>
              <div className="mt-6 pt-4 border-t border-slate-100 dark:border-slate-800 flex justify-between items-end">
                <div>
                  <div className="text-xs font-semibold text-slate-400">Al día</div>
                  <div className="text-3xl font-black text-blue-600 dark:text-blue-400">
                    {stats.reading_pace?.avg_pages_per_day || 0}
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-xs font-semibold text-slate-400">Al mes</div>
                  <div className="text-2xl font-black text-slate-700 dark:text-slate-300">
                    {stats.reading_pace?.avg_pages_per_month || 0}
                  </div>
                </div>
              </div>
            </div>

            {/* Mes Pico */}
            <div className="p-6 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 shadow-sm flex flex-col justify-between">
              <div>
                <div className="w-10 h-10 rounded-2xl bg-amber-100 dark:bg-amber-900/40 text-amber-600 dark:text-amber-300 flex items-center justify-center text-xl mb-4">
                  🌟
                </div>
                <h3 className="text-base font-bold text-slate-900 dark:text-white">
                  Mes Récord de Lectura
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                  El periodo con mayor concentración de libros terminados.
                </p>
              </div>
              <div className="mt-6 pt-4 border-t border-slate-100 dark:border-slate-800">
                <div className="text-xl font-bold text-amber-600 dark:text-amber-400 truncate">
                  {stats.reading_pace?.highest_reading_month?.label || '—'}
                </div>
                <div className="text-xs text-slate-500 mt-0.5">
                  {stats.reading_pace?.highest_reading_month?.count || 0} libros completados
                </div>
              </div>
            </div>
          </div>

          {/* Extremos de Velocidad: Más Rápido y Más Pausado */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Libro más rápido */}
            <div className="p-6 rounded-3xl bg-emerald-50/50 dark:bg-emerald-950/20 border border-emerald-200 dark:border-emerald-800/50 shadow-sm">
              <div className="flex items-center gap-2 text-emerald-700 dark:text-emerald-300 font-bold text-sm mb-4">
                <span>⚡</span> Lectura más veloz
              </div>
              {stats.reading_pace?.fastest_book ? (
                <div className="flex items-center gap-4">
                  <div className="w-16 h-24 rounded-lg bg-emerald-100 dark:bg-emerald-900/50 overflow-hidden shrink-0 flex items-center justify-center text-2xl shadow-xs">
                    {stats.reading_pace.fastest_book.cover ? (
                      <img
                        src={stats.reading_pace.fastest_book.cover}
                        alt={stats.reading_pace.fastest_book.title}
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      '📗'
                    )}
                  </div>
                  <div>
                    <h4 className="font-bold text-slate-900 dark:text-white text-base">
                      {stats.reading_pace.fastest_book.title}
                    </h4>
                    <p className="text-xs text-slate-600 dark:text-slate-400 mt-0.5">
                      {stats.reading_pace.fastest_book.author}
                    </p>
                    <div className="inline-block mt-3 px-3 py-1 bg-emerald-200/60 dark:bg-emerald-900/80 text-emerald-800 dark:text-emerald-200 text-xs font-black rounded-full">
                      Terminado en {stats.reading_pace.fastest_book.days}{' '}
                      {stats.reading_pace.fastest_book.days === 1 ? 'día' : 'días'}
                    </div>
                  </div>
                </div>
              ) : (
                <p className="text-xs text-slate-500">
                  Registra fecha de inicio y finalización en tus lecturas para descubrir tu récord.
                </p>
              )}
            </div>

            {/* Libro más sosegado */}
            <div className="p-6 rounded-3xl bg-indigo-50/50 dark:bg-indigo-950/20 border border-indigo-200 dark:border-indigo-800/50 shadow-sm">
              <div className="flex items-center gap-2 text-indigo-700 dark:text-indigo-300 font-bold text-sm mb-4">
                <span>🕰️</span> Lectura más pausada y reposada
              </div>
              {stats.reading_pace?.slowest_book ? (
                <div className="flex items-center gap-4">
                  <div className="w-16 h-24 rounded-lg bg-indigo-100 dark:bg-indigo-900/50 overflow-hidden shrink-0 flex items-center justify-center text-2xl shadow-xs">
                    {stats.reading_pace.slowest_book.cover ? (
                      <img
                        src={stats.reading_pace.slowest_book.cover}
                        alt={stats.reading_pace.slowest_book.title}
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      '📘'
                    )}
                  </div>
                  <div>
                    <h4 className="font-bold text-slate-900 dark:text-white text-base">
                      {stats.reading_pace.slowest_book.title}
                    </h4>
                    <p className="text-xs text-slate-600 dark:text-slate-400 mt-0.5">
                      {stats.reading_pace.slowest_book.author}
                    </p>
                    <div className="inline-block mt-3 px-3 py-1 bg-indigo-200/60 dark:bg-indigo-900/80 text-indigo-800 dark:text-indigo-200 text-xs font-black rounded-full">
                      Completado en {stats.reading_pace.slowest_book.days} días
                    </div>
                  </div>
                </div>
              ) : (
                <p className="text-xs text-slate-500">
                  Añade fechas a tus libros para comparar el ritmo de tus lecturas.
                </p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ── PESTAÑA 3: LONGITUD & FORMATOS ── */}
      {activeTab === 'length' && (
        <div className="space-y-8 animate-fadeIn">
          {/* Distribución por Tamaño de Páginas */}
          <div className="p-6 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 shadow-sm">
            <h2 className="text-lg font-bold text-slate-900 dark:text-white flex items-center gap-2 mb-1">
              <span>📏</span> Distribución por Longitud
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400 mb-6">
              Volumen y proporción de libros leídos clasificados por su número de páginas.
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {stats.length_distribution && (
                <>
                  {/* Cortos */}
                  <div className="p-4 rounded-2xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200/60 dark:border-slate-700/60">
                    <div className="flex justify-between items-center text-xs font-bold text-slate-600 dark:text-slate-300">
                      <span>{stats.length_distribution.short.label}</span>
                      <span className="text-teal-600 dark:text-teal-400">
                        {stats.length_distribution.short.percentage}%
                      </span>
                    </div>
                    <div className="text-2xl font-black text-slate-900 dark:text-white my-2">
                      {stats.length_distribution.short.count}
                    </div>
                    <div className="w-full h-2 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-teal-500 rounded-full"
                        style={{ width: `${stats.length_distribution.short.percentage}%` }}
                      />
                    </div>
                  </div>

                  {/* Medios */}
                  <div className="p-4 rounded-2xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200/60 dark:border-slate-700/60">
                    <div className="flex justify-between items-center text-xs font-bold text-slate-600 dark:text-slate-300">
                      <span>{stats.length_distribution.medium.label}</span>
                      <span className="text-blue-600 dark:text-blue-400">
                        {stats.length_distribution.medium.percentage}%
                      </span>
                    </div>
                    <div className="text-2xl font-black text-slate-900 dark:text-white my-2">
                      {stats.length_distribution.medium.count}
                    </div>
                    <div className="w-full h-2 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-blue-500 rounded-full"
                        style={{ width: `${stats.length_distribution.medium.percentage}%` }}
                      />
                    </div>
                  </div>

                  {/* Largos */}
                  <div className="p-4 rounded-2xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200/60 dark:border-slate-700/60">
                    <div className="flex justify-between items-center text-xs font-bold text-slate-600 dark:text-slate-300">
                      <span>{stats.length_distribution.long.label}</span>
                      <span className="text-indigo-600 dark:text-indigo-400">
                        {stats.length_distribution.long.percentage}%
                      </span>
                    </div>
                    <div className="text-2xl font-black text-slate-900 dark:text-white my-2">
                      {stats.length_distribution.long.count}
                    </div>
                    <div className="w-full h-2 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-indigo-500 rounded-full"
                        style={{ width: `${stats.length_distribution.long.percentage}%` }}
                      />
                    </div>
                  </div>

                  {/* Épicos */}
                  <div className="p-4 rounded-2xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200/60 dark:border-slate-700/60">
                    <div className="flex justify-between items-center text-xs font-bold text-slate-600 dark:text-slate-300">
                      <span>{stats.length_distribution.epic.label}</span>
                      <span className="text-purple-600 dark:text-purple-400">
                        {stats.length_distribution.epic.percentage}%
                      </span>
                    </div>
                    <div className="text-2xl font-black text-slate-900 dark:text-white my-2">
                      {stats.length_distribution.epic.count}
                    </div>
                    <div className="w-full h-2 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-purple-500 rounded-full"
                        style={{ width: `${stats.length_distribution.epic.percentage}%` }}
                      />
                    </div>
                  </div>
                </>
              )}
            </div>

            {/* Extremos de Páginas: Más Largo vs Más Corto */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-6 pt-6 border-t border-slate-100 dark:border-slate-800">
              {stats.length_distribution?.longest_book && (
                <div className="flex items-center gap-3 p-3 rounded-xl bg-slate-50 dark:bg-slate-800/40">
                  <span className="text-2xl">📚</span>
                  <div className="min-w-0">
                    <div className="text-xs text-slate-400 font-semibold">Libro más extenso</div>
                    <div className="font-bold text-sm text-slate-900 dark:text-white truncate">
                      {stats.length_distribution.longest_book.title}
                    </div>
                    <div className="text-xs font-black text-teal-600 dark:text-teal-400">
                      {stats.length_distribution.longest_book.pages} páginas
                    </div>
                  </div>
                </div>
              )}

              {stats.length_distribution?.shortest_book && (
                <div className="flex items-center gap-3 p-3 rounded-xl bg-slate-50 dark:bg-slate-800/40">
                  <span className="text-2xl">🔖</span>
                  <div className="min-w-0">
                    <div className="text-xs text-slate-400 font-semibold">Libro más breve</div>
                    <div className="font-bold text-sm text-slate-900 dark:text-white truncate">
                      {stats.length_distribution.shortest_book.title}
                    </div>
                    <div className="text-xs font-black text-blue-600 dark:text-blue-400">
                      {stats.length_distribution.shortest_book.pages} páginas
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Formato y Propiedad */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Formato: Físico vs Digital */}
            <div className="p-6 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 shadow-sm">
              <h3 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2 mb-4">
                <span>📱</span> Formato de Lectura
              </h3>
              <div className="space-y-4">
                <div>
                  <div className="flex justify-between text-xs font-bold text-slate-700 dark:text-slate-300 mb-1">
                    <span>📖 Papel / Físico</span>
                    <span>
                      {stats.format_distribution?.physical_count || 0} (
                      {stats.format_distribution?.physical_percentage || 0}%)
                    </span>
                  </div>
                  <div className="w-full h-3 bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-amber-500 rounded-full"
                      style={{ width: `${stats.format_distribution?.physical_percentage || 0}%` }}
                    />
                  </div>
                </div>
                <div>
                  <div className="flex justify-between text-xs font-bold text-slate-700 dark:text-slate-300 mb-1">
                    <span>📱 Digital / Ebook</span>
                    <span>
                      {stats.format_distribution?.digital_count || 0} (
                      {stats.format_distribution?.digital_percentage || 0}%)
                    </span>
                  </div>
                  <div className="w-full h-3 bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-cyan-500 rounded-full"
                      style={{ width: `${stats.format_distribution?.digital_percentage || 0}%` }}
                    />
                  </div>
                </div>
              </div>
            </div>

            {/* Posesión: En propiedad vs Biblioteca/Prestado */}
            <div className="p-6 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 shadow-sm">
              <h3 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2 mb-4">
                <span>🏷️</span> Estado de Posesión
              </h3>
              <div className="space-y-4">
                <div>
                  <div className="flex justify-between text-xs font-bold text-slate-700 dark:text-slate-300 mb-1">
                    <span>🏠 En Propiedad</span>
                    <span>
                      {stats.format_distribution?.owned_count || 0} (
                      {stats.format_distribution?.owned_percentage || 0}%)
                    </span>
                  </div>
                  <div className="w-full h-3 bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-teal-500 rounded-full"
                      style={{ width: `${stats.format_distribution?.owned_percentage || 0}%` }}
                    />
                  </div>
                </div>
                <div>
                  <div className="flex justify-between text-xs font-bold text-slate-700 dark:text-slate-300 mb-1">
                    <span>🏛️ Biblioteca / Prestado</span>
                    <span>
                      {stats.format_distribution?.borrowed_count || 0} (
                      {stats.format_distribution?.borrowed_percentage || 0}%)
                    </span>
                  </div>
                  <div className="w-full h-3 bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-purple-500 rounded-full"
                      style={{ width: `${stats.format_distribution?.borrowed_percentage || 0}%` }}
                    />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── PESTAÑA 4: MEMORIA ANUAL / "YEAR IN REVIEW" ── */}
      {activeTab === 'review' && (
        <div className="space-y-8 animate-fadeIn">
          {stats.year_in_review ? (
            <div className="p-8 rounded-3xl bg-gradient-to-br from-slate-900 via-slate-800 to-teal-950 text-white shadow-xl border border-teal-500/20">
              <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 border-b border-slate-700/60 pb-6 mb-8">
                <div>
                  <span className="px-3 py-1 bg-teal-500/20 text-teal-300 text-xs font-bold rounded-full border border-teal-500/30">
                    Memoria Lectora Oficial
                  </span>
                  <h2 className="text-3xl sm:text-4xl font-black mt-2 tracking-tight">
                    Año {stats.year_in_review.year} en Resumen
                  </h2>
                </div>
                <div className="text-right">
                  <div className="text-3xl sm:text-4xl font-black text-teal-400">
                    {stats.year_in_review.total_books}
                  </div>
                  <div className="text-xs text-slate-300 font-semibold uppercase tracking-wider">
                    Libros Completados
                  </div>
                </div>
              </div>

              {/* Grid de Destacados del Año */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                {/* Total Páginas */}
                <div className="p-5 rounded-2xl bg-white/5 border border-white/10 backdrop-blur-sm">
                  <div className="text-2xl mb-2">📄</div>
                  <div className="text-2xl sm:text-3xl font-black text-cyan-300">
                    {stats.year_in_review.total_pages.toLocaleString()}
                  </div>
                  <div className="text-xs text-slate-300 font-medium mt-1">
                    Páginas leídas en el año
                  </div>
                </div>

                {/* Género Favorito */}
                <div className="p-5 rounded-2xl bg-white/5 border border-white/10 backdrop-blur-sm">
                  <div className="text-2xl mb-2">🎭</div>
                  <div className="text-xl font-black text-amber-300 truncate">
                    {stats.year_in_review.favorite_genre || 'No determinado'}
                  </div>
                  <div className="text-xs text-slate-300 font-medium mt-1">
                    Género predilecto
                  </div>
                </div>

                {/* Autor Favorito */}
                <div className="p-5 rounded-2xl bg-white/5 border border-white/10 backdrop-blur-sm">
                  <div className="text-2xl mb-2">✍️</div>
                  <div className="text-xl font-black text-emerald-300 truncate">
                    {stats.year_in_review.favorite_author || 'No determinado'}
                  </div>
                  <div className="text-xs text-slate-300 font-medium mt-1">
                    Autor con más presencia
                  </div>
                </div>
              </div>

              {/* Libro Mejor Valorado del Año */}
              {stats.year_in_review.highest_rated_book && (
                <div className="p-6 rounded-2xl bg-white/10 border border-white/15 backdrop-blur-md mb-8 flex flex-col sm:flex-row items-center gap-6">
                  <div className="w-20 h-28 rounded-lg bg-teal-900/50 overflow-hidden shrink-0 flex items-center justify-center text-3xl shadow-md">
                    {stats.year_in_review.highest_rated_book.cover ? (
                      <img
                        src={stats.year_in_review.highest_rated_book.cover}
                        alt={stats.year_in_review.highest_rated_book.title}
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      '⭐'
                    )}
                  </div>
                  <div className="text-center sm:text-left flex-1">
                    <span className="text-xs font-bold text-amber-300 uppercase tracking-wider">
                      Tu libro mejor puntuado del año
                    </span>
                    <h3 className="text-xl font-bold mt-1">
                      {stats.year_in_review.highest_rated_book.title}
                    </h3>
                    <p className="text-sm text-slate-300">
                      {stats.year_in_review.highest_rated_book.author}
                    </p>
                    <div className="flex items-center justify-center sm:justify-start gap-1 mt-2 text-amber-400 font-black text-sm">
                      <span>{'★'.repeat(stats.year_in_review.highest_rated_book.rating)}</span>
                      <span className="text-xs text-slate-300 ml-1">
                        ({stats.year_in_review.highest_rated_book.rating}/5 estrellas)
                      </span>
                    </div>
                  </div>
                </div>
              )}

              {/* Comparativa con el Año Previo */}
              <div className="p-6 rounded-2xl bg-white/5 border border-white/10">
                <h4 className="text-sm font-bold uppercase tracking-wider text-slate-300 mb-4">
                  Comparativa frente a {stats.year_in_review.comparison_previous_year.previous_year}
                </h4>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="flex items-center gap-3">
                    {stats.year_in_review.comparison_previous_year.books_difference >= 0 ? (
                      <div className="w-10 h-10 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center">
                        <HiOutlineArrowSmUp className="w-6 h-6" />
                      </div>
                    ) : (
                      <div className="w-10 h-10 rounded-full bg-rose-500/20 text-rose-400 flex items-center justify-center">
                        <HiOutlineArrowSmDown className="w-6 h-6" />
                      </div>
                    )}
                    <div>
                      <div className="text-lg font-bold">
                        {stats.year_in_review.comparison_previous_year.books_difference >= 0 ? '+' : ''}
                        {stats.year_in_review.comparison_previous_year.books_difference} libros
                        {stats.year_in_review.comparison_previous_year.books_percentage_change !== null && (
                          <span className="text-xs ml-2 text-slate-300">
                            ({stats.year_in_review.comparison_previous_year.books_percentage_change >= 0 ? '+' : ''}
                            {stats.year_in_review.comparison_previous_year.books_percentage_change}%)
                          </span>
                        )}
                      </div>
                      <div className="text-xs text-slate-400">
                        En {stats.year_in_review.comparison_previous_year.previous_year}:{' '}
                        {stats.year_in_review.comparison_previous_year.previous_year_books} libros
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-blue-500/20 text-blue-400 flex items-center justify-center text-lg font-bold">
                      📄
                    </div>
                    <div>
                      <div className="text-lg font-bold">
                        {stats.year_in_review.total_pages -
                          stats.year_in_review.comparison_previous_year.previous_year_pages >= 0
                          ? '+'
                          : ''}
                        {(
                          stats.year_in_review.total_pages -
                          stats.year_in_review.comparison_previous_year.previous_year_pages
                        ).toLocaleString()}{' '}
                        páginas
                      </div>
                      <div className="text-xs text-slate-400">
                        En {stats.year_in_review.comparison_previous_year.previous_year}:{' '}
                        {stats.year_in_review.comparison_previous_year.previous_year_pages.toLocaleString()} pág.
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="text-center py-12 text-slate-400">
              No hay suficientes datos para generar la memoria anual de este periodo.
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default ReadingStats;
