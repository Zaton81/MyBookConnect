import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../../../api/client';
import { queryKeys } from '../../../api/queryKeys';

export interface NotificationItem {
  id: number;
  verb: string;
  actor?: {
    id: number;
    username: string;
    avatar?: string;
  };
  target_url?: string;
  is_read: boolean;
  created_at: string;
}

export function useNotifications() {
  return useQuery<NotificationItem[]>({
    queryKey: queryKeys.notifications.list(),
    queryFn: async () => {
      const res = await api.get('/api/v1/notifications/');
      return Array.isArray(res) ? res : res?.results || [];
    },
  });
}

export function useMarkNotificationRead() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (notificationId: number | string) => {
      return api.post(`/api/v1/notifications/${notificationId}/read/`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.notifications.all });
    },
  });
}
