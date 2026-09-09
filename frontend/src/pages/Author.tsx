import React, { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useAuthStore } from '../store/auth';
import { createErrata } from '../services/erratas';
import { Spinner } from 'flowbite-react';

export function Author() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { token } = useAuthStore();
  const [author, setAuthor] = useState<any | null>(null);
  const [localBooks, setLocalBooks] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [errataText, setErrataText] = useState('');
  const [errataType, setErrataType] = useState<'errata' | 'suggestion' | 'other'>('errata');
  const [reportSent, setReportSent] = useState(false);

  const apiUrl = (import.meta as any).env.VITE_API_URL || 'http://localhost:8000';

  const loadAuthorData = async () => {
    if (!token || !id) return;
    try {
      setLoading(true);
      setError(null);
      const res = await fetch(`${apiUrl}/api/v1/books/authors/${id}/`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!res.ok) throw new Error('No se pudo cargar la información del autor');

      const data = await res.json();
      if (data?.photo && typeof data.photo === 'string' && data.photo.startsWith('/')) {
        data.photo = `${apiUrl}${data.photo}`;
      }
      setAuthor(data);

      // Cargar libros del autor
      const booksRes = await fetch(`${apiUrl}/api/v1/books/authors/${id}/books/`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (booksRes.ok) {
        const bData = await booksRes.json();
        const bList = Array.isArray(bData) ? bData : bData.local || [];
        setLocalBooks(bList);
      }
    } catch (e: any) {
      console.error(e);
      setError(e.message || 'Error al obtener datos');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAuthorData();
  }, [id, token]);

  const handleRefreshAuthor = async () => {
    if (!token || !id) return;
    setRefreshing(true);
    try {
      await fetch(`${apiUrl}/api/v1/books/authors/${id}/refresh-books/`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
      await loadAuthorData();
    } catch (e) {
      console.error(e);
    } finally {
      setRefreshing(false);
    }
  };

  const handleSendErrata = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token || !id || !errataText.trim()) return;
    try {
      await createErrata(token, {
        author_id: Number(id),
        type: errataType,
        text: errataText.trim(),
      });
      setErrataText('');
      setReportSent(true);
      setTimeout(() => setReportSent(false), 4000);
    } catch (e) {
      alert('No se pudo enviar el reporte.');
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-[50vh]">
        <Spinner size="xl" color="info" />
      </div>
    );
  }

  if (error || !author) {
    return (
      <div className="max-w-2xl mx-auto p-6 bg-white dark:bg-slate-800 rounded-3xl border border-slate-200 dark:border-slate-700 text-center">
        <span className="text-4xl">⚠️</span>
        <h3 className="text-lg font-bold text-slate-900 dark:text-white mt-2">
          {error || 'Autor no encontrado'}
        </h3>
        <button
          onClick={() => navigate(-1)}
          className="mt-4 text-teal-600 hover:underline text-sm font-semibold"
        >
          ← Volver atrás
        </button>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto space-y-8">
      {/* Botón Volver */}
      <button
        onClick={() => navigate(-1)}
        className="inline-flex items-center gap-1.5 text-xs font-bold text-slate-500 hover:text-teal-600 transition-colors"
      >
        <span>←</span>
        <span>Volver</span>
      </button>

      {/* Hero del Autor */}
      <div className="bg-white dark:bg-slate-800 rounded-3xl border border-slate-200/80 dark:border-slate-700 p-6 sm:p-8 shadow-sm relative overflow-hidden">
        <div className="flex flex-col sm:flex-row items-center sm:items-start gap-6">
          {/* Foto de Autor */}
          <div className="relative shrink-0">
            {author.photo ? (
              <img
                src={author.photo}
                alt={author.name}
                className="w-32 h-32 sm:w-40 sm:h-40 rounded-3xl object-cover shadow-lg border-4 border-white dark:border-slate-700"
              />
            ) : (
              <div className="w-32 h-32 sm:w-40 sm:h-40 rounded-3xl bg-gradient-to-tr from-teal-600 to-emerald-700 text-white flex items-center justify-center text-4xl font-extrabold shadow-lg">
                {author.name[0]?.toUpperCase() || 'A'}
              </div>
            )}
          </div>

          {/* Información */}
          <div className="flex-1 text-center sm:text-left space-y-3">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div>
                <span className="text-xs font-bold uppercase tracking-wider text-teal-600 dark:text-teal-400">
                  Escritor / Autor
                </span>
                <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-white tracking-tight">
                  {author.name}
                </h1>
              </div>

              <button
                onClick={handleRefreshAuthor}
                disabled={refreshing}
                className="bg-slate-100 hover:bg-slate-200 dark:bg-slate-700 dark:hover:bg-slate-600 text-slate-700 dark:text-slate-200 font-semibold px-3 py-1.5 rounded-xl text-xs transition-colors flex items-center justify-center gap-1.5 self-center sm:self-auto"
              >
                <span>{refreshing ? '⏳' : '🔄'}</span>
                <span>{refreshing ? 'Actualizando...' : 'Buscar más obras'}</span>
              </button>
            </div>

            {author.biography ? (
              <div className="text-sm text-slate-600 dark:text-slate-300 leading-relaxed max-w-2xl whitespace-pre-line pt-2">
                {author.biography}
              </div>
            ) : (
              <p className="text-xs text-slate-400 italic pt-2">
                Biografía en proceso de recopilación bibliográfica.
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Obras del Autor */}
      <div className="space-y-4">
        <h2 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
          <span>📚</span>
          <span>Obras de {author.name}</span>
          <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-teal-100 text-teal-800 dark:bg-teal-900/40 dark:text-teal-300">
            {localBooks.length}
          </span>
        </h2>

        {localBooks.length === 0 ? (
          <div className="p-8 text-center bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 text-slate-500 text-sm">
            Aún no hay libros catalogados de este autor en MyBookConnect. Haz clic en "Buscar más obras" para descubrirlos.
          </div>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4 sm:gap-6">
            {localBooks.map((book: any) => {
              const coverUrl =
                book.cover && typeof book.cover === 'string' && book.cover.startsWith('/')
                  ? `${apiUrl}${book.cover}`
                  : book.cover;

              return (
                <div
                  key={book.id}
                  onClick={() => navigate(`/books/${book.id}`)}
                  className="group bg-white dark:bg-slate-800 rounded-2xl p-3 border border-slate-200/80 dark:border-slate-700 shadow-sm hover:shadow-lg transition-all duration-200 cursor-pointer flex flex-col justify-between"
                >
                  <div className="relative aspect-[2/3] w-full rounded-xl overflow-hidden bg-slate-100 dark:bg-slate-700 mb-2 shadow-inner">
                    {coverUrl ? (
                      <img
                        src={coverUrl}
                        alt={book.title}
                        className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                        loading="lazy"
                      />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center p-2 text-center text-xs font-semibold text-slate-400">
                        {book.title}
                      </div>
                    )}
                  </div>

                  <div>
                    <h4 className="font-bold text-xs sm:text-sm text-slate-900 dark:text-white truncate group-hover:text-teal-600 transition-colors">
                      {book.title}
                    </h4>
                    {book.published_date && (
                      <p className="text-[11px] text-slate-400 mt-0.5">
                        {new Date(book.published_date).getFullYear() || book.published_date}
                      </p>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Formulario de Erratas / Sugerencias */}
      <div className="bg-white dark:bg-slate-800 rounded-3xl border border-slate-200/80 dark:border-slate-700 p-6 shadow-sm">
        <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-1.5 mb-2">
          <span>✍️</span>
          <span>¿Algún dato de {author.name} es incorrecto?</span>
        </h3>
        <p className="text-xs text-slate-500 dark:text-slate-400 mb-4">
          Nuestra comunidad cuida los datos bibliográficos. Envía una sugerencia o corrección.
        </p>

        {reportSent ? (
          <div className="p-4 bg-emerald-50 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-300 rounded-xl text-xs font-semibold">
            ✓ ¡Gracias! Tu reporte ha sido enviado a los editores.
          </div>
        ) : (
          <form onSubmit={handleSendErrata} className="space-y-3">
            <div className="flex gap-3 items-center">
              <label className="text-xs font-bold text-slate-700 dark:text-slate-300">
                Tipo de reporte:
              </label>
              <select
                value={errataType}
                onChange={(e) => setErrataType(e.target.value as any)}
                className="text-xs rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-700 py-1.5 px-3"
              >
                <option value="errata">Errata bibliográfica</option>
                <option value="suggestion">Sugerencia de biografía</option>
                <option value="other">Otro motivo</option>
              </select>
            </div>

            <textarea
              rows={3}
              value={errataText}
              onChange={(e) => setErrataText(e.target.value)}
              placeholder="Describe el dato que consideras incorrecto o la corrección sugerida..."
              className="w-full text-xs rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-700 p-3 focus:ring-teal-500"
            />

            <button
              type="submit"
              disabled={!errataText.trim()}
              className="bg-teal-600 hover:bg-teal-700 text-white font-bold text-xs px-4 py-2 rounded-xl transition-all disabled:opacity-50"
            >
              Enviar reporte
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
