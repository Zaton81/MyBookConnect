import React, { useState, useEffect } from 'react';
import { Modal, Button, Spinner } from 'flowbite-react';
import { Link } from 'react-router-dom';
import { useAuthStore } from '../../../store/auth';
import { ImportBooksModal } from '../../library/components/ImportBooksModal';

interface CategoryOption {
  id: number;
  name: string;
  slug: string;
  books_count?: number;
}

interface SuggestedBook {
  id: number;
  title: string;
  author_name: string;
  cover?: string;
  average_rating?: number;
  category_names?: string[];
}

export interface OnboardingModalProps {
  isOpen: boolean;
  onClose: () => void;
  onComplete?: () => void;
}

const CATEGORY_ICONS: Record<string, string> = {
  'ciencia-ficcion': '🚀',
  'fantasia': '🧙‍♂️',
  'misterio': '🔍',
  'novela-negra': '🕵️',
  'romance': '💖',
  'thriller': '⚡',
  'historica': '🏛️',
  'terror': '👻',
  'filosofia': '🧠',
  'clasicos': '📜',
  'poesia': '✒️',
  'biografia': '👤',
  'ensayo': '📚',
  'juvenil': '🌟',
  'aventura': '🗺️',
};

export function OnboardingModal({ isOpen, onClose, onComplete }: OnboardingModalProps) {
  const { token, updateProfile, user } = useAuthStore();
  const [step, setStep] = useState<1 | 2 | 3>(1);

  const [loading, setLoading] = useState<boolean>(true);
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const [availableCategories, setAvailableCategories] = useState<CategoryOption[]>([]);
  const [suggestedBooks, setSuggestedBooks] = useState<SuggestedBook[]>([]);

  // Estado del usuario en el onboarding
  const [selectedCategoryIds, setSelectedCategoryIds] = useState<number[]>([]);
  const [selectedBooks, setSelectedBooks] = useState<Array<{ book_id: number; status: string }>>([]);
  const [bio, setBio] = useState<string>('');
  const [firstRec, setFirstRec] = useState<any>(null);

  // Submodal de importación CSV
  const [isImportModalOpen, setIsImportModalOpen] = useState<boolean>(false);

  const apiUrl = (import.meta as any).env.VITE_API_URL || 'http://localhost:8000';

  useEffect(() => {
    if (!isOpen || !token) return;

    const loadOptions = async () => {
      try {
        setLoading(true);
        setError(null);
        const res = await fetch(`${apiUrl}/api/v1/users/onboarding/`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (res.ok) {
          const data = await res.json();
          setAvailableCategories(data.available_categories || []);
          setSuggestedBooks(data.suggested_books || []);
          if (data.favorite_categories && data.favorite_categories.length > 0) {
            setSelectedCategoryIds(data.favorite_categories.map((c: any) => c.id));
          }
        }
      } catch (err: any) {
        console.error('Error cargando onboarding data:', err);
      } finally {
        setLoading(false);
      }
    };

    loadOptions();
  }, [isOpen, token, apiUrl]);

  const toggleCategory = (catId: number) => {
    setSelectedCategoryIds((prev) =>
      prev.includes(catId) ? prev.filter((id) => id !== catId) : [...prev, catId]
    );
  };

  const toggleBookSelection = (bookId: number, status: 'read' | 'want_to_read') => {
    setSelectedBooks((prev) => {
      const exists = prev.find((b) => b.book_id === bookId);
      if (exists) {
        if (exists.status === status) {
          return prev.filter((b) => b.book_id !== bookId);
        }
        return prev.map((b) => (b.book_id === bookId ? { ...b, status } : b));
      }
      return [...prev, { book_id: bookId, status }];
    });
  };

  const handleSkip = async () => {
    try {
      if (token) {
        await fetch(`${apiUrl}/api/v1/users/onboarding/skip/`, {
          method: 'POST',
          headers: { Authorization: `Bearer ${token}` },
        });
        if (user) {
          updateProfile({ ...user, onboarding_completed: true });
        }
      }
    } catch (e) {
      console.error('Error saltando onboarding:', e);
    } finally {
      onClose();
    }
  };

  const handleFinish = async () => {
    try {
      setSubmitting(true);
      setError(null);

      const res = await fetch(`${apiUrl}/api/v1/users/onboarding/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          category_ids: selectedCategoryIds,
          books: selectedBooks,
          bio: bio.trim(),
        }),
      });

      if (!res.ok) {
        throw new Error('No se pudo guardar la configuración de bienvenida.');
      }

      const data = await res.json();
      setFirstRec(data.first_recommendation);
      if (user) {
        updateProfile({ ...user, onboarding_completed: true });
      }

      if (onComplete) {
        onComplete();
      }
    } catch (err: any) {
      setError(err?.message || 'Error al completar el onboarding.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <>
      <Modal
        show={isOpen}
        onClose={handleSkip}
        size="2xl"
        dismissible
        className="backdrop-blur-sm"
      >
        <div className="relative bg-white dark:bg-slate-900 rounded-3xl overflow-hidden shadow-2xl border border-slate-100 dark:border-slate-800">
          {/* Header con Barra de Progreso y Botón Omitir */}
          <div className="px-6 pt-6 pb-4 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className="w-9 h-9 rounded-2xl bg-teal-50 dark:bg-teal-950/80 text-teal-600 dark:text-teal-400 flex items-center justify-center font-black text-base shadow-sm border border-teal-100 dark:border-teal-900/50">
                {step}
              </span>
              <div>
                <h2 className="text-lg font-bold text-slate-900 dark:text-white leading-tight">
                  {step === 1 && '¿Qué géneros literarios te apasionan?'}
                  {step === 2 && 'Añade tus primeras lecturas'}
                  {step === 3 && '¡Tu espacio de lectura está listo!'}
                </h2>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Paso {step} de 3 • Personalización rápida en 1 minuto
                </p>
              </div>
            </div>

            <button
              type="button"
              onClick={handleSkip}
              className="text-xs font-semibold text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 transition-colors px-2 py-1 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 cursor-pointer"
            >
              Explorar directamente ✕
            </button>
          </div>

          {/* Contenido del Paso */}
          <div className="p-6 max-h-[65vh] overflow-y-auto">
            {loading ? (
              <div className="py-16 text-center">
                <Spinner size="xl" className="fill-teal-600" />
                <p className="mt-3 text-sm text-slate-500 dark:text-slate-400">
                  Preparando tu biblioteca personalizada...
                </p>
              </div>
            ) : error ? (
              <div className="p-4 rounded-xl bg-red-50 dark:bg-red-950/50 text-red-700 dark:text-red-300 text-sm">
                {error}
              </div>
            ) : (
              <>
                {/* PASO 1: Géneros favoritos */}
                {step === 1 && (
                  <div className="space-y-4">
                    <p className="text-sm text-slate-600 dark:text-slate-300">
                      Selecciona las temáticas que más disfrutas. Las utilizaremos para recomendarte
                      nuevos títulos desde el primer instante:
                    </p>

                    <div className="flex flex-wrap gap-2.5 pt-2">
                      {availableCategories.map((cat) => {
                        const isSelected = selectedCategoryIds.includes(cat.id);
                        const icon = CATEGORY_ICONS[cat.slug] || '📖';

                        return (
                          <button
                            key={cat.id}
                            type="button"
                            onClick={() => toggleCategory(cat.id)}
                            className={`px-3.5 py-2 rounded-2xl text-xs font-semibold flex items-center gap-2 border transition-all cursor-pointer select-none ${
                              isSelected
                                ? 'bg-teal-600 text-white border-teal-600 shadow-md shadow-teal-500/20 scale-[1.02]'
                                : 'bg-slate-50 dark:bg-slate-800/80 hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300 border-slate-200 dark:border-slate-700/80 hover:border-teal-400'
                            }`}
                          >
                            <span>{icon}</span>
                            <span>{cat.name}</span>
                            {isSelected && <span className="text-[10px]">✓</span>}
                          </button>
                        );
                      })}
                    </div>

                    <div className="pt-4 flex items-center justify-between text-xs text-slate-400">
                      <span>{selectedCategoryIds.length} géneros seleccionados</span>
                      {selectedCategoryIds.length === 0 && (
                        <span className="text-amber-500 font-medium">
                          Selecciona al menos 1 para mejores recomendaciones
                        </span>
                      )}
                    </div>
                  </div>
                )}

                {/* PASO 2: Primeros libros / Importar de Goodreads */}
                {step === 2 && (
                  <div className="space-y-5">
                    {/* Banner destacado de importación */}
                    <div className="p-4 rounded-2xl bg-gradient-to-r from-teal-500/10 via-emerald-500/10 to-transparent border border-teal-200 dark:border-teal-800/60 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
                      <div>
                        <h4 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
                          <span>📦</span> ¿Ya tienes historial en Goodreads o StoryGraph?
                        </h4>
                        <p className="text-xs text-slate-600 dark:text-slate-400 mt-0.5">
                          Importa tu archivo CSV con todas tus lecturas y valoraciones en 30 segundos.
                        </p>
                      </div>
                      <button
                        type="button"
                        onClick={() => setIsImportModalOpen(true)}
                        className="px-3.5 py-2 bg-teal-600 hover:bg-teal-700 text-white rounded-xl text-xs font-semibold transition-colors shadow-sm whitespace-nowrap cursor-pointer"
                      >
                        Importar CSV
                      </button>
                    </div>

                    <div>
                      <h4 className="text-sm font-bold text-slate-800 dark:text-slate-200 mb-2">
                        O marca algunos de estos libros populares para arrancar:
                      </h4>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                        {suggestedBooks.slice(0, 6).map((book) => {
                          const userSelection = selectedBooks.find((b) => b.book_id === book.id);

                          return (
                            <div
                              key={book.id}
                              className="p-3 rounded-2xl border border-slate-200 dark:border-slate-800 bg-slate-50/60 dark:bg-slate-800/40 flex items-center justify-between gap-3"
                            >
                              <div className="flex items-center gap-2.5 overflow-hidden">
                                {book.cover ? (
                                  <img
                                    src={book.cover}
                                    alt={book.title}
                                    className="w-10 h-14 object-cover rounded-lg shadow-xs flex-shrink-0"
                                  />
                                ) : (
                                  <div className="w-10 h-14 bg-slate-200 dark:bg-slate-700 rounded-lg flex items-center justify-center text-xs text-slate-400 flex-shrink-0">
                                    📖
                                  </div>
                                )}
                                <div className="truncate">
                                  <p className="text-xs font-bold text-slate-900 dark:text-white truncate">
                                    {book.title}
                                  </p>
                                  <p className="text-[11px] text-slate-500 dark:text-slate-400 truncate">
                                    {book.author_name}
                                  </p>
                                </div>
                              </div>

                              <div className="flex items-center gap-1.5 flex-shrink-0">
                                <button
                                  type="button"
                                  title="Marcar como ya leído"
                                  onClick={() => toggleBookSelection(book.id, 'read')}
                                  className={`px-2 py-1 rounded-lg text-[10px] font-bold transition-colors cursor-pointer ${
                                    userSelection?.status === 'read'
                                      ? 'bg-emerald-600 text-white'
                                      : 'bg-slate-200 dark:bg-slate-700 hover:bg-emerald-100 text-slate-700 dark:text-slate-300'
                                  }`}
                                >
                                  Leído
                                </button>
                                <button
                                  type="button"
                                  title="Quiero leerlo"
                                  onClick={() => toggleBookSelection(book.id, 'want_to_read')}
                                  className={`px-2 py-1 rounded-lg text-[10px] font-bold transition-colors cursor-pointer ${
                                    userSelection?.status === 'want_to_read'
                                      ? 'bg-teal-600 text-white'
                                      : 'bg-slate-200 dark:bg-slate-700 hover:bg-teal-100 text-slate-700 dark:text-slate-300'
                                  }`}
                                >
                                  Por leer
                                </button>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  </div>
                )}

                {/* PASO 3: Perfil y Primera Recomendación */}
                {step === 3 && (
                  <div className="space-y-5">
                    {firstRec ? (
                      <div className="p-5 rounded-2xl bg-teal-50/80 dark:bg-teal-950/40 border border-teal-200 dark:border-teal-800 text-center space-y-3">
                        <span className="text-2xl">🎉</span>
                        <h3 className="text-base font-bold text-teal-950 dark:text-teal-200">
                          ¡Tu primera recomendación está lista!
                        </h3>
                        <div className="max-w-md mx-auto p-4 rounded-xl bg-white dark:bg-slate-900 border border-teal-100 dark:border-teal-900/60 shadow-xs flex items-center gap-4 text-left">
                          {firstRec.cover ? (
                            <img
                              src={firstRec.cover}
                              alt={firstRec.title}
                              className="w-14 h-20 object-cover rounded-lg shadow-xs flex-shrink-0"
                            />
                          ) : (
                            <div className="w-14 h-20 bg-slate-200 dark:bg-slate-800 rounded-lg flex items-center justify-center text-xl flex-shrink-0">
                              📚
                            </div>
                          )}
                          <div>
                            <h4 className="text-sm font-bold text-slate-900 dark:text-white line-clamp-1">
                              {firstRec.title}
                            </h4>
                            <p className="text-xs text-slate-500 dark:text-slate-400">
                              {firstRec.author_name}
                            </p>
                            <span className="inline-block mt-1 text-[11px] font-semibold text-teal-600 dark:text-teal-400 bg-teal-50 dark:bg-teal-950 px-2 py-0.5 rounded-md">
                              {firstRec.reason || 'Recomendado por tus géneros'}
                            </span>
                          </div>
                        </div>
                      </div>
                    ) : (
                      <div className="space-y-4">
                        <div>
                          <label
                            htmlFor="onboarding-bio"
                            className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1"
                          >
                            Preséntate brevemente a la comunidad (opcional):
                          </label>
                          <textarea
                            id="onboarding-bio"
                            rows={3}
                            value={bio}
                            onChange={(e) => setBio(e.target.value)}
                            placeholder="Ej: Devorador de novelas de fantasía y ciencia ficción clásica..."
                            className="w-full text-xs rounded-xl border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-white p-3 focus:ring-teal-500 focus:border-teal-500"
                          />
                        </div>

                        <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-800/40 border border-slate-200 dark:border-slate-700/60 text-xs text-slate-600 dark:text-slate-400">
                          <p>
                            <strong>Resumen de tu selección:</strong> {selectedCategoryIds.length} géneros
                            favoritos y {selectedBooks.length} libros añadidos a tu estantería inicial.
                          </p>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </>
            )}
          </div>

          {/* Footer de navegación */}
          <div className="px-6 py-4 bg-slate-50/80 dark:bg-slate-800/50 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between">
            {step > 1 ? (
              <Button
                color="light"
                size="xs"
                onClick={() => setStep((s) => (s - 1) as any)}
                disabled={submitting || firstRec !== null}
              >
                ← Anterior
              </Button>
            ) : (
              <div />
            )}

            <div className="flex items-center gap-3">
              {step < 3 && (
                <Button
                  color="teal"
                  size="sm"
                  onClick={() => setStep((s) => (s + 1) as any)}
                  disabled={loading}
                >
                  Continuar →
                </Button>
              )}

              {step === 3 && !firstRec && (
                <Button
                  color="teal"
                  size="sm"
                  onClick={handleFinish}
                  disabled={submitting}
                >
                  {submitting ? (
                    <>
                      <Spinner size="xs" className="mr-2" /> Guardando...
                    </>
                  ) : (
                    'Finalizar y descubrir libros'
                  )}
                </Button>
              )}

              {firstRec && (
                <Button color="teal" size="sm" onClick={onClose}>
                  ¡Empezar a explorar!
                </Button>
              )}
            </div>
          </div>
        </div>
      </Modal>

      {/* Modal de importación CSV si el usuario decide importar */}
      {isImportModalOpen && (
        <ImportBooksModal
          isOpen={isImportModalOpen}
          onClose={() => setIsImportModalOpen(false)}
          onSuccess={() => {
            setIsImportModalOpen(false);
            setStep(3);
          }}
        />
      )}
    </>
  );
}

export default OnboardingModal;
