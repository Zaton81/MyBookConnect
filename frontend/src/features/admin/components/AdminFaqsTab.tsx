import React, { useState, useEffect, useMemo } from 'react';
import { Spinner, Modal, Button } from 'flowbite-react';
import {
  HiOutlineQuestionMarkCircle,
  HiOutlinePlus,
  HiOutlinePencil,
  HiOutlineTrash,
  HiOutlineEye,
  HiOutlineEyeOff,
  HiOutlineSearch,
} from 'react-icons/hi';
import { useAuthStore } from '../../../store/auth';

interface AdminFAQ {
  id: number;
  question: string;
  answer: string;
  category: string;
  order: number;
  is_published: boolean;
  created_at: string;
  updated_at: string;
}

const CATEGORY_OPTIONS = [
  { value: 'general', label: 'General' },
  { value: 'authors', label: 'Autores y Perfiles' },
  { value: 'books', label: 'Libros y Catálogo' },
  { value: 'account', label: 'Cuenta y Privacidad' },
  { value: 'community', label: 'Comunidad y Reseñas' },
];

export function AdminFaqsTab() {
  const { token } = useAuthStore();
  const [faqs, setFaqs] = useState<AdminFAQ[]>([]);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('all');
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' } | null>(null);

  // Modal Crear / Editar
  const [showModal, setShowModal] = useState(false);
  const [editingFaq, setEditingFaq] = useState<AdminFAQ | null>(null);
  const [formData, setFormData] = useState({
    question: '',
    answer: '',
    category: 'general',
    order: 0,
    is_published: true,
  });
  const [saving, setSaving] = useState(false);

  // Modal Borrado
  const [deletingFaq, setDeletingFaq] = useState<AdminFAQ | null>(null);
  const [deleting, setDeleting] = useState(false);

  const apiUrl = (import.meta as any).env.VITE_API_URL || 'http://localhost:8000';

  const loadFaqs = async () => {
    if (!token) return;
    try {
      setLoading(true);
      const res = await fetch(`${apiUrl}/api/v1/admin/faqs/`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error('Error al cargar preguntas frecuentes');
      const data = await res.json();
      setFaqs(Array.isArray(data) ? data : data.results || []);
    } catch (err: any) {
      console.error(err);
      setMessage({ text: err.message || 'Error de conexión', type: 'error' });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadFaqs();
  }, [token]);

  const handleOpenCreate = () => {
    setEditingFaq(null);
    setFormData({
      question: '',
      answer: '',
      category: 'general',
      order: (faqs.length + 1) * 10,
      is_published: true,
    });
    setShowModal(true);
  };

  const handleOpenEdit = (faq: AdminFAQ) => {
    setEditingFaq(faq);
    setFormData({
      question: faq.question,
      answer: faq.answer,
      category: faq.category,
      order: faq.order,
      is_published: faq.is_published,
    });
    setShowModal(true);
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token) return;
    if (!formData.question.trim() || !formData.answer.trim()) {
      setMessage({ text: 'La pregunta y la respuesta son obligatorias.', type: 'error' });
      return;
    }

    try {
      setSaving(true);
      const url = editingFaq
        ? `${apiUrl}/api/v1/admin/faqs/${editingFaq.id}/`
        : `${apiUrl}/api/v1/admin/faqs/`;
      const method = editingFaq ? 'PUT' : 'POST';

      const res = await fetch(url, {
        method,
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(formData),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => null);
        throw new Error(errData?.detail || 'No se pudo guardar la pregunta FAQ');
      }

      setMessage({
        text: editingFaq ? 'Pregunta actualizada correctamente' : 'Pregunta FAQ creada con éxito',
        type: 'success',
      });
      setShowModal(false);
      await loadFaqs();
    } catch (err: any) {
      setMessage({ text: err.message || 'Error al guardar', type: 'error' });
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!token || !deletingFaq) return;
    try {
      setDeleting(true);
      const res = await fetch(`${apiUrl}/api/v1/admin/faqs/${deletingFaq.id}/`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!res.ok) throw new Error('Error al eliminar la pregunta');

      setMessage({ text: 'Pregunta eliminada con éxito', type: 'success' });
      setDeletingFaq(null);
      await loadFaqs();
    } catch (err: any) {
      setMessage({ text: err.message || 'Error al eliminar', type: 'error' });
    } finally {
      setDeleting(false);
    }
  };

  const filteredFaqs = useMemo(() => {
    return faqs.filter((faq) => {
      const matchesCat = categoryFilter === 'all' || faq.category === categoryFilter;
      const q = search.toLowerCase().trim();
      const matchesSearch =
        !q ||
        faq.question.toLowerCase().includes(q) ||
        faq.answer.toLowerCase().includes(q);
      return matchesCat && matchesSearch;
    });
  }, [faqs, categoryFilter, search]);

  return (
    <div className="space-y-6">
      {/* Header and Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 bg-white dark:bg-slate-900 p-6 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm">
        <div>
          <h2 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
            <HiOutlineQuestionMarkCircle className="w-6 h-6 text-teal-600" />
            Gestión de Preguntas Frecuentes (FAQs)
          </h2>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            Crea, edita y ordena las preguntas y respuestas visualizadas en formato acordeón en el frontend público.
          </p>
        </div>

        <button
          type="button"
          onClick={handleOpenCreate}
          className="inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-teal-600 hover:bg-teal-700 text-white font-medium text-sm transition-colors shadow-sm cursor-pointer"
        >
          <HiOutlinePlus className="w-5 h-5" />
          <span>Nueva Pregunta FAQ</span>
        </button>
      </div>

      {/* Alerts */}
      {message && (
        <div
          className={`p-4 rounded-xl text-sm flex items-center justify-between ${
            message.type === 'success'
              ? 'bg-emerald-50 dark:bg-emerald-950/40 text-emerald-800 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800'
              : 'bg-red-50 dark:bg-red-950/40 text-red-800 dark:text-red-300 border border-red-200 dark:border-red-800'
          }`}
        >
          <span>{message.text}</span>
          <button
            type="button"
            onClick={() => setMessage(null)}
            className="text-xs font-bold underline ml-4 cursor-pointer"
          >
            Cerrar
          </button>
        </div>
      )}

      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="relative flex-1">
          <HiOutlineSearch className="w-5 h-5 absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Buscar por pregunta o contenido de respuesta..."
            className="w-full pl-10 pr-4 py-2 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-sm text-slate-900 dark:text-white focus:ring-2 focus:ring-teal-500"
          />
        </div>

        <select
          value={categoryFilter}
          onChange={(e) => setCategoryFilter(e.target.value)}
          className="px-4 py-2 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-sm text-slate-900 dark:text-white focus:ring-2 focus:ring-teal-500"
        >
          <option value="all">Todas las categorías ({faqs.length})</option>
          {CATEGORY_OPTIONS.map((cat) => (
            <option key={cat.value} value={cat.value}>
              {cat.label}
            </option>
          ))}
        </select>
      </div>

      {/* Table / List */}
      {loading ? (
        <div className="flex justify-center py-16">
          <Spinner size="xl" className="fill-teal-600" />
        </div>
      ) : filteredFaqs.length === 0 ? (
        <div className="text-center py-16 bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 text-slate-500">
          No se encontraron preguntas frecuentes con los filtros aplicados.
        </div>
      ) : (
        <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 overflow-hidden shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-600 dark:text-slate-300">
              <thead className="bg-slate-50 dark:bg-slate-800/60 text-xs uppercase font-semibold text-slate-500 dark:text-slate-400 border-b border-slate-200 dark:border-slate-800">
                <tr>
                  <th className="px-6 py-4">Orden</th>
                  <th className="px-6 py-4">Categoría</th>
                  <th className="px-6 py-4">Pregunta</th>
                  <th className="px-6 py-4">Estado</th>
                  <th className="px-6 py-4 text-right">Acciones</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {filteredFaqs.map((faq) => (
                  <tr key={faq.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/30 transition-colors">
                    <td className="px-6 py-4 font-mono text-xs text-slate-400">
                      #{faq.order}
                    </td>
                    <td className="px-6 py-4">
                      <span className="inline-flex px-2.5 py-1 rounded-md text-xs font-semibold bg-teal-50 dark:bg-teal-950/60 text-teal-700 dark:text-teal-300 border border-teal-200/60 dark:border-teal-800">
                        {CATEGORY_OPTIONS.find((c) => c.value === faq.category)?.label || faq.category}
                      </span>
                    </td>
                    <td className="px-6 py-4 font-medium text-slate-900 dark:text-white max-w-md">
                      <div>{faq.question}</div>
                      <div className="text-xs text-slate-400 truncate max-w-sm mt-0.5">
                        {faq.answer}
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      {faq.is_published ? (
                        <span className="inline-flex items-center gap-1 text-xs font-medium text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/40 px-2 py-0.5 rounded-full">
                          <HiOutlineEye className="w-3.5 h-3.5" />
                          Publicada
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-xs font-medium text-slate-500 dark:text-slate-400 bg-slate-100 dark:bg-slate-800 px-2 py-0.5 rounded-full">
                          <HiOutlineEyeOff className="w-3.5 h-3.5" />
                          Borrador
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-4 text-right space-x-2">
                      <button
                        type="button"
                        onClick={() => handleOpenEdit(faq)}
                        className="p-1.5 rounded-lg text-slate-500 hover:text-teal-600 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors cursor-pointer"
                        title="Editar FAQ"
                      >
                        <HiOutlinePencil className="w-4 h-4" />
                      </button>
                      <button
                        type="button"
                        onClick={() => setDeletingFaq(faq)}
                        className="p-1.5 rounded-lg text-slate-500 hover:text-red-600 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors cursor-pointer"
                        title="Eliminar FAQ"
                      >
                        <HiOutlineTrash className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Modal Crear / Editar */}
      <Modal show={showModal} onClose={() => setShowModal(false)} size="lg">
        <Modal.Header>
          <span className="font-bold text-slate-900 dark:text-white">
            {editingFaq ? 'Editar Pregunta FAQ' : 'Crear Nueva Pregunta FAQ'}
          </span>
        </Modal.Header>
        <form onSubmit={handleSave}>
          <Modal.Body className="space-y-4">
            <div>
              <label className="block text-xs font-bold uppercase text-slate-600 dark:text-slate-300 mb-1">
                Pregunta *
              </label>
              <input
                type="text"
                required
                value={formData.question}
                onChange={(e) => setFormData({ ...formData, question: e.target.value })}
                placeholder="¿Cómo puedo añadir un libro a mi biblioteca?"
                className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm text-slate-900 dark:text-white focus:ring-2 focus:ring-teal-500"
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-bold uppercase text-slate-600 dark:text-slate-300 mb-1">
                  Categoría *
                </label>
                <select
                  value={formData.category}
                  onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm text-slate-900 dark:text-white focus:ring-2 focus:ring-teal-500"
                >
                  {CATEGORY_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold uppercase text-slate-600 dark:text-slate-300 mb-1">
                  Orden de Visualización
                </label>
                <input
                  type="number"
                  value={formData.order}
                  onChange={(e) => setFormData({ ...formData, order: parseInt(e.target.value, 10) || 0 })}
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm text-slate-900 dark:text-white focus:ring-2 focus:ring-teal-500"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-bold uppercase text-slate-600 dark:text-slate-300 mb-1">
                Respuesta Detallada *
              </label>
              <textarea
                required
                rows={5}
                value={formData.answer}
                onChange={(e) => setFormData({ ...formData, answer: e.target.value })}
                placeholder="Escribe la respuesta clara y concisa..."
                className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm text-slate-900 dark:text-white focus:ring-2 focus:ring-teal-500"
              />
            </div>

            <div className="flex items-center gap-3 pt-2">
              <input
                id="is_published"
                type="checkbox"
                checked={formData.is_published}
                onChange={(e) => setFormData({ ...formData, is_published: e.target.checked })}
                className="w-4 h-4 text-teal-600 rounded border-slate-300 focus:ring-teal-500"
              />
              <label htmlFor="is_published" className="text-sm font-medium text-slate-700 dark:text-slate-300">
                Publicar inmediatamente (visible para todos los usuarios)
              </label>
            </div>
          </Modal.Body>
          <Modal.Footer className="flex justify-end gap-2">
            <Button color="gray" onClick={() => setShowModal(false)} disabled={saving}>
              Cancelar
            </Button>
            <Button type="submit" className="bg-teal-600 hover:bg-teal-700 text-white" disabled={saving}>
              {saving ? <Spinner size="sm" className="mr-2" /> : null}
              {editingFaq ? 'Guardar Cambios' : 'Crear Pregunta'}
            </Button>
          </Modal.Footer>
        </form>
      </Modal>

      {/* Modal Confirmar Borrado */}
      <Modal show={!!deletingFaq} onClose={() => setDeletingFaq(null)} size="sm">
        <Modal.Header>
          <span className="font-bold text-red-600">Eliminar Pregunta FAQ</span>
        </Modal.Header>
        <Modal.Body>
          <p className="text-sm text-slate-600 dark:text-slate-300">
            ¿Estás seguro de que deseas eliminar permanentemente la pregunta:
          </p>
          <p className="font-semibold text-slate-900 dark:text-white text-sm mt-2">
            "{deletingFaq?.question}"?
          </p>
        </Modal.Body>
        <Modal.Footer className="flex justify-end gap-2">
          <Button color="gray" onClick={() => setDeletingFaq(null)} disabled={deleting}>
            Cancelar
          </Button>
          <Button color="failure" onClick={handleDelete} disabled={deleting}>
            {deleting ? <Spinner size="sm" className="mr-2" /> : null}
            Eliminar
          </Button>
        </Modal.Footer>
      </Modal>
    </div>
  );
}

export default AdminFaqsTab;
