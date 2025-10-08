import React, { useState, useEffect } from 'react';
import { useAuthStore } from '../store/auth';
import { Button } from 'flowbite-react';

export function AddBook() {
  const { token } = useAuthStore();
  const [title, setTitle] = useState('');
  const [authorName, setAuthorName] = useState('');
  const [search, setSearch] = useState('');
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [isSearching, setIsSearching] = useState(false);

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

  // Búsqueda por título o ISBN
  useEffect(() => {
    const controller = new AbortController();
    const run = async () => {
      const q = search.trim();
      if (!token || q.length < 2) {
        setSearchResults([]);
        return;
      }
      setIsSearching(true);
      try {
        const apiUrl = (import.meta as any).env.VITE_API_URL || 'http://localhost:8000';
        const res = await fetch(`${apiUrl}/api/v1/books/books/?q=${encodeURIComponent(q)}`, {
          headers: { Authorization: `Bearer ${token}` },
          signal: controller.signal,
        });
        const data = await res.json();
        setSearchResults(Array.isArray(data) ? data : []);
      } catch (err) {
        if ((err as any)?.name !== 'AbortError') {
          console.error(err);
        }
      } finally {
        setIsSearching(false);
      }
    };
    const t = setTimeout(run, 300);
    return () => { clearTimeout(t); controller.abort(); };
  }, [search, token]);

  const addExistingToLibrary = async (bookId: number) => {
    if (!token) return;
    try {
      const apiUrl = (import.meta as any).env.VITE_API_URL || 'http://localhost:8000';
      await fetch(`${apiUrl}/api/v1/books/user/books/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ book_id: bookId }),
      });
      alert('Libro añadido a tu biblioteca');
    } catch (err) {
      console.error(err);
      alert('Error añadiendo libro a tu biblioteca');
    }
  };

  return (
    <div className="max-w-md mx-auto p-4">
      <h2 className="text-xl font-bold mb-4">Añadir libro</h2>
      <div className="mb-6">
        <label htmlFor="searchBook" className="block text-sm font-medium mb-1">Buscar por título o ISBN</label>
        <input
          id="searchBook"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="p. ej. Dune o 9788497596825"
          className="w-full border rounded px-3 py-2"
        />
        <div className="mt-2">
          {isSearching && <div className="text-sm text-gray-500">Buscando…</div>}
          {!isSearching && searchResults.length > 0 && (
            <div className="border rounded divide-y max-h-64 overflow-auto">
              {searchResults.map((b) => (
                <div key={b.id} className="p-2 flex items-center justify-between gap-3">
                  <div className="min-w-0">
                    <div className="font-medium truncate">{b.title}</div>
                    <div className="text-xs text-gray-600 truncate">{b.author?.name || 'Autor desconocido'} · ISBN: {b.isbn || 'N/A'}</div>
                  </div>
                  <Button size="xs" onClick={() => addExistingToLibrary(b.id)}>Añadir</Button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
      <form onSubmit={handleSubmit}>
        <div className="mb-4">
          <label htmlFor="titleInput">Título</label>
          <input id="titleInput" value={title} onChange={(e) => setTitle(e.target.value)} className="w-full" placeholder="Título del libro" />
        </div>
        <div className="mb-4">
          <label htmlFor="authorInput">Autor</label>
          <input id="authorInput" value={authorName} onChange={(e) => setAuthorName(e.target.value)} className="w-full" placeholder="Nombre del autor" />
        </div>
        <button type="submit" className="px-4 py-2 bg-teal-600 text-white rounded">Crear y añadir</button>
      </form>
    </div>
  );
}
