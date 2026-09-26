import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../../../api/client';
import { queryKeys } from '../../../api/queryKeys';

export function useBookReviews(bookId?: string | number) {
  return useQuery({
    queryKey: queryKeys.reviews.byBook(bookId || ''),
    queryFn: async () => {
      if (!bookId) return [];
      const res = await api.get(`/api/v1/books/${bookId}/reviews/`);
      return Array.isArray(res) ? res : res?.results || [];
    },
    enabled: Boolean(bookId),
  });
}

export function useCreateReview(bookId?: string | number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: { rating: number; title?: string; text?: string }) => {
      if (!bookId) throw new Error('ID de libro requerido');
      return api.post(`/api/v1/books/${bookId}/reviews/`, data);
    },
    onSuccess: () => {
      if (bookId) {
        queryClient.invalidateQueries({ queryKey: queryKeys.reviews.byBook(bookId) });
        queryClient.invalidateQueries({ queryKey: queryKeys.books.detail(bookId) });
      }
    },
  });
}

export function useLikeReview(bookId?: string | number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (reviewId: number | string) => {
      return api.post(`/api/v1/reviews/${reviewId}/like/`);
    },
    onSuccess: () => {
      if (bookId) {
        queryClient.invalidateQueries({ queryKey: queryKeys.reviews.byBook(bookId) });
      }
    },
  });
}

export function useAddReviewComment(bookId?: string | number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ reviewId, content }: { reviewId: number | string; content: string }) => {
      return api.post(`/api/v1/reviews/${reviewId}/comments/`, { content });
    },
    onSuccess: () => {
      if (bookId) {
        queryClient.invalidateQueries({ queryKey: queryKeys.reviews.byBook(bookId) });
      }
    },
  });
}
