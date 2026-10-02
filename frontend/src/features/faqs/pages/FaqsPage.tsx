import React, { useState, useEffect, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { Spinner } from 'flowbite-react';
import {
  HiOutlineChevronDown,
  HiOutlineSearch,
  HiOutlineQuestionMarkCircle,
  HiOutlineSparkles,
  HiOutlineMail,
  HiOutlineBookOpen,
  HiOutlineUser,
  HiOutlineShieldCheck,
  HiOutlineChatAlt2,
} from 'react-icons/hi';

interface FAQ {
  id: number;
  question: string;
  answer: string;
  category: string;
  order: number;
  created_at: string;
}

const CATEGORY_MAP: Record<string, { label: string; icon: React.ComponentType<{ className?: string }> }> = {
  all: { label: 'Todas las preguntas', icon: HiOutlineSparkles },
  general: { label: 'General', icon: HiOutlineQuestionMarkCircle },
  authors: { label: 'Autores y Perfiles', icon: HiOutlineBookOpen },
  books: { label: 'Libros y Catálogo', icon: HiOutlineBookOpen },
  account: { label: 'Cuenta y Privacidad', icon: HiOutlineShieldCheck },
  community: { label: 'Comunidad y Reseñas', icon: HiOutlineChatAlt2 },
};

export function FaqsPage() {
  const [faqs, setFaqs] = useState<FAQ[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [openIds, setOpenIds] = useState<Set<number>>(new Set());

  const apiUrl = (import.meta as any).env.VITE_API_URL || 'http://localhost:8000';

  useEffect(() => {
    const fetchFaqs = async () => {
      try {
        setLoading(true);
        setError(null);
        const res = await fetch(`${apiUrl}/api/v1/faqs/`);
        if (!res.ok) {
          throw new Error('Error al cargar las preguntas frecuentes');
        }
        const data = await res.json();
        const items = Array.isArray(data) ? data : data.results || [];
        setFaqs(items);
        // Expandir por defecto las dos primeras preguntas si existen
        if (items.length > 0) {
          setOpenIds(new Set([items[0].id]));
        }
      } catch (err: any) {
        console.error('Error fetching FAQs:', err);
        setError(err.message || 'Error al comunicarse con el servidor');
      } finally {
        setLoading(false);
      }
    };

    fetchFaqs();
  }, [apiUrl]);

  const toggleAccordion = (id: number) => {
    setOpenIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const filteredFaqs = useMemo(() => {
    return faqs.filter((faq) => {
      const matchesCategory =
        selectedCategory === 'all' || faq.category.toLowerCase() === selectedCategory.toLowerCase();
      const q = searchQuery.toLowerCase().trim();
      const matchesSearch =
        !q ||
        faq.question.toLowerCase().includes(q) ||
        faq.answer.toLowerCase().includes(q);
      return matchesCategory && matchesSearch;
    });
  }, [faqs, selectedCategory, searchQuery]);

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 py-12 px-4 sm:px-6 lg:px-8 transition-colors">
      <div className="max-w-4xl mx-auto space-y-10">
        {/* Header Hero */}
        <div className="text-center space-y-4">
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-teal-100/80 dark:bg-teal-900/40 text-teal-800 dark:text-teal-300 text-xs font-semibold tracking-wide shadow-sm border border-teal-200/60 dark:border-teal-800">
            <HiOutlineSparkles className="w-4 h-4 text-teal-600 dark:text-teal-400" />
            <span>Centro de Ayuda y Soporte</span>
          </div>

          <h1 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold text-slate-900 dark:text-white tracking-tight">
            Preguntas Frecuentes
          </h1>
          <p className="text-base sm:text-lg text-slate-600 dark:text-slate-400 max-w-2xl mx-auto leading-relaxed">
            Encuentra respuestas inmediatas sobre cómo gestionar tu biblioteca, interactuar con autores,
            reclamar tu perfil y sacar el máximo partido a MyBookSocial.
          </p>

          {/* Search Bar */}
          <div className="pt-4 max-w-xl mx-auto">
            <div className="relative">
              <HiOutlineSearch className="w-5 h-5 absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Busca por palabra clave (ej. autor, biblioteca, reseñas, privacidad)..."
                className="w-full pl-11 pr-4 py-3.5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm focus:ring-2 focus:ring-teal-500 focus:border-teal-500 text-slate-900 dark:text-white placeholder-slate-400 text-sm transition-all"
              />
              {searchQuery && (
                <button
                  type="button"
                  onClick={() => setSearchQuery('')}
                  className="absolute right-3.5 top-1/2 -translate-y-1/2 text-xs text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 px-2 py-1 rounded-md"
                >
                  Limpiar
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Category Filter Pills */}
        <div className="flex flex-wrap items-center justify-center gap-2 pt-2">
          {Object.entries(CATEGORY_MAP).map(([key, config]) => {
            const Icon = config.icon;
            const isSelected = selectedCategory === key;
            return (
              <button
                key={key}
                type="button"
                onClick={() => setSelectedCategory(key)}
                className={`inline-flex items-center gap-2 px-4 py-2 rounded-xl text-xs sm:text-sm font-medium transition-all cursor-pointer ${
                  isSelected
                    ? 'bg-teal-600 text-white shadow-md shadow-teal-600/20'
                    : 'bg-white dark:bg-slate-900 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 border border-slate-200/80 dark:border-slate-800'
                }`}
              >
                <Icon className={`w-4 h-4 ${isSelected ? 'text-white' : 'text-slate-400'}`} />
                <span>{config.label}</span>
              </button>
            );
          })}
        </div>

        {/* Content Section */}
        {loading ? (
          <div className="flex flex-col items-center justify-center py-20 space-y-4">
            <Spinner size="xl" className="fill-teal-600" />
            <p className="text-sm text-slate-500 dark:text-slate-400">Cargando preguntas frecuentes...</p>
          </div>
        ) : error ? (
          <div className="p-6 rounded-2xl bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-900/60 text-center space-y-2">
            <p className="text-red-700 dark:text-red-300 font-semibold">{error}</p>
            <p className="text-xs text-red-600 dark:text-red-400">
              Verifica tu conexión o vuelve a intentar en unos instantes.
            </p>
          </div>
        ) : filteredFaqs.length === 0 ? (
          <div className="p-12 text-center rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 space-y-4">
            <div className="w-12 h-12 rounded-full bg-slate-100 dark:bg-slate-800 mx-auto flex items-center justify-center text-slate-400">
              <HiOutlineQuestionMarkCircle className="w-6 h-6" />
            </div>
            <h3 className="text-lg font-bold text-slate-900 dark:text-white">
              No encontramos preguntas relacionadas
            </h3>
            <p className="text-sm text-slate-500 dark:text-slate-400 max-w-md mx-auto">
              Intenta cambiar tu término de búsqueda o selecciona otra categoría temática.
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {filteredFaqs.map((faq) => {
              const isOpen = openIds.has(faq.id);
              return (
                <div
                  key={faq.id}
                  className={`group rounded-2xl transition-all duration-200 border overflow-hidden ${
                    isOpen
                      ? 'bg-white dark:bg-slate-900 border-teal-500/50 shadow-md shadow-teal-500/5 ring-1 ring-teal-500/30'
                      : 'bg-white/80 dark:bg-slate-900/80 border-slate-200/80 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700 hover:shadow-sm'
                  }`}
                >
                  <button
                    type="button"
                    onClick={() => toggleAccordion(faq.id)}
                    aria-expanded={isOpen}
                    aria-controls={`faq-answer-${faq.id}`}
                    className="w-full px-6 py-5 text-left flex items-center justify-between gap-4 focus:outline-none focus-visible:ring-2 focus-visible:ring-teal-500"
                  >
                    <div className="space-y-1">
                      <div className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 text-[11px] font-medium uppercase tracking-wider">
                        {CATEGORY_MAP[faq.category.toLowerCase()]?.label || faq.category}
                      </div>
                      <h2 className="text-base sm:text-lg font-bold text-slate-900 dark:text-white pr-2 group-hover:text-teal-600 dark:group-hover:text-teal-400 transition-colors">
                        {faq.question}
                      </h2>
                    </div>

                    <div
                      className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center transition-transform duration-200 ${
                        isOpen
                          ? 'rotate-180 bg-teal-100 dark:bg-teal-900/50 text-teal-700 dark:text-teal-300'
                          : 'bg-slate-100 dark:bg-slate-800 text-slate-400 group-hover:text-slate-600 dark:group-hover:text-slate-300'
                      }`}
                    >
                      <HiOutlineChevronDown className="w-5 h-5" />
                    </div>
                  </button>

                  {/* Accordion Content */}
                  {isOpen && (
                    <div
                      id={`faq-answer-${faq.id}`}
                      role="region"
                      className="px-6 pb-6 pt-1 text-slate-600 dark:text-slate-300 text-sm sm:text-base leading-relaxed border-t border-slate-100 dark:border-slate-800/80 mt-1 whitespace-pre-line animate-fadeIn"
                    >
                      {faq.answer}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {/* Footer Help Banner */}
        <div className="rounded-3xl p-8 bg-gradient-to-br from-teal-700 to-slate-900 text-white shadow-xl flex flex-col sm:flex-row items-center justify-between gap-6">
          <div className="space-y-2 text-center sm:text-left">
            <h3 className="text-xl font-bold flex items-center justify-center sm:justify-start gap-2">
              <HiOutlineMail className="w-5 h-5 text-teal-300" />
              ¿Tienes otra duda que no aparece aquí?
            </h3>
            <p className="text-sm text-teal-100 max-w-lg">
              Nuestro equipo de soporte y la comunidad de lectores están encantados de ayudarte en cualquier momento.
            </p>
          </div>
          <Link
            to="/contact"
            className="inline-flex items-center gap-2 px-6 py-3 rounded-2xl bg-white text-slate-900 font-bold text-sm hover:bg-teal-50 transition-colors shadow-lg hover:shadow-xl cursor-pointer flex-shrink-0"
          >
            <span>Contactar Soporte</span>
          </Link>
        </div>
      </div>
    </div>
  );
}

export default FaqsPage;
