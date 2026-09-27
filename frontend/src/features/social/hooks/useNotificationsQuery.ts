import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../../../api/client';
import { queryKeys } from '../../../api/queryKeys';

export type NotificationType =
  | 'FOLLOW'
  | 'FOLLOW_ACCEPTED'
  | 'MESSAGE'
  | 'REVIEW'
  | 'LIKE'
  | 'COMMENT'
  | 'REPLY'
  | 'LIST_FOLLOW'
  | 'RECOMMENDATION'
  | 'SYSTEM';

export interface NotificationItem {
  id: number;
  type: NotificationType;
  title: string;
  message: string;
  link: string;
  read: boolean;
  created_at: string;
  actor?: {
    id: number;
    username: string;
    avatar?: string;
  };
}

export interface NotificationPreferences {
  in_app_follow: boolean;
  in_app_follow_accepted: boolean;
  in_app_like: boolean;
  in_app_comment: boolean;
  in_app_reply: boolean;
  in_app_list: boolean;
  in_app_message: boolean;
  in_app_recommendation: boolean;
  email_follow: boolean;
  email_follow_accepted: boolean;
  email_like: boolean;
  email_comment: boolean;
  email_reply: boolean;
  email_list: boolean;
  email_message: boolean;
  email_recommendation: boolean;
  push_enabled: boolean;
  updated_at?: string;
}

export function useNotifications(params?: { unread?: boolean; type?: string }) {
  return useQuery<NotificationItem[]>({
    queryKey: [...queryKeys.notifications.list(), params],
    queryFn: async () => {
      const searchParams = new URLSearchParams();
      if (params?.unread) searchParams.set('unread', '1');
      if (params?.type) searchParams.set('type', params.type);
      const queryStr = searchParams.toString() ? `?${searchParams.toString()}` : '';
      const res = await api.get(`/api/v1/users/notifications/${queryStr}`);
      return Array.isArray(res) ? res : res?.results || [];
    },
  });
}

export function useNotificationPreferences() {
  return useQuery<NotificationPreferences>({
    queryKey: ['notifications', 'preferences'],
    queryFn: async () => {
      const res = await api.get('/api/v1/users/notifications/preferences/');
      return res as NotificationPreferences;
    },
  });
}

export function useUpdateNotificationPreferences() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (updatedFields: Partial<NotificationPreferences>) => {
      return api.patch('/api/v1/users/notifications/preferences/', updatedFields);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications', 'preferences'] });
    },
  });
}

export function useMarkNotificationRead() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (notificationId: number | string) => {
      return api.post(`/api/v1/users/notifications/${notificationId}/read/`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.notifications.all });
    },
  });
}

export function useMarkAllNotificationsRead() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      return api.post('/api/v1/users/notifications/read-all/');
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.notifications.all });
    },
  });
}

export function useClearReadNotifications() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      return api.post('/api/v1/users/notifications/clear-read/');
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.notifications.all });
    },
  });
}

export function useDeleteNotification() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (notificationId: number | string) => {
      return api.delete(`/api/v1/users/notifications/${notificationId}/`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.notifications.all });
    },
  });
}
