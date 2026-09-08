const API_URL = (import.meta as any).env.VITE_API_URL || 'http://localhost:8000';

export type ErrataPayload = {
  book_id?: number | null;
  author_id?: number | null;
  type: 'errata' | 'suggestion' | 'other';
  text: string;
};

export async function createErrata(token: string, payload: ErrataPayload) {
  const res = await fetch(`${API_URL}/api/v1/books/erratas/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error('No se pudo enviar la errata');
  return res.json();
}

export async function listErratas(token: string) {
  const res = await fetch(`${API_URL}/api/v1/books/erratas/`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error('No se pudo obtener el listado de erratas');
  return res.json();
}

export async function updateErrata(token: string, id: number, data: Partial<{ status: string; resolution_notes: string; text: string }>) {
  const res = await fetch(`${API_URL}/api/v1/books/erratas/${id}/`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error('No se pudo actualizar la errata');
  return res.json();
}
