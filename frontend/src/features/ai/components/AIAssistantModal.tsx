import { useState, useEffect, useRef } from 'react';
import { Modal, Button, Spinner } from 'flowbite-react';
import { useAuthStore } from '../../../store/auth';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  imageUrl?: string;
  badge?: string;
}

export interface AIAssistantModalProps {
  isOpen: boolean;
  onClose: () => void;
  contextBookId?: number;
  contextBookTitle?: string;
}

const PROMPT_SUGGESTIONS = [
  '¿Qué libro me recomiendas según mi historial?',
  'Explícame el contexto histórico y claves de lectura',
  'Compara dos obras destacadas de este autor o género',
  'Novelas de misterio con giros inesperados',
];

export function AIAssistantModal({
  isOpen,
  onClose,
  contextBookId,
  contextBookTitle,
}: AIAssistantModalProps) {
  const { token, user } = useAuthStore();
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'assistant',
      content: `¡Hola ${user?.username || ''}! Soy **BookAI**, tu asistente literario inteligente. ¿En qué puedo orientarte hoy? Puedes pedirme recomendaciones, análisis temáticos o adjuntarme una foto de portada para analizar su arte.`,
    },
  ]);
  const [inputText, setInputText] = useState('');
  const [attachedImage, setAttachedImage] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [isAiOnline, setIsAiOnline] = useState<boolean | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const apiUrl = (import.meta as any).env.VITE_API_URL || 'http://localhost:8000';

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView?.({ behavior: 'smooth' });
  }, [messages]);

  // Consultar estado de IA al abrir
  useEffect(() => {
    if (isOpen && token) {
      fetch(`${apiUrl}/api/v1/books/ai/status/`, {
        headers: { Authorization: `Bearer ${token}` },
      })
        .then((res) => (res.ok ? res.json() : null))
        .then((data) => {
          if (data) setIsAiOnline(data.is_online);
        })
        .catch(() => setIsAiOnline(false));
    }
  }, [isOpen, token, apiUrl]);

  const handleImageSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file && file.type.startsWith('image/')) {
      const reader = new FileReader();
      reader.onload = () => {
        setAttachedImage(reader.result as string);
      };
      reader.readAsDataURL(file);
    }
  };

  const handleSendMessage = async (textToSend?: string) => {
    const text = (textToSend || inputText).trim();
    if ((!text && !attachedImage) || loading || !token) return;

    const currentImage = attachedImage;
    const userMsg: Message = {
      role: 'user',
      content: text || (currentImage ? '¿Qué puedes decirme sobre esta portada?' : ''),
      imageUrl: currentImage || undefined,
    };

    const newMessages: Message[] = [...messages, userMsg];
    setMessages(newMessages);
    setInputText('');
    setAttachedImage(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
    setLoading(true);

    try {
      // Si hay imagen adjunta, invocar el endpoint multimodal
      const endpoint = currentImage
        ? `${apiUrl}/api/v1/books/ai/multimodal/assistant/`
        : `${apiUrl}/api/v1/books/ai/assistant/`;

      const bodyPayload = currentImage
        ? {
            messages: newMessages.map((m) => ({ role: m.role, content: m.content })),
            image_base64: currentImage,
            book_id: contextBookId || undefined,
          }
        : {
            messages: newMessages.map((m) => ({ role: m.role, content: m.content })),
            book_id: contextBookId || undefined,
          };

      const res = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(bodyPayload),
      });

      if (res.ok) {
        const data = await res.json();
        if (data.message) {
          setMessages((prev) => [
            ...prev,
            {
              role: data.message.role,
              content: data.message.content,
              badge: data.badge,
            },
          ]);
        }
        if (typeof data.ai_online === 'boolean') {
          setIsAiOnline(data.ai_online);
        }
      } else {
        setMessages((prev) => [
          ...prev,
          {
            role: 'assistant',
            content: 'Lo siento, ocurrió un error al procesar tu consulta literaria.',
          },
        ]);
      }
    } catch (err) {
      console.error('Error in BookAI chat', err);
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: 'Error de conexión con el servicio de IA.',
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  // Renderizar markdown sencillo con negritas y listas
  const renderFormattedContent = (content: string) => {
    const lines = content.split('\n');
    return lines.map((line, idx) => {
      const parts = line.split(/(\*\*.*?\*\*)/g);
      const formattedParts = parts.map((part, pIdx) => {
        if (part.startsWith('**') && part.endsWith('**')) {
          return (
            <strong key={pIdx} className="font-semibold text-teal-900 dark:text-teal-200">
              {part.slice(2, -2)}
            </strong>
          );
        }
        return part;
      });

      if (line.trim().startsWith('- ') || line.trim().startsWith('* ')) {
        return (
          <li key={idx} className="ml-4 list-disc text-sm my-1">
            {formattedParts}
          </li>
        );
      }

      return (
        <p key={idx} className="my-1.5 text-sm leading-relaxed">
          {formattedParts}
        </p>
      );
    });
  };

  return (
    <Modal show={isOpen} onClose={onClose} size="xl" popup>
      <div className="bg-white dark:bg-gray-800 rounded-2xl overflow-hidden shadow-2xl flex flex-col h-[650px] max-h-[85vh]">
        {/* Encabezado */}
        <div className="p-4 bg-gradient-to-r from-teal-600 to-emerald-600 text-white flex items-center justify-between shadow-md">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-white/20 backdrop-blur-md flex items-center justify-center text-xl shadow-inner">
              ✨
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-lg font-bold">BookAI Assistant</h3>
                <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-white/20 text-teal-100 border border-white/20">
                  Multimodal
                </span>
              </div>
              <p className="text-xs text-teal-100">
                {contextBookTitle
                  ? `Contexto: ${contextBookTitle}`
                  : 'Asistente literario y análisis visual'}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            {isAiOnline !== null && (
              <span
                className={`text-[10px] font-bold px-2 py-0.5 rounded-full border flex items-center gap-1 ${
                  isAiOnline
                    ? 'bg-emerald-500/20 text-emerald-100 border-emerald-400/30'
                    : 'bg-amber-500/20 text-amber-100 border-amber-400/30'
                }`}
              >
                <span className={`w-1.5 h-1.5 rounded-full ${isAiOnline ? 'bg-emerald-300' : 'bg-amber-300'}`} />
                {isAiOnline ? 'En línea' : 'Modo local'}
              </span>
            )}
            <button
              onClick={onClose}
              aria-label="Cerrar modal"
              className="text-white/80 hover:text-white p-1 rounded-lg hover:bg-white/10 transition-colors"
            >
              ✕
            </button>
          </div>
        </div>

        {/* Zona de Mensajes */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-gray-50/50 dark:bg-gray-900/50">
          {messages.map((msg, idx) => (
            <div
              key={idx}
              className={`flex items-start gap-2.5 ${
                msg.role === 'user' ? 'justify-end' : 'justify-start'
              }`}
            >
              {msg.role === 'assistant' && (
                <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-teal-500 to-emerald-400 text-white flex items-center justify-center text-xs font-bold shrink-0 shadow-sm">
                  AI
                </div>
              )}
              <div
                className={`max-w-[85%] rounded-2xl px-4 py-3 shadow-xs space-y-2 ${
                  msg.role === 'user'
                    ? 'bg-teal-600 text-white rounded-tr-none'
                    : 'bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-200 border border-gray-100 dark:border-gray-700 rounded-tl-none'
                }`}
              >
                {/* Imagen adjunta por el usuario */}
                {msg.imageUrl && (
                  <div className="rounded-xl overflow-hidden border border-white/20 max-w-[200px]">
                    <img
                      src={msg.imageUrl}
                      alt="Portada adjunta"
                      className="w-full h-auto object-cover max-h-40"
                    />
                  </div>
                )}

                <div>{renderFormattedContent(msg.content)}</div>

                {msg.badge && (
                  <span className="inline-block text-[9px] uppercase font-bold px-1.5 py-0.5 rounded bg-teal-50 dark:bg-teal-950/60 text-teal-700 dark:text-teal-300 border border-teal-200 dark:border-teal-800">
                    {msg.badge}
                  </span>
                )}
              </div>
            </div>
          ))}

          {loading && (
            <div className="flex items-start gap-2.5">
              <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-teal-500 to-emerald-400 text-white flex items-center justify-center text-xs font-bold shrink-0 shadow-sm">
                AI
              </div>
              <div className="bg-white dark:bg-gray-800 border border-gray-100 dark:border-gray-700 rounded-2xl rounded-tl-none px-4 py-3 shadow-sm flex items-center gap-2 text-sm text-gray-500">
                <Spinner size="sm" color="info" />
                <span>BookAI está analizando la consulta y visión multimodal...</span>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Sugerencias Rápidas */}
        {messages.length <= 2 && (
          <div className="px-4 py-2 bg-gray-50 dark:bg-gray-800 border-t border-gray-100 dark:border-gray-700 flex flex-wrap gap-1.5">
            {PROMPT_SUGGESTIONS.map((prompt, i) => (
              <button
                key={i}
                onClick={() => handleSendMessage(prompt)}
                className="text-xs bg-white dark:bg-gray-700 border border-teal-200 dark:border-teal-800 text-teal-700 dark:text-teal-300 rounded-full px-3 py-1 hover:bg-teal-50 dark:hover:bg-teal-900/30 transition-all shadow-sm"
              >
                {prompt}
              </button>
            ))}
          </div>
        )}

        {/* Input Bar con soporte Multimodal */}
        <div className="p-3 bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700">
          {/* Previsualización de imagen adjunta antes de enviar */}
          {attachedImage && (
            <div className="mb-2 p-2 bg-teal-50 dark:bg-teal-950/40 rounded-xl border border-teal-200 dark:border-teal-800 flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <img
                  src={attachedImage}
                  alt="Miniatura adjunta"
                  className="w-10 h-10 object-cover rounded-lg border border-teal-300"
                />
                <div>
                  <span className="text-xs font-bold text-teal-900 dark:text-teal-200">
                    📷 Imagen adjunta para visión IA
                  </span>
                  <p className="text-[10px] text-teal-700 dark:text-teal-400">
                    Se analizará junto con tu mensaje
                  </p>
                </div>
              </div>
              <button
                onClick={() => {
                  setAttachedImage(null);
                  if (fileInputRef.current) fileInputRef.current.value = '';
                }}
                className="p-1 text-slate-400 hover:text-rose-600 rounded-full hover:bg-white dark:hover:bg-slate-800"
                title="Descartar imagen"
              >
                ✕
              </button>
            </div>
          )}

          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSendMessage();
            }}
            className="flex items-center space-x-2"
          >
            {/* Botón de adjuntar imagen */}
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              className="p-2.5 rounded-xl border border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-700 hover:bg-teal-50 dark:hover:bg-teal-950 text-slate-600 dark:text-slate-300 hover:text-teal-600 transition-colors"
              title="Adjuntar foto de portada o página"
              aria-label="Adjuntar foto de portada"
            >
              📷
            </button>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              onChange={handleImageSelect}
              className="hidden"
            />

            <input
              type="text"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              placeholder={
                attachedImage
                  ? 'Pregunta sobre la imagen o pulsa enviar...'
                  : 'Pregúntale a BookAI sobre recomendaciones, autores...'
              }
              disabled={loading}
              className="flex-1 text-sm rounded-xl border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-700 dark:text-white focus:ring-teal-500 focus:border-teal-500 py-2.5 px-4"
            />
            <Button
              type="submit"
              color="teal"
              disabled={(!inputText.trim() && !attachedImage) || loading}
              className="rounded-xl px-2"
            >
              Enviar
            </Button>
          </form>
          <p className="text-[10px] text-gray-500 dark:text-gray-400 text-center mt-2 flex items-center justify-center gap-1">
            <span>ℹ️</span>
            <span>
              BookAI es una inteligencia artificial literaria multimodal. Las respuestas son orientativas.
            </span>
          </p>
        </div>
      </div>
    </Modal>
  );
}

export default AIAssistantModal;
