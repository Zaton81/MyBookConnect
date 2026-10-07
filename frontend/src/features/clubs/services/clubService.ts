import { apiClient } from '../../../api/client';
import {
  ReadingClub,
  ClubMember,
  ClubBook,
  ClubDiscussion,
  ClubDiscussionComment,
} from '../types';

export const clubService = {
  async getClubs(params?: { q?: string; my_clubs?: boolean }): Promise<ReadingClub[]> {
    const query = new URLSearchParams();
    if (params?.q) query.set('q', params.q);
    if (params?.my_clubs) query.set('my_clubs', 'true');
    const qs = query.toString() ? `?${query.toString()}` : '';
    const res = await apiClient<{ results?: ReadingClub[] } | ReadingClub[]>(`/api/v1/clubs/${qs}`);
    return Array.isArray(res) ? res : res.results || [];
  },

  async getClub(slug: string): Promise<ReadingClub> {
    return apiClient<ReadingClub>(`/api/v1/clubs/${slug}/`);
  },

  async createClub(data: {
    name: string;
    description?: string;
    is_private?: boolean;
    rules?: string;
  }): Promise<ReadingClub> {
    return apiClient<ReadingClub>('/api/v1/clubs/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  async updateClub(slug: string, data: Partial<ReadingClub>): Promise<ReadingClub> {
    return apiClient<ReadingClub>(`/api/v1/clubs/${slug}/`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  },

  async joinClub(slug: string): Promise<{ detail: string; status: string }> {
    return apiClient<{ detail: string; status: string }>(`/api/v1/clubs/${slug}/join/`, {
      method: 'POST',
    });
  },

  async leaveClub(slug: string): Promise<{ detail: string }> {
    return apiClient<{ detail: string }>(`/api/v1/clubs/${slug}/leave/`, {
      method: 'POST',
    });
  },

  async getMembers(slug: string): Promise<ClubMember[]> {
    return apiClient<ClubMember[]>(`/api/v1/clubs/${slug}/members/`);
  },

  async manageMember(
    slug: string,
    userId: number,
    data: { role?: string; status?: string }
  ): Promise<ClubMember> {
    return apiClient<ClubMember>(`/api/v1/clubs/${slug}/members/${userId}/`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  },

  async addReadingBook(
    slug: string,
    data: { book_id: number; status: string; target_milestones?: string }
  ): Promise<ClubBook> {
    return apiClient<ClubBook>(`/api/v1/clubs/${slug}/books/`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  async getDiscussions(slug: string, bookId?: number): Promise<ClubDiscussion[]> {
    const qs = bookId ? `?book_id=${bookId}` : '';
    const res = await apiClient<{ results?: ClubDiscussion[] } | ClubDiscussion[]>(
      `/api/v1/clubs/${slug}/discussions/${qs}`
    );
    return Array.isArray(res) ? res : res.results || [];
  },

  async createDiscussion(
    slug: string,
    data: {
      title: string;
      content: string;
      book_id?: number | null;
      has_spoilers?: boolean;
    }
  ): Promise<ClubDiscussion> {
    return apiClient<ClubDiscussion>(`/api/v1/clubs/${slug}/discussions/`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  async getDiscussion(slug: string, discussionId: number): Promise<ClubDiscussion> {
    return apiClient<ClubDiscussion>(`/api/v1/clubs/${slug}/discussions/${discussionId}/`);
  },

  async getComments(slug: string, discussionId: number): Promise<ClubDiscussionComment[]> {
    return apiClient<ClubDiscussionComment[]>(
      `/api/v1/clubs/${slug}/discussions/${discussionId}/comments/`
    );
  },

  async addComment(
    slug: string,
    discussionId: number,
    data: { content: string; has_spoilers?: boolean }
  ): Promise<ClubDiscussionComment> {
    return apiClient<ClubDiscussionComment>(
      `/api/v1/clubs/${slug}/discussions/${discussionId}/comments/`,
      {
        method: 'POST',
        body: JSON.stringify(data),
      }
    );
  },
};
