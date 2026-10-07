import React, { useEffect, useState } from 'react';
import { Spinner, Modal, Button } from 'flowbite-react';
import {
  HiOutlineBookOpen,
  HiOutlinePlus,
  HiOutlineClock,
  HiOutlineExclamation,
  HiOutlineTrash,
  HiOutlinePencil,
  HiOutlineBookmark,
  HiOutlineX,
  HiOutlineEye,
  HiOutlineEyeOff,
} from 'react-icons/hi';
import { useAuthStore } from '../../../store/auth';

export interface AuthorPublicationItem {
  id: number;
  author_profile: number;
  author?: number | null;
  author_name: string;
  author_photo?: string | null;
  book?: number | null;
  book_title?: string | null;
  book_cover?: string | null;
  title: string;
  content: string;
  excerpt: string;
  publication_type: 'ANNOUNCEMENT' | 'CHAPTER_PREVIEW' | 'AUTHOR_DIARY' | 'DELETED_SCENE' | 'Q_AND_A';
  publication_type_display: string;
  has_spoilers: boolean;
  spoiler_warning: string;
  estimated_reading_time: number;
  is_pinned: boolean;
  is_draft: boolean;
  created_at: string;
  updated_at: string;
}

interface AuthorPublicationsSectionProps {
  authorId: number;
  authorName: string;
  isAuthorOwner: boolean;
  books: { id: number; title: string; cover?: string }[];
}

export const AuthorPublicationsSection: React.FC<AuthorPublicationsSectionProps> = ({
  authorId,
  authorName,
  isAuthorOwner,
  books,
}) => {
  const { token } = useAuthStore();
  const [publications, setPublications] = useState<AuthorPublicationItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedType, setSelectedType] = useState<string>('ALL');
  const [showDrafts, setShowDrafts] = useState<boolean>(false);
  const [revealedSpoilers, setRevealedSpoilers] = useState<Record<number, boolean>>({});
  const [expandedContent, setExpandedContent] = useState<Record<number, boolean>>({});

  // Modal Crear / Editar
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingItem, setEditingItem] = useState<AuthorPublicationItem | null>(null);
  const [form, setForm] = useState({
    title: '',
    content: '',
    book: '',
    publication_type: 'ANNOUNCEMENT',
    has_spoilers: false,
    spoiler_warning: '',
    is_pinned: false,
    is_draft: false,
  });
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const apiUrl = (import.meta as any).env.VITE_API_URL || 'http://localhost:8000';

  const loadPublications = async () => {
    try {
      setLoading(true);
      const headers: Record<string, string> = {};
      if (token) headers['Authorization'] = `Bearer ${token}`;

      let url = `${apiUrl}/api/v1/books/author-publications/?author=${authorId}`;
      if (selectedType !== 'ALL') {
        url += `&type=${selectedType}`;
      }
      if (isAuthorOwner && showDrafts) {
        url += `&drafts=true`;
      }

      const res = await fetch(url, { headers });
      if (res.ok) {
        const data = await res.json();
        const list = Array.isArray(data) ? data : data.results || [];
        setPublications(list);
      }
    } catch (e) {
      console.error('Error al cargar publicaciones del autor:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadPublications();
  }, [authorId, selectedType, showDrafts, token]);

  const handleOpenCreateModal = () => {
    setEditingItem(null);
    setForm({
      title: '',
      content: '',
      book: '',
      publication_type: 'ANNOUNCEMENT',
      has_spoilers: false,
      spoiler_warning: '',
      is_pinned: false,
      is_draft: false,
    });
    setFormError(null);
    setIsModalOpen(true);
  };

  const handleOpenEditModal = (item: AuthorPublicationItem) => {
    setEditingItem(item);
    setForm({
      title: item.title,
      content: item.content,
      book: item.book ? String(item.book) : '',
      publication_type: item.publication_type,
      has_spoilers: item.has_spoilers,
      spoiler_warning: item.spoiler_warning,
      is_pinned: item.is_pinned,
      is_draft: item.is_draft,
    });
    setFormError(null);
    setIsModalOpen(true);
  };

  const handleSubmitForm = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token) return;

    if (!form.title.trim() || !form.content.trim()) {
      setFormError('Por favor completa el título y contenido.');
      return;
    }

    try {
      setSubmitting(true);
      setFormError(null);

      const payload: any = {
        author: authorId,
        title: form.title.trim(),
        content: form.content.trim(),
        publication_type: form.publication_type,
        has_spoilers: form.has_spoilers,
        spoiler_warning: form.spoiler_warning.trim(),
        is_pinned: form.is_pinned,
        is_draft: form.is_draft,
      };

      if (form.book) {
        payload.book = Number(form.book);
      } else {
        payload.book = null;
      }

      const isEdit = Boolean(editingItem);
      const url = isEdit
        ? `${apiUrl}/api/v1/books/author-publications/${editingItem!.id}/`
        : `${apiUrl}/api/v1/books/author-publications/`;

      const method = isEdit ? 'PATCH' : 'POST';

      const res = await fetch(url, {
        method,
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(payload),
      });

      if (res.ok) {
        setIsModalOpen(false);
        await loadPublications();
      } else {
        const err = await res.json();
        setFormError(err.detail || err.title || 'Error al guardar la publicación.');
      }
    } catch (e: any) {
      setFormError(e.message || 'Error de conexión.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleTogglePin = async (id: number) => {
    if (!token) return;
    try {
      const res = await fetch(`${apiUrl}/api/v1/books/author-publications/${id}/toggle_pin/`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        await loadPublications();
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleDelete = async (id: number) => {
    if (!token) return;
    if (!confirm('¿Estás seguro de que deseas eliminar esta publicación?')) return;

    try {
      const res = await fetch(`${apiUrl}/api/v1/books/author-publications/${id}/`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        await loadPublications();
      }
    } catch (e) {
      console.error(e);
    }
  };

  const toggleSpoilerReveal = (id: number) => {
    setRevealedSpoilers((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const toggleExpandContent = (id: number) => {
    setExpandedContent((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const getTypeBadge = (type: string) => {
    const map: Record<string, { label: string; icon: string; bg: string }> = {
      ANNOUNCEMENT: { label: 'Comunicado', icon: '📢', bg: 'bg-teal-50 text-teal-800 dark:bg-teal-950/60 dark:text-teal-300 border-teal-200 dark:border-teal-800' },
      CHAPTER_PREVIEW: { label: 'Adelanto de capítulo', icon: '📖', bg: 'bg-indigo-50 text-indigo-800 dark:bg-indigo-950/60 dark:text-indigo-300 border-indigo-200 dark:border-indigo-800' },
      AUTHOR_DIARY: { label: 'Diario de autor', icon: '✍️', bg: 'bg-amber-50 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300 border-amber-200 dark:border-amber-800' },
      DELETED_SCENE: { label: 'Escena eliminada / Extra', icon: '✂️', bg: 'bg-purple-50 text-purple-800 dark:bg-purple-950/60 dark:text-purple-300 border-purple-200 dark:border-purple-800' },
      Q_AND_A: { label: 'Q&A Literario', icon: '💬', bg: 'bg-sky-50 text-sky-800 dark:bg-sky-950/60 dark:text-sky-300 border-sky-200 dark:border-sky-800' },
    };
    const info = map[type] || { label: type, icon: '📄', bg: 'bg-slate-50 text-slate-800 dark:bg-slate-800 dark:text-slate-200 border-slate-200 dark:border-slate-700' };
    return (
      <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold border ${info.bg}`}>
        <span>{info.icon}</span>
        <span>{info.label}</span>
      </span>
    );
  };

  return (
    <div className="space-y-6">
      {/* Cabecera de la sección */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200/80 dark:border-slate-800 pb-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
            <span>📰</span>
            <span>Publicaciones y Adelantos</span>
            <span className="text-xs font-bold px-2.5 py-0.5 rounded-full bg-teal-100 text-teal-800 dark:bg-teal-900/40 dark:text-teal-300">
              {publications.length}
            </span>
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Novedades exclusivas, notas de proceso creativo y adelantos de {authorName}.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {/* Filtro por tipo */}
          <select
            value={selectedType}
            onChange={(e) => setSelectedType(e.target.value)}
            className="text-xs rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 py-1.5 px-3 text-slate-800 dark:text-slate-200 font-semibold focus:ring-teal-500"
          >
            <option value="ALL">Todas las publicaciones</option>
            <option value="ANNOUNCEMENT">📢 Comunicados oficiales</option>
            <option value="CHAPTER_PREVIEW">📖 Adelantos de capítulos</option>
            <option value="AUTHOR_DIARY">✍️ Diarios de escritura</option>
            <option value="DELETED_SCENE">✂️ Escenas eliminadas</option>
            <option value="Q_AND_A">💬 Preguntas y respuestas</option>
          </select>

          {/* Toggle borradores si es autor */}
          {isAuthorOwner && (
            <button
              onClick={() => setShowDrafts(!showDrafts)}
              className={`px-3 py-1.5 rounded-xl text-xs font-bold border transition-colors cursor-pointer ${
                showDrafts
                  ? 'bg-amber-100 text-amber-900 border-amber-300 dark:bg-amber-950/60 dark:text-amber-300'
                  : 'bg-slate-100 text-slate-700 border-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:border-slate-700'
              }`}
            >
              {showDrafts ? '👁️ Viendo borradores' : 'Borradores'}
            </button>
          )}

          {/* Botón de crear publicación */}
          {isAuthorOwner && (
            <button
              onClick={handleOpenCreateModal}
              className="bg-teal-600 hover:bg-teal-700 text-white font-bold text-xs px-3.5 py-2 rounded-xl transition-all shadow-sm hover:shadow flex items-center gap-1.5 cursor-pointer"
            >
              <HiOutlinePlus className="w-4 h-4" />
              <span>Nueva Publicación</span>
            </button>
          )}
        </div>
      </div>

      {/* Listado de Publicaciones */}
      {loading ? (
        <div className="py-12 flex justify-center">
          <Spinner size="lg" color="teal" />
        </div>
      ) : publications.length === 0 ? (
        <div className="text-center p-8 bg-white dark:bg-slate-900 rounded-3xl border border-slate-200/80 dark:border-slate-800 text-slate-500 text-sm space-y-2">
          <div className="text-3xl">📝</div>
          <p className="font-semibold text-slate-700 dark:text-slate-300">
            Aún no hay publicaciones en esta categoría.
          </p>
          <p className="text-xs text-slate-400">
            {isAuthorOwner
              ? 'Comparte adelantos, noticias o escenas eliminadas con tu comunidad de lectores.'
              : 'Vuelve pronto para leer nuevos comunicados o adelantos de este autor.'}
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {publications.map((item) => {
            const isSpoilerBlocked = item.has_spoilers && !revealedSpoilers[item.id];
            const isExpanded = Boolean(expandedContent[item.id]);

            return (
              <article
                key={item.id}
                className={`bg-white dark:bg-slate-900 rounded-3xl p-6 border shadow-sm transition-all ${
                  item.is_pinned
                    ? 'border-teal-500/60 dark:border-teal-600/60 ring-1 ring-teal-500/20'
                    : 'border-slate-200/80 dark:border-slate-800'
                }`}
              >
                {/* Cabecera del post */}
                <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
                  <div className="flex flex-wrap items-center gap-2">
                    {getTypeBadge(item.publication_type)}
                    {item.is_pinned && (
                      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-teal-100 text-teal-800 dark:bg-teal-950/60 dark:text-teal-300">
                        <HiOutlineBookmark className="w-3.5 h-3.5" /> Fijado
                      </span>
                    )}
                    {item.is_draft && (
                      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300">
                        Borrador privado
                      </span>
                    )}
                    <span className="text-xs text-slate-400 flex items-center gap-1">
                      <HiOutlineClock className="w-3.5 h-3.5" />
                      <span>{item.estimated_reading_time} min de lectura</span>
                    </span>
                  </div>

                  {/* Acciones de gestión para el Autor */}
                  {isAuthorOwner && (
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => handleTogglePin(item.id)}
                        title={item.is_pinned ? 'Desfijar de la cabecera' : 'Fijar en cabecera'}
                        className={`p-1.5 rounded-lg text-xs transition-colors cursor-pointer ${
                          item.is_pinned
                            ? 'text-teal-600 hover:bg-teal-50 dark:hover:bg-teal-950/40'
                            : 'text-slate-400 hover:text-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800'
                        }`}
                      >
                        <HiOutlineBookmark className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => handleOpenEditModal(item)}
                        title="Editar publicación"
                        className="p-1.5 rounded-lg text-xs text-slate-400 hover:text-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors cursor-pointer"
                      >
                        <HiOutlinePencil className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => handleDelete(item.id)}
                        title="Eliminar publicación"
                        className="p-1.5 rounded-lg text-xs text-rose-500 hover:text-rose-700 hover:bg-rose-50 dark:hover:bg-rose-950/40 transition-colors cursor-pointer"
                      >
                        <HiOutlineTrash className="w-4 h-4" />
                      </button>
                    </div>
                  )}
                </div>

                {/* Título */}
                <h3 className="text-lg sm:text-xl font-bold text-slate-900 dark:text-white mb-2">
                  {item.title}
                </h3>

                {/* Libro relacionado */}
                {item.book_title && (
                  <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-100 dark:border-slate-800 text-xs mb-3">
                    <HiOutlineBookOpen className="w-4 h-4 text-teal-600 shrink-0" />
                    <span className="text-slate-500 dark:text-slate-400">Obra vinculada:</span>
                    <strong className="text-slate-800 dark:text-slate-200">{item.book_title}</strong>
                  </div>
                )}

                {/* Advertencia y control de Spoilers */}
                {item.has_spoilers && (
                  <div className="p-3 mb-3 bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-800 rounded-2xl flex items-center justify-between gap-3 text-xs">
                    <div className="flex items-center gap-2 text-amber-800 dark:text-amber-300 font-semibold">
                      <HiOutlineExclamation className="w-4 h-4 shrink-0 text-amber-600" />
                      <span>{item.spoiler_warning || 'Esta publicación contiene revelaciones de la trama.'}</span>
                    </div>
                    <button
                      onClick={() => toggleSpoilerReveal(item.id)}
                      className="px-3 py-1 rounded-xl bg-amber-200/80 hover:bg-amber-300/80 dark:bg-amber-800 dark:hover:bg-amber-700 text-amber-900 dark:text-amber-100 font-bold text-[11px] transition-colors flex items-center gap-1 cursor-pointer shrink-0"
                    >
                      {revealedSpoilers[item.id] ? (
                        <>
                          <HiOutlineEyeOff className="w-3.5 h-3.5" /> Ocultar
                        </>
                      ) : (
                        <>
                          <HiOutlineEye className="w-3.5 h-3.5" /> Revelar
                        </>
                      )}
                    </button>
                  </div>
                )}

                {/* Contenido / Texto */}
                {isSpoilerBlocked ? (
                  <div className="p-6 bg-slate-50 dark:bg-slate-800/40 rounded-2xl border border-dashed border-slate-200 dark:border-slate-700 text-center text-xs text-slate-500 italic">
                    Contenido oculto para evitar spoilers. Pulsa "Revelar" para leer.
                  </div>
                ) : (
                  <div className="prose prose-sm dark:prose-invert max-w-none text-slate-700 dark:text-slate-300 text-xs sm:text-sm whitespace-pre-line leading-relaxed">
                    {isExpanded ? item.content : item.excerpt || item.content.slice(0, 300)}
                  </div>
                )}

                {/* Botón expandir lectura */}
                {!isSpoilerBlocked && item.content.length > 300 && (
                  <div className="mt-3">
                    <button
                      onClick={() => toggleExpandContent(item.id)}
                      className="text-xs font-bold text-teal-600 hover:text-teal-700 dark:text-teal-400 hover:underline cursor-pointer flex items-center gap-1"
                    >
                      <span>{isExpanded ? 'Contraer texto' : 'Leer publicación completa →'}</span>
                    </button>
                  </div>
                )}

                {/* Fecha al pie */}
                <div className="mt-4 pt-3 border-t border-slate-100 dark:border-slate-800 text-[11px] text-slate-400">
                  Publicado el {new Date(item.created_at).toLocaleDateString('es-ES', { day: 'numeric', month: 'long', year: 'numeric' })}
                </div>
              </article>
            );
          })}
        </div>
      )}

      {/* Modal Crear / Editar Publicación */}
      <Modal show={isModalOpen} onClose={() => setIsModalOpen(false)} size="lg">
        <div className="p-6 space-y-4 bg-white dark:bg-slate-900 rounded-3xl max-h-[90vh] overflow-y-auto">
          <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-3">
            <h3 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
              <span>✍️</span>
              <span>{editingItem ? 'Editar Publicación de Autor' : 'Nueva Publicación o Adelanto'}</span>
            </h3>
            <button
              onClick={() => setIsModalOpen(false)}
              className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 p-1 cursor-pointer"
            >
              <HiOutlineX className="w-5 h-5" />
            </button>
          </div>

          {formError && (
            <div className="p-3 bg-rose-50 text-rose-800 dark:bg-rose-950/60 dark:text-rose-300 rounded-xl text-xs font-semibold">
              {formError}
            </div>
          )}

          <form onSubmit={handleSubmitForm} className="space-y-4 text-xs">
            <div>
              <label className="block font-bold text-slate-700 dark:text-slate-300 mb-1">
                Título *
              </label>
              <input
                type="text"
                required
                value={form.title}
                onChange={(e) => setForm({ ...form, title: e.target.value })}
                placeholder="Ej. Adelanto: Capítulo 1 - Las primeras cenizas"
                className="w-full text-xs rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 py-2 px-3 text-slate-900 dark:text-white focus:ring-teal-500"
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block font-bold text-slate-700 dark:text-slate-300 mb-1">
                  Tipo de Publicación
                </label>
                <select
                  value={form.publication_type}
                  onChange={(e) => setForm({ ...form, publication_type: e.target.value as any })}
                  className="w-full text-xs rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 py-2 px-3 text-slate-900 dark:text-white focus:ring-teal-500"
                >
                  <option value="ANNOUNCEMENT">📢 Comunicado oficial</option>
                  <option value="CHAPTER_PREVIEW">📖 Adelanto de capítulo</option>
                  <option value="AUTHOR_DIARY">✍️ Diario de escritura</option>
                  <option value="DELETED_SCENE">✂️ Escena eliminada / Extra</option>
                  <option value="Q_AND_A">💬 Preguntas y respuestas</option>
                </select>
              </div>

              {books.length > 0 && (
                <div>
                  <label className="block font-bold text-slate-700 dark:text-slate-300 mb-1">
                    Libro Vinculado (Opcional)
                  </label>
                  <select
                    value={form.book}
                    onChange={(e) => setForm({ ...form, book: e.target.value })}
                    className="w-full text-xs rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 py-2 px-3 text-slate-900 dark:text-white focus:ring-teal-500"
                  >
                    <option value="">Ninguno / General</option>
                    {books.map((b) => (
                      <option key={b.id} value={b.id}>
                        {b.title}
                      </option>
                    ))}
                  </select>
                </div>
              )}
            </div>

            <div>
              <label className="block font-bold text-slate-700 dark:text-slate-300 mb-1">
                Contenido Completo *
              </label>
              <textarea
                rows={8}
                required
                value={form.content}
                onChange={(e) => setForm({ ...form, content: e.target.value })}
                placeholder="Escribe el texto íntegro del adelanto, comunicado o fragmento..."
                className="w-full text-xs rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 p-3 text-slate-900 dark:text-white focus:ring-teal-500 font-mono"
              />
            </div>

            {/* Configuración de Spoilers */}
            <div className="p-3 bg-slate-50 dark:bg-slate-800/60 rounded-2xl border border-slate-100 dark:border-slate-800 space-y-3">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={form.has_spoilers}
                  onChange={(e) => setForm({ ...form, has_spoilers: e.target.checked })}
                  className="rounded text-teal-600 focus:ring-teal-500"
                />
                <span className="font-bold text-slate-800 dark:text-slate-200">
                  ⚠️ Contiene spoilers o revelaciones importantes de la trama
                </span>
              </label>

              {form.has_spoilers && (
                <div>
                  <label className="block text-[11px] font-semibold text-slate-600 dark:text-slate-400 mb-1">
                    Texto de advertencia para el lector:
                  </label>
                  <input
                    type="text"
                    value={form.spoiler_warning}
                    onChange={(e) => setForm({ ...form, spoiler_warning: e.target.value })}
                    placeholder="Ej. Revela la resolución del capítulo 15"
                    className="w-full text-xs rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 py-1.5 px-3 text-slate-900 dark:text-white focus:ring-teal-500"
                  />
                </div>
              )}
            </div>

            {/* Opciones de publicación */}
            <div className="flex flex-wrap items-center gap-6 pt-1">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={form.is_pinned}
                  onChange={(e) => setForm({ ...form, is_pinned: e.target.checked })}
                  className="rounded text-teal-600 focus:ring-teal-500"
                />
                <span className="font-semibold text-slate-700 dark:text-slate-300">
                  📌 Fijar en la cabecera del perfil
                </span>
              </label>

              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={form.is_draft}
                  onChange={(e) => setForm({ ...form, is_draft: e.target.checked })}
                  className="rounded text-teal-600 focus:ring-teal-500"
                />
                <span className="font-semibold text-slate-700 dark:text-slate-300">
                  Guardar como borrador privado
                </span>
              </label>
            </div>

            <div className="flex justify-end gap-2 pt-3 border-t border-slate-100 dark:border-slate-800">
              <Button color="gray" size="sm" onClick={() => setIsModalOpen(false)}>
                Cancelar
              </Button>
              <Button color="teal" size="sm" type="submit" disabled={submitting}>
                {submitting ? 'Guardando...' : editingItem ? 'Actualizar' : 'Publicar'}
              </Button>
            </div>
          </form>
        </div>
      </Modal>
    </div>
  );
};
