import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/auth';

export function BookDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { token } = useAuthStore();
  const [book, setBook] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token || !id) return;
    const apiUrl = (import.meta as any).env.VITE_API_URL || 'http://localhost:8000';
    setLoading(true);
    fetch(`${apiUrl}/api/v1/books/books/${id}/`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(async (r) => {
        if (!r.ok) throw new Error('No se pudo cargar el libro');
        return r.json();
      })
      .then(setBook)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [id, token]);

  if (!id) return null;

  return (
    <div className="max-w-3xl mx-auto p-4">
      <button onClick={() => navigate(-1)} className="text-teal-700 hover:underline mb-4">Volver</button>
      {loading && <div>Cargando…</div>}
      {error && <div className="text-red-600">{error}</div>}
      {book && (
        <div className="border rounded shadow p-4">
          <h1 className="text-2xl font-bold mb-2">{book.title}</h1>
          <div className="text-gray-700 mb-2">Autor: {book.author?.name || 'Desconocido'}</div>
          {book.isbn && <div className="text-gray-700 mb-2">ISBN: {book.isbn}</div>}
          {book.average_rating && <div className="text-gray-700 mb-2">Nota media: {book.average_rating}</div>}
          {book.description && (
            <div className="prose max-w-none" dangerouslySetInnerHTML={{ __html: book.description }} />
          )}
        </div>
      )}
    </div>
  );
}


