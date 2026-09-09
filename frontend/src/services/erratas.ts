import { api } from '../api/client';

export type ErrataPayload = {
  book_id?: number | null;
  author_id?: number | null;
  type: 'errata' | 'suggestion' | 'other';
  text: string;
};

export async function createErrata(token: string, payload: ErrataPayload) {
  return api.post('/api/v1/books/erratas/', payload, {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function listErratas(token: string) {
  return api.get('/api/v1/books/erratas/', {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function updateErrata(
  token: string,
  id: number,
  data: Partial<{ status: string; resolution_notes: string; text: string }>
) {
  return api.patch(`/api/v1/books/erratas/${id}/`, data, {
    headers: { Authorization: `Bearer ${token}` },
  });
}
