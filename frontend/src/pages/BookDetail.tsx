import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/auth';
import { Button, Label, Select, Textarea } from 'flowbite-react';
import DOMPurify from 'dompurify';

export function BookDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { token } = useAuthStore();
  const [book, setBook] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [userBook, setUserBook] = useState<any | null>(null);
  const [isDigital, setIsDigital] = useState<boolean>(false);
  const [isRead, setIsRead] = useState<boolean>(false);
  const [rating, setRating] = useState<number | ''>('');
  const [notes, setNotes] = useState<string>('');

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

    // cargar userbook (si existe)
    fetch(`${apiUrl}/api/v1/books/user/books/?search=&ordering=-updated_at`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(r => r.json())
      .then((data) => {
        const results = Array.isArray(data) ? data : data?.results || [];
        const found = results.find((ub: any) => String(ub.book.id) === String(id));
        if (found) {
          setUserBook(found);
          setIsDigital(!!found.is_digital);
          setIsRead(!!found.is_read);
          setRating(found.rating ?? '');
          setNotes(found.notes || '');
        } else {
          setUserBook(null);
        }
      })
      .catch(() => {})
      .finally(() => {});
  }, [id, token]);

  if (!id) return null;

  return (
    <div className="max-w-3xl mx-auto p-4">
      <button onClick={() => navigate(-1)} className="text-teal-700 hover:underline mb-4">Volver</button>
      {loading && <div>Cargando…</div>}
      {error && <div className="text-red-600">{error}</div>}
      {book && (
        <div className="border rounded shadow p-4">
          <div className="flex items-center gap-2 ">
            <img src={book.cover} alt={book.title} className="w-32 h-48 object-cover" />
            <h1 className="text-2xl font-bold mb-2">{book.title}</h1>
          </div>
          <div className="text-green-700 mb-2">Autor: {book.author ? (
            <a className="underline hover:text-teal-700" href={`/authors/${book.author.id}`}>{book.author.name}</a>
          ) : 'Desconocido'}</div>
          {book.isbn && <div className="text-black-700 mb-2">ISBN: {book.isbn}</div>}
          {book.average_rating && <div className="text-red-700 mb-2">Nota media: {book.average_rating}</div>}
          {book.description && (
            <div className="prose max-w-none" dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(book.description) }} />
          )}

          {/* Metadatos del usuario si el libro está en su biblioteca */}
          {userBook ? (
            <div className="mt-6 space-y-3">
              <div>
                <Label htmlFor="formatSelect" value="Formato" />
                <Select id="formatSelect" value={isDigital ? 'digital' : 'fisico'} onChange={(e) => setIsDigital(e.target.value === 'digital')}>
                  <option value="digital">Digital</option>
                  <option value="fisico">Físico</option>
                </Select>
              </div>
              <div className="flex items-center gap-2">
                <input id="isRead" aria-label="Leído" type="checkbox" checked={isRead} onChange={(e) => setIsRead(e.target.checked)} />
                <Label htmlFor="isRead" value="Leído" />
              </div>
              <div>
                <Label htmlFor="ratingInput" value="Nota (1-10)" />
                <input id="ratingInput" aria-label="Nota" type="number" min={1} max={10} value={rating} onChange={(e) => setRating(e.target.value === '' ? '' : Number(e.target.value))} className="border rounded px-2 py-1 w-24" />
              </div>
              <div>
                <Label htmlFor="notesInput" value="Reseña / Notas" />
                <Textarea id="notesInput" rows={4} value={notes} onChange={(e) => setNotes(e.target.value)} />
              </div>
              <div>
                <Button onClick={async () => {
                  if (!token || !userBook) return;
                  const apiUrl = (import.meta as any).env.VITE_API_URL || 'http://localhost:8000';
                  await fetch(`${apiUrl}/api/v1/books/user/books/${userBook.id}/`, {
                    method: 'PATCH',
                    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
                    body: JSON.stringify({ is_digital: isDigital, is_read: isRead, rating: rating === '' ? null : rating, notes })
                  });
                  alert('Guardado');
                }}>Guardar</Button>
              </div>
            </div>
          ) : (
            <div className="mt-4 text-sm text-gray-600">Este libro no está en tu biblioteca.</div>
          )}
        </div>
      )}
    </div>
  );
}