import React, { useEffect, useState } from 'react';
import { useSearchParams, useNavigate, Link } from 'react-router-dom';
import { Button, Spinner } from 'flowbite-react';
import { useAuthStore } from '../store/auth';

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
  count: number;
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
}

export function ReadingStats() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { token, user } = useAuthStore();

  const userIdParam = searchParams.get('user_id');
  const isOwnStats = !userIdParam || (user && String(user.id) === userIdParam);

  const [stats, setStats] = useState<ReadingStatsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const apiUrl = (import.meta as any).env.VITE_API_URL || 'http://localhost:8000';

  useEffect(() => {
    const fetchStats = async () => {
      setLoading(true);
      setError(null);
      try {
        const query = userIdParam ? `?user_id=${encodeURIComponent(userIdParam)}` : '';
        const res = await fetch(`${apiUrl}/api/v1/books/statistics/${query}`, {
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

    fetchStats();
  }, [apiUrl, token, userIdParam]);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[50vh] gap-3">
        <Spinner size="xl" color="teal" />
        <p className="text-sm font-medium text-slate-600 dark:text-slate-400">
          Analizando biblioteca y calculando estadísticas...
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
        <p className="text-slate-600 dark:text-slate-400 text-sm mb-6">
          {error}
        </p>
        <Button color="light" onClick={() => navigate(-1)} className="mx-auto">
          Volver atrás
        </Button>
      </div>
    );
  }

  if (!stats) {
    return null;
  }

  const maxMonthCount = Math.max(...(stats.books_per_month.map((m) => m.count) || [1]), 1);

  return (
    <div className="max-w-6xl mx-auto space-y-8 pb-12">
      {/* Encabezado Principal */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 border-b border-slate-200 dark:border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-3xl">📊</span>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-white tracking-tight">
              {isOwnStats ? 'Mis Estadísticas de Lectura' : 'Estadísticas de Lectura'}
            </h1>
          </div>
          <p className="text-slate-500 dark:text-slate-400 text-sm mt-1">
            {isOwnStats
              ? 'Métricas detalladas de tu biblioteca, ritmo de lectura y hábitos literarios.'
              : 'Exploración de hábitos y trayectoria lectora de este usuario.'}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {isOwnStats && (
            <Link to="/library">
              <Button size="sm" color="teal">
                📚 Ver Biblioteca
              </Button>
            </Link>
          )}
        </div>
      </div>

      {/* Tarjetas de Resumen KPI */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
        {/* Total Leídos */}
        <div className="p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 shadow-sm flex flex-col justify-between transition-all hover:border-teal-500/40">
          <span className="text-2xl">📚</span>
          <div className="mt-2">
            <div className="text-2xl sm:text-3xl font-black text-teal-600 dark:text-teal-400">
              {stats.total_read}
            </div>
            <div className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mt-0.5">
              Leídos
            </div>
          </div>
        </div>

        {/* Calificación Media */}
        <div className="p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 shadow-sm flex flex-col justify-between transition-all hover:border-amber-500/40">
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
        <div className="p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 shadow-sm flex flex-col justify-between transition-all hover:border-blue-500/40">
          <span className="text-2xl">📄</span>
          <div className="mt-2">
            <div className="text-2xl sm:text-3xl font-black text-blue-600 dark:text-blue-400">
              {stats.total_pages_read.toLocaleString()}
            </div>
            <div className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mt-0.5">
              Páginas
            </div>
          </div>
        </div>

        {/* En Progreso */}
        <div className="p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 shadow-sm flex flex-col justify-between transition-all hover:border-emerald-500/40">
          <span className="text-2xl">📖</span>
          <div className="mt-2">
            <div className="text-2xl sm:text-3xl font-black text-emerald-600 dark:text-emerald-400">
              {stats.currently_reading}
            </div>
            <div className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mt-0.5">
              Leyendo
            </div>
          </div>
        </div>

        {/* Por Leer / Deseos */}
        <div className="p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 shadow-sm flex flex-col justify-between transition-all hover:border-purple-500/40">
          <span className="text-2xl">🎯</span>
          <div className="mt-2">
            <div className="text-2xl sm:text-3xl font-black text-purple-600 dark:text-purple-400">
              {stats.want_to_read}
            </div>
            <div className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mt-0.5">
              Por Leer
            </div>
          </div>
        </div>

        {/* Este Año */}
        <div className="p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 shadow-sm flex flex-col justify-between transition-all hover:border-orange-500/40">
          <span className="text-2xl">📅</span>
          <div className="mt-2">
            <div className="text-2xl sm:text-3xl font-black text-orange-600 dark:text-orange-400">
              {stats.books_this_year}
            </div>
            <div className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mt-0.5">
              Este Año
            </div>
          </div>
        </div>
      </div>

      {/* Gráfico de Evolución Mensual (Últimos 12 meses) */}
      <div className="p-6 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 shadow-sm">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-lg font-bold text-slate-900 dark:text-white flex items-center gap-2">
              <span>📈</span> Libros Terminados por Mes
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              Historial de finalización durante los últimos 12 meses.
            </p>
          </div>
          <div className="text-xs font-semibold px-3 py-1 bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 rounded-full">
            Total periodo: {stats.books_per_month.reduce((acc, m) => acc + m.count, 0)} libros
          </div>
        </div>

        {/* Barras mensuales interactivas */}
        <div className="grid grid-cols-6 sm:grid-cols-12 gap-2 sm:gap-3 items-end h-44 pt-6 border-b border-slate-100 dark:border-slate-800 pb-2">
          {stats.books_per_month.map((item) => {
            const heightPercent = maxMonthCount > 0 ? (item.count / maxMonthCount) * 100 : 0;
            return (
              <div key={item.key} className="flex flex-col items-center h-full justify-end group relative">
                {/* Tooltip flotante */}
                <div className="absolute -top-7 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none bg-slate-900 text-white text-[10px] py-1 px-2 rounded font-medium whitespace-nowrap z-10 shadow-lg">
                  {item.label}: {item.count} {item.count === 1 ? 'libro' : 'libros'}
                </div>

                {/* Valor numérico encima de la barra */}
                <span className="text-[11px] font-bold text-slate-600 dark:text-slate-400 mb-1">
                  {item.count > 0 ? item.count : ''}
                </span>

                {/* Barra */}
                <div
                  className="w-full max-w-[28px] rounded-t-lg bg-gradient-to-t from-teal-600 to-teal-400 dark:from-teal-700 dark:to-teal-500 transition-all duration-300 group-hover:brightness-110 shadow-sm"
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
        {/* Distribución de Calificaciones (1 a 10) */}
        <div className="p-6 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 shadow-sm">
          <h2 className="text-lg font-bold text-slate-900 dark:text-white flex items-center gap-2 mb-1">
            <span>⭐</span> Distribución de Calificaciones
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400 mb-6">
            Frecuencia de puntuaciones otorgadas a tus libros leídos.
          </p>

          <div className="space-y-2.5">
            {[10, 9, 8, 7, 6, 5, 4, 3, 2, 1].map((score) => {
              const count = stats.ratings_distribution[score] || 0;
              const totalRatings = Object.values(stats.ratings_distribution).reduce((a, b) => a + b, 0);
              const percentage = totalRatings > 0 ? Math.round((count / totalRatings) * 100) : 0;

              return (
                <div key={score} className="flex items-center gap-3 text-xs">
                  <span className="w-8 font-bold text-slate-700 dark:text-slate-300 text-right">
                    {score} ★
                  </span>
                  <div className="flex-1 h-3.5 bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all duration-500 ${
                        score >= 8
                          ? 'bg-amber-400'
                          : score >= 6
                          ? 'bg-teal-500'
                          : 'bg-slate-400'
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
              No hay suficientes datos de géneros registrados aún.
            </div>
          ) : (
            <div className="space-y-4">
              {stats.top_genres.map((genre, idx) => (
                <div key={genre.name} className="space-y-1">
                  <div className="flex justify-between text-xs font-semibold text-slate-700 dark:text-slate-300">
                    <span className="flex items-center gap-1.5 truncate">
                      <span className="text-teal-600 dark:text-teal-400 font-bold">#{idx + 1}</span>
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

      {/* Ranking de Autores Predilectos */}
      <div className="p-6 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 shadow-sm">
        <h2 className="text-lg font-bold text-slate-900 dark:text-white flex items-center gap-2 mb-1">
          <span>✍️</span> Autores más leídos
        </h2>
        <p className="text-xs text-slate-500 dark:text-slate-400 mb-6">
          Los escritores con mayor presencia en tu catálogo de lecturas.
        </p>

        {stats.top_authors.length === 0 ? (
          <div className="text-center py-8 text-slate-400 dark:text-slate-500 text-sm">
            Aún no hay autores asociados a tus lecturas.
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
                  <span>Libros leídos</span>
                  <span className="font-bold text-slate-700 dark:text-slate-200">
                    {author.count}
                  </span>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
