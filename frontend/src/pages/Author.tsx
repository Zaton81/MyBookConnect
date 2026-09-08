import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/auth';
import { createErrata } from '../services/erratas';

export function Author() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { token } = useAuthStore();
  const [author, setAuthor] = useState<any | null>(null);
  const [localBooks, setLocalBooks] = useState<any[]>([]);
  const [externalBooks, setExternalBooks] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [errataText, setErrataText] = useState('');
  const [errataType, setErrataType] = useState<'errata' | 'suggestion' | 'other'>('errata');

  const loadAuthorBooks = (apiUrl: string) => {
    if (!token || !id) return;
    fetch(`${apiUrl}/api/v1/books/authors/${id}/books/`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(r => r.ok ? r.json() : { local: [], external: [] })
      .then((payload) => {
        const local = Array.isArray(payload) ? payload : (payload.local || []);
        const external = Array.isArray(payload) ? [] : (payload.external || []);
        setLocalBooks(local);
        setExternalBooks(external);
      })
      .catch(() => { setLocalBooks([]); setExternalBooks([]); });
  };

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
      .then((data) => {
        if (data?.photo && typeof data.photo === 'string' && data.photo.startsWith('/')) {
          data.photo = `${apiUrl}${data.photo}`;
        }
        setAuthor(data);
        if (Array.isArray(data?.books) && data.books.length) {
          setLocalBooks(data.books);
        }
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));

    loadAuthorBooks(apiUrl);
  }, [id, token]);

  const refreshBooks = () => {
    if (!token || !id) return;
    const apiUrl = (import.meta as any).env.VITE_API_URL || 'http://localhost:8000';
    setLoading(true);
    fetch(`${apiUrl}/api/v1/books/authors/${id}/refresh-books/`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
    })
    .then(r => r.json())
    .then(data => {
        alert(`Se encontraron ${data.count} libros nuevos.`);
        fetch(`${apiUrl}/api/v1/books/authors/${id}/`, {
            headers: { Authorization: `Bearer ${token}` },
        })
        .then(r => r.json())
        .then(setAuthor);
        loadAuthorBooks(apiUrl);
    })
    .catch(console.error)
    .finally(() => setLoading(false));
  };

  if (!id) return null;

  return (
    <div className="max-w-5xl mx-auto p-4">
      <button onClick={() => navigate(-1)} className="text-teal-700 hover:underline mb-4">Volver</button>
      {loading && <div>Cargando…</div>}
      {error && <div className="text-red-600">{error}</div>}
      {author && (
        <div className="space-y-8">
          <div className="border rounded shadow p-4 space-y-4">
            <div className="flex items-center gap-4">
              {author.photo && (
                <img src={author.photo} alt={author.name} className="w-32 h-32 object-cover rounded-full" />
              )}
              <h1 className="text-2xl font-bold">{author.name}</h1>
              {token && (
                <button onClick={refreshBooks} className="ml-auto text-sm bg-teal-600 text-white px-3 py-1 rounded hover:bg-teal-700">
                    Actualizar libros
                </button>
              )}
            </div>
            {author.biography && (
              <div className="prose max-w-none whitespace-pre-wrap">{author.biography}</div>
            )}
          </div>

          <div>
            <h2 className="text-xl font-bold mb-3">Libros en MyBookConnect</h2>
            {localBooks.length === 0 ? (
              <p className="text-gray-600">No hay libros registrados de este autor.</p>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {localBooks.map((book: any) => (
                  <div key={book.id} className="border rounded shadow p-3 hover:shadow-lg cursor-pointer transition-shadow" onClick={() => navigate(`/books/${book.id}`)}>
                    {book.cover && (
                      <img src={typeof book.cover === 'string' && book.cover.startsWith('/') ? `${(import.meta as any).env.VITE_API_URL || 'http://localhost:8000'}${book.cover}` : book.cover} alt={book.title} className="w-full h-40 object-cover rounded mb-2" />
                    )}
                    <div className="font-semibold text-teal-700 line-clamp-2">{book.title}</div>
                    {book.published_date && <div className="text-sm text-gray-600">{new Date(book.published_date).getFullYear?.() ? new Date(book.published_date).getFullYear() : String(book.published_date)}</div>}
                  </div>
                ))}
              </div>
            )}
          </div>

          {externalBooks.length > 0 && (
            <div>
              <h2 className="text-xl font-bold mb-3">También te puede interesar</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {externalBooks.map((book: any) => (
                  <div key={book.id} className="border rounded shadow p-3">
                    {book.cover && (
                      <img src={book.cover} alt={book.title} className="w-full h-40 object-cover rounded mb-2" />
                    )}
                    <div className="font-semibold line-clamp-2">{book.title}</div>
                    {book.published_date && <div className="text-sm text-gray-600">{book.published_date}</div>}
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="border-t pt-4">
            <h3 className="font-semibold mb-2">¿Algún dato del autor incorrecto?</h3>
            <div className="flex gap-2 items-center mb-2">
              <label htmlFor="atype" className="text-sm">Tipo:</label>
              <select id="atype" value={errataType} onChange={(e) => setErrataType(e.target.value as any)} className="border rounded px-2 py-1">
                <option value="errata">Errata</option>
                <option value="suggestion">Sugerencia</option>
                <option value="other">Otro</option>
              </select>
            </div>
            <textarea rows={3} className="w-full border rounded p-2" placeholder="Describe el problema..." value={errataText} onChange={(e) => setErrataText(e.target.value)} />
            <div className="mt-2">
              <button className="px-3 py-1 bg-teal-700 text-white rounded" onClick={async () => {
                if (!token || !id || !errataText.trim()) return;
                try {
                  await createErrata(token, { author_id: Number(id), type: errataType, text: errataText.trim() });
                  setErrataText('');
                  alert('Reporte enviado. ¡Gracias!');
                } catch (e) {
                  alert('No se pudo enviar el reporte');
                }
              }}>Enviar reporte</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
