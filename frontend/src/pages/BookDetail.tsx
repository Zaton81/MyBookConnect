import React, { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useAuthStore } from '../store/auth';
import { Button, Label, Select, Textarea } from 'flowbite-react';
import DOMPurify from 'dompurify';
import { createErrata } from '../services/erratas';

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
  const [wishlist, setWishlist] = useState<boolean>(false);
  const [isEditing, setIsEditing] = useState(false);
  const [errataText, setErrataText] = useState<string>('');
  const [errataType, setErrataType] = useState<'errata' | 'suggestion' | 'other'>('errata');

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

    // cargar userbook (si existe) - endpoint optimizado
    fetch(`${apiUrl}/api/v1/books/user/books/by-book/${id}/`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(async (r) => {
        if (r.status === 404) {
          setUserBook(null);
          return;
        }
        if (!r.ok) throw new Error('Error al cargar userbook');
        return r.json();
      })
      .then((found) => {
        if (found) {
          setUserBook(found);
          setIsDigital(!!found.is_digital);
          setIsRead(!!found.is_read);
          setWishlist(!!found.wishlist);
          setRating(found.rating ?? '');
          setNotes(found.notes || '');
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
            <img src={book.cover} alt={book.title} className="w-32 h-48 object-cover" loading="lazy" />
            <h1 className="text-2xl font-bold mb-2">{book.title}</h1>
          </div>
          <div className="text-green-700 mb-2">Autor: {book.author ? (
            <Link className="underline hover:text-teal-700" to={`/authors/${book.author.id}`}>{book.author.name}</Link>
          ) : 'Desconocido'}</div>
          {book.isbn && <div className="text-black-700 mb-2">ISBN: {book.isbn}</div>}
          {book.average_rating && <div className="text-red-700 mb-2">Nota media: {book.average_rating}</div>}
          
          {book.categories && book.categories.length > 0 && (
            <div className="flex gap-2 mb-4">
              {book.categories.map((c: any) => (
                <span key={c.id} className="bg-gray-200 px-2 py-1 rounded text-xs text-gray-700">{c.name}</span>
              ))}
            </div>
          )}

          {book.description && (
            <div className="prose max-w-none" dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(book.description) }} />
          )}

          {/* Metadatos del usuario si el libro está en su biblioteca */}
          {userBook ? (
            <div className="mt-6 space-y-3">
              {!isEditing ? (
                <div className="bg-gray-50 p-4 rounded border">
                  <div className="flex justify-between items-start mb-2">
                    <h3 className="font-bold text-lg text-teal-800">En tu biblioteca</h3>
                    <Button size="xs" color="light" onClick={() => setIsEditing(true)}>Editar</Button>
                  </div>
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <span className="font-semibold">Estado:</span> {isRead ? 'Leído' : 'Pendiente'} {wishlist && <span className="text-xs bg-purple-100 text-purple-800 px-2 py-0.5 rounded ml-2">En lista de deseos</span>}
                    </div>
                    <div>
                      <span className="font-semibold">Formato:</span> {isDigital ? 'Digital' : 'Físico'}
                    </div>
                    <div>
                      <span className="font-semibold">Nota:</span> {rating ? `${rating}/10` : '-'}
                    </div>
                    <div className="col-span-2">
                      <span className="font-semibold">Notas:</span>
                      <p className="mt-1 text-gray-600 whitespace-pre-wrap">{notes || 'Sin notas'}</p>
                    </div>
                  </div>
                  <div className="mt-4 pt-2 border-t flex justify-end">
                     <Button color="failure" size="xs" onClick={async () => {
                        if (!token || !userBook) return;
                        if (!confirm('¿Estás seguro de quitar este libro de tu biblioteca?')) return;
                        const apiUrl = (import.meta as any).env.VITE_API_URL || 'http://localhost:8000';
                        await fetch(`${apiUrl}/api/v1/books/user/books/${userBook.id}/`, {
                          method: 'DELETE',
                          headers: { Authorization: `Bearer ${token}` },
                        });
                        setUserBook(null);
                        alert('Eliminado de la biblioteca');
                      }}>Eliminar de mi biblioteca</Button>
                  </div>
                </div>
              ) : (
                <div className="bg-white p-4 rounded border border-teal-200 shadow-sm">
                  <div className="flex justify-between items-center mb-4">
                    <h3 className="font-bold text-lg">Editar detalles</h3>
                    <Button size="xs" color="gray" onClick={() => setIsEditing(false)}>Cancelar</Button>
                  </div>
                  <div className="space-y-3">
                    <div>
                      <Label htmlFor="formatSelect" value="Formato" />
                      <Select id="formatSelect" value={isDigital ? 'digital' : 'fisico'} onChange={(e) => setIsDigital(e.target.value === 'digital')}>
                        <option value="digital">Digital</option>
                        <option value="fisico">Físico</option>
                      </Select>
                    </div>
                    <div className="flex items-center gap-4">
                        <div className="flex items-center gap-2">
                            <input id="isRead" aria-label="Leído" type="checkbox" checked={isRead} onChange={(e) => setIsRead(e.target.checked)} />
                            <Label htmlFor="isRead" value="Leído" />
                        </div>
                        <div className="flex items-center gap-2">
                            <input id="wishlist" aria-label="Lista de deseos" type="checkbox" checked={wishlist} onChange={(e) => setWishlist(e.target.checked)} />
                            <Label htmlFor="wishlist" value="Lista de deseos" />
                        </div>
                    </div>
                    <div>
                      <Label htmlFor="ratingInput" value="Nota (1-10)" />
                      <input id="ratingInput" aria-label="Nota" type="number" min={1} max={10} value={rating} onChange={(e) => setRating(e.target.value === '' ? '' : Number(e.target.value))} className="border rounded px-2 py-1 w-24" />
                    </div>
                    <div>
                      <Label htmlFor="notesInput" value="Reseña / Notas" />
                      <Textarea id="notesInput" rows={4} value={notes} onChange={(e) => setNotes(e.target.value)} />
                    </div>
                    <div className="flex gap-2 justify-end mt-2">
                      <Button onClick={async () => {
                        if (!token || !userBook) return;
                        const apiUrl = (import.meta as any).env.VITE_API_URL || 'http://localhost:8000';
                        await fetch(`${apiUrl}/api/v1/books/user/books/${userBook.id}/`, {
                          method: 'PATCH',
                          headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
                          body: JSON.stringify({ is_digital: isDigital, is_read: isRead, wishlist: wishlist, rating: rating === '' ? null : rating, notes })
                        });
                        setIsEditing(false);
                      }}>Guardar Cambios</Button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="mt-6 p-4 bg-blue-50 rounded border border-blue-100">
              <p className="text-sm text-blue-800 mb-3">Este libro no está en tu biblioteca.</p>
              <Button onClick={async () => {
                  if (!token) return alert('Debes iniciar sesión');
                  const apiUrl = (import.meta as any).env.VITE_API_URL || 'http://localhost:8000';
                  try {
                      const res = await fetch(`${apiUrl}/api/v1/books/user/books/`, {
                          method: 'POST',
                          headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
                          body: JSON.stringify({ book_id: id })
                      });
                      if (res.ok) {
                          const newUserBook = await res.json();
                          setUserBook(newUserBook);
                          setIsDigital(!!newUserBook.is_digital);
                          setIsRead(!!newUserBook.is_read);
                          setWishlist(!!newUserBook.wishlist);
                          setRating(newUserBook.rating ?? '');
                          setNotes(newUserBook.notes || '');
                      } else {
                          alert('Error al añadir a la biblioteca');
                      }
                  } catch (e) {
                      console.error(e);
                  }
              }}>
                Añadir a mi biblioteca
              </Button>
            </div>
          )}

          {/* Sección de Recomendaciones */}
          <RecommendationsSection bookId={id} token={token} />

          {/* Sección de Reseñas Públicas */}
          <div className="mt-8 pt-6 border-t">
            <h2 className="text-xl font-bold mb-4">Reseñas de la comunidad</h2>
            <ReviewsSection bookId={id} token={token} />
          </div>

          {/* Reportar errata/sugerencia */}
          <div className="mt-8 border-t pt-4">
            <h3 className="font-semibold mb-2">¿Ves algo para corregir? Reporta una errata o sugiere una mejora</h3>
            <div className="flex gap-2 items-center mb-2">
              <label htmlFor="etype" className="text-sm">Tipo:</label>
              <select id="etype" value={errataType} onChange={(e) => setErrataType(e.target.value as any)} className="border rounded px-2 py-1">
                <option value="errata">Errata</option>
                <option value="suggestion">Sugerencia</option>
                <option value="other">Otro</option>
              </select>
            </div>
            <Textarea rows={3} placeholder="Describe el problema o sugerencia..." value={errataText} onChange={(e) => setErrataText(e.target.value)} />
            <div className="mt-2">
              <Button color="light" onClick={async () => {
                if (!token || !id || !errataText.trim()) return;
                try {
                  await createErrata(token, { book_id: Number(id), type: errataType, text: errataText.trim() });
                  setErrataText('');
                  alert('Gracias por tu reporte. Lo revisará un editor.');
                } catch (e) {
                  alert('No se pudo enviar el reporte');
                }
              }}>Enviar reporte</Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function RecommendationsSection({ bookId, token }: { bookId: string, token: string | null }) {
  const [books, setBooks] = useState<any[]>([]);

  useEffect(() => {
    if (!token) return;
    const apiUrl = (import.meta as any).env.VITE_API_URL || 'http://localhost:8000';
    fetch(`${apiUrl}/api/v1/books/books/${bookId}/recommendations/`, {
        headers: { Authorization: `Bearer ${token}` },
    })
      .then(r => r.json())
      .then(data => {
          const list = Array.isArray(data) ? data : (data.results || []);
          setBooks(list);
      })
      .catch(console.error);
  }, [bookId, token]);

  if (books.length === 0) return null;

  return (
    <div className="mt-8 pt-6 border-t">
      <h2 className="text-xl font-bold mb-4">También te podría gustar</h2>
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        {books.map((b) => (
          <div key={b.id} className="border rounded p-2">
             <Link to={`/books/${b.id}`}>
               <img src={b.cover} alt={b.title} className="w-full h-32 object-cover mb-2" />
               <h3 className="text-sm font-bold truncate">{b.title}</h3>
             </Link>
          </div>
        ))}
      </div>
    </div>
  );
}

function ReviewsSection({ bookId, token }: { bookId: string, token: string | null }) {
  const [reviews, setReviews] = useState<any[]>([]);
  const { user: authUser } = useAuthStore();
  const [showAll, setShowAll] = useState(false);
  const [newReviewText, setNewReviewText] = useState('');
  const [newReviewRating, setNewReviewRating] = useState(5);

  const fetchReviews = () => {
    const apiUrl = (import.meta as any).env.VITE_API_URL || 'http://localhost:8000';
    fetch(`${apiUrl}/api/v1/books/reviews/?book=${bookId}`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
      .then(r => r.json())
      .then(data => {
          const res = Array.isArray(data) ? data : data.results || [];
          setReviews(res);
      })
      .catch(console.error);
  };

  useEffect(() => {
    fetchReviews();
  }, [bookId]);

  const handleSubmit = async () => {
      if (!token) return alert('Debes iniciar sesión');
      const apiUrl = (import.meta as any).env.VITE_API_URL || 'http://localhost:8000';
      try {
          const res = await fetch(`${apiUrl}/api/v1/books/reviews/`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
              body: JSON.stringify({ book_id: bookId, rating: newReviewRating, text: newReviewText })
          });
          if (res.ok) {
              setNewReviewText('');
              fetchReviews();
          } else {
              alert('Error al enviar reseña');
          }
      } catch (e) {
          console.error(e);
      }
  };

  const displayedReviews = showAll ? reviews : reviews.slice(0, 5);

  return (
      <div className="space-y-4">
          {/* Formulario */}
          {token && (
              <div className="bg-gray-50 p-4 rounded">
                  <h3 className="font-bold mb-2">Escribe una reseña</h3>
                  <div className="flex gap-4 mb-2">
                      <input type="number" min={1} max={10} value={newReviewRating} onChange={e => setNewReviewRating(Number(e.target.value))} className="border rounded px-2 py-1 w-20" />
                      <textarea className="flex-1 border rounded px-2 py-1" rows={2} placeholder="Tu opinión..." value={newReviewText} onChange={e => setNewReviewText(e.target.value)} />
                  </div>
                  <Button size="xs" onClick={handleSubmit}>Enviar</Button>
              </div>
          )}

          {/* Lista */}
          <div className="space-y-4">
              {displayedReviews.map((r: any) => (
                  <div key={r.id} className="border-b pb-2">
                      <div className="flex justify-between items-start">
                          <div className="flex items-center gap-2">
                              {r.user_avatar && <img src={r.user_avatar} alt={r.user} className="w-6 h-6 rounded-full" />}
                              <div>
                                  {(r.privacy_level === 'public' || r.is_friend || r.user === authUser?.username) ? (
                                      <Link to={`/users/${r.user_id}`} className="font-bold text-sm hover:underline text-teal-700">{r.user}</Link>
                                  ) : (
                                      <span className="font-bold text-sm text-gray-700">{r.user}</span>
                                  )}
                                  
                                  {/* Logic for "Add Friend" or "Private" */}
                                  {r.privacy_level === 'friends' && !r.is_friend && r.user !== authUser?.username && (
                                      <Button size="xs" color="light" className="ml-2 inline-block py-0 px-1 h-6 text-xs" onClick={() => alert('Solicitud de amistad enviada (simulado)')}>
                                          Solicitar amistad
                                      </Button>
                                  )}
                              </div>
                          </div>
                          <span className="text-yellow-600 font-bold">{r.rating}/10</span>
                      </div>
                      <p className="text-gray-700 text-sm mt-1">{r.text}</p>
                      <div className="text-xs text-gray-400 mt-1">{new Date(r.created_at).toLocaleDateString()}</div>
                  </div>
              ))}
              {reviews.length === 0 && <p className="text-gray-500 text-sm">No hay reseñas aún.</p>}
          </div>

          {reviews.length > 5 && (
              <Button color="light" size="xs" onClick={() => setShowAll(!showAll)}>
                  {showAll ? 'Ver menos' : `Ver todas (${reviews.length})`}
              </Button>
          )}
      </div>
  );
}