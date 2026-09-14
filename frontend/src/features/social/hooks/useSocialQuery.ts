import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../../../api/client';
import { queryKeys } from '../../../api/queryKeys';
import { User } from '../../../types/auth';

export function useHomeFeed(page = 1) {
  return useQuery({
    queryKey: queryKeys.social.feed(page),
    queryFn: async () => {
      return api.get(`/api/v1/feed/?page=${page}`);
    },
  });
}

export function useFollowers(userId?: string | number) {
  return useQuery<User[]>({
    queryKey: queryKeys.social.followers(userId),
    queryFn: async () => {
      const url = userId
        ? `/api/v1/users/${userId}/followers/`
        : '/api/v1/users/followers/';
      const res = await api.get(url);
      return Array.isArray(res) ? res : (res?.results || []);
    },
  });
}

export function useFollowing(userId?: string | number) {
  return useQuery<User[]>({
    queryKey: queryKeys.social.following(userId),
    queryFn: async () => {
      const url = userId
        ? `/api/v1/users/${userId}/following/`
        : '/api/v1/users/following/';
      const res = await api.get(url);
      return Array.isArray(res) ? res : (res?.results || []);
    },
  });
}

export function useFollowStatus(userId?: string | number) {
  return useQuery({
    queryKey: queryKeys.social.followStatus(userId || ''),
    queryFn: async () => {
      if (!userId) return { is_following: false, is_follower: false, is_mutual: false };
      return api.get(`/api/v1/users/${userId}/follow-status/`);
    },
    enabled: Boolean(userId),
  });
}

export function useFollowUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (userId: number | string) => {
      return api.post(`/api/v1/users/${userId}/follow/`);
    },
    onSuccess: (_, userId) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.social.followStatus(userId) });
      queryClient.invalidateQueries({ queryKey: queryKeys.social.following() });
      queryClient.invalidateQueries({ queryKey: queryKeys.users.profile(userId) });
      queryClient.invalidateQueries({ queryKey: queryKeys.users.profile() });
    },
  });
}

export function useUnfollowUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (userId: number | string) => {
      return api.post(`/api/v1/users/${userId}/unfollow/`);
    },
    onSuccess: (_, userId) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.social.followStatus(userId) });
      queryClient.invalidateQueries({ queryKey: queryKeys.social.following() });
      queryClient.invalidateQueries({ queryKey: queryKeys.users.profile(userId) });
      queryClient.invalidateQueries({ queryKey: queryKeys.users.profile() });
    },
  });
}
