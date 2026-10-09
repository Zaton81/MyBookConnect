import React, { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../../../store/auth';

interface VisualSearchResult {
  status: string;
  is_ai_generated: boolean;
  badge: string;
  art_style: string;
  mood_atmosphere: string;
  color_palette: Array<{ name: string; hex: string }>;
  accessible_alt_text: string;
  matching_book?: {
    id: number;
    title: string;
    author_name: string;
    cover?: string | null;
    match_confidence: number;
  } | null;
}

interface VisualBookSearchModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const VisualBookSearchModal: React.FC<VisualBookSearchModalProps> = ({ isOpen, onClose }) => {
  const { token } = useAuthStore();
  const navigate = useNavigate();
  const [selectedImage, setSelectedImage] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<VisualSearchResult | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const apiUrl = (import.meta as any).env.VITE_API_URL || 'http://localhost:8000';

  if (!isOpen) return null;

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      if (!file.type.startsWith('image/')) {
        setError('Por favor selecciona un archivo de imagen válido (JPEG, PNG, WebP).');
        return;
      }
      setError(null);
      setResult(null);
      const reader = new FileReader();
      reader.onload = () => {
        setSelectedImage(reader.result as string);
      };
      reader.readAsDataURL(file);
    }
  };

  const handleAnalyzeImage = async () => {
    if (!selectedImage || !token) return;
    setLoading(true);
    setError(null);

    try {
      const res = await fetch(`${apiUrl}/api/v1/books/ai/multimodal/analyze-cover/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          image_base64: selectedImage,
        }),
      });

      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new Error(errJson.detail || 'Error al analizar la imagen con BookAI.');
      }

      const json: VisualSearchResult = await res.json();
      setResult(json);
    } catch (err: any) {
      setError(err.message || 'No se pudo completar el análisis visual de la portada.');
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setSelectedImage(null);
    setResult(null);
    setError(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="visual-search-title"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/70 backdrop-blur-sm animate-fade-in"
    >
      <div className="relative w-full max-w-lg bg-white dark:bg-slate-900 rounded-3xl shadow-2xl border border-slate-200 dark:border-slate-800 overflow-hidden flex flex-col max-h-[90vh]">
        {/* Cabecera */}
        <div className="p-5 sm:p-6 border-b border-slate-100 dark:border-slate-800 flex items-start justify-between bg-gradient-to-r from-teal-500/10 via-indigo-500/5 to-transparent">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-xl">📷</span>
              <span className="text-xs uppercase font-extrabold tracking-wider px-2 py-0.5 rounded-full bg-teal-100 dark:bg-teal-950 text-teal-800 dark:text-teal-300 border border-teal-200 dark:border-teal-800">
                Búsqueda Visual & Portadas
              </span>
            </div>
            <h3 id="visual-search-title" className="text-lg sm:text-xl font-black text-slate-900 dark:text-white">
              Identificar libro por foto de portada
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              Sube una fotografía de la cubierta o estantería para localizar la obra y analizar su arte.
            </p>
          </div>

          <button
            onClick={onClose}
            aria-label="Cerrar modal"
            className="p-2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 rounded-full hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
          >
            ✕
          </button>
        </div>

        {/* Cuerpo */}
        <div className="p-5 sm:p-6 overflow-y-auto space-y-4 flex-1">
          {error && (
            <div className="p-3.5 rounded-2xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900 text-xs text-rose-700 dark:text-rose-300">
              {error}
            </div>
          )}

          {!selectedImage ? (
            <div
              onClick={() => fileInputRef.current?.click()}
              className="border-2 border-dashed border-slate-300 dark:border-slate-700 hover:border-teal-500 dark:hover:border-teal-400 rounded-3xl p-8 flex flex-col items-center justify-center gap-3 cursor-pointer transition-all hover:bg-slate-50/50 dark:hover:bg-slate-800/30 text-center"
            >
              <div className="w-14 h-14 rounded-2xl bg-teal-50 dark:bg-teal-950/80 text-teal-600 dark:text-teal-400 flex items-center justify-center text-2xl shadow-xs">
                📸
              </div>
              <div>
                <p className="text-sm font-bold text-slate-800 dark:text-slate-200">
                  Haz clic para subir o arrastra una foto
                </p>
                <p className="text-xs text-slate-400 mt-0.5">Formatos JPEG, PNG, WebP (máx. 10MB)</p>
              </div>
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                onChange={handleFileChange}
                className="hidden"
              />
            </div>
          ) : (
            <div className="space-y-4">
              <div className="relative rounded-2xl overflow-hidden bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 flex justify-center p-3">
                <img
                  src={selectedImage}
                  alt="Portada seleccionada"
                  className="max-h-56 object-contain rounded-xl shadow-md"
                />
                <button
                  onClick={handleReset}
                  className="absolute top-3 right-3 px-2.5 py-1 text-xs font-bold bg-slate-900/80 hover:bg-slate-900 text-white rounded-xl backdrop-blur-xs transition-colors"
                >
                  Cambiar foto
                </button>
              </div>

              {!result && (
                <button
                  onClick={handleAnalyzeImage}
                  disabled={loading}
                  className="w-full py-3 bg-gradient-to-r from-teal-600 to-indigo-600 hover:from-teal-700 hover:to-indigo-700 text-white font-extrabold text-xs rounded-2xl shadow-md transition-all flex items-center justify-center gap-2 disabled:opacity-50"
                >
                  {loading ? (
                    <>
                      <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                      <span>Analizando portada con Visión Multimodal...</span>
                    </>
                  ) : (
                    <>
                      <span>🔍</span>
                      <span>Identificar y analizar con BookAI</span>
                    </>
                  )}
                </button>
              )}
            </div>
          )}

          {/* Resultados del análisis */}
          {result && (
            <div className="p-4 rounded-2xl bg-gradient-to-br from-teal-50/60 to-indigo-50/40 dark:from-slate-800/80 dark:to-teal-950/30 border border-teal-200 dark:border-teal-800 space-y-3.5">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-extrabold text-teal-800 dark:text-teal-300 flex items-center gap-1">
                  <span>✨</span>
                  <span>Resultado del análisis visual</span>
                </span>
                <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded-full bg-teal-200 dark:bg-teal-900 text-teal-900 dark:text-teal-200">
                  {result.badge}
                </span>
              </div>

              {/* Libro coincidente */}
              {result.matching_book && (
                <div className="p-3 rounded-xl bg-white dark:bg-slate-900 border border-teal-100 dark:border-slate-700 flex items-center justify-between gap-3 shadow-xs">
                  <div className="flex items-center gap-3">
                    {result.matching_book.cover ? (
                      <img
                        src={result.matching_book.cover}
                        alt={result.matching_book.title}
                        className="w-10 h-14 object-cover rounded-lg shadow-xs"
                      />
                    ) : (
                      <div className="w-10 h-14 rounded-lg bg-slate-200 dark:bg-slate-700 flex items-center justify-center text-xs">
                        📖
                      </div>
                    )}
                    <div>
                      <h4 className="text-xs font-bold text-slate-900 dark:text-white leading-tight">
                        {result.matching_book.title}
                      </h4>
                      <p className="text-[11px] text-slate-500 mt-0.5">{result.matching_book.author_name}</p>
                      <span className="text-[10px] font-semibold text-emerald-600 dark:text-emerald-400">
                        ✓ Coincidencia detectada ({(result.matching_book.match_confidence * 100).toFixed(0)}%)
                      </span>
                    </div>
                  </div>

                  <button
                    onClick={() => {
                      onClose();
                      navigate(`/books/${result.matching_book?.id}`);
                    }}
                    className="px-3 py-1.5 bg-teal-600 hover:bg-teal-700 text-white font-bold text-xs rounded-xl shadow-xs transition-colors whitespace-nowrap"
                  >
                    Ver ficha →
                  </button>
                </div>
              )}

              {/* Paleta de colores */}
              <div>
                <p className="text-[11px] font-bold text-slate-700 dark:text-slate-300 mb-1.5">
                  Paleta cromática identificada:
                </p>
                <div className="flex flex-wrap gap-2">
                  {result.color_palette.map((color, idx) => (
                    <div
                      key={idx}
                      className="flex items-center gap-1.5 px-2 py-1 rounded-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-[10px]"
                    >
                      <span
                        className="w-3.5 h-3.5 rounded-full border border-black/10 shrink-0"
                        style={{ backgroundColor: color.hex }}
                      />
                      <span className="font-semibold text-slate-800 dark:text-slate-200">{color.name}</span>
                      <span className="text-slate-400 font-mono text-[9px]">{color.hex}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Estilo y atmósfera */}
              <div className="text-xs space-y-1 text-slate-600 dark:text-slate-300">
                <p>
                  <span className="font-bold text-slate-800 dark:text-slate-200">Estilo artístico:</span>{' '}
                  {result.art_style}
                </p>
                <p>
                  <span className="font-bold text-slate-800 dark:text-slate-200">Atmósfera:</span>{' '}
                  {result.mood_atmosphere}
                </p>
              </div>

              {/* Alt-Text accesible */}
              <div className="pt-2 border-t border-teal-100 dark:border-slate-800">
                <p className="text-[10px] text-slate-400 leading-relaxed italic">
                  ♿ <span className="font-semibold">Descripción accesible generada:</span> {result.accessible_alt_text}
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Pie */}
        <div className="p-4 bg-slate-50 dark:bg-slate-950/80 border-t border-slate-100 dark:border-slate-800 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-slate-200 hover:bg-slate-300 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-800 dark:text-slate-200 font-bold text-xs rounded-xl transition-colors"
          >
            Cerrar
          </button>
        </div>
      </div>
    </div>
  );
};

export default VisualBookSearchModal;
