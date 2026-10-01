import React, { useState, useEffect } from 'react';
import { ToggleSwitch, Spinner, Alert } from 'flowbite-react';
import {
  useNotificationPreferences,
  useUpdateNotificationPreferences,
  NotificationPreferences,
} from '../../social/hooks/useNotificationsQuery';

export const NotificationSettingsSection: React.FC = () => {
  const { data: prefs, isLoading, isError } = useNotificationPreferences();
  const updateMutation = useUpdateNotificationPreferences();

  const [formState, setFormState] = useState<Partial<NotificationPreferences>>({});
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  useEffect(() => {
    if (prefs) {
      setFormState(prefs);
    }
  }, [prefs]);

  const handleToggle = async (key: keyof NotificationPreferences, value: boolean) => {
    const updated = { ...formState, [key]: value };
    setFormState(updated);
    try {
      await updateMutation.mutateAsync({ [key]: value });
      setSuccessMessage('Preferencia actualizada correctamente');
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (e) {
      console.error('Error al actualizar preferencias de notificación:', e);
    }
  };

  if (isLoading) {
    return (
      <div className="flex justify-center p-8">
        <Spinner size="md" color="info" />
      </div>
    );
  }

  if (isError || !prefs) {
    return (
      <Alert color="failure" className="my-4">
        No se pudieron cargar las preferencias de notificación. Inténtalo de nuevo más tarde.
      </Alert>
    );
  }

  const notificationCategories = [
    {
      title: 'Seguimiento social',
      description: 'Cuando otros lectores comienzan a seguirte o aceptan tu solicitud.',
      inAppKey: 'in_app_follow' as keyof NotificationPreferences,
      emailKey: 'email_follow' as keyof NotificationPreferences,
    },
    {
      title: 'Me gusta en reseñas',
      description: 'Cuando a alguien le parece útil o le gusta una de tus reseñas.',
      inAppKey: 'in_app_like' as keyof NotificationPreferences,
      emailKey: 'email_like' as keyof NotificationPreferences,
    },
    {
      title: 'Comentarios y respuestas',
      description: 'Cuando alguien comenta tus reseñas o responde a un comentario previo.',
      inAppKey: 'in_app_comment' as keyof NotificationPreferences,
      emailKey: 'email_comment' as keyof NotificationPreferences,
    },
    {
      title: 'Listas de lectura',
      description: 'Cuando otros lectores siguen, guardan o comentan en tus listas públicas.',
      inAppKey: 'in_app_list' as keyof NotificationPreferences,
      emailKey: 'email_list' as keyof NotificationPreferences,
    },
    {
      title: 'Mensajes directos',
      description: 'Nuevos mensajes recibidos en tus conversaciones privadas de chat.',
      inAppKey: 'in_app_message' as keyof NotificationPreferences,
      emailKey: 'email_message' as keyof NotificationPreferences,
    },
    {
      title: 'Recomendaciones y afinidad',
      description: 'Sugerencias personalizadas de lectura y libros descubiertos por el motor.',
      inAppKey: 'in_app_recommendation' as keyof NotificationPreferences,
      emailKey: 'email_recommendation' as keyof NotificationPreferences,
    },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-bold text-gray-900 dark:text-white">
          Preferencias de Notificaciones
        </h3>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          Personaliza los canales a través de los cuales deseas recibir avisos sobre la actividad de
          la comunidad.
        </p>
      </div>

      {successMessage && (
        <Alert color="success" className="py-2.5 text-xs">
          {successMessage}
        </Alert>
      )}

      <div className="divide-y divide-gray-100 dark:divide-gray-700 border border-gray-200 dark:border-gray-700 rounded-2xl bg-white dark:bg-slate-800 p-5 shadow-sm">
        {notificationCategories.map((cat, idx) => (
          <div
            key={cat.title}
            className={`py-4 flex flex-col md:flex-row md:items-center justify-between gap-4 ${
              idx === 0 ? 'pt-0' : ''
            }`}
          >
            <div className="max-w-md">
              <h4 className="text-sm font-semibold text-gray-900 dark:text-white">{cat.title}</h4>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{cat.description}</p>
            </div>

            <div className="flex items-center gap-6 self-end md:self-center">
              <div className="flex items-center gap-2">
                <span className="text-xs font-medium text-gray-600 dark:text-gray-300">
                  En la app
                </span>
                <ToggleSwitch
                  checked={Boolean(formState[cat.inAppKey])}
                  onChange={(checked) => handleToggle(cat.inAppKey, checked)}
                />
              </div>

              <div className="flex items-center gap-2">
                <span className="text-xs font-medium text-gray-600 dark:text-gray-300">Email</span>
                <ToggleSwitch
                  checked={Boolean(formState[cat.emailKey])}
                  onChange={(checked) => handleToggle(cat.emailKey, checked)}
                />
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="p-4 rounded-xl bg-teal-50/70 dark:bg-teal-900/20 border border-teal-200/60 dark:border-teal-800/40 text-xs text-teal-800 dark:text-teal-300 flex items-start gap-2.5">
        <span className="text-base">🔔</span>
        <div>
          <span className="font-bold">Notificaciones en tiempo real y privacidad:</span> Las
          notificaciones nunca se enviarán si has bloqueado o silenciado a otro usuario,
          garantizando un entorno seguro y libre de molestias.
        </div>
      </div>
    </div>
  );
};
