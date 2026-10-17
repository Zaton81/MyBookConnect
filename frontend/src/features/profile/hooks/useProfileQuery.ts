import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../../../api/client';
import { queryKeys } from '../../../api/queryKeys';
import { User } from '../../../types/auth';

export function useUserProfile(userIdOrUsername?: string | number) {
  return useQuery({
    queryKey: queryKeys.profile.detail(userIdOrUsername || 'me'),
    queryFn: async () => {
      const endpoint =
        userIdOrUsername && userIdOrUsername !== 'me'
          ? `/api/v1/users/${userIdOrUsername}/`
          : '/api/v1/auth/profile/';
      return api.get<User>(endpoint);
    },
  });
}

export function useUserWall(userId?: string | number) {
  return useQuery({
    queryKey: ['profile', 'wall', String(userId || 'me')],
    queryFn: async () => {
      if (!userId) return [];
      const res = await api.get(`/api/v1/users/${userId}/wall/`);
      return Array.isArray(res) ? res : res?.results || [];
    },
    enabled: Boolean(userId),
  });
}

export function useFollowUserMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (userId: number) => api.post(`/api/v1/users/${userId}/follow/`),
    onSuccess: (_, userId) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.social.followStatus(userId) });
      queryClient.invalidateQueries({ queryKey: queryKeys.profile.detail(userId) });
      queryClient.invalidateQueries({ queryKey: queryKeys.social.following() });
    },
  });
}

export function useUnfollowUserMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (userId: number) => api.delete(`/api/v1/users/${userId}/follow/`),
    onSuccess: (_, userId) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.social.followStatus(userId) });
      queryClient.invalidateQueries({ queryKey: queryKeys.profile.detail(userId) });
      queryClient.invalidateQueries({ queryKey: queryKeys.social.following() });
    },
  });
}

export function useUpdateProfileMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: FormData | Partial<User>) =>
      api.patch('/api/v1/auth/profile/update/', data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.users.profile() });
      queryClient.invalidateQueries({ queryKey: queryKeys.profile.all });
    },
  });
}
