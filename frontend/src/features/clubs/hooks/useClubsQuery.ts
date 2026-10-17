import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { clubService } from '../services/clubService';
import { queryKeys } from '../../../api/queryKeys';

export function useClubs(params?: { q?: string; my_clubs?: boolean }) {
  return useQuery({
    queryKey: queryKeys.clubs.list(params),
    queryFn: () => clubService.getClubs(params),
  });
}

export function useClubDetail(slug?: string) {
  return useQuery({
    queryKey: queryKeys.clubs.detail(slug || ''),
    queryFn: async () => {
      if (!slug) throw new Error('Slug de club requerido');
      return clubService.getClub(slug);
    },
    enabled: Boolean(slug),
  });
}

export function useClubMembers(slug?: string) {
  return useQuery({
    queryKey: queryKeys.clubs.members(slug || ''),
    queryFn: async () => {
      if (!slug) throw new Error('Slug de club requerido');
      return clubService.getMembers(slug);
    },
    enabled: Boolean(slug),
  });
}

export function useClubDiscussions(slug?: string) {
  return useQuery({
    queryKey: queryKeys.clubs.discussions(slug || ''),
    queryFn: async () => {
      if (!slug) throw new Error('Slug de club requerido');
      return clubService.getDiscussions(slug);
    },
    enabled: Boolean(slug),
  });
}

export function useJoinClubMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (slug: string) => clubService.joinClub(slug),
    onSuccess: (_, slug) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.clubs.detail(slug) });
      queryClient.invalidateQueries({ queryKey: queryKeys.clubs.list() });
    },
  });
}

export function useLeaveClubMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (slug: string) => clubService.leaveClub(slug),
    onSuccess: (_, slug) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.clubs.detail(slug) });
      queryClient.invalidateQueries({ queryKey: queryKeys.clubs.list() });
    },
  });
}

export function useCreateClubMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: { name: string; description?: string; is_private?: boolean; rules?: string }) =>
      clubService.createClub(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.clubs.list() });
    },
  });
}
