import React, { useEffect, useState, useId } from 'react';
import { Link } from 'react-router-dom';
import { clubService } from '../services/clubService';
import { ReadingClub } from '../types';

export const ClubsPage: React.FC = () => {
  const [clubs, setClubs] = useState<ReadingClub[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'all' | 'my'>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  // Form states for creating a club
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [rules, setRules] = useState('');
  const [isPrivate, setIsPrivate] = useState(false);

  const searchInputId = useId();

  const fetchClubs = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await clubService.getClubs({
        q: searchQuery.trim() || undefined,
        my_clubs: activeTab === 'my',
      });
      setClubs(data);
    } catch (err: any) {
      setError(err?.message || 'Error al cargar los clubs de lectura');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchClubs();
  }, [activeTab]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    fetchClubs();
  };

  const handleCreateClub = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;

    try {
      setSubmitting(true);
      const newClub = await clubService.createClub({
        name: name.trim(),
        description: description.trim(),
        rules: rules.trim(),
        is_private: isPrivate,
      });
      setIsModalOpen(false);
      setName('');
      setDescription('');
      setRules('');
      setIsPrivate(false);
      // Actualizar listado
      setClubs((prev) => [newClub, ...prev]);
    } catch (err: any) {
      alert(err?.message || 'Error al crear el club de lectura');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Cabecera */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-gray-200 dark:border-gray-800 pb-6">
        <div>
          <h1 className="text-3xl font-extrabold text-gray-900 dark:text-white tracking-tight">
            Clubs de Lectura y Grupos Literarios
          </h1>
          <p className="mt-2 text-base text-gray-600 dark:text-gray-400">
            Descubre comunidades de lectores, participa en lecturas conjuntas y comparte debates por capítulos.
          </p>
        </div>
        <button
          type="button"
          onClick={() => setIsModalOpen(true)}
          className="inline-flex items-center justify-center px-5 py-2.5 rounded-xl font-medium text-white bg-indigo-600 hover:bg-indigo-700 transition shadow-sm focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
        >
          <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 4v16m8-8H4" />
          </svg>
          Crear Club
        </button>
      </div>

      {/* Pestañas y Búsqueda */}
      <div className="mt-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        {/* WAI-ARIA tablist */}
        <div role="tablist" aria-label="Filtro de clubs" className="flex bg-gray-100 dark:bg-gray-800 p-1 rounded-xl">
          <button
            role="tab"
            id="tab-all"
            aria-selected={activeTab === 'all'}
            aria-controls="panel-clubs"
            onClick={() => setActiveTab('all')}
            className={`px-4 py-2 text-sm font-semibold rounded-lg transition ${
              activeTab === 'all'
                ? 'bg-white dark:bg-gray-700 text-indigo-600 dark:text-indigo-400 shadow-sm'
                : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
            }`}
          >
            Explorar Clubs
          </button>
          <button
            role="tab"
            id="tab-my"
            aria-selected={activeTab === 'my'}
            aria-controls="panel-clubs"
            onClick={() => setActiveTab('my')}
            className={`px-4 py-2 text-sm font-semibold rounded-lg transition ${
              activeTab === 'my'
                ? 'bg-white dark:bg-gray-700 text-indigo-600 dark:text-indigo-400 shadow-sm'
                : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
            }`}
          >
            Mis Clubs
          </button>
        </div>

        {/* Buscador */}
        <form onSubmit={handleSearchSubmit} className="flex gap-2 w-full sm:w-80">
          <label htmlFor={searchInputId} className="sr-only">
            Buscar clubs de lectura
          </label>
          <input
            id={searchInputId}
            type="search"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Buscar por nombre o tema..."
            className="w-full px-4 py-2 text-sm bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-xl text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
          <button
            type="submit"
            className="px-4 py-2 bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-gray-800 dark:text-white rounded-xl text-sm font-medium transition"
          >
            Buscar
          </button>
        </form>
      </div>

      {/* Contenido / Listado */}
      <div id="panel-clubs" role="tabpanel" aria-labelledby={`tab-${activeTab}`} className="mt-8">
        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6" data-testid="clubs-loading">
            {[1, 2, 3].map((i) => (
              <div key={i} className="animate-pulse bg-gray-100 dark:bg-gray-800 rounded-2xl h-56 p-6"></div>
            ))}
          </div>
        ) : error ? (
          <div className="p-4 rounded-xl bg-red-50 dark:bg-red-900/30 text-red-700 dark:text-red-300 text-sm">
            {error}
          </div>
        ) : clubs.length === 0 ? (
          <div className="text-center py-16 bg-gray-50 dark:bg-gray-800/50 rounded-2xl border border-dashed border-gray-300 dark:border-gray-700">
            <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
            </svg>
            <h3 className="mt-4 text-base font-semibold text-gray-900 dark:text-white">
              {activeTab === 'my' ? 'No perteneces a ningún club aún' : 'No se encontraron clubs de lectura'}
            </h3>
            <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
              {activeTab === 'my'
                ? 'Explora la lista de clubs públicos o crea tu propia comunidad literaria.'
                : 'Intenta con otro término de búsqueda o sé el primero en fundar un nuevo club.'}
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6" data-testid="clubs-grid">
            {clubs.map((club) => (
              <div
                key={club.id}
                className="flex flex-col justify-between bg-white dark:bg-gray-800 rounded-2xl border border-gray-200 dark:border-gray-700/80 p-6 shadow-sm hover:shadow-md transition duration-200"
              >
                <div>
                  <div className="flex items-center justify-between gap-2">
                    <span
                      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                        club.is_private
                          ? 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300'
                          : 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300'
                      }`}
                    >
                      {club.is_private ? 'Privado' : 'Público'}
                    </span>
                    <span className="text-xs text-gray-500 dark:text-gray-400">
                      {club.members_count} {club.members_count === 1 ? 'miembro' : 'miembros'}
                    </span>
                  </div>

                  <h2 className="mt-3 text-xl font-bold text-gray-900 dark:text-white line-clamp-1">
                    <Link to={`/clubs/${club.slug}`} className="hover:text-indigo-600 dark:hover:text-indigo-400">
                      {club.name}
                    </Link>
                  </h2>

                  <p className="mt-2 text-sm text-gray-600 dark:text-gray-300 line-clamp-2">
                    {club.description || 'Sin descripción disponible.'}
                  </p>

                  {/* Lectura actual */}
                  {club.current_book && (
                    <div className="mt-4 p-3 bg-gray-50 dark:bg-gray-750 rounded-xl flex items-center gap-3">
                      {club.current_book.cover_image_url ? (
                        <img
                          src={club.current_book.cover_image_url}
                          alt={club.current_book.title}
                          className="w-10 h-14 object-cover rounded shadow-sm"
                        />
                      ) : (
                        <div className="w-10 h-14 bg-indigo-100 dark:bg-indigo-900/50 flex items-center justify-center rounded text-indigo-600 dark:text-indigo-400">
                          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                          </svg>
                        </div>
                      )}
                      <div className="min-w-0 flex-1">
                        <span className="text-[10px] uppercase font-bold tracking-wider text-indigo-600 dark:text-indigo-400">
                          Leyendo ahora
                        </span>
                        <p className="text-xs font-semibold text-gray-900 dark:text-white truncate">
                          {club.current_book.title}
                        </p>
                        {club.current_book.author_name && (
                          <p className="text-xs text-gray-500 dark:text-gray-400 truncate">
                            {club.current_book.author_name}
                          </p>
                        )}
                      </div>
                    </div>
                  )}
                </div>

                <div className="mt-6 pt-4 border-t border-gray-100 dark:border-gray-700/60 flex items-center justify-between">
                  <span className="text-xs text-gray-400 dark:text-gray-500">
                    Por @{club.creator.username}
                  </span>
                  <Link
                    to={`/clubs/${club.slug}`}
                    className="inline-flex items-center text-sm font-semibold text-indigo-600 dark:text-indigo-400 hover:text-indigo-700 dark:hover:text-indigo-300"
                  >
                    Ver club
                    <svg className="w-4 h-4 ml-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5l7 7-7 7" />
                    </svg>
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Modal Crear Club */}
      {isModalOpen && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="create-club-title"
          className="fixed inset-0 z-50 overflow-y-auto bg-black/60 backdrop-blur-sm flex items-center justify-center p-4"
        >
          <div className="bg-white dark:bg-gray-800 rounded-2xl max-w-lg w-full p-6 shadow-xl border border-gray-200 dark:border-gray-700">
            <div className="flex items-center justify-between pb-4 border-b border-gray-100 dark:border-gray-700">
              <h2 id="create-club-title" className="text-xl font-bold text-gray-900 dark:text-white">
                Crear Nuevo Club de Lectura
              </h2>
              <button
                type="button"
                onClick={() => setIsModalOpen(false)}
                className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
              >
                <span className="sr-only">Cerrar</span>
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <form onSubmit={handleCreateClub} className="mt-4 space-y-4">
              <div>
                <label htmlFor="club-name" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Nombre del Club *
                </label>
                <input
                  id="club-name"
                  type="text"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Ej. Club de Novela Fantástica"
                  className="mt-1 w-full px-3 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-xl text-gray-900 dark:text-white focus:ring-2 focus:ring-indigo-500 focus:outline-none text-sm"
                />
              </div>

              <div>
                <label htmlFor="club-description" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Descripción
                </label>
                <textarea
                  id="club-description"
                  rows={3}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="¿De qué trata el club? ¿Qué tipo de libros leen?"
                  className="mt-1 w-full px-3 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-xl text-gray-900 dark:text-white focus:ring-2 focus:ring-indigo-500 focus:outline-none text-sm"
                />
              </div>

              <div>
                <label htmlFor="club-rules" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Reglas o Pautas
                </label>
                <textarea
                  id="club-rules"
                  rows={2}
                  value={rules}
                  onChange={(e) => setRules(e.target.value)}
                  placeholder="Ej. Respeto mutuo, usar etiquetas de spoiler..."
                  className="mt-1 w-full px-3 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-xl text-gray-900 dark:text-white focus:ring-2 focus:ring-indigo-500 focus:outline-none text-sm"
                />
              </div>

              <div className="flex items-center gap-3 pt-2">
                <input
                  type="checkbox"
                  id="is-private"
                  checked={isPrivate}
                  onChange={(e) => setIsPrivate(e.target.checked)}
                  className="h-4 w-4 text-indigo-600 focus:ring-indigo-500 rounded border-gray-300 dark:border-gray-600"
                />
                <label htmlFor="is-private" className="text-sm text-gray-700 dark:text-gray-300 font-medium">
                  Club Privado (requiere que el administrador apruebe a los nuevos miembros)
                </label>
              </div>

              <div className="mt-6 flex items-center justify-end gap-3 pt-4 border-t border-gray-100 dark:border-gray-700">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-xl transition"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={submitting || !name.trim()}
                  className="px-5 py-2 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 rounded-xl transition shadow disabled:opacity-50"
                >
                  {submitting ? 'Creando...' : 'Crear Club'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
