export interface FeedFilterTabsProps {
  feedMode: 'smart' | 'chronological';
  feedCategory: 'all' | 'reads' | 'reviews' | 'lists' | 'social';
  feedLoading: boolean;
  onFeedModeChange: (mode: 'smart' | 'chronological') => void;
  onFeedCategoryChange: (category: 'all' | 'reads' | 'reviews' | 'lists' | 'social') => void;
}

export function FeedFilterTabs({
  feedMode,
  feedCategory,
  feedLoading,
  onFeedModeChange,
  onFeedCategoryChange,
}: FeedFilterTabsProps) {
  const categories = [
    { id: 'all', label: '✨ Todo' },
    { id: 'reads', label: '📖 Lecturas' },
    { id: 'reviews', label: '✍️ Reseñas' },
    { id: 'lists', label: '📑 Listas' },
    { id: 'social', label: '👥 Social' },
  ] as const;

  return (
    <div className="space-y-3">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <span>✨</span>
            <span>Muro Social de Lecturas</span>
          </h2>
          <p className="text-xs sm:text-sm text-gray-500 dark:text-gray-400">
            {feedMode === 'smart'
              ? 'Feed inteligente personalizado por tus gustos, lecturas y amigos'
              : 'Actividad social reciente en estricto orden cronológico'}
          </p>
        </div>

        {/* Selector de modo Feed */}
        <div className="inline-flex p-1 bg-gray-100 dark:bg-gray-700/60 rounded-xl border border-gray-200 dark:border-gray-600/50 self-start sm:self-auto shadow-inner">
          <button
            type="button"
            disabled={feedLoading}
            onClick={() => onFeedModeChange('smart')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center gap-1.5 cursor-pointer ${
              feedMode === 'smart'
                ? 'bg-teal-600 text-white shadow-sm'
                : 'text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white'
            }`}
          >
            <span>✨</span>
            <span>Para ti</span>
          </button>
          <button
            type="button"
            disabled={feedLoading}
            onClick={() => onFeedModeChange('chronological')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center gap-1.5 cursor-pointer ${
              feedMode === 'chronological'
                ? 'bg-teal-600 text-white shadow-sm'
                : 'text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white'
            }`}
          >
            <span>🕒</span>
            <span>Cronológico</span>
          </button>
        </div>
      </div>

      {/* Píldoras de filtro por categoría temático */}
      <div className="flex flex-wrap items-center gap-1.5 pb-1">
        {categories.map((cat) => (
          <button
            key={cat.id}
            type="button"
            disabled={feedLoading}
            onClick={() => onFeedCategoryChange(cat.id)}
            className={`px-3 py-1 rounded-full text-xs font-semibold transition-all cursor-pointer ${
              feedCategory === cat.id
                ? 'bg-teal-600 text-white shadow-sm'
                : 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700'
            }`}
          >
            {cat.label}
          </button>
        ))}
      </div>
    </div>
  );
}

export default FeedFilterTabs;
