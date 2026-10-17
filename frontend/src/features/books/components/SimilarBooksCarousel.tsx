import { useNavigate } from 'react-router-dom';
import { resolveMediaUrl } from '../../../utils/media';

export interface SimilarBookItem {
  id: number;
  title: string;
  cover?: string;
  author_name: string;
  average_rating?: number;
  reason?: string;
}

export interface SimilarBooksCarouselProps {
  books: SimilarBookItem[];
}

export function SimilarBooksCarousel({ books }: SimilarBooksCarouselProps) {
  const navigate = useNavigate();

  if (!books || books.length === 0) return null;

  return (
    <div className="bg-white dark:bg-slate-800 rounded-3xl p-6 border border-slate-100 dark:border-slate-700 shadow-sm space-y-4">
      <div>
        <h3 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
          <span>📚</span>
          <span>Lectores también disfrutaron</span>
        </h3>
        <p className="text-xs text-slate-500 dark:text-slate-400">
          Títulos recomendados por afinidad de autor, temática y co-lecturas de la comunidad
        </p>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-4">
        {books.map((rel) => (
          <div
            key={rel.id}
            onClick={() => navigate(`/books/${rel.id}`)}
            className="group bg-slate-50 dark:bg-slate-900/60 p-3 rounded-2xl border border-slate-200/60 dark:border-slate-700/60 hover:shadow-md hover:border-teal-400 transition-all cursor-pointer flex flex-col justify-between"
          >
            <div>
              <div className="aspect-[2/3] w-full rounded-xl overflow-hidden bg-slate-200 dark:bg-slate-700 mb-2">
                {rel.cover ? (
                  <img
                    src={resolveMediaUrl(rel.cover)}
                    alt={rel.title}
                    className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-200"
                    loading="lazy"
                  />
                ) : (
                  <div className="w-full h-full flex items-center justify-center p-2 text-center text-xs text-slate-400">
                    {rel.title}
                  </div>
                )}
              </div>
              <h4 className="text-xs font-bold text-slate-900 dark:text-white truncate group-hover:text-teal-600 transition-colors">
                {rel.title}
              </h4>
              <p className="text-[11px] text-slate-500 truncate">{rel.author_name}</p>
              {rel.average_rating && (
                <span className="text-[11px] text-amber-500 font-medium flex items-center gap-1 mt-0.5">
                  ★ {rel.average_rating.toFixed(1)}
                </span>
              )}
            </div>

            {rel.reason && (
              <div className="mt-2 pt-1.5 border-t border-slate-200/60 dark:border-slate-800">
                <span className="inline-block text-[10px] text-teal-700 dark:text-teal-300 bg-teal-50 dark:bg-teal-950/40 px-1.5 py-0.5 rounded line-clamp-2">
                  💡 {rel.reason}
                </span>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

export default SimilarBooksCarousel;
