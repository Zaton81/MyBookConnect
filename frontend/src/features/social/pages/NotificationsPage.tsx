import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Spinner, Button, Badge } from 'flowbite-react';
import {
  useNotifications,
  useMarkNotificationRead,
  useMarkAllNotificationsRead,
  useClearReadNotifications,
  useDeleteNotification,
  NotificationItem,
} from '../hooks/useNotificationsQuery';

export const NotificationsPage: React.FC = () => {
  const navigate = useNavigate();
  const [filterTab, setFilterTab] = useState<'all' | 'unread' | 'social' | 'follow'>('all');

  const {
    data: notifications,
    isLoading,
    isError,
    refetch,
  } = useNotifications(filterTab === 'unread' ? { unread: true } : undefined);

  const markReadMutation = useMarkNotificationRead();
  const markAllReadMutation = useMarkAllNotificationsRead();
  const clearReadMutation = useClearReadNotifications();
  const deleteMutation = useDeleteNotification();

  const filteredNotifications = React.useMemo(() => {
    if (!notifications) return [];
    if (filterTab === 'unread') {
      return notifications.filter((n) => !n.read);
    }
    if (filterTab === 'social') {
      return notifications.filter((n) => ['LIKE', 'COMMENT', 'REPLY', 'REVIEW'].includes(n.type));
    }
    if (filterTab === 'follow') {
      return notifications.filter((n) =>
        ['FOLLOW', 'FOLLOW_ACCEPTED', 'LIST_FOLLOW'].includes(n.type)
      );
    }
    return notifications;
  }, [notifications, filterTab]);

  const handleNotificationClick = async (n: NotificationItem) => {
    if (!n.read) {
      await markReadMutation.mutateAsync(n.id);
    }
    if (n.link) {
      navigate(n.link);
    }
  };

  const getNotificationIcon = (type: string) => {
    switch (type) {
      case 'FOLLOW':
      case 'FOLLOW_ACCEPTED':
        return '👤';
      case 'LIKE':
        return '❤️';
      case 'COMMENT':
        return '💬';
      case 'REPLY':
        return '↩️';
      case 'LIST_FOLLOW':
        return '📚';
      case 'RECOMMENDATION':
        return '✨';
      case 'MESSAGE':
        return '✉️';
      default:
        return '📢';
    }
  };

  const unreadCount = notifications ? notifications.filter((n) => !n.read).length : 0;

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900 py-10 px-4 sm:px-6 lg:px-8">
      <div className="max-w-4xl mx-auto space-y-6">
        {/* Cabecera y acciones principales */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-white">
                Centro de Notificaciones
              </h1>
              {unreadCount > 0 && (
                <Badge color="info" size="sm">
                  {unreadCount} nuevas
                </Badge>
              )}
            </div>
            <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
              Todas las interacciones, comentarios, nuevos lectores y recomendaciones en un único
              lugar.
            </p>
          </div>

          <div className="flex items-center gap-2.5">
            <Link
              to="/profile/edit"
              className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold text-slate-700 dark:text-slate-200 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors shadow-sm"
              title="Configurar canales y alertas"
            >
              <span>⚙️</span>
              <span>Preferencias</span>
            </Link>

            {unreadCount > 0 && (
              <Button
                size="xs"
                color="light"
                onClick={() => markAllReadMutation.mutate()}
                disabled={markAllReadMutation.isPending}
                className="rounded-xl font-semibold border-slate-200 dark:border-slate-700"
              >
                Marcar todas leídas
              </Button>
            )}

            <Button
              size="xs"
              color="light"
              onClick={() => clearReadMutation.mutate()}
              disabled={clearReadMutation.isPending}
              className="rounded-xl font-semibold text-rose-600 dark:text-rose-400 hover:text-rose-700 border-slate-200 dark:border-slate-700"
              title="Eliminar del historial las notificaciones ya leídas"
            >
              Limpiar leídas
            </Button>
          </div>
        </div>

        {/* Barra de pestañas */}
        <div className="flex border-b border-slate-200 dark:border-slate-700 space-x-2 overflow-x-auto">
          <button
            onClick={() => setFilterTab('all')}
            className={`pb-3 px-4 text-sm font-semibold border-b-2 whitespace-nowrap transition-colors ${
              filterTab === 'all'
                ? 'border-teal-600 text-teal-600 dark:text-teal-400'
                : 'border-transparent text-slate-500 hover:text-slate-700 dark:text-slate-400'
            }`}
          >
            Todas ({notifications?.length || 0})
          </button>
          <button
            onClick={() => setFilterTab('unread')}
            className={`pb-3 px-4 text-sm font-semibold border-b-2 whitespace-nowrap transition-colors ${
              filterTab === 'unread'
                ? 'border-teal-600 text-teal-600 dark:text-teal-400'
                : 'border-transparent text-slate-500 hover:text-slate-700 dark:text-slate-400'
            }`}
          >
            No leídas ({unreadCount})
          </button>
          <button
            onClick={() => setFilterTab('social')}
            className={`pb-3 px-4 text-sm font-semibold border-b-2 whitespace-nowrap transition-colors ${
              filterTab === 'social'
                ? 'border-teal-600 text-teal-600 dark:text-teal-400'
                : 'border-transparent text-slate-500 hover:text-slate-700 dark:text-slate-400'
            }`}
          >
            ❤️ Interacciones & Reseñas
          </button>
          <button
            onClick={() => setFilterTab('follow')}
            className={`pb-3 px-4 text-sm font-semibold border-b-2 whitespace-nowrap transition-colors ${
              filterTab === 'follow'
                ? 'border-teal-600 text-teal-600 dark:text-teal-400'
                : 'border-transparent text-slate-500 hover:text-slate-700 dark:text-slate-400'
            }`}
          >
            👥 Seguidores & Listas
          </button>
        </div>

        {/* Lista de Notificaciones */}
        <div className="bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 shadow-sm divide-y divide-slate-100 dark:divide-slate-700/60 overflow-hidden">
          {isLoading ? (
            <div className="p-12 flex flex-col items-center justify-center gap-3">
              <Spinner size="lg" color="info" />
              <span className="text-xs text-slate-400">Cargando tus notificaciones...</span>
            </div>
          ) : isError ? (
            <div className="p-8 text-center text-rose-500">
              <p className="text-sm font-medium">Error al cargar las notificaciones.</p>
              <Button size="xs" color="light" onClick={() => refetch()} className="mt-3 mx-auto">
                Reintentar
              </Button>
            </div>
          ) : filteredNotifications.length === 0 ? (
            <div className="p-16 text-center">
              <div className="text-4xl mb-3">🔔</div>
              <h3 className="text-base font-bold text-slate-800 dark:text-slate-200">
                Todo al día
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 max-w-sm mx-auto">
                No tienes notificaciones en esta categoría. Cuando interactúes con la comunidad
                aparecerán aquí.
              </p>
            </div>
          ) : (
            filteredNotifications.map((n) => (
              <div
                key={n.id}
                className={`p-4 sm:p-5 flex items-start gap-4 transition-colors ${
                  !n.read
                    ? 'bg-teal-50/50 dark:bg-teal-900/10 hover:bg-teal-100/40 dark:hover:bg-teal-900/20'
                    : 'hover:bg-slate-50 dark:hover:bg-slate-700/30 opacity-90'
                }`}
              >
                {/* Icono del tipo */}
                <div className="w-10 h-10 rounded-xl bg-slate-100 dark:bg-slate-700 flex items-center justify-center text-lg flex-shrink-0 shadow-inner">
                  {getNotificationIcon(n.type)}
                </div>

                {/* Contenido principal */}
                <div
                  role="button"
                  tabIndex={0}
                  className="flex-1 min-w-0 cursor-pointer text-left"
                  onClick={() => handleNotificationClick(n)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      handleNotificationClick(n);
                    }
                  }}
                >
                  <div className="flex items-center gap-2">
                    <h4 className="text-sm font-bold text-slate-900 dark:text-white truncate">
                      {n.title}
                    </h4>
                    {!n.read && <span className="w-2 h-2 rounded-full bg-teal-500 flex-shrink-0" />}
                  </div>

                  {n.message && (
                    <p className="text-xs text-slate-600 dark:text-slate-300 mt-1 line-clamp-2">
                      {n.message}
                    </p>
                  )}

                  <div className="flex items-center gap-3 mt-2 text-[11px] text-slate-400">
                    <span>{new Date(n.created_at).toLocaleString()}</span>
                    {n.link && (
                      <span className="text-teal-600 dark:text-teal-400 font-medium hover:underline">
                        Ver detalles →
                      </span>
                    )}
                  </div>
                </div>

                {/* Acciones individuales */}
                <div className="flex items-center gap-1 self-center">
                  {!n.read && (
                    <button
                      onClick={() => markReadMutation.mutate(n.id)}
                      className="p-1.5 rounded-lg text-slate-400 hover:text-teal-600 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
                      title="Marcar como leída"
                    >
                      ✓
                    </button>
                  )}
                  <button
                    onClick={() => deleteMutation.mutate(n.id)}
                    className="p-1.5 rounded-lg text-slate-400 hover:text-rose-500 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
                    title="Eliminar notificación"
                  >
                    ✕
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};

export default NotificationsPage;
