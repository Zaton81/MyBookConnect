import React, { useState, useEffect } from 'react';
import { Spinner } from 'flowbite-react';

interface CategoryItem {
  id: number;
  name: string;
  slug: string;
  description?: string | null;
}

interface AdminCategoriesTabProps {
  token: string | null;
  apiUrl: string;
}

export function AdminCategoriesTab({ token, apiUrl }: AdminCategoriesTabProps) {
  const [categories, setCategories] = useState<CategoryItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState('');

  // Formulario de nueva categoría
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState('');
  const [slug, setSlug] = useState('');
  const [description, setDescription] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [actionMsg, setActionMsg] = useState<{ text: string; type: 'success' | 'error' } | null>(null);

  const fetchCategories = async () => {
    if (!token) return;
    setLoading(true);
    try {
      const res = await fetch(`${apiUrl}/api/v1/admin/categories/?all=true`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setCategories(Array.isArray(data) ? data : data.results || []);
      }
    } catch (e) {
      console.error('Error al cargar categorías:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCategories();
  }, [token]);

  const handleNameChange = (val: string) => {
    setName(val);
    if (!slug || slug === name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '')) {
      setSlug(
        val
          .toLowerCase()
          .normalize('NFD')
          .replace(/[\u0300-\u036f]/g, '')
          .replace(/[^a-z0-9]+/g, '-')
          .replace(/(^-|-$)/g, '')
      );
    }
  };

  const handleCreateCategory = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token || !name.trim()) return;
    setSubmitting(true);
    setActionMsg(null);

    try {
      const payload: any = {
        name: name.trim(),
        slug: slug.trim() || undefined,
        description: description.trim() || undefined,
      };

      const res = await fetch(`${apiUrl}/api/v1/admin/categories/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(payload),
      });

      if (res.ok) {
        setActionMsg({ text: 'Categoría creada con éxito.', type: 'success' });
        setName('');
        setSlug('');
        setDescription('');
        setShowForm(false);
        fetchCategories();
      } else {
        const err = await res.json().catch(() => ({}));
        setActionMsg({ text: err.name?.[0] || err.slug?.[0] || 'Error al crear la categoría.', type: 'error' });
      }
    } catch (err: any) {
      setActionMsg({ text: err.message || 'Error de conexión', type: 'error' });
    } finally {
      setSubmitting(false);
    }
  };

  const filteredCategories = categories.filter((c) =>
    c.name.toLowerCase().includes(search.toLowerCase()) ||
    c.slug.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Cabecera y acciones */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-white dark:bg-slate-800 p-6 rounded-3xl border border-slate-200/80 dark:border-slate-700 shadow-sm">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-2xl">🏷️</span>
            <h2 className="text-lg font-bold text-slate-900 dark:text-white">
              Categorías y Géneros Literarios
            </h2>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-teal-50 text-teal-700 dark:bg-teal-900/30 dark:text-teal-300">
              {categories.length} géneros
            </span>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 max-w-xl">
            Gestiona la taxonomía oficial de géneros y clasificaciones del catálogo editorial de la plataforma.
          </p>
        </div>

        <button
          onClick={() => setShowForm(!showForm)}
          className="bg-teal-600 hover:bg-teal-700 text-white text-xs font-bold px-4 py-2.5 rounded-2xl transition-all shadow-md shadow-teal-600/20 flex items-center gap-1.5"
        >
          <span>{showForm ? '✕ Cancelar' : '+ Nueva Categoría'}</span>
        </button>
      </div>

      {actionMsg && (
        <div
          className={`p-3 rounded-2xl text-xs font-semibold flex items-center justify-between ${
            actionMsg.type === 'success'
              ? 'bg-emerald-50 text-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800'
              : 'bg-rose-50 text-rose-800 dark:bg-rose-950/40 dark:text-rose-300 border border-rose-200 dark:border-rose-800'
          }`}
        >
          <span>{actionMsg.text}</span>
          <button onClick={() => setActionMsg(null)} className="font-bold ml-2">
            &times;
          </button>
        </div>
      )}

      {/* Formulario de creación */}
      {showForm && (
        <form
          onSubmit={handleCreateCategory}
          className="bg-slate-50 dark:bg-slate-800/80 p-5 rounded-3xl border border-slate-200 dark:border-slate-700 space-y-4 shadow-sm"
        >
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300">
            Añadir Nuevo Género o Categoría
          </h3>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1">
                Nombre de la Categoría *
              </label>
              <input
                type="text"
                required
                value={name}
                onChange={(e) => handleNameChange(e.target.value)}
                placeholder="Ej: Novela Gráfica, Distopía, Ensayo..."
                className="w-full text-xs rounded-xl border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-900 p-2.5 focus:ring-2 focus:ring-teal-500 font-semibold"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1">
                Slug (URL identificador)
              </label>
              <input
                type="text"
                value={slug}
                onChange={(e) => setSlug(e.target.value)}
                placeholder="novela-grafica"
                className="w-full text-xs rounded-xl border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-900 p-2.5 focus:ring-2 focus:ring-teal-500 font-mono"
              />
            </div>

            <div className="sm:col-span-2">
              <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1">
                Descripción (Opcional)
              </label>
              <textarea
                rows={2}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Breve definición o alcance de este género literario..."
                className="w-full text-xs rounded-xl border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-900 p-2.5 focus:ring-2 focus:ring-teal-500"
              />
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={() => setShowForm(false)}
              className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-600 hover:bg-slate-200 dark:text-slate-300 dark:hover:bg-slate-700"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="bg-teal-600 hover:bg-teal-700 text-white text-xs font-bold px-5 py-2 rounded-xl shadow-md transition-all disabled:opacity-50"
            >
              {submitting ? 'Guardando...' : 'Crear Categoría'}
            </button>
          </div>
        </form>
      )}

      {/* Buscador */}
      <div className="flex items-center gap-3 bg-white dark:bg-slate-800 p-4 rounded-2xl border border-slate-200 dark:border-slate-700">
        <span className="text-slate-400">🔍</span>
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Buscar categorías por nombre o slug..."
          className="w-full text-xs bg-transparent border-none focus:outline-none focus:ring-0 text-slate-800 dark:text-white"
        />
        {search && (
          <button onClick={() => setSearch('')} className="text-xs text-slate-400 hover:text-slate-600">
            Limpiar
          </button>
        )}
      </div>

      {/* Listado en tabla / grid */}
      {loading ? (
        <div className="flex justify-center p-12">
          <Spinner size="xl" color="info" />
        </div>
      ) : filteredCategories.length === 0 ? (
        <div className="text-center py-12 bg-white dark:bg-slate-800 rounded-3xl border border-dashed border-slate-200 dark:border-slate-700 text-slate-500 dark:text-slate-400 text-xs">
          No se encontraron categorías.
        </div>
      ) : (
        <div className="bg-white dark:bg-slate-800 rounded-3xl border border-slate-200/80 dark:border-slate-700 shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-600 dark:text-slate-300">
              <thead className="bg-slate-50 dark:bg-slate-700/50 text-[11px] uppercase tracking-wider text-slate-500 dark:text-slate-400 border-b border-slate-200 dark:border-slate-700">
                <tr>
                  <th className="py-3.5 px-4 font-bold">ID</th>
                  <th className="py-3.5 px-4 font-bold">Nombre del Género</th>
                  <th className="py-3.5 px-4 font-bold">Slug URL</th>
                  <th className="py-3.5 px-4 font-bold">Descripción</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-700/50">
                {filteredCategories.map((c) => (
                  <tr key={c.id} className="hover:bg-slate-50/70 dark:hover:bg-slate-700/30 transition-colors">
                    <td className="py-3 px-4 font-mono text-slate-400 font-bold">#{c.id}</td>
                    <td className="py-3 px-4 font-bold text-slate-900 dark:text-white flex items-center gap-2">
                      <span>📚</span>
                      <span>{c.name}</span>
                    </td>
                    <td className="py-3 px-4 font-mono text-[11px] text-teal-600 dark:text-teal-400">
                      {c.slug}
                    </td>
                    <td className="py-3 px-4 text-slate-500 max-w-md line-clamp-1">
                      {c.description || <span className="italic text-slate-400">Sin descripción</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
export default AdminCategoriesTab;
