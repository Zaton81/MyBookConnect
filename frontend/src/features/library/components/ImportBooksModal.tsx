import React, { useState, useRef } from 'react';
import { Modal, Button, Spinner } from 'flowbite-react';
import { useAuthStore } from '../../../store/auth';

interface PreviewItem {
  row_index: number;
  title: string;
  author: string;
  isbn?: string;
  status: 'want_to_read' | 'reading' | 'read' | 'abandoned';
  rating?: number | null;
  match_status: 'new' | 'in_catalog' | 'in_library';
  existing_book_id?: number | null;
  has_review?: boolean;
  tags?: string[];
}

interface PreviewResponse {
  format: 'goodreads' | 'calibre' | 'generic';
  format_label: string;
  total_rows: number;
  valid_rows: number;
  invalid_rows: number;
  new_books_count: number;
  in_catalog_count: number;
  in_library_count: number;
  preview_items: PreviewItem[];
  raw_items_payload: any[];
}

interface ConfirmResponse {
  success: boolean;
  created_books: number;
  created_user_books: number;
  updated_user_books: number;
  created_reviews: number;
  total_processed: number;
  errors: string[];
}

export interface ImportBooksModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export function ImportBooksModal({ isOpen, onClose, onSuccess }: ImportBooksModalProps) {
  const { token } = useAuthStore();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [dragActive, setDragActive] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [previewData, setPreviewData] = useState<PreviewResponse | null>(null);
  const [importResult, setImportResult] = useState<ConfirmResponse | null>(null);

  const apiUrl = (import.meta as any).env.VITE_API_URL || 'http://localhost:8000';

  const resetState = () => {
    setSelectedFile(null);
    setLoading(false);
    setError(null);
    setPreviewData(null);
    setImportResult(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleClose = () => {
    resetState();
    onClose();
  };

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      if (file.name.endsWith('.csv') || file.type === 'text/csv') {
        processFile(file);
      } else {
        setError('Por favor selecciona un archivo en formato CSV (.csv).');
      }
    }
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      processFile(e.target.files[0]);
    }
  };

  const processFile = async (file: File) => {
    setSelectedFile(file);
    setError(null);
    setLoading(true);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await fetch(`${apiUrl}/api/v1/books/import/csv/preview/`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
      });

      const data = await res.json();
      if (res.ok) {
        setPreviewData(data);
      } else {
        setError(data.error || 'Error al procesar la vista previa del archivo CSV.');
      }
    } catch (err) {
      console.error('Error previewing CSV:', err);
      setError('Error de conexión con el servidor al procesar el archivo CSV.');
    } finally {
      setLoading(false);
    }
  };

  const handleConfirmImport = async () => {
    const itemsPayload = previewData?.raw_items_payload || previewData?.preview_items || [];
    if (!previewData || !itemsPayload.length) {
      setError('No hay libros válidos para importar en el archivo.');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const res = await fetch(`${apiUrl}/api/v1/books/import/csv/confirm/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          items: itemsPayload,
        }),
      });

      const data = await res.json();
      if (res.ok && data.success) {
        setImportResult({
          success: true,
          created_books: data.created_books ?? data.imported_books_count ?? 0,
          created_user_books: data.created_user_books ?? data.added_to_library_count ?? 0,
          updated_user_books: data.updated_user_books ?? data.updated_in_library_count ?? 0,
          created_reviews: data.created_reviews ?? data.reviews_created_count ?? 0,
          total_processed: data.total_processed ?? itemsPayload.length,
          errors: data.errors || [],
        });
        onSuccess();
      } else {
        setError(data.error || data.detail || 'Error durante la ejecución de la importación.');
      }
    } catch (err) {
      console.error('Error importing CSV:', err);
      setError('Error de conexión al importar la biblioteca.');
    } finally {
      setLoading(false);
    }
  };

  const getStatusLabel = (status: string) => {
    switch (status) {
      case 'read':
        return {
          label: 'Leído',
          color: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300',
        };
      case 'reading':
        return {
          label: 'Leyendo',
          color: 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-300',
        };
      case 'want_to_read':
        return {
          label: 'Por leer',
          color: 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300',
        };
      case 'abandoned':
        return {
          label: 'Abandonado',
          color: 'bg-rose-100 text-rose-700 dark:bg-rose-900/40 dark:text-rose-300',
        };
      default:
        return {
          label: status,
          color: 'bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-300',
        };
    }
  };

  return (
    <Modal show={isOpen} onClose={handleClose} size="4xl" popup>
      <div className="bg-white dark:bg-slate-800 rounded-3xl overflow-hidden shadow-2xl flex flex-col max-h-[90vh]">
        {/* Encabezado */}
        <div className="p-5 bg-gradient-to-r from-teal-600 via-teal-700 to-emerald-700 text-white flex items-center justify-between shadow-md">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-2xl bg-white/20 backdrop-blur-md flex items-center justify-center text-xl shadow-inner">
              📥
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-lg font-bold">Importar Biblioteca</h3>
                <span className="text-[10px] font-semibold uppercase px-2.5 py-0.5 rounded-full bg-teal-400/30 text-teal-100 border border-teal-300/40">
                  Goodreads &bull; Calibre &bull; CSV
                </span>
              </div>
              <p className="text-xs text-teal-100/90">
                Añade tus libros, estados de lectura, valoraciones y reseñas masivamente.
              </p>
            </div>
          </div>
          <button
            onClick={handleClose}
            className="text-white/80 hover:text-white rounded-xl p-1.5 hover:bg-white/10 transition-colors text-xl leading-none"
            aria-label="Cerrar"
          >
            &times;
          </button>
        </div>

        {/* Contenido Principal */}
        <div className="p-6 overflow-y-auto space-y-6 flex-1">
          {error && (
            <div className="p-4 rounded-2xl bg-rose-50 dark:bg-rose-900/20 border border-rose-200 dark:border-rose-800 text-rose-700 dark:text-rose-300 text-sm flex items-start gap-3">
              <span className="text-base">⚠️</span>
              <div className="flex-1">
                <span className="font-bold block">Error en la importación:</span>
                <span>{error}</span>
              </div>
            </div>
          )}

          {/* Estado 1: Éxito completado */}
          {importResult ? (
            <div className="text-center py-8 space-y-6">
              <div className="w-20 h-20 mx-auto rounded-full bg-emerald-100 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-400 flex items-center justify-center text-4xl shadow-inner">
                ✓
              </div>
              <div>
                <h4 className="text-2xl font-black text-slate-900 dark:text-white">
                  ¡Importación completada con éxito!
                </h4>
                <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
                  Tu biblioteca y catálogo se han sincronizado correctamente sin duplicados.
                </p>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 max-w-2xl mx-auto">
                <div className="p-3.5 bg-slate-50 dark:bg-slate-700/50 rounded-2xl border border-slate-200/60 dark:border-slate-600">
                  <span className="block text-2xl font-black text-slate-800 dark:text-slate-100">
                    {importResult.total_processed}
                  </span>
                  <span className="text-xs text-slate-500">Procesados</span>
                </div>
                <div className="p-3.5 bg-emerald-50 dark:bg-emerald-900/20 rounded-2xl border border-emerald-200/60 dark:border-emerald-700">
                  <span className="block text-2xl font-black text-emerald-600 dark:text-emerald-400">
                    {importResult.created_user_books}
                  </span>
                  <span className="text-xs text-emerald-600 dark:text-emerald-400">Añadidos</span>
                </div>
                <div className="p-3.5 bg-indigo-50 dark:bg-indigo-900/20 rounded-2xl border border-indigo-200/60 dark:border-indigo-700">
                  <span className="block text-2xl font-black text-indigo-600 dark:text-indigo-400">
                    {importResult.updated_user_books}
                  </span>
                  <span className="text-xs text-indigo-600 dark:text-indigo-400">Actualizados</span>
                </div>
                <div className="p-3.5 bg-amber-50 dark:bg-amber-900/20 rounded-2xl border border-amber-200/60 dark:border-amber-700">
                  <span className="block text-2xl font-black text-amber-600 dark:text-amber-400">
                    {importResult.created_reviews}
                  </span>
                  <span className="text-xs text-amber-600 dark:text-amber-400">Reseñas</span>
                </div>
              </div>

              {importResult.errors && importResult.errors.length > 0 && (
                <div className="text-left bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 p-4 rounded-2xl text-xs text-amber-800 dark:text-amber-200 max-h-36 overflow-y-auto">
                  <span className="font-bold block mb-1">Avisos durante la importación:</span>
                  <ul className="list-disc list-inside space-y-0.5">
                    {importResult.errors.map((err, idx) => (
                      <li key={idx}>{err}</li>
                    ))}
                  </ul>
                </div>
              )}

              <div className="pt-4 flex justify-center">
                <Button
                  color="teal"
                  onClick={handleClose}
                  className="px-6 py-1 rounded-xl font-bold"
                >
                  Ver Mi Biblioteca
                </Button>
              </div>
            </div>
          ) : !previewData ? (
            /* Estado 2: Selector de Archivo / Dropzone */
            <div className="space-y-5">
              <div
                onDragEnter={handleDrag}
                onDragLeave={handleDrag}
                onDragOver={handleDrag}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                className={`border-2 border-dashed rounded-3xl p-8 text-center cursor-pointer transition-all flex flex-col items-center justify-center gap-3 ${
                  dragActive
                    ? 'border-teal-500 bg-teal-50/50 dark:bg-teal-900/20 scale-[1.01]'
                    : 'border-slate-300 dark:border-slate-600 hover:border-teal-400 hover:bg-slate-50 dark:hover:bg-slate-700/40'
                }`}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".csv"
                  className="hidden"
                  onChange={handleFileInputChange}
                />
                <div className="w-16 h-16 rounded-2xl bg-teal-50 dark:bg-teal-900/30 text-teal-600 dark:text-teal-400 flex items-center justify-center text-3xl shadow-inner">
                  📄
                </div>
                <div>
                  <p className="text-base font-bold text-slate-800 dark:text-slate-100">
                    Arrastra aquí tu archivo CSV o{' '}
                    <span className="text-teal-600 dark:text-teal-400 underline">
                      haz clic para examinar
                    </span>
                  </p>
                  <p className="text-xs text-slate-400 dark:text-slate-500 mt-1">
                    Formatos detectados automáticamente: Goodreads Export, Calibre CSV o CSV
                    estándar.
                  </p>
                </div>
              </div>

              {/* Guía rápida de exportación */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="p-4 bg-slate-50 dark:bg-slate-700/40 rounded-2xl border border-slate-200/80 dark:border-slate-700 text-xs text-slate-600 dark:text-slate-300 space-y-1.5">
                  <div className="flex items-center gap-2 font-bold text-slate-800 dark:text-slate-200">
                    <span className="text-amber-500">📖</span>
                    <span>Desde Goodreads</span>
                  </div>
                  <p>
                    Ve a <strong>My Books &rarr; Import and export</strong> y pulsa en{' '}
                    <em>Export Library</em>. Descarga el archivo CSV generado y súbelo aquí.
                  </p>
                </div>
                <div className="p-4 bg-slate-50 dark:bg-slate-700/40 rounded-2xl border border-slate-200/80 dark:border-slate-700 text-xs text-slate-600 dark:text-slate-300 space-y-1.5">
                  <div className="flex items-center gap-2 font-bold text-slate-800 dark:text-slate-200">
                    <span className="text-indigo-500">📚</span>
                    <span>Desde Calibre</span>
                  </div>
                  <p>
                    En Calibre, ve a <strong>Convertir libros &rarr; Crear un catálogo</strong>,
                    selecciona formato <em>CSV</em> e incluye título, autores e identificadores.
                  </p>
                </div>
              </div>
            </div>
          ) : (
            /* Estado 3: Vista previa de libros detectados */
            <div className="space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-slate-50 dark:bg-slate-700/40 p-4 rounded-2xl border border-slate-200/80 dark:border-slate-700">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-semibold text-slate-500">Formato:</span>
                  <span className="px-2.5 py-1 text-xs font-bold rounded-lg bg-teal-100 text-teal-800 dark:bg-teal-900/40 dark:text-teal-300 border border-teal-200 dark:border-teal-700">
                    {previewData.format_label}
                  </span>
                  <span className="text-xs text-slate-400">({selectedFile?.name})</span>
                </div>
                <button
                  onClick={resetState}
                  className="text-xs text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200 underline font-medium"
                >
                  Cambiar archivo
                </button>
              </div>

              {/* Métricas de Vista Previa */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="p-3 bg-slate-50 dark:bg-slate-700/50 rounded-2xl border border-slate-200/60 dark:border-slate-600 text-center">
                  <span className="block text-xl font-bold text-slate-800 dark:text-slate-100">
                    {previewData.valid_rows}
                  </span>
                  <span className="text-[11px] text-slate-500">Válidos para importar</span>
                </div>
                <div className="p-3 bg-emerald-50 dark:bg-emerald-900/20 rounded-2xl border border-emerald-200/60 dark:border-emerald-700 text-center">
                  <span className="block text-xl font-bold text-emerald-600 dark:text-emerald-400">
                    {previewData.new_books_count}
                  </span>
                  <span className="text-[11px] text-emerald-600 dark:text-emerald-400">
                    Libros nuevos
                  </span>
                </div>
                <div className="p-3 bg-amber-50 dark:bg-amber-900/20 rounded-2xl border border-amber-200/60 dark:border-amber-700 text-center">
                  <span className="block text-xl font-bold text-amber-600 dark:text-amber-400">
                    {previewData.in_catalog_count}
                  </span>
                  <span className="text-[11px] text-amber-600 dark:text-amber-400">
                    En catálogo
                  </span>
                </div>
                <div className="p-3 bg-slate-100 dark:bg-slate-700/80 rounded-2xl border border-slate-300/60 dark:border-slate-600 text-center">
                  <span className="block text-xl font-bold text-slate-600 dark:text-slate-300">
                    {previewData.in_library_count}
                  </span>
                  <span className="text-[11px] text-slate-500">Ya en tu estantería</span>
                </div>
              </div>

              {/* Tabla de Libros Detectados */}
              <div className="rounded-2xl border border-slate-200 dark:border-slate-700 overflow-hidden shadow-sm">
                <div className="max-h-72 overflow-y-auto">
                  <table className="w-full text-left border-collapse text-xs">
                    <thead className="bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 sticky top-0 font-bold">
                      <tr>
                        <th className="p-3">Título y Autor</th>
                        <th className="p-3">ISBN</th>
                        <th className="p-3">Estado</th>
                        <th className="p-3">Valoración</th>
                        <th className="p-3 text-right">Destino</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 dark:divide-slate-700/60 text-slate-700 dark:text-slate-200">
                      {previewData.preview_items.map((item) => {
                        const statusBadge = getStatusLabel(item.status);
                        return (
                          <tr
                            key={item.row_index}
                            className="hover:bg-slate-50 dark:hover:bg-slate-700/40 transition-colors"
                          >
                            <td className="p-3">
                              <span
                                className="font-semibold block truncate max-w-xs"
                                title={item.title}
                              >
                                {item.title}
                              </span>
                              <span className="text-[11px] text-slate-400 dark:text-slate-500 block">
                                {item.author || 'Autor desconocido'}
                              </span>
                            </td>
                            <td className="p-3 font-mono text-[11px] text-slate-500">
                              {item.isbn || '—'}
                            </td>
                            <td className="p-3">
                              <span
                                className={`px-2 py-0.5 rounded-md text-[10px] font-bold ${statusBadge.color}`}
                              >
                                {statusBadge.label}
                              </span>
                            </td>
                            <td className="p-3">
                              {item.rating ? (
                                <span className="text-amber-500 font-bold">
                                  {'★'.repeat(item.rating)}
                                  {'☆'.repeat(5 - item.rating)}
                                </span>
                              ) : (
                                <span className="text-slate-400 text-[11px]">—</span>
                              )}
                            </td>
                            <td className="p-3 text-right whitespace-nowrap">
                              {item.match_status === 'new' && (
                                <span className="inline-flex items-center gap-1 text-[11px] font-bold text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-900/30 px-2 py-0.5 rounded-full border border-emerald-200 dark:border-emerald-800">
                                  <span>🟢</span> Nuevo
                                </span>
                              )}
                              {item.match_status === 'in_catalog' && (
                                <span className="inline-flex items-center gap-1 text-[11px] font-bold text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/30 px-2 py-0.5 rounded-full border border-amber-200 dark:border-amber-800">
                                  <span>🟡</span> En catálogo
                                </span>
                              )}
                              {item.match_status === 'in_library' && (
                                <span className="inline-flex items-center gap-1 text-[11px] font-bold text-slate-500 dark:text-slate-400 bg-slate-100 dark:bg-slate-700/60 px-2 py-0.5 rounded-full border border-slate-200 dark:border-slate-600">
                                  <span>⚪</span> En estantería
                                </span>
                              )}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer con Acciones */}
        {!importResult && (
          <div className="p-4 bg-slate-50 dark:bg-slate-700/50 border-t border-slate-200/80 dark:border-slate-700 flex items-center justify-between">
            <button
              onClick={handleClose}
              disabled={loading}
              className="px-4 py-2 text-sm font-semibold text-slate-600 dark:text-slate-300 hover:text-slate-800 dark:hover:text-white rounded-xl hover:bg-slate-200/60 dark:hover:bg-slate-600 transition-colors"
            >
              Cancelar
            </button>

            <div className="flex items-center gap-3">
              {previewData && (
                <button
                  onClick={resetState}
                  disabled={loading}
                  className="px-4 py-2 text-sm font-semibold text-slate-600 dark:text-slate-300 hover:bg-slate-200/60 dark:hover:bg-slate-600 rounded-xl transition-colors"
                >
                  Cambiar archivo
                </button>
              )}

              {previewData ? (
                <Button
                  color="teal"
                  disabled={loading || previewData.valid_rows === 0}
                  onClick={handleConfirmImport}
                  className="px-5 py-0.5 rounded-xl font-bold shadow-md shadow-teal-600/20"
                >
                  {loading ? (
                    <div className="flex items-center gap-2">
                      <Spinner size="sm" />
                      <span>Importando biblioteca...</span>
                    </div>
                  ) : (
                    <span>Confirmar e importar ({previewData.valid_rows} libros)</span>
                  )}
                </Button>
              ) : (
                <Button
                  color="teal"
                  disabled={loading}
                  onClick={() => fileInputRef.current?.click()}
                  className="px-5 py-0.5 rounded-xl font-bold"
                >
                  {loading ? (
                    <div className="flex items-center gap-2">
                      <Spinner size="sm" />
                      <span>Analizando CSV...</span>
                    </div>
                  ) : (
                    <span>Seleccionar CSV</span>
                  )}
                </Button>
              )}
            </div>
          </div>
        )}
      </div>
    </Modal>
  );
}
