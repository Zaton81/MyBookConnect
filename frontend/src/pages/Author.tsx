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

    // Auto-discover books
    fetch(`${apiUrl}/api/v1/books/authors/${id}/refresh-books/`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
    })
    .then(r => r.json())
    .then(data => {
        if (data.count > 0) {
             // Reload author to show new books
             fetch(`${apiUrl}/api/v1/books/authors/${id}/`, {
                headers: { Authorization: `Bearer ${token}` },
            })
            .then(r => r.json())
            .then(setAuthor);
        }
    })
    .catch(console.error);
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

          {author.books && author.books.length > 0 && (
            <div className="mt-8 pt-4 border-t">
              <h2 className="text-xl font-bold mb-4">Libros de {author.name}</h2>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {author.books.map((book: any) => (
                  <div key={book.id} className="cursor-pointer group" onClick={() => navigate(`/books/${book.id}`)}>
                    <div className="aspect-[2/3] overflow-hidden rounded shadow mb-2">
                      {book.cover ? (
                        <img src={book.cover} alt={book.title} className="w-full h-full object-cover group-hover:scale-105 transition-transform" />
                      ) : (
                        <div className="w-full h-full bg-gray-200 flex items-center justify-center text-gray-400">Sin portada</div>
                      )}
                    </div>
                    <div className="font-medium text-sm group-hover:text-teal-700">{book.title}</div>
                    <div className="text-xs text-gray-500">{book.published_date}</div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}


