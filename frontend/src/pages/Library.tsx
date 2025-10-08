
import React, { useEffect, useState } from 'react';
import { useAuthStore } from '../store/auth';
import { Button } from 'flowbite-react';
import { useNavigate } from 'react-router-dom';

const DEFAULT_PAGE_SIZE = 10;

export function Library() {
  const { user, token } = useAuthStore();
  const [books, setBooks] = useState<any[]>([]);
  const [filtered, setFiltered] = useState<any[]>([]);
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
    // paginación
    params.set('page', String(page));
    params.set('page_size', String(pageSize));
    // map order -> ordering
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
        if (Array.isArray(data)) {
          setBooks(data);
          setTotalCount(data.length);
        } else {
          setBooks(data?.results || []);
          setTotalCount(data?.count || 0);
        }
      })
      .catch(err => console.error(err));
  }, [token, order, filters, page, pageSize]);

  useEffect(() => {
    // Backend ya retorna filtrado y ordenado
    setFiltered(books);
    setPage(1);
  }, [books]);

  if (!user) return null;

  // Paginación
  const paginated = filtered.slice((page - 1) * pageSize, page * pageSize);
  const totalPages = Math.ceil((totalCount || filtered.length) / pageSize);

  return (
    <div className="max-w-5xl mx-auto p-4">
      <h2 className="text-2xl font-bold mb-4">Mi Biblioteca</h2>
      <div className="mb-4 flex flex-wrap gap-2">
        <label htmlFor="lib-search" className="sr-only">Buscar título</label>
        <input id="lib-search" type="text" placeholder="Buscar título..." value={filters.search} onChange={e => setFilters(f => ({...f, search: e.target.value}))} className="border rounded px-2 py-1" />
        <label htmlFor="lib-read" className="sr-only">Leído</label>
        <select id="lib-read" value={filters.is_read} onChange={e => setFilters(f => ({...f, is_read: e.target.value}))} className="border rounded px-2 py-1">
          <option value="">Leído</option>
          <option value="true">Sí</option>
          <option value="false">No</option>
        </select>
        <label htmlFor="lib-wishlist" className="sr-only">Wishlist</label>
        <select id="lib-wishlist" value={filters.wishlist} onChange={e => setFilters(f => ({...f, wishlist: e.target.value}))} className="border rounded px-2 py-1">
          <option value="">Wishlist</option>
          <option value="true">Sí</option>
          <option value="false">No</option>
        </select>
        <label htmlFor="lib-format" className="sr-only">Formato</label>
        <select id="lib-format" value={filters.is_digital} onChange={e => setFilters(f => ({...f, is_digital: e.target.value}))} className="border rounded px-2 py-1">
          <option value="">Formato</option>
          <option value="true">Digital</option>
          <option value="false">Físico</option>
        </select>
        <label htmlFor="lib-owned" className="sr-only">Propiedad</label>
        <select id="lib-owned" value={filters.owned} onChange={e => setFilters(f => ({...f, owned: e.target.value}))} className="border rounded px-2 py-1">
          <option value="">Propiedad</option>
          <option value="true">Lo tengo</option>
          <option value="false">No lo tengo</option>
        </select>
        <label htmlFor="lib-min-rating" className="sr-only">Nota mínima</label>
        <input id="lib-min-rating" type="number" min={1} max={10} placeholder="Nota mínima" value={filters.min_rating} onChange={e => setFilters(f => ({...f, min_rating: e.target.value}))} className="border rounded px-2 py-1 w-24" />
        <label htmlFor="lib-order" className="sr-only">Ordenar por</label>
        <select id="lib-order" value={order} onChange={e => setOrder(e.target.value)} className="border rounded px-2 py-1">
          <option value="fecha">Fecha</option>
          <option value="nota">Nota</option>
          <option value="alfabetico">Alfabético</option>
          <option value="wishlist">Wishlist</option>
          <option value="formato">Formato (Digital/Físico)</option>
          <option value="propiedad">Propiedad (Lo tengo)</option>
        </select>
        <label htmlFor="lib-page-size" className="sr-only">Cantidad a mostrar</label>
        <select id="lib-page-size" value={String(pageSize)} onChange={e => { setPageSize(Number(e.target.value)); setPage(1); }} className="border rounded px-2 py-1">
          <option value="10">Mostrar 10</option>
          <option value="20">Mostrar 20</option>
          <option value="50">Mostrar 50</option>
        </select>
      </div>
      {filtered.length === 0 ? (
        <p>No tienes libros añadidos.</p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {paginated.map((ub) => (
            <div key={ub.id} className="border rounded shadow p-4 flex flex-col">
              <div className="font-bold text-lg mb-1 cursor-pointer text-teal-700 hover:underline" onClick={() => navigate(`/books/${ub.book.id}`)}>
                {ub.book.title}
              </div>
              <div className="text-sm text-gray-600 mb-1">Autor: {ub.book.author?.name || 'Desconocido'}</div>
              <div className="flex flex-wrap gap-2 mb-2">
                {ub.is_read && <span className="px-2 py-1 bg-green-100 rounded text-green-800 text-xs">Leído</span>}
                {ub.wishlist && <span className="px-2 py-1 bg-yellow-100 rounded text-yellow-800 text-xs">Wishlist</span>}
                {ub.is_digital ? <span className="px-2 py-1 bg-blue-100 rounded text-blue-800 text-xs">Digital</span> : <span className="px-2 py-1 bg-purple-100 rounded text-purple-800 text-xs">Físico</span>}
                {ub.owned && <span className="px-2 py-1 bg-teal-100 rounded text-teal-800 text-xs">Lo tengo</span>}
              </div>
              <div className="text-xs text-gray-500 mb-1">Última actualización: {new Date(ub.updated_at).toLocaleDateString()}</div>
              <div className="text-xs text-gray-500 mb-1">Nota: {ub.rating ?? 'Sin nota'}</div>
              <div className="text-xs text-gray-500 mb-1">ISBN: {ub.book.isbn || 'N/A'}</div>
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
