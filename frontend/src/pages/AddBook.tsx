import React, { useState, useEffect } from 'react';
import { useAuthStore } from '../store/auth';
import { Button, Modal, Label, TextInput, Select, FileInput, Textarea } from 'flowbite-react';

export function AddBook() {
  const { token } = useAuthStore();
  const [title, setTitle] = useState('');
  const [authorName, setAuthorName] = useState('');
  const [isbn, setIsbn] = useState('');
  const [description, setDescription] = useState('');
  const [publishedDate, setPublishedDate] = useState('');
  const [coverImage, setCoverImage] = useState<File | null>(null);
  const [search, setSearch] = useState('');
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [format, setFormat] = useState<'digital' | 'fisico'>('digital');
  const [selectedBookId, setSelectedBookId] = useState<number | null>(null);
  const [manualOpen, setManualOpen] = useState(false);
  const [offset, setOffset] = useState(0);
  const [hasMoreResults, setHasMoreResults] = useState(false);

  const handleSearch = async (q: string, currentOffset: number, signal: AbortSignal) => {
    if (!token || q.length < 2) {
      setSearchResults([]);
      return;
    }
    setIsSearching(true);
    try {
      const apiUrl = (import.meta as any).env.VITE_API_URL || 'http://localhost:8000';
      
      if (currentOffset === 0) {
        const res = await fetch(`${apiUrl}/api/v1/books/books/?q=${encodeURIComponent(q)}`, {
          headers: { Authorization: `Bearer ${token}` },
          signal,
        });
        const data = await res.json();
        const localResults = Array.isArray(data) ? data : [];
        if (localResults.length > 0) {
          setSearchResults(localResults);
          setHasMoreResults(false);
          setIsSearching(false);
          return;
        }
      }

      const isIsbn = /\d[\d-]{8,}/.test(q.replace(/\s+/g, ''));
      const importBody = isIsbn ? { isbn: q } : { title: q, offset: currentOffset };
      const importRes = await fetch(`${apiUrl}/api/v1/books/books/import/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(importBody),
        signal,
      });

      if (importRes.ok) {
        const importData = await importRes.json();
        const created = Array.isArray(importData) ? importData : [importData];
        setSearchResults(prev => currentOffset === 0 ? created : [...prev, ...created]);
        setHasMoreResults(created.length === 5);
      } else {
        setSearchResults(prev => currentOffset === 0 ? [] : prev);
        setHasMoreResults(false);
      }
    } catch (err) {
      if ((err as any)?.name !== 'AbortError') {
        console.error(err);
      }
    } finally {
      setIsSearching(false);
    }
  };

  useEffect(() => {
    const controller = new AbortController();
    const run = () => {
      setOffset(0);
      handleSearch(search.trim(), 0, controller.signal);
    };
    const t = setTimeout(run, 300);
    return () => {
      clearTimeout(t);
      controller.abort();
    };
  }, [search, token]);

  const handleLoadMore = () => {
    const newOffset = offset + 5;
    setOffset(newOffset);
    const controller = new AbortController(); // A new controller for this specific call
    handleSearch(search.trim(), newOffset, controller.signal);
  };

  const openConfirmForBook = (bookId: number) => {
    setSelectedBookId(bookId);
    setFormat('digital');
    setConfirmOpen(true);
  };

  const confirmAddToLibrary = async () => {
    if (!token || !selectedBookId) return;
    try {
      const apiUrl = (import.meta as any).env.VITE_API_URL || 'http://localhost:8000';
      const res = await fetch(`${apiUrl}/api/v1/books/user/books/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ book_id: selectedBookId, is_digital: format === 'digital', owned: true }),
      });
      if (!res.ok) {
        const err = await res.text();
        throw new Error(err || 'Error en la creación de UserBook');
      }
      setConfirmOpen(false);
      setSelectedBookId(null);
      alert('Libro añadido a tu biblioteca');
      window.location.href = '/library';
    } catch (err) {
      console.error(err);
      alert('Error añadiendo libro a tu biblioteca');
    }
  };

  const createManualAndAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token) return;
    try {
      const apiUrl = (import.meta as any).env.VITE_API_URL || 'http://localhost:8000';

      const authorRes = await fetch(`${apiUrl}/api/v1/books/authors/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
          body: JSON.stringify({ name: authorName }),
      });
      if (!authorRes.ok) {
          const err = await authorRes.text();
          throw new Error(err || 'No se pudo crear/obtener el autor');
      }
      const author = await authorRes.json();

      const formData = new FormData();
      formData.append('title', title);
      formData.append('author_id', author.id);
      formData.append('isbn', isbn);
      formData.append('description', description);
      if(publishedDate) {
        formData.append('published_date', publishedDate);
      }
      if (coverImage) {
        formData.append('cover', coverImage);
      }

      const bookRes = await fetch(`${apiUrl}/api/v1/books/books/`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });

      if (!bookRes.ok) {
        const err = await bookRes.text();
        throw new Error(err || 'No se pudo crear el libro');
      }
      const book = await bookRes.json();

      const userBookRes = await fetch(`${apiUrl}/api/v1/books/user/books/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ book_id: book.id, is_digital: format === 'digital', owned: true }),
      });
      if (!userBookRes.ok) {
        const err = await userBookRes.text();
        throw new Error(err || 'No se pudo asociar el libro al usuario');
      }
      setManualOpen(false);
      setTitle(''); setAuthorName(''); setIsbn(''); setDescription(''); setPublishedDate(''); setCoverImage(null);
      alert('Libro creado y añadido');
      window.location.href = '/library';
    } catch (err) {
      console.error(err);
      alert('Error creando/añadiendo libro');
    }
  };

  return (
    <div className="max-w-md mx-auto p-4">
      <h2 className="text-xl font-bold mb-4">Añadir libro</h2>
      <div className="mb-6">
        <div className="flex items-center gap-2 mb-4">
            <label htmlFor="searchBook" className="block text-sm font-medium mb-1 flex-grow">Buscar por título o ISBN</label>
            <Button size="xs" color="light" onClick={() => { setManualOpen(true); setFormat('digital'); }}>Añadir manualmente</Button>
        </div>
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
            <div className="border rounded divide-y max-h-96 overflow-auto">
              {searchResults.map((b) => (
                <div key={b.id} className="p-2 flex items-center justify-between gap-3">
                  <div className="min-w-0">
                    <div className="font-medium truncate">{b.title}</div>
                    <div className="text-xs text-gray-600 truncate">
                      {b.author?.name || 'Autor desconocido'} · {b.published_date || 'N/A'}
                    </div>
                    <div className="text-xs text-gray-600 truncate">ISBN: {b.isbn || 'N/A'}</div>
                  </div>
                  <Button size="xs" onClick={() => openConfirmForBook(b.id)}>Añadir</Button>
                </div>
              ))}
              {hasMoreResults && (
                <div className="p-2 text-center">
                  <Button size="xs" color="light" onClick={handleLoadMore} isProcessing={isSearching}>
                    Ver más
                  </Button>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      <Modal show={confirmOpen} onClose={() => setConfirmOpen(false)}>
        <Modal.Header>Confirmar adición</Modal.Header>
        <Modal.Body>
          <div className="space-y-3">
            <Label htmlFor="formatSelect" value="Formato" />
            <Select id="formatSelect" value={format} onChange={(e) => setFormat(e.target.value as 'digital' | 'fisico')}>
              <option value="digital">Digital</option>
              <option value="fisico">Físico</option>
            </Select>
            <p className="text-sm text-gray-600">Se añadirá a tu biblioteca.</p>
          </div>
        </Modal.Body>
        <Modal.Footer>
          <Button onClick={confirmAddToLibrary}>Confirmar</Button>
          <Button color="light" onClick={() => setConfirmOpen(false)}>Cancelar</Button>
        </Modal.Footer>
      </Modal>

      <Modal show={manualOpen} onClose={() => setManualOpen(false)}>
        <Modal.Header>Añadir libro manualmente</Modal.Header>
        <Modal.Body>
          <form id="manualForm" onSubmit={createManualAndAdd} className="space-y-4">
            <div>
              <Label htmlFor="manualTitle" value="Título" />
              <TextInput id="manualTitle" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Título del libro" required />
            </div>
            <div>
              <Label htmlFor="manualAuthor" value="Autor" />
              <TextInput id="manualAuthor" value={authorName} onChange={(e) => setAuthorName(e.target.value)} placeholder="Nombre del autor" required />
            </div>
            <div>
              <Label htmlFor="manualIsbn" value="ISBN" />
              <TextInput id="manualIsbn" value={isbn} onChange={(e) => setIsbn(e.target.value)} placeholder="ISBN" />
            </div>
            <div>
              <Label htmlFor="manualPublishedDate" value="Fecha de Publicación" />
              <TextInput id="manualPublishedDate" type="date" value={publishedDate} onChange={(e) => setPublishedDate(e.target.value)} />
            </div>
            <div>
                <Label htmlFor="manualDescription" value="Descripción" />
                <Textarea id="manualDescription" value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Descripción del libro" />
            </div>
            <div>
              <Label htmlFor="manualCover" value="Portada" />
              <FileInput id="manualCover" onChange={(e) => setCoverImage(e.target.files ? e.target.files[0] : null)} />
            </div>
            <div>
              <Label htmlFor="manualFormat" value="Formato" />
              <Select id="manualFormat" value={format} onChange={(e) => setFormat(e.target.value as 'digital' | 'fisico')}>
                <option value="digital">Digital</option>
                <option value="fisico">Físico</option>
              </Select>
            </div>
          </form>
        </Modal.Body>
        <Modal.Footer>
          <Button type="submit" form="manualForm">Crear y añadir</Button>
          <Button color="light" onClick={() => setManualOpen(false)}>Cancelar</Button>
        </Modal.Footer>
      </Modal>
    </div>
  );
}
