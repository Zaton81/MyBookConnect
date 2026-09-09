import React, { useState, useEffect, useRef } from 'react';
import { Modal, Button, Spinner } from 'flowbite-react';
import { useAuthStore } from '../store/auth';

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

interface AIAssistantModalProps {
  isOpen: boolean;
  onClose: () => void;
  contextBookId?: number;
  contextBookTitle?: string;
}

const PROMPT_SUGGESTIONS = [
  '¿Qué libro me recomiendas según mi historial?',
  'Recomiéndame novelas cortas y adictivas',
  '¿Qué leer si me encantó Cien Años de Soledad?',
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
      content: `¡Hola ${user?.username || ''}! Soy **BookAI**, tu asistente literario inteligente. ¿En qué puedo orientarte hoy? Puedes pedirme recomendaciones personalizadas, análisis de autores o sugerencias para tu próxima lectura.`,
    },
  ]);
  const [inputText, setInputText] = useState('');
  const [loading, setLoading] = useState(false);
  const [isAiOnline, setIsAiOnline] = useState<boolean | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const apiUrl = (import.meta as any).env.VITE_API_URL || 'http://localhost:8000';

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
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

  const handleSendMessage = async (textToSend?: string) => {
    const text = (textToSend || inputText).trim();
    if (!text || loading || !token) return;

    const newMessages: Message[] = [...messages, { role: 'user', content: text }];
    setMessages(newMessages);
    setInputText('');
    setLoading(true);

    try {
      const res = await fetch(`${apiUrl}/api/v1/books/ai/assistant/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          messages: newMessages,
          book_id: contextBookId || undefined,
        }),
      });

      if (res.ok) {
        const data = await res.json();
        if (data.message) {
          setMessages((prev) => [...prev, data.message]);
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
      // Reemplazo básico de **texto**
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
                <span
                  className={`text-[10px] font-semibold uppercase px-2 py-0.5 rounded-full ${
                    isAiOnline
                      ? 'bg-emerald-400/30 text-emerald-100 border border-emerald-300/40'
                      : 'bg-amber-400/30 text-amber-100 border border-amber-300/40'
                  }`}
                >
                  {isAiOnline ? 'Neuronal Online' : 'Modo Asistido'}
                </span>
              </div>
              <p className="text-xs text-white/80">
                {contextBookTitle
                  ? `Consultando sobre: ${contextBookTitle}`
                  : 'Recomendaciones inteligentes y guía literaria'}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-white/70 hover:text-white text-xl font-bold w-8 h-8 rounded-lg flex items-center justify-center hover:bg-white/10 transition-colors"
          >
            ✕
          </button>
        </div>

        {/* Historial de Mensajes */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-gray-50/60 dark:bg-gray-900">
          {messages.map((msg, idx) => {
            const isUser = msg.role === 'user';
            return (
              <div
                key={idx}
                className={`flex items-start gap-2.5 ${isUser ? 'flex-row-reverse' : ''}`}
              >
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold shrink-0 ${
                    isUser
                      ? 'bg-teal-700 text-white'
                      : 'bg-gradient-to-tr from-teal-500 to-emerald-400 text-white shadow-sm'
                  }`}
                >
                  {isUser ? user?.username?.[0]?.toUpperCase() || 'Tú' : 'AI'}
                </div>
                <div
                  className={`max-w-[85%] rounded-2xl px-4 py-3 shadow-sm ${
                    isUser
                      ? 'bg-teal-600 text-white rounded-tr-none'
                      : 'bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-100 border border-gray-100 dark:border-gray-700 rounded-tl-none'
                  }`}
                >
                  {renderFormattedContent(msg.content)}
                </div>
              </div>
            );
          })}

          {loading && (
            <div className="flex items-start gap-2.5">
              <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-teal-500 to-emerald-400 text-white flex items-center justify-center text-xs font-bold shrink-0 shadow-sm">
                AI
              </div>
              <div className="bg-white dark:bg-gray-800 border border-gray-100 dark:border-gray-700 rounded-2xl rounded-tl-none px-4 py-3 shadow-sm flex items-center gap-2 text-sm text-gray-500">
                <Spinner size="sm" color="info" />
                <span>BookAI está explorando la biblioteca...</span>
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

        {/* Input Bar */}
        <div className="p-3 bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSendMessage();
            }}
            className="flex items-center space-x-2"
          >
            <input
              type="text"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              placeholder="Pregúntale a BookAI sobre recomendaciones, autores..."
              disabled={loading}
              className="flex-1 text-sm rounded-xl border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-700 dark:text-white focus:ring-teal-500 focus:border-teal-500 py-2.5 px-4"
            />
            <Button
              type="submit"
              color="teal"
              disabled={!inputText.trim() || loading}
              className="rounded-xl px-2"
            >
              Enviar
            </Button>
          </form>
        </div>
      </div>
    </Modal>
  );
}
