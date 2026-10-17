import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../../../api/client';
import { queryKeys } from '../../../api/queryKeys';

export function useUserBooks(params?: Record<string, any>) {
  return useQuery({
    queryKey: queryKeys.library.userBooks(params),
    queryFn: async () => {
      const qs = params ? `?${new URLSearchParams(params as Record<string, string>).toString()}` : '';
      const res = await api.get(`/api/v1/books/user/books/${qs}`);
      return res;
    },
  });
}

export function useUpdateUserBookMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: Record<string, any> }) =>
      api.patch(`/api/v1/books/user/books/${id}/`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.library.all });
    },
  });
}

export function useDeleteUserBookMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api.delete(`/api/v1/books/user/books/${id}/`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.library.all });
    },
  });
}
