import React from 'react';
import { useNavigate } from 'react-router-dom';
import { resolveMediaUrl } from '../../../utils/media';

export interface FeedItem {
  id: string | number;
  type: string;
  type_display?: string;
  timestamp?: string;
  created_at?: string;
  score?: number;
  feed_signal?: string;
  user: {
    id: number;
    username: string;
    avatar?: string;
  };
  target_user?: {
    id: number;
    username: string;
    avatar?: string;
  };
  metadata?: {
    list_id?: number;
    name?: string;
    privacy?: string;
    rating?: number;
    comment_id?: number;
    review_id?: number;
    status?: string;
    progress?: number;
  };
  book?: {
    id: number;
    title: string;
    cover?: string;
    author_name?: string;
  };
  comment?: string;
  review?: {
    id: number;
    rating?: number;
    text?: string;
  };
  rating?: number;
}

export interface FeedActivityCardProps {
  item: FeedItem;
  currentUserId?: number;
  activeMenuId: string | number | null;
  setActiveMenuId: (id: string | number | null) => void;
  onHideActivity: (id: string | number) => void;
  onMuteUser: (userId: number, username: string) => void;
  onUnfollowUser: (userId: number, username: string) => void;
  onBlockUser: (userId: number, username: string) => void;
  renderStars: (rating: number) => React.ReactNode;
  formatRelativeTime: (dateStr?: string) => string;
  getActivityActionText: (item: FeedItem) => string;
}

export function FeedActivityCard({
  item,
  currentUserId,
  activeMenuId,
  setActiveMenuId,
  onHideActivity,
  onMuteUser,
  onUnfollowUser,
  onBlockUser,
  renderStars,
  formatRelativeTime,
  getActivityActionText,
}: FeedActivityCardProps) {
  const navigate = useNavigate();

  return (
    <div className="bg-white dark:bg-gray-800 rounded-2xl p-5 border border-gray-100 dark:border-gray-700 shadow-sm hover:shadow-md transition-shadow relative">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center space-x-3">
          {item.user.avatar ? (
            <img
              src={resolveMediaUrl(item.user.avatar)}
              alt={item.user.username}
              className="w-10 h-10 rounded-full object-cover cursor-pointer hover:opacity-80 shrink-0"
              onClick={() => navigate(`/users/${item.user.id}`)}
            />
          ) : (
            <div
              onClick={() => navigate(`/users/${item.user.id}`)}
              className="w-10 h-10 rounded-full bg-teal-600 text-white flex items-center justify-center font-bold cursor-pointer hover:bg-teal-700 shrink-0"
            >
              {item.user.username[0]?.toUpperCase()}
            </div>
          )}
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <p className="text-sm text-gray-900 dark:text-white">
                <strong
                  onClick={() => navigate(`/users/${item.user.id}`)}
                  className="cursor-pointer hover:text-teal-600 font-bold"
                >
                  @{item.user.username}
                </strong>{' '}
                <span className="text-gray-500 dark:text-gray-400">
                  {getActivityActionText(item)}
                </span>{' '}
                {item.target_user && (
                  <strong
                    onClick={() => navigate(`/users/${item.target_user?.id}`)}
                    className="cursor-pointer hover:text-teal-600 font-bold"
                  >
                    @{item.target_user.username}
                  </strong>
                )}
              </p>
              {item.feed_signal && (
                <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium bg-teal-50 text-teal-700 dark:bg-teal-950/60 dark:text-teal-300 border border-teal-200/60 dark:border-teal-800/60">
                  {item.feed_signal}
                </span>
              )}
            </div>
            <span className="text-[11px] text-gray-400">
              {formatRelativeTime(item.timestamp || item.created_at)}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          {(item.rating || item.review?.rating) &&
            renderStars(item.rating || item.review?.rating || 0)}

          {/* Menú de Opciones y Controles del Feed */}
          <div className="relative">
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                setActiveMenuId(activeMenuId === item.id ? null : item.id);
              }}
              className="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors cursor-pointer"
              title="Opciones de publicación"
            >
              <span className="text-base font-bold leading-none px-1">⋮</span>
            </button>

            {activeMenuId === item.id && (
              <div
                onClick={(e) => e.stopPropagation()}
                className="absolute right-0 top-8 z-30 w-52 bg-white dark:bg-gray-800 rounded-2xl shadow-xl border border-gray-100 dark:border-gray-700 py-1.5 text-xs divide-y divide-gray-100 dark:divide-gray-700/80 animate-fade-in"
              >
                <div className="py-1">
                  <button
                    type="button"
                    onClick={() => onHideActivity(item.id)}
                    className="w-full text-left px-3.5 py-2 hover:bg-gray-50 dark:hover:bg-gray-700/60 text-gray-700 dark:text-gray-200 flex items-center gap-2 cursor-pointer"
                  >
                    <span>👁️</span>
                    <span>Ocultar esta publicación</span>
                  </button>
                </div>
                {currentUserId && item.user.id !== currentUserId && (
                  <div className="py-1">
                    <button
                      type="button"
                      onClick={() => onMuteUser(item.user.id, item.user.username)}
                      className="w-full text-left px-3.5 py-2 hover:bg-gray-50 dark:hover:bg-gray-700/60 text-gray-700 dark:text-gray-200 flex items-center gap-2 cursor-pointer"
                    >
                      <span>🔇</span>
                      <span>Silenciar a @{item.user.username}</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => onUnfollowUser(item.user.id, item.user.username)}
                      className="w-full text-left px-3.5 py-2 hover:bg-gray-50 dark:hover:bg-gray-700/60 text-gray-700 dark:text-gray-200 flex items-center gap-2 cursor-pointer"
                    >
                      <span>👤</span>
                      <span>Dejar de seguir</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => onBlockUser(item.user.id, item.user.username)}
                      className="w-full text-left px-3.5 py-2 hover:bg-red-50 dark:hover:bg-red-950/40 text-red-600 dark:text-red-400 flex items-center gap-2 cursor-pointer"
                    >
                      <span>🚫</span>
                      <span>Bloquear a @{item.user.username}</span>
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Tarjeta de Lista Creada (LIST_CREATED) */}
      {item.type === 'LIST_CREATED' && item.metadata?.name && (
        <div
          onClick={() => navigate('/lists')}
          className="mt-4 p-3.5 rounded-xl bg-gradient-to-r from-teal-50 to-emerald-50 dark:from-teal-950/40 dark:to-emerald-950/40 hover:from-teal-100 hover:to-emerald-100 dark:hover:from-teal-900/50 dark:hover:to-emerald-900/50 cursor-pointer flex items-center space-x-3 border border-teal-200/60 dark:border-teal-800/60 transition-all shadow-sm"
        >
          <div className="w-10 h-10 rounded-xl bg-teal-600 text-white flex items-center justify-center font-bold text-lg shrink-0 shadow-inner">
            📑
          </div>
          <div className="min-w-0 flex-1">
            <h4 className="font-bold text-sm text-teal-900 dark:text-teal-200 truncate">
              {item.metadata.name}
            </h4>
            <p className="text-xs text-teal-700/80 dark:text-teal-400">
              Colección de libros comunitaria • Explorar listas ➔
            </p>
          </div>
        </div>
      )}

      {item.book && (
        <div
          onClick={() => navigate(`/books/${item.book?.id}`)}
          className="mt-4 p-3 rounded-xl bg-gray-50 dark:bg-gray-700/50 hover:bg-teal-50/50 dark:hover:bg-gray-700 cursor-pointer flex items-center space-x-3 border border-gray-100 dark:border-gray-600/50 transition-colors"
        >
          {item.book.cover ? (
            <img
              src={resolveMediaUrl(item.book.cover)}
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
      )}

      {(item.comment || item.review?.text) && (
        <div className="mt-3 text-sm text-gray-700 dark:text-gray-300 italic bg-gray-50/70 dark:bg-gray-700/30 p-3 rounded-xl border-l-2 border-teal-500">
          "{item.comment || item.review?.text}"
        </div>
      )}
    </div>
  );
}

export default FeedActivityCard;
