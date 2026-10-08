import React, { useEffect, useState } from 'react';
import { Spinner, Modal, Button } from 'flowbite-react';
import {
  HiOutlineFire,
  HiOutlineCalendar,
  HiOutlineCheckCircle,
  HiOutlineLogout,
} from 'react-icons/hi';
import { useAuthStore } from '../../../store/auth';
import {
  GamificationOverviewData,
  ChallengeItem,
  BadgeItem,
  ReadingGoalData,
  ReadingStreakData,
} from '../components/gamification/types';

export const ChallengesPage: React.FC = () => {
  const { token } = useAuthStore();
  const [data, setData] = useState<GamificationOverviewData | null>(null);
  const [allChallenges, setAllChallenges] = useState<ChallengeItem[]>([]);
  const [allBadges, setAllBadges] = useState<BadgeItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'challenges' | 'goal' | 'streak' | 'badges'>('challenges');
  const [badgeFilter, setBadgeFilter] = useState<string>('all');

  // Modales
  const [isGoalModalOpen, setIsGoalModalOpen] = useState(false);
  const [goalTargetBooks, setGoalTargetBooks] = useState(12);
  const [goalTargetPages, setGoalTargetPages] = useState(0);
  const [savingGoal, setSavingGoal] = useState(false);

  const [isLogModalOpen, setIsLogModalOpen] = useState(false);
  const [logPages, setLogPages] = useState(25);
  const [logMinutes, setLogMinutes] = useState(30);
  const [savingLog, setSavingLog] = useState(false);

  const [joiningSlug, setJoiningSlug] = useState<string | null>(null);
  const [leavingSlug, setLeavingSlug] = useState<string | null>(null);

  const apiUrl = (import.meta as any).env.VITE_API_URL || 'http://localhost:8000';

  const loadData = async () => {
    try {
      setLoading(true);
      const headers: HeadersInit = { 'Content-Type': 'application/json' };
      if (token) headers['Authorization'] = `Bearer ${token}`;

      // 1. Resumen de gamificación
      const overviewRes = await fetch(`${apiUrl}/api/v1/gamification/overview/`, { headers });
      if (overviewRes.ok) {
        const overviewData = await overviewRes.json();
        setData(overviewData);
        if (overviewData.goal) {
          setGoalTargetBooks(overviewData.goal.target_books || 12);
          setGoalTargetPages(overviewData.goal.target_pages || 0);
        }
      }

      // 2. Todos los retos comunitarios
      const challengesRes = await fetch(`${apiUrl}/api/v1/gamification/challenges/`, { headers });
      if (challengesRes.ok) {
        const chData = await challengesRes.json();
        setAllChallenges(Array.isArray(chData) ? chData : chData.results || []);
      }

      // 3. Catálogo completo de insignias
      const badgesRes = await fetch(`${apiUrl}/api/v1/gamification/badges/`, { headers });
      if (badgesRes.ok) {
        const bData = await badgesRes.json();
        setAllBadges(Array.isArray(bData) ? bData : bData.results || []);
      }
    } catch (e) {
      console.error('Error fetching challenges data', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [token]);

  const handleSaveGoal = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token) return;
    setSavingGoal(true);
    try {
      const year = new Date().getFullYear();
      const res = await fetch(`${apiUrl}/api/v1/gamification/goals/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          year,
          target_books: Number(goalTargetBooks),
          target_pages: Number(goalTargetPages),
        }),
      });

      if (res.ok) {
        setIsGoalModalOpen(false);
        await loadData();
      }
    } catch (e) {
      console.error('Error saving reading goal', e);
    } finally {
      setSavingGoal(false);
    }
  };

  const handleSaveLog = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token) return;
    setSavingLog(true);
    try {
      const res = await fetch(`${apiUrl}/api/v1/gamification/log/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          pages_read: Number(logPages),
          minutes_read: Number(logMinutes),
        }),
      });

      if (res.ok) {
        setIsLogModalOpen(false);
        await loadData();
      }
    } catch (e) {
      console.error('Error logging daily reading', e);
    } finally {
      setSavingLog(false);
    }
  };

  const handleJoinChallenge = async (slug: string) => {
    if (!token || joiningSlug) return;
    setJoiningSlug(slug);
    try {
      const res = await fetch(`${apiUrl}/api/v1/gamification/challenges/${slug}/join/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
      });
      if (res.ok) {
        await loadData();
      }
    } catch (e) {
      console.error('Error joining challenge', e);
    } finally {
      setJoiningSlug(null);
    }
  };

  const handleLeaveChallenge = async (slug: string) => {
    if (!token || leavingSlug) return;
    setLeavingSlug(slug);
    try {
      const res = await fetch(`${apiUrl}/api/v1/gamification/challenges/${slug}/leave/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
      });
      if (res.ok) {
        await loadData();
      }
    } catch (e) {
      console.error('Error leaving challenge', e);
    } finally {
      setLeavingSlug(null);
    }
  };

  const filteredBadges = allBadges.filter((b) => {
    if (badgeFilter === 'all') return true;
    if (badgeFilter === 'unlocked') return b.unlocked;
    if (badgeFilter === 'locked') return !b.unlocked;
    return b.category === badgeFilter;
  });

  const streak: ReadingStreakData | undefined = data?.streak;
  const goal: ReadingGoalData | undefined = data?.goal;
  const currentYear = new Date().getFullYear();

  return (
    <div className="max-w-6xl mx-auto px-4 py-8 space-y-8 animate-fadeIn">
      {/* Cabecera Principal */}
      <div className="bg-gradient-to-r from-rose-500 via-pink-600 to-indigo-600 rounded-3xl p-6 sm:p-10 text-white shadow-xl relative overflow-hidden">
        <div className="relative z-10 max-w-2xl">
          <div className="inline-flex items-center gap-2 px-3 py-1 bg-white/20 backdrop-blur-md rounded-full text-xs font-semibold mb-3">
            <span>🏆</span>
            <span>Comunidad de Retos Literarios</span>
          </div>
          <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight">
            Retos de Lectura & Gamificación
          </h1>
          <p className="mt-2 text-sm sm:text-base text-rose-100 leading-relaxed">
            Fija tus objetivos anuales, mantén encendida tu racha de lectura diaria y compite con la comunidad superando desafíos temáticos.
          </p>
        </div>

        {/* Tarjetas rápidas en la cabecera */}
        {data && (
          <div className="mt-6 grid grid-cols-1 sm:grid-cols-3 gap-4 pt-4 border-t border-white/20">
            <div className="bg-white/10 backdrop-blur-md rounded-2xl p-4 flex items-center gap-3">
              <span className="text-3xl">🔥</span>
              <div>
                <div className="text-2xl font-black">{streak?.current_streak || 0} días</div>
                <div className="text-xs text-rose-200">Racha actual</div>
              </div>
            </div>

            <div className="bg-white/10 backdrop-blur-md rounded-2xl p-4 flex items-center gap-3">
              <span className="text-3xl">🎯</span>
              <div>
                <div className="text-2xl font-black">
                  {goal?.current_books || 0}/{goal?.target_books || 12}
                </div>
                <div className="text-xs text-rose-200">Meta {currentYear} ({goal?.percentage || 0}%)</div>
              </div>
            </div>

            <div className="bg-white/10 backdrop-blur-md rounded-2xl p-4 flex items-center gap-3">
              <span className="text-3xl">🎖️</span>
              <div>
                <div className="text-2xl font-black">
                  {data.badges?.unlocked_count || 0}/{data.badges?.total_badges || allBadges.length}
                </div>
                <div className="text-xs text-rose-200">Insignias obtenidas</div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Pestañas de Navegación WAI-ARIA */}
      <div className="flex border-b border-gray-200 dark:border-gray-700 space-x-2 sm:space-x-4" role="tablist">
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === 'challenges'}
          onClick={() => setActiveTab('challenges')}
          className={`py-3 px-4 font-semibold text-sm rounded-t-xl transition-all border-b-2 flex items-center gap-2 ${
            activeTab === 'challenges'
              ? 'border-rose-600 text-rose-600 dark:text-rose-400 bg-rose-50/50 dark:bg-rose-950/20'
              : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'
          }`}
        >
          <span>🏆</span>
          <span>Retos Activos</span>
          <span className="text-xs bg-gray-100 dark:bg-gray-800 px-2 py-0.5 rounded-full">
            {allChallenges.length}
          </span>
        </button>

        <button
          type="button"
          role="tab"
          aria-selected={activeTab === 'goal'}
          onClick={() => setActiveTab('goal')}
          className={`py-3 px-4 font-semibold text-sm rounded-t-xl transition-all border-b-2 flex items-center gap-2 ${
            activeTab === 'goal'
              ? 'border-rose-600 text-rose-600 dark:text-rose-400 bg-rose-50/50 dark:bg-rose-950/20'
              : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'
          }`}
        >
          <span>🎯</span>
          <span>Mi Meta Anual</span>
        </button>

        <button
          type="button"
          role="tab"
          aria-selected={activeTab === 'streak'}
          onClick={() => setActiveTab('streak')}
          className={`py-3 px-4 font-semibold text-sm rounded-t-xl transition-all border-b-2 flex items-center gap-2 ${
            activeTab === 'streak'
              ? 'border-rose-600 text-rose-600 dark:text-rose-400 bg-rose-50/50 dark:bg-rose-950/20'
              : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'
          }`}
        >
          <span>🔥</span>
          <span>Racha & Registro</span>
        </button>

        <button
          type="button"
          role="tab"
          aria-selected={activeTab === 'badges'}
          onClick={() => setActiveTab('badges')}
          className={`py-3 px-4 font-semibold text-sm rounded-t-xl transition-all border-b-2 flex items-center gap-2 ${
            activeTab === 'badges'
              ? 'border-rose-600 text-rose-600 dark:text-rose-400 bg-rose-50/50 dark:bg-rose-950/20'
              : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'
          }`}
        >
          <span>🎖️</span>
          <span>Medallero</span>
        </button>
      </div>

      {loading ? (
        <div className="py-20 flex justify-center items-center">
          <Spinner size="xl" color="pink" />
        </div>
      ) : (
        <>
          {/* TAB 1: RETOS ACTIVOS */}
          {activeTab === 'challenges' && (
            <div className="space-y-6" role="tabpanel">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                  <h2 className="text-xl font-bold text-gray-900 dark:text-white">
                    Retos de Lectura Comunitarios
                  </h2>
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    Únete a retos con lectores de todo el mundo y obtén recompensas exclusivas al completarlos.
                  </p>
                </div>
              </div>

              {allChallenges.length === 0 ? (
                <div className="p-8 text-center bg-gray-50 dark:bg-gray-800 rounded-2xl text-gray-500 text-sm">
                  No hay retos activos en este momento.
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {allChallenges.map((ch) => {
                    // Buscar si el usuario ya participa en este reto
                    const userProgressItem = data?.challenges?.find((c) => c.slug === ch.slug);
                    const isJoined = !!userProgressItem;
                    const isCompleted = userProgressItem?.is_completed;
                    const progress = userProgressItem?.current_progress || 0;
                    const percentage = userProgressItem?.percentage || 0;

                    return (
                      <div
                        key={ch.id}
                        className={`rounded-2xl p-6 border transition-all relative overflow-hidden ${
                          isCompleted
                            ? 'bg-gradient-to-br from-emerald-50/70 to-teal-50/30 dark:from-emerald-950/30 dark:to-gray-800 border-emerald-200 dark:border-emerald-800'
                            : 'bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700 shadow-sm hover:shadow-md'
                        }`}
                      >
                        <div className="flex items-start justify-between gap-4">
                          <div>
                            <div className="flex items-center gap-2 mb-1">
                              <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-rose-100 text-rose-800 dark:bg-rose-900/40 dark:text-rose-300">
                                Meta: {ch.target_count} {ch.challenge_type === 'pages_count' ? 'págs' : 'libros'}
                              </span>
                              {isCompleted && (
                                <span className="text-xs font-bold px-2.5 py-0.5 rounded-full bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300 flex items-center gap-1">
                                  <HiOutlineCheckCircle className="w-3.5 h-3.5" />
                                  ¡Superado!
                                </span>
                              )}
                            </div>
                            <h3 className="text-lg font-bold text-gray-900 dark:text-white">
                              {ch.title}
                            </h3>
                          </div>

                          {ch.badge_reward && (
                            <div className="w-12 h-12 rounded-xl bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-800 flex items-center justify-center text-2xl shadow-inner flex-shrink-0" title={`Recompensa: ${ch.badge_reward.name}`}>
                              {ch.badge_reward.icon}
                            </div>
                          )}
                        </div>

                        <p className="mt-3 text-sm text-gray-600 dark:text-gray-300 leading-relaxed">
                          {ch.description}
                        </p>

                        {/* Barra de progreso */}
                        {isJoined && (
                          <div className="mt-4 space-y-1.5">
                            <div className="flex justify-between text-xs font-semibold text-gray-600 dark:text-gray-300">
                              <span>Tu progreso</span>
                              <span>
                                {progress} / {ch.target_count} ({percentage}%)
                              </span>
                            </div>
                            <div className="w-full bg-gray-200 dark:bg-gray-700 h-2.5 rounded-full overflow-hidden">
                              <div
                                className={`h-full rounded-full transition-all duration-500 ${
                                  isCompleted ? 'bg-emerald-500' : 'bg-rose-500'
                                }`}
                                style={{ width: `${Math.min(100, percentage)}%` }}
                              />
                            </div>
                          </div>
                        )}

                        {/* Fechas y Botones de Acción */}
                        <div className="mt-6 pt-4 border-t border-gray-100 dark:border-gray-700 flex items-center justify-between">
                          <span className="text-xs text-gray-400 flex items-center gap-1">
                            <HiOutlineCalendar className="w-4 h-4" />
                            Hasta el {new Date(ch.end_date).toLocaleDateString('es-ES', { month: 'short', day: 'numeric', year: 'numeric' })}
                          </span>

                          <div className="flex items-center gap-2">
                            {token ? (
                              isJoined ? (
                                <>
                                  <span className="text-xs font-semibold text-emerald-600 dark:text-emerald-400 flex items-center gap-1">
                                    <HiOutlineCheckCircle className="w-4 h-4" />
                                    Participando
                                  </span>
                                  <button
                                    type="button"
                                    onClick={() => handleLeaveChallenge(ch.slug)}
                                    disabled={leavingSlug === ch.slug}
                                    className="text-xs text-gray-400 hover:text-red-500 dark:hover:text-red-400 p-1 rounded transition-colors"
                                    title="Abandonar reto"
                                  >
                                    <HiOutlineLogout className="w-4 h-4" />
                                  </button>
                                </>
                              ) : (
                                <button
                                  type="button"
                                  onClick={() => handleJoinChallenge(ch.slug)}
                                  disabled={joiningSlug === ch.slug}
                                  className="px-4 py-2 text-xs font-bold text-white bg-rose-600 hover:bg-rose-700 rounded-xl transition-all shadow-sm"
                                >
                                  {joiningSlug === ch.slug ? <Spinner size="sm" /> : 'Unirme al reto'}
                                </button>
                              )
                            ) : (
                              <span className="text-xs text-gray-400">Inicia sesión para unirte</span>
                            )}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}

          {/* TAB 2: MI META ANUAL */}
          {activeTab === 'goal' && (
            <div className="space-y-6" role="tabpanel">
              <div className="bg-white dark:bg-gray-800 rounded-3xl p-6 sm:p-8 border border-gray-200 dark:border-gray-700 shadow-sm">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-gray-100 dark:border-gray-700">
                  <div>
                    <h2 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
                      <span>🎯</span>
                      <span>Objetivo de Lectura {currentYear}</span>
                    </h2>
                    <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                      Mantén el rumbo con tu reto anual personalizado.
                    </p>
                  </div>

                  {token && (
                    <button
                      type="button"
                      onClick={() => setIsGoalModalOpen(true)}
                      className="inline-flex items-center gap-1.5 px-4 py-2 text-sm font-semibold text-white bg-rose-600 hover:bg-rose-700 rounded-xl shadow-sm transition-all"
                    >
                      <span>Ajustar mi meta</span>
                    </button>
                  )}
                </div>

                <div className="mt-8 grid grid-cols-1 md:grid-cols-3 gap-6 text-center">
                  <div className="p-6 bg-rose-50/60 dark:bg-rose-950/20 rounded-2xl border border-rose-100 dark:border-rose-900/30">
                    <div className="text-4xl font-black text-rose-600 dark:text-rose-400">
                      {goal?.current_books || 0}
                    </div>
                    <div className="mt-1 text-sm font-semibold text-gray-700 dark:text-gray-300">
                      Libros completados
                    </div>
                  </div>

                  <div className="p-6 bg-pink-50/60 dark:bg-pink-950/20 rounded-2xl border border-pink-100 dark:border-pink-900/30">
                    <div className="text-4xl font-black text-pink-600 dark:text-pink-400">
                      {goal?.target_books || 12}
                    </div>
                    <div className="mt-1 text-sm font-semibold text-gray-700 dark:text-gray-300">
                      Meta fijada
                    </div>
                  </div>

                  <div className="p-6 bg-indigo-50/60 dark:bg-indigo-950/20 rounded-2xl border border-indigo-100 dark:border-indigo-900/30">
                    <div className="text-4xl font-black text-indigo-600 dark:text-indigo-400">
                      {goal?.percentage || 0}%
                    </div>
                    <div className="mt-1 text-sm font-semibold text-gray-700 dark:text-gray-300">
                      Progreso global
                    </div>
                  </div>
                </div>

                {/* Barra de Progreso y Ritmo */}
                <div className="mt-8 space-y-3">
                  <div className="w-full bg-gray-200 dark:bg-gray-700 h-4 rounded-full overflow-hidden">
                    <div
                      className="bg-gradient-to-r from-rose-500 to-indigo-600 h-full rounded-full transition-all duration-700"
                      style={{ width: `${Math.min(100, goal?.percentage || 0)}%` }}
                    />
                  </div>

                  <div className="flex flex-col sm:flex-row items-center justify-between text-xs font-medium text-gray-500 dark:text-gray-400 gap-2">
                    <span>
                      {goal?.remaining_books === 0
                        ? '¡Enhorabuena, has alcanzado tu meta!'
                        : `Te faltan ${goal?.remaining_books || 0} libros para completar el reto`}
                    </span>
                    <span className="font-semibold text-rose-600 dark:text-rose-400">
                      {goal?.pacing_text || 'Ritmo previsto'}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 3: RACHA & REGISTRO */}
          {activeTab === 'streak' && (
            <div className="space-y-6" role="tabpanel">
              <div className="bg-white dark:bg-gray-800 rounded-3xl p-6 sm:p-8 border border-gray-200 dark:border-gray-700 shadow-sm">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-gray-100 dark:border-gray-700">
                  <div>
                    <h2 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
                      <span>🔥</span>
                      <span>Racha de Lectura Consecutiva</span>
                    </h2>
                    <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                      Cada día que abres un libro y registras tu avance cuenta para mantener la llama encendida.
                    </p>
                  </div>

                  {token && (
                    <button
                      type="button"
                      onClick={() => setIsLogModalOpen(true)}
                      className="inline-flex items-center gap-2 px-5 py-2.5 text-sm font-semibold text-white bg-gradient-to-r from-amber-500 to-rose-600 hover:from-amber-600 hover:to-rose-700 rounded-xl shadow-md transition-all"
                    >
                      <HiOutlineFire className="w-5 h-5" />
                      <span>He leído hoy</span>
                    </button>
                  )}
                </div>

                <div className="mt-8 grid grid-cols-1 sm:grid-cols-2 gap-6">
                  <div className="p-8 rounded-2xl bg-amber-50/70 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-800 flex items-center gap-6">
                    <span className="text-6xl">🔥</span>
                    <div>
                      <div className="text-5xl font-black text-amber-600 dark:text-amber-400">
                        {streak?.current_streak || 0}
                      </div>
                      <div className="text-sm font-bold text-gray-700 dark:text-gray-200 uppercase tracking-wider mt-1">
                        Días consecutivos de racha
                      </div>
                    </div>
                  </div>

                  <div className="p-8 rounded-2xl bg-indigo-50/70 dark:bg-indigo-950/20 border border-indigo-200 dark:border-indigo-800 flex items-center gap-6">
                    <span className="text-6xl">⚡</span>
                    <div>
                      <div className="text-5xl font-black text-indigo-600 dark:text-indigo-400">
                        {streak?.longest_streak || 0}
                      </div>
                      <div className="text-sm font-bold text-gray-700 dark:text-gray-200 uppercase tracking-wider mt-1">
                        Récord histórico de racha
                      </div>
                    </div>
                  </div>
                </div>

                <div className="mt-8 p-4 bg-gray-50 dark:bg-gray-750 rounded-2xl text-xs text-gray-500 dark:text-gray-400 flex items-center gap-3">
                  <span className="text-xl">💡</span>
                  <span>
                    Basta con registrar unas pocas páginas o minutos de lectura cada día para alimentar tu racha y desbloquear medallas secretas.
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* TAB 4: MEDALLERO */}
          {activeTab === 'badges' && (
            <div className="space-y-6" role="tabpanel">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                  <h2 className="text-xl font-bold text-gray-900 dark:text-white">
                    Catálogo de Insignias y Logros
                  </h2>
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    Descubre los hitos literarios que puedes alcanzar y coleccionar en tu perfil.
                  </p>
                </div>

                {/* Filtro por categoría */}
                <div className="flex flex-wrap gap-1.5">
                  {[
                    { id: 'all', label: 'Todas' },
                    { id: 'unlocked', label: 'Desbloqueadas' },
                    { id: 'locked', label: 'Pendientes' },
                    { id: 'reading', label: 'Lectura' },
                    { id: 'streak', label: 'Rachas' },
                    { id: 'reviews', label: 'Reseñas' },
                    { id: 'challenges', label: 'Retos' },
                  ].map((cat) => (
                    <button
                      key={cat.id}
                      type="button"
                      onClick={() => setBadgeFilter(cat.id)}
                      className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                        badgeFilter === cat.id
                          ? 'bg-rose-600 text-white font-semibold'
                          : 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700'
                      }`}
                    >
                      {cat.label}
                    </button>
                  ))}
                </div>
              </div>

              {filteredBadges.length === 0 ? (
                <div className="p-8 text-center bg-gray-50 dark:bg-gray-800 rounded-2xl text-gray-500 text-sm">
                  No hay insignias en esta categoría.
                </div>
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                  {filteredBadges.map((badge) => (
                    <div
                      key={badge.id}
                      className={`rounded-2xl p-5 border transition-all flex flex-col items-center text-center ${
                        badge.unlocked
                          ? 'bg-white dark:bg-gray-800 border-amber-200 dark:border-amber-900/40 shadow-sm'
                          : 'bg-gray-50/70 dark:bg-gray-850 border-gray-200 dark:border-gray-800 opacity-60'
                      }`}
                    >
                      <div
                        className={`w-16 h-16 rounded-2xl flex items-center justify-center text-3xl mb-3 shadow-inner ${
                          badge.unlocked
                            ? 'bg-gradient-to-br from-amber-100 to-rose-100 dark:from-amber-900/30 dark:to-rose-900/30 border border-amber-200 dark:border-amber-800'
                            : 'bg-gray-200 dark:bg-gray-700 grayscale'
                        }`}
                      >
                        {badge.icon}
                      </div>

                      <h4 className="font-bold text-sm text-gray-900 dark:text-white">
                        {badge.name}
                      </h4>
                      <p className="mt-1 text-xs text-gray-500 dark:text-gray-400 line-clamp-2">
                        {badge.description}
                      </p>

                      <div className="mt-4 pt-3 border-t border-gray-100 dark:border-gray-750 w-full flex items-center justify-between text-[11px]">
                        <span className="font-semibold text-rose-600 dark:text-rose-400">
                          +{badge.points} pts
                        </span>
                        <span
                          className={`font-semibold ${
                            badge.unlocked ? 'text-emerald-600 dark:text-emerald-400' : 'text-gray-400'
                          }`}
                        >
                          {badge.unlocked ? '✓ Desbloqueada' : '🔒 Bloqueada'}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </>
      )}

      {/* Modal: Ajustar Meta Anual */}
      <Modal show={isGoalModalOpen} onClose={() => setIsGoalModalOpen(false)}>
        <Modal.Header>Ajustar Meta de Lectura {currentYear}</Modal.Header>
        <form onSubmit={handleSaveGoal}>
          <Modal.Body className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-900 dark:text-white mb-1">
                ¿Cuántos libros te propones leer este año?
              </label>
              <input
                type="number"
                min="1"
                max="500"
                required
                value={goalTargetBooks}
                onChange={(e) => setGoalTargetBooks(Number(e.target.value))}
                className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-900 dark:text-white mb-1">
                Meta de páginas (opcional)
              </label>
              <input
                type="number"
                min="0"
                value={goalTargetPages}
                onChange={(e) => setGoalTargetPages(Number(e.target.value))}
                className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
              />
            </div>
          </Modal.Body>
          <Modal.Footer>
            <Button color="gray" onClick={() => setIsGoalModalOpen(false)}>
              Cancelar
            </Button>
            <Button color="pink" type="submit" disabled={savingGoal}>
              {savingGoal ? <Spinner size="sm" /> : 'Guardar Meta'}
            </Button>
          </Modal.Footer>
        </form>
      </Modal>

      {/* Modal: Registrar Lectura de Hoy */}
      <Modal show={isLogModalOpen} onClose={() => setIsLogModalOpen(false)}>
        <Modal.Header>Registrar Sesión de Lectura</Modal.Header>
        <form onSubmit={handleSaveLog}>
          <Modal.Body className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-900 dark:text-white mb-1">
                Páginas leídas
              </label>
              <input
                type="number"
                min="1"
                required
                value={logPages}
                onChange={(e) => setLogPages(Number(e.target.value))}
                className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-900 dark:text-white mb-1">
                Minutos dedicados
              </label>
              <input
                type="number"
                min="1"
                required
                value={logMinutes}
                onChange={(e) => setLogMinutes(Number(e.target.value))}
                className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
              />
            </div>
          </Modal.Body>
          <Modal.Footer>
            <Button color="gray" onClick={() => setIsLogModalOpen(false)}>
              Cancelar
            </Button>
            <Button color="pink" type="submit" disabled={savingLog}>
              {savingLog ? <Spinner size="sm" /> : 'Registrar'}
            </Button>
          </Modal.Footer>
        </form>
      </Modal>
    </div>
  );
};
