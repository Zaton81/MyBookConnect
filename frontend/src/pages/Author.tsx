import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/auth';

export function Author() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { token } = useAuthStore();
  const [author, setAuthor] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token || !id) return;
    const apiUrl = (import.meta as any).env.VITE_API_URL || 'http://localhost:8000';
    setLoading(true);
    fetch(`${apiUrl}/api/v1/books/authors/${id}/`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(async (r) => {
        if (!r.ok) throw new Error('No se pudo cargar el autor');
        return r.json();
      })
      .then(setAuthor)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [id, token]);

  if (!id) return null;

  return (
    <div className="max-w-3xl mx-auto p-4">
      <button onClick={() => navigate(-1)} className="text-teal-700 hover:underline mb-4">Volver</button>
      {loading && <div>Cargando…</div>}
      {error && <div className="text-red-600">{error}</div>}
      {author && (
        <div className="border rounded shadow p-4 space-y-4">
          <div className="flex items-center gap-4">
            {author.photo && (
              <img src={author.photo} alt={author.name} className="w-32 h-32 object-cover rounded-full" />
            )}
            <h1 className="text-2xl font-bold">{author.name}</h1>
          </div>
          {author.biography && (
            <div className="prose max-w-none whitespace-pre-wrap">{author.biography}</div>
          )}
        </div>
      )}
    </div>
  );
}


