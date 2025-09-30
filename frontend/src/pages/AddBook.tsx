import React, { useState, useEffect } from 'react';
import { useAuthStore } from '../store/auth';

export function AddBook() {
  const { token } = useAuthStore();
  const [title, setTitle] = useState('');
  const [authorName, setAuthorName] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token) return;

    try {
      // Crear autor (si no existe) y libro simplificado
  const apiUrl = (import.meta as any).env.VITE_API_URL || 'http://localhost:8000';
  const authorRes = await fetch(`${apiUrl}/api/v1/books/authors/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ name: authorName }),
      });
      const author = await authorRes.json();

  const bookRes = await fetch(`${apiUrl}/api/v1/books/books/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ title, author_id: author.id }),
      });
      const book = await bookRes.json();

      // Asociar libro al usuario
  await fetch(`${apiUrl}/api/v1/books/user/books/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ book_id: book.id }),
      });

      alert('Libro añadido');
      setTitle(''); setAuthorName('');
    } catch (err) {
      console.error(err);
      alert('Error añadiendo libro');
    }
  };

  return (
    <div className="max-w-md mx-auto p-4">
      <h2 className="text-xl font-bold mb-4">Añadir libro</h2>
      <form onSubmit={handleSubmit}>
        <div className="mb-4">
          <label>Título</label>
          <input value={title} onChange={(e) => setTitle(e.target.value)} className="w-full" />
        </div>
        <div className="mb-4">
          <label>Autor</label>
          <input value={authorName} onChange={(e) => setAuthorName(e.target.value)} className="w-full" />
        </div>
        <button type="submit" className="px-4 py-2 bg-teal-600 text-white rounded">Añadir</button>
      </form>
    </div>
  );
}
