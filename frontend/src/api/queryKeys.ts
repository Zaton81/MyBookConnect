/**
 * Factoría unificada de Query Keys para TanStack React Query.
 * Previene colisiones de cache y garantiza invalidaciones predecibles.
 */
export const queryKeys = {
  books: {
    all: ['books'] as const,
    detail: (id: string | number) => ['books', 'detail', String(id)] as const,
    search: (params?: Record<string, any>) => ['books', 'search', params ?? {}] as const,
    author: (id: string | number) => ['books', 'author', String(id)] as const,
    readingLists: () => ['books', 'reading-lists'] as const,
    readingStats: (userId?: string | number) => ['books', 'reading-stats', userId ? String(userId) : 'me'] as const,
    trending: () => ['books', 'trending'] as const,
    recommended: () => ['books', 'recommended'] as const,
    contextual: (id: string | number) => ['books', 'contextual', String(id)] as const,
  },
  reviews: {
    all: ['reviews'] as const,
    byBook: (bookId: string | number) => ['reviews', 'byBook', String(bookId)] as const,
    detail: (id: string | number) => ['reviews', 'detail', String(id)] as const,
  },
  social: {
    all: ['social'] as const,
    feed: (page?: number) => ['social', 'feed', page ?? 1] as const,
    followers: (userId?: string | number) => ['social', 'followers', userId ? String(userId) : 'me'] as const,
    following: (userId?: string | number) => ['social', 'following', userId ? String(userId) : 'me'] as const,
    followStatus: (userId: string | number) => ['social', 'followStatus', String(userId)] as const,
  },
  users: {
    all: ['users'] as const,
    profile: (userId?: string | number) => ['users', 'profile', userId ? String(userId) : 'me'] as const,
    search: (query: string) => ['users', 'search', query] as const,
  },
  notifications: {
    all: ['notifications'] as const,
    list: () => ['notifications', 'list'] as const,
    unreadCount: () => ['notifications', 'unreadCount'] as const,
  },
  admin: {
    all: ['admin'] as const,
    stats: () => ['admin', 'stats'] as const,
    reports: () => ['admin', 'reports'] as const,
    audit: (page?: number) => ['admin', 'audit', page ?? 1] as const,
  },
} as const;

export default queryKeys;
