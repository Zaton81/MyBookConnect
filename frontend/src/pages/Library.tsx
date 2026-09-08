import React, { useEffect, useState } from 'react';
import { useAuthStore } from '../store/auth';
import { Button, TextInput, Select } from 'flowbite-react';
import { useNavigate, Link } from 'react-router-dom';

const DEFAULT_PAGE_SIZE = 10;

export function Library() {
  const { user, token } = useAuthStore();
  const [books, setBooks] = useState<any[]>([]);
  const [order, setOrder] = useState('fecha');
  const [filters, setFilters] = useState({
    is_read: '',
    wishlist: '',
    is_digital: '',
    owned: '',
    min_rating: '',
    search: '',
  });
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState<number>(DEFAULT_PAGE_SIZE);
  const [totalCount, setTotalCount] = useState<number>(0);
  const navigate = useNavigate();
  const [selectedBooks, setSelectedBooks] = useState<Set<number>>(new Set());
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    if (!token) return;
    const apiUrl = (import.meta as any).env.VITE_API_URL || 'http://localhost:8000';
    const params = new URLSearchParams();
    if (filters.is_read) params.set('is_read', filters.is_read);
    if (filters.wishlist) params.set('wishlist', filters.wishlist);
    if (filters.is_digital) params.set('is_digital', filters.is_digital);
    if (filters.owned) params.set('owned', filters.owned);
    if (filters.min_rating) params.set('min_rating', String(filters.min_rating));
    if (filters.search) params.set('search', filters.search);
    params.set('page', String(page));
    params.set('page_size', String(pageSize));
    const ordering =
      order === 'fecha' ? '-updated_at' :
      order === 'nota' ? '-rating' :
      order === 'alfabetico' ? 'book__title' :
      order === 'wishlist' ? '-wishlist' :
      order === 'formato' ? '-is_digital' :
      order === 'propiedad' ? '-owned' : '-updated_at';
    params.set('ordering', ordering);

    fetch(`${apiUrl}/api/v1/books/user/books/?${params.toString()}`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(r => r.json())
      .then((data) => {
        const results = data?.results || [];
        const count = data?.count || 0;
        setBooks(results);
        setTotalCount(count);
      })
      .catch(err => console.error(err));
  }, [token, order, filters, page, pageSize, refreshKey]);

  const toggleSelect = (id: number) => {
    const newSet = new Set(selectedBooks);
    if (newSet.has(id)) newSet.delete(id);
    else newSet.add(id);
    setSelectedBooks(newSet);
  };

  const deleteSelected = async () => {
    if (selectedBooks.size === 0) return;
    if (!confirm(`¿Eliminar ${selectedBooks.size} libros?`)) return;

    const apiUrl = (import.meta as any).env.VITE_API_URL || 'http://localhost:8000';
    for (const id of selectedBooks) {
      await fetch(`${apiUrl}/api/v1/books/user/books/${id}/`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      });
    }
    setSelectedBooks(new Set());
    setRefreshKey((k: number) => k + 1);
  };

  if (!user) return null;

  const totalPages = Math.ceil(totalCount / pageSize);

  return (
    <div className="max-w-5xl mx-auto p-4">
      <h2 className="text-2xl font-bold mb-4">Mi Biblioteca</h2>

      <div className="mb-4 flex flex-wrap gap-2 items-center">
        <TextInput placeholder="Buscar título..." value={filters.search} onChange={e => setFilters(f => ({...f, search: e.target.value}))} />

        <Select value={filters.is_read} onChange={e => setFilters(f => ({...f, is_read: e.target.value}))}>
          <option value="">Leído</option>
          <option value="true">Sí</option>
          <option value="false">No</option>
        </Select>

        <Select value={filters.wishlist} onChange={e => setFilters(f => ({...f, wishlist: e.target.value}))}>
          <option value="">Wishlist</option>
          <option value="true">Sí</option>
          <option value="false">No</option>
        </Select>

        <Select value={filters.is_digital} onChange={e => setFilters(f => ({...f, is_digital: e.target.value}))}>
          <option value="">Formato</option>
          <option value="true">Digital</option>
          <option value="false">Físico</option>
        </Select>

        <Select value={filters.owned} onChange={e => setFilters(f => ({...f, owned: e.target.value}))}>
          <option value="">Propiedad</option>
          <option value="true">Lo tengo</option>
          <option value="false">No lo tengo</option>
        </Select>

        <input type="number" min={1} max={10} placeholder="Nota min" value={filters.min_rating} onChange={e => setFilters(f => ({...f, min_rating: e.target.value}))} className="border rounded px-2 py-2 w-24" />

        <Select value={order} onChange={e => setOrder(e.target.value)}>
          <option value="fecha">Fecha</option>
          <option value="nota">Nota</option>
          <option value="alfabetico">Alfabético</option>
          <option value="wishlist">Wishlist</option>
          <option value="formato">Formato</option>
          <option value="propiedad">Propiedad</option>
        </Select>

        <Select value={String(pageSize)} onChange={e => { setPageSize(Number(e.target.value)); setPage(1); }}>
          <option value="10">10</option>
          <option value="20">20</option>
          <option value="50">50</option>
        </Select>

        {selectedBooks.size > 0 && (
            <Button color="failure" onClick={deleteSelected}>Eliminar ({selectedBooks.size})</Button>
        )}
      </div>
      {books.length === 0 ? (
        <p>No tienes libros añadidos.</p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {books.map((ub) => (
            <div key={ub.id} className="border rounded shadow hover:shadow-lg transition-shadow duration-200 overflow-hidden flex flex-col bg-white relative">
              <div className="absolute top-2 right-2 z-10">
                  <input type="checkbox" checked={selectedBooks.has(ub.id)} onChange={() => toggleSelect(ub.id)} className="w-5 h-5 cursor-pointer" />
              </div>
              <div className="relative h-64 bg-gray-100 flex items-center justify-center overflow-hidden cursor-pointer" onClick={() => navigate(`/books/${ub.book.id}`)}>
                {ub.book.cover ? (
                  <img
                    src={ub.book.cover}
                    alt={`Portada de ${ub.book.title}`}
                    loading="lazy"
                    className="h-full w-full object-cover hover:scale-105 transition-transform duration-300"
                  />
                ) : (
                  <div className="flex flex-col items-center justify-center text-gray-400">
                    <span className="text-sm">Sin portada</span>
                  </div>
                )}
              </div>

              <div className="p-4 flex flex-col flex-grow">
                <div className="font-bold text-lg mb-1 cursor-pointer text-teal-700 hover:underline line-clamp-2" onClick={() => navigate(`/books/${ub.book.id}`)}>
                  {ub.book.title}
                </div>
                <div className="text-sm text-gray-600 mb-2">
                  Autor: {ub.book.author ? (
                    <Link to={`/authors/${ub.book.author.id}`} className="underline cursor-pointer text-teal-700 hover:text-teal-900" onClick={(e) => e.stopPropagation()}>
                      {ub.book.author.name}
                    </Link>
                  ) : (
                    <span>Desconocido</span>
                  )}
                </div>

                <div className="flex flex-wrap gap-2 mb-3">
                  {ub.is_read && <span className="px-2 py-1 bg-green-100 rounded text-green-800 text-xs">Leído</span>}
                  {ub.wishlist && <span className="px-2 py-1 bg-yellow-100 rounded text-yellow-800 text-xs">Wishlist</span>}
                  {ub.is_digital ? <span className="px-2 py-1 bg-blue-100 rounded text-blue-800 text-xs">Digital</span> : <span className="px-2 py-1 bg-purple-100 rounded text-purple-800 text-xs">Físico</span>}
                  {ub.owned && <span className="px-2 py-1 bg-teal-100 rounded text-teal-800 text-xs">Lo tengo</span>}
                </div>

                <div className="mt-auto space-y-1">
                  {ub.rating && (
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium">{ub.rating}/10</span>
                    </div>
                  )}
                  <div className="text-xs text-gray-500">Actualizado: {new Date(ub.updated_at).toLocaleDateString()}</div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
      {totalPages > 1 && (
        <div className="flex gap-2 mt-4 justify-center">
          <Button size="xs" disabled={page === 1} onClick={() => setPage(page - 1)}>Anterior</Button>
          <span className="px-2">Página {page} de {totalPages}</span>
          <Button size="xs" disabled={page === totalPages} onClick={() => setPage(page + 1)}>Siguiente</Button>
        </div>
      )}
    </div>
  );
}
