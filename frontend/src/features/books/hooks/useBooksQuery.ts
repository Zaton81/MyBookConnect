import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../../../api/client';
import { queryKeys } from '../../../api/queryKeys';

export function useBookDetail(bookId?: string | number) {
  return useQuery({
    queryKey: queryKeys.books.detail(bookId || ''),
    queryFn: async () => {
      if (!bookId) throw new Error('ID de libro requerido');
      return api.get(`/api/v1/books/${bookId}/`);
    },
    enabled: Boolean(bookId),
  });
}

export function useAuthorDetail(authorId?: string | number) {
  return useQuery({
    queryKey: queryKeys.books.author(authorId || ''),
    queryFn: async () => {
      if (!authorId) throw new Error('ID de autor requerido');
      return api.get(`/api/v1/authors/${authorId}/`);
    },
    enabled: Boolean(authorId),
  });
}

export function useReadingLists() {
  return useQuery({
    queryKey: queryKeys.books.readingLists(),
    queryFn: async () => {
      const res = await api.get('/api/v1/books/reading-lists/');
      return Array.isArray(res) ? res : (res?.results || []);
    },
  });
}

export function useReadingStats(userId?: string | number) {
  return useQuery({
    queryKey: queryKeys.books.readingStats(userId),
    queryFn: async () => {
      const url = userId
        ? `/api/v1/users/${userId}/reading-stats/`
        : '/api/v1/users/reading-stats/';
      return api.get(url);
    },
  });
}

export function useTrendingBooks() {
  return useQuery({
    queryKey: queryKeys.books.trending(),
    queryFn: async () => {
      const res = await api.get('/api/v1/books/trending/');
      return Array.isArray(res) ? res : (res?.results || []);
    },
  });
}

export function useRecommendedBooks() {
  return useQuery({
    queryKey: queryKeys.books.recommended(),
    queryFn: async () => {
      const res = await api.get('/api/v1/books/recommendations/');
      return Array.isArray(res) ? res : (res?.results || []);
    },
  });
}

export function useCreateReadingList() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: { name: string; description?: string; is_public?: boolean }) => {
      return api.post('/api/v1/books/reading-lists/', data);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.books.readingLists() });
    },
  });
}
