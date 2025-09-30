import React, { useEffect, useState } from 'react';
import { useAuthStore } from '../store/auth';

export function Library() {
  const { user, token } = useAuthStore();
  const [books, setBooks] = useState<any[]>([]);

  useEffect(() => {
    if (!token) return;
    // Obtener libros del usuario
    const apiUrl = (import.meta as any).env.VITE_API_URL || 'http://localhost:8000';
    fetch(`${apiUrl}/api/v1/books/user/books/`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(r => r.json())
      .then(setBooks)
      .catch(err => console.error(err));
  }, [token]);

  if (!user) return null;

  return (
    <div className="max-w-4xl mx-auto p-4">
      <h2 className="text-2xl font-bold mb-4">Mi Biblioteca</h2>
      {books.length === 0 ? (
        <p>No tienes libros añadidos.</p>
      ) : (
        <ul>
          {books.map((ub) => (
            <li key={ub.id} className="mb-2">
              {ub.book.title} {ub.is_read ? '(Leído)' : ''}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
