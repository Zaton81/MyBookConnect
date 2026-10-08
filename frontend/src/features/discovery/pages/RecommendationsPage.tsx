import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { Button, Spinner } from 'flowbite-react';
import {
  HiOutlineSparkles,
  HiOutlineUserGroup,
  HiOutlineBookOpen,
  HiOutlineGlobeAlt,
  HiOutlineFilter,
  HiOutlineCheck,
  HiOutlineX,
  HiOutlinePlus,
  HiOutlineChevronRight,
  HiOutlineStar,
} from 'react-icons/hi';
import { useAuthStore } from '../../../store/auth';
import { resolveMediaUrl } from '../../../utils/media';

export type RecommendationStrategy = 'hybrid' | 'collab' | 'semantic' | 'serendipity';

export interface CategoryItem {
  id: number;
  name: string;
}

export interface RecommendedBook {
  id: number;
  title: string;
  author_name: string;
  cover: string | null;
  average_rating: number | null;
  score: number;
  affinity_percentage?: number;
  reason: string;
  categories?: CategoryItem[];
  pages?: number;
  breakdown?: Record<string, number>;
}

export interface SimilarReader {
  user_id: number;
  username: string;
  similarity_score: number;
  shared_books_count: number;
  avatar_url: string | null;
}

export function RecommendationsPage() {
  const { token } = useAuthStore();
  const apiUrl = (import.meta as any).env.VITE_API_URL || 'http://localhost:8000';

  const [strategy, setStrategy] = useState<RecommendationStrategy>('hybrid');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [selectedLength, setSelectedLength] = useState<string>('all');

  const [books, setBooks] = useState<RecommendedBook[]>([]);
  const [similarReaders, setSimilarReaders] = useState<SimilarReader[]>([]);
  const [availableCategories, setAvailableCategories] = useState<CategoryItem[]>([]);

  const [loading, setLoading] = useState(true);
  const [loadingReaders, setLoadingReaders] = useState(false);
  const [addedBooks, setAddedBooks] = useState<Record<number, boolean>>({});
  const [dismissingBookId, setDismissingBookId] = useState<number | null>(null);

  // Cargar categorías disponibles
  useEffect(() => {
    const fetchCategories = async () => {
      try {
        const res = await fetch(`${apiUrl}/api/v1/books/categories/`, {
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        });
        if (res.ok) {
          const data = await res.json();
          const items = Array.isArray(data) ? data : data.results || [];
          setAvailableCategories(items);
        }
      } catch (err) {
        console.warn('Error fetching categories:', err);
      }
    };
    fetchCategories();
  }, [apiUrl, token]);

  // Cargar lectores similares
  useEffect(() => {
    const fetchSimilarReaders = async () => {
      if (!token) return;
      setLoadingReaders(true);
      try {
        const res = await fetch(`${apiUrl}/api/v1/books/recommendations/similar-readers/?limit=5`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (res.ok) {
          const data = await res.json();
          setSimilarReaders(data.results || []);
        }
      } catch (err) {
        console.warn('Error fetching similar readers:', err);
      } finally {
        setLoadingReaders(false);
      }
    };
    fetchSimilarReaders();
  }, [apiUrl, token]);

  // Cargar recomendaciones
  const fetchRecommendations = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      params.set('strategy', strategy);
      params.set('limit', '18');
      params.set('exclude_dismissed', 'true');

      if (selectedCategory !== 'all') {
        params.set('category_id', selectedCategory);
      }
      if (selectedLength !== 'all') {
        params.set('length_tier', selectedLength);
      }

      const res = await fetch(`${apiUrl}/api/v1/books/recommendations/?${params.toString()}`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });

      if (res.ok) {
        const data = await res.json();
        setBooks(data.results || []);
      } else {
        setBooks([]);
      }
    } catch (err) {
      console.error('Error fetching recommendations:', err);
      setBooks([]);
    } finally {
      setLoading(false);
    }
  }, [apiUrl, token, strategy, selectedCategory, selectedLength]);

  useEffect(() => {
    fetchRecommendations();
  }, [fetchRecommendations]);

  // Añadir a "Quiero Leer"
  const handleAddToShelf = async (bookId: number) => {
    if (!token) return;
    try {
      const res = await fetch(`${apiUrl}/api/v1/books/user-books/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          book_id: bookId,
          status: 'want_to_read',
        }),
      });
      if (res.ok) {
        setAddedBooks((prev) => ({ ...prev, [bookId]: true }));
      }
    } catch (err) {
      console.error('Error adding book to shelf:', err);
    }
  };

  // Descartar recomendación ("No me interesa")
  const handleDismiss = async (bookId: number) => {
    if (!token) return;
    setDismissingBookId(bookId);
    try {
      const res = await fetch(`${apiUrl}/api/v1/books/recommendations/dismiss/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          book_id: bookId,
          reason: 'not_interested',
        }),
      });
      if (res.ok) {
        setBooks((prev) => prev.filter((b) => b.id !== bookId));
      }
    } catch (err) {
      console.error('Error dismissing recommendation:', err);
    } finally {
      setDismissingBookId(null);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 sm:py-8 space-y-8 animate-fadeIn">
      {/* ── Cabecera Principal ── */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-slate-200 dark:border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <span className="p-2 rounded-2xl bg-teal-50 dark:bg-teal-950/60 text-teal-600 dark:text-teal-400 text-2xl shadow-xs">
              ✨
            </span>
            <h1 className="text-2xl sm:text-3xl font-black text-slate-900 dark:text-white tracking-tight">
              Recomendaciones Inteligentes
            </h1>
          </div>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1 max-w-2xl">
            Descubre lecturas seleccionadas a tu medida combinando algoritmos de afinidad semántica,
            gustos de lectores gemelos y análisis de tus preferencias literarias.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Link to="/home">
            <Button size="xs" color="light" className="font-semibold">
              ← Volver al Muro
            </Button>
          </Link>
        </div>
      </div>

      {/* ── Selector de Estrategia Algorítmica ── */}
      <div className="space-y-3">
        <label className="block text-xs font-bold uppercase tracking-wider text-slate-400">
          Modo de Recomendación
        </label>
        <div
          role="tablist"
          aria-label="Estrategias de recomendación"
          className="grid grid-cols-2 lg:grid-cols-4 gap-3"
        >
          {/* Híbrido IA */}
          <button
            role="tab"
            aria-selected={strategy === 'hybrid'}
            type="button"
            onClick={() => setStrategy('hybrid')}
            className={`p-3.5 rounded-2xl text-left border transition-all ${
              strategy === 'hybrid'
                ? 'bg-teal-500/10 border-teal-500 text-teal-900 dark:text-teal-200 shadow-sm ring-1 ring-teal-500'
                : 'bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400 hover:border-slate-300 dark:hover:border-slate-700'
            }`}
          >
            <div className="flex items-center gap-2 font-bold text-sm">
              <HiOutlineSparkles className="w-4 h-4 text-teal-500" />
              <span>Híbrido IA</span>
            </div>
            <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1 line-clamp-2">
              Fusión tri-vectorial de semántica, afinidad social y temática.
            </p>
          </button>

          {/* Gemelos Lectores */}
          <button
            role="tab"
            aria-selected={strategy === 'collab'}
            type="button"
            onClick={() => setStrategy('collab')}
            className={`p-3.5 rounded-2xl text-left border transition-all ${
              strategy === 'collab'
                ? 'bg-teal-500/10 border-teal-500 text-teal-900 dark:text-teal-200 shadow-sm ring-1 ring-teal-500'
                : 'bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400 hover:border-slate-300 dark:hover:border-slate-700'
            }`}
          >
            <div className="flex items-center gap-2 font-bold text-sm">
              <HiOutlineUserGroup className="w-4 h-4 text-indigo-500" />
              <span>Gemelos Lectores</span>
            </div>
            <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1 line-clamp-2">
              Libros amados por lectores con tus mismos patrones de valoración.
            </p>
          </button>

          {/* Semántico & Estilo */}
          <button
            role="tab"
            aria-selected={strategy === 'semantic'}
            type="button"
            onClick={() => setStrategy('semantic')}
            className={`p-3.5 rounded-2xl text-left border transition-all ${
              strategy === 'semantic'
                ? 'bg-teal-500/10 border-teal-500 text-teal-900 dark:text-teal-200 shadow-sm ring-1 ring-teal-500'
                : 'bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400 hover:border-slate-300 dark:hover:border-slate-700'
            }`}
          >
            <div className="flex items-center gap-2 font-bold text-sm">
              <HiOutlineBookOpen className="w-4 h-4 text-cyan-500" />
              <span>Estilo y Temática</span>
            </div>
            <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1 line-clamp-2">
              Coincidencia de vectores de embedding con tus libros predilectos.
            </p>
          </button>

          {/* Serendipia & Descubrimiento */}
          <button
            role="tab"
            aria-selected={strategy === 'serendipity'}
            type="button"
            onClick={() => setStrategy('serendipity')}
            className={`p-3.5 rounded-2xl text-left border transition-all ${
              strategy === 'serendipity'
                ? 'bg-teal-500/10 border-teal-500 text-teal-900 dark:text-teal-200 shadow-sm ring-1 ring-teal-500'
                : 'bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400 hover:border-slate-300 dark:hover:border-slate-700'
            }`}
          >
            <div className="flex items-center gap-2 font-bold text-sm">
              <HiOutlineGlobeAlt className="w-4 h-4 text-amber-500" />
              <span>Descubrimiento</span>
            </div>
            <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1 line-clamp-2">
              Joyas de alta valoración de autores que aún no has leído.
            </p>
          </button>
        </div>
      </div>

      {/* ── Barra de Filtros: Categoría y Longitud ── */}
      <div className="flex flex-wrap items-center gap-4 p-4 rounded-2xl bg-slate-50 dark:bg-slate-900/60 border border-slate-200/80 dark:border-slate-800 text-xs">
        <div className="flex items-center gap-1.5 font-bold text-slate-600 dark:text-slate-300">
          <HiOutlineFilter className="w-4 h-4 text-teal-600" />
          <span>Filtros:</span>
        </div>

        {/* Filtro Género */}
        <div className="flex items-center gap-2">
          <label htmlFor="rec-cat-filter" className="text-slate-500 font-semibold">
            Género:
          </label>
          <select
            id="rec-cat-filter"
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value)}
            className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200 text-xs py-1.5 px-3 font-medium focus:ring-teal-500"
          >
            <option value="all">Todos los géneros</option>
            {availableCategories.map((c) => (
              <option key={c.id} value={String(c.id)}>
                {c.name}
              </option>
            ))}
          </select>
        </div>

        {/* Filtro Longitud */}
        <div className="flex items-center gap-2">
          <label htmlFor="rec-len-filter" className="text-slate-500 font-semibold">
            Longitud:
          </label>
          <select
            id="rec-len-filter"
            value={selectedLength}
            onChange={(e) => setSelectedLength(e.target.value)}
            className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200 text-xs py-1.5 px-3 font-medium focus:ring-teal-500"
          >
            <option value="all">Cualquier longitud</option>
            <option value="short">Cortos (&lt; 200 págs)</option>
            <option value="medium">Medios (200 - 399 págs)</option>
            <option value="long">Largos (400 - 599 págs)</option>
            <option value="epic">Épicos (600+ págs)</option>
          </select>
        </div>

        <div className="ml-auto text-slate-400 font-medium text-[11px]">
          {books.length} sugerencias encontradas
        </div>
      </div>

      {/* ── Contenido Principal: Grid de Recomendaciones y Lectores Gemelos ── */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
        {/* Columna Izquierda / Central: Libros Recomendados */}
        <div className="lg:col-span-3 space-y-6">
          {loading ? (
            <div className="flex flex-col justify-center items-center py-20 space-y-3">
              <Spinner size="xl" color="info" />
              <p className="text-xs text-slate-400 font-medium animate-pulse">
                Calculando recomendaciones multimodales...
              </p>
            </div>
          ) : books.length === 0 ? (
            <div className="text-center py-16 p-8 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 space-y-3">
              <span className="text-4xl">📚</span>
              <h3 className="text-base font-bold text-slate-800 dark:text-white">
                No hay libros que coincidan con estos filtros
              </h3>
              <p className="text-xs text-slate-400 max-w-sm mx-auto">
                Prueba a restablecer los filtros de categoría o longitud para explorar más obras
                compatibles con tu perfil.
              </p>
              <Button
                size="xs"
                color="teal"
                onClick={() => {
                  setSelectedCategory('all');
                  setSelectedLength('all');
                }}
                className="mt-2"
              >
                Restablecer filtros
              </Button>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-5">
              {books.map((book) => {
                const isAdded = addedBooks[book.id];
                const isDismissing = dismissingBookId === book.id;

                return (
                  <div
                    key={book.id}
                    className="group bg-white dark:bg-slate-900 rounded-3xl p-4 border border-slate-200/80 dark:border-slate-800 shadow-xs hover:shadow-lg hover:border-teal-500/40 dark:hover:border-teal-500/40 transition-all flex flex-col justify-between"
                  >
                    <div>
                      {/* Cabecera de la tarjeta: Badge de Match % y Descarte */}
                      <div className="flex items-center justify-between mb-3">
                        <span className="px-2.5 py-0.5 rounded-full text-[10px] font-black tracking-wide bg-gradient-to-r from-teal-500/20 to-emerald-500/20 text-teal-700 dark:text-teal-300 border border-teal-500/30">
                          {book.affinity_percentage || 85}% Afinidad
                        </span>
                        <button
                          type="button"
                          onClick={() => handleDismiss(book.id)}
                          disabled={isDismissing}
                          className="p-1 rounded-lg text-slate-400 hover:text-rose-500 hover:bg-rose-50 dark:hover:bg-rose-950/40 transition-colors"
                          title="No me interesa esta recomendación"
                          aria-label={`Descartar ${book.title}`}
                        >
                          <HiOutlineX className="w-3.5 h-3.5" />
                        </button>
                      </div>

                      {/* Portada */}
                      <Link to={`/books/${book.id}`} className="block">
                        <div className="relative aspect-[2/3] w-full overflow-hidden rounded-2xl bg-slate-100 dark:bg-slate-800 mb-3 shadow-inner group-hover:scale-[1.02] transition-transform duration-200">
                          {book.cover ? (
                            <img
                              src={resolveMediaUrl(book.cover)}
                              alt={book.title}
                              className="w-full h-full object-cover"
                              loading="lazy"
                            />
                          ) : (
                            <div className="w-full h-full flex items-center justify-center p-3 text-center text-xs font-bold text-slate-400">
                              {book.title}
                            </div>
                          )}
                        </div>
                      </Link>

                      {/* Título y Autor */}
                      <Link to={`/books/${book.id}`}>
                        <h2 className="font-bold text-sm text-slate-900 dark:text-white line-clamp-1 group-hover:text-teal-600 transition-colors">
                          {book.title}
                        </h2>
                      </Link>
                      <p className="text-xs text-slate-500 dark:text-slate-400 truncate mt-0.5">
                        {book.author_name}
                      </p>

                      {/* Categorías y Rating */}
                      <div className="flex items-center justify-between gap-2 mt-2 pt-2 border-t border-slate-100 dark:border-slate-800/80 text-[11px]">
                        <span className="text-slate-400 truncate max-w-[120px]">
                          {book.categories && book.categories.length > 0
                            ? book.categories[0].name
                            : 'Literatura'}
                        </span>
                        <div className="flex items-center gap-1 font-bold text-amber-500 shrink-0">
                          <HiOutlineStar className="w-3.5 h-3.5 fill-current" />
                          <span>{book.average_rating ? book.average_rating.toFixed(1) : '—'}</span>
                        </div>
                      </div>

                      {/* Motivo Explicable */}
                      <div className="mt-2.5 p-2 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-100 dark:border-slate-800">
                        <p className="text-[11px] text-slate-600 dark:text-slate-300 font-medium line-clamp-2">
                          💡 {book.reason}
                        </p>
                      </div>
                    </div>

                    {/* Botón de 1 Clic para añadir a "Quiero Leer" */}
                    <div className="mt-4 pt-3 border-t border-slate-100 dark:border-slate-800">
                      {isAdded ? (
                        <Button
                          size="xs"
                          color="light"
                          disabled
                          className="w-full font-bold text-xs text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/40 border-emerald-200"
                        >
                          <HiOutlineCheck className="w-3.5 h-3.5 mr-1" />
                          En tu biblioteca
                        </Button>
                      ) : (
                        <Button
                          size="xs"
                          color="teal"
                          onClick={() => handleAddToShelf(book.id)}
                          className="w-full font-bold text-xs flex items-center justify-center gap-1 shadow-xs"
                        >
                          <HiOutlinePlus className="w-3.5 h-3.5 mr-1" />
                          Quiero leer
                        </Button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Columna Derecha: Lectores Gemelos / Gustos Similares */}
        <div className="space-y-6">
          <div className="p-5 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 shadow-xs space-y-4">
            <div className="flex items-center gap-2 border-b border-slate-100 dark:border-slate-800 pb-3">
              <span className="text-xl">👥</span>
              <div>
                <h3 className="font-bold text-sm text-slate-900 dark:text-white">
                  Gemelos Lectores
                </h3>
                <p className="text-[11px] text-slate-400">
                  Lectores con patrones afines de valoración
                </p>
              </div>
            </div>

            {loadingReaders ? (
              <div className="py-6 flex justify-center">
                <Spinner size="sm" color="info" />
              </div>
            ) : similarReaders.length === 0 ? (
              <p className="text-xs text-slate-400 text-center py-4">
                Sigue valorando libros para descubrir lectores afines.
              </p>
            ) : (
              <div className="space-y-3">
                {similarReaders.map((reader) => (
                  <Link
                    key={reader.user_id}
                    to={`/users/${reader.user_id}`}
                    className="flex items-center justify-between p-2.5 rounded-2xl bg-slate-50 dark:bg-slate-800/40 hover:bg-teal-50/50 dark:hover:bg-slate-800 transition-colors group"
                  >
                    <div className="flex items-center gap-2.5 min-w-0">
                      <div className="w-8 h-8 rounded-full bg-teal-100 dark:bg-teal-900 text-teal-700 dark:text-teal-300 font-black text-xs flex items-center justify-center shrink-0 overflow-hidden">
                        {reader.avatar_url ? (
                          <img
                            src={resolveMediaUrl(reader.avatar_url)}
                            alt={reader.username}
                            className="w-full h-full object-cover"
                          />
                        ) : (
                          reader.username.charAt(0).toUpperCase()
                        )}
                      </div>
                      <div className="min-w-0">
                        <div className="text-xs font-bold text-slate-800 dark:text-slate-200 truncate group-hover:text-teal-600 transition-colors">
                          @{reader.username}
                        </div>
                        <div className="text-[10px] text-slate-400">
                          {reader.shared_books_count} libros en común
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-1.5 shrink-0 ml-2">
                      <span className="text-[11px] font-black text-teal-600 dark:text-teal-400">
                        {Math.round(reader.similarity_score * 100)}%
                      </span>
                      <HiOutlineChevronRight className="w-3.5 h-3.5 text-slate-400 group-hover:translate-x-0.5 transition-transform" />
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </div>

          {/* Tarjeta Informativa sobre Algoritmos */}
          <div className="p-5 rounded-3xl bg-gradient-to-br from-teal-900 to-slate-900 text-white shadow-lg space-y-3">
            <span className="px-2.5 py-0.5 bg-white/10 text-teal-300 text-[10px] font-bold rounded-full border border-white/10">
              Motor v3
            </span>
            <h4 className="font-extrabold text-sm tracking-tight">
              ¿Cómo calculamos tu afinidad?
            </h4>
            <p className="text-[11px] text-slate-300 leading-relaxed">
              Analizamos tus lecturas con 5 estrellas, libros terminados y autores predilectos para
              generar tu <strong>vector de preferencias semánticas</strong>, comparándolo con miles de
              obras en tiempo real.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default RecommendationsPage;
