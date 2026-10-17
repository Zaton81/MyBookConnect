import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../../../api/client';
import { queryKeys } from '../../../api/queryKeys';

export function useDiscoveryTrending(params?: Record<string, any>) {
  return useQuery({
    queryKey: queryKeys.discovery.trending(params),
    queryFn: async () => {
      const query = new URLSearchParams(params as Record<string, string>).toString();
      const qs = query ? `?${query}` : '';
      const res = await api.get(`/api/v1/books/trending/${qs}`);
      return Array.isArray(res) ? res : res?.results || [];
    },
  });
}

export function useDiscoverySearch(query: string, params?: Record<string, any>) {
  return useQuery({
    queryKey: queryKeys.discovery.search(query, params),
    queryFn: async () => {
      const searchParams = new URLSearchParams({
        q: query,
        ...(params as Record<string, string>),
      }).toString();
      const res = await api.get(`/api/v1/books/search/?${searchParams}`);
      return res;
    },
    enabled: Boolean(query && query.trim().length > 0),
  });
}

export function useDiscoveryRecommendations(params?: {
  strategy?: string;
  limit?: number;
  category?: string;
  length_tier?: string;
  exclude_dismissed?: boolean;
}) {
  return useQuery({
    queryKey: queryKeys.discovery.recommendations(params),
    queryFn: async () => {
      const query = new URLSearchParams(params as Record<string, any>).toString();
      const qs = query ? `?${query}` : '';
      const res = await api.get(`/api/v1/books/recommendations/${qs}`);
      return Array.isArray(res) ? res : res?.results || [];
    },
  });
}

export function useContextualRecommendations(bookId?: string | number) {
  return useQuery({
    queryKey: queryKeys.books.contextual(bookId || ''),
    queryFn: async () => {
      if (!bookId) throw new Error('ID de libro requerido');
      const res = await api.get(`/api/v1/books/${bookId}/recommendations/contextual/`);
      return Array.isArray(res) ? res : res?.results || [];
    },
    enabled: Boolean(bookId),
  });
}

export function useRecommendationFeedbackMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: { book_id: number; action: string; reason?: string }) =>
      api.post('/api/v1/books/recommendations/feedback/', data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.discovery.recommendations() });
      queryClient.invalidateQueries({ queryKey: queryKeys.books.recommended() });
    },
  });
}
