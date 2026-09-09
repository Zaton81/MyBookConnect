import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/auth';
import { useChatWebSocket, ChatMessage } from '../hooks/useChatWebSocket';
import { Spinner } from 'flowbite-react';

interface Participant {
  id: number;
  username: string;
  first_name?: string;
  last_name?: string;
  avatar?: string;
}

interface Conversation {
  id: number;
  participants: number[];
  participants_details?: Participant[];
  created_at: string;
  updated_at: string;
  last_message?: ChatMessage | null;
  unread_count?: number;
}

export function Chat() {
  const { user, token } = useAuthStore();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const initialConvId = searchParams.get('conversationId')
    ? Number(searchParams.get('conversationId'))
    : null;

  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConvId, setActiveConvId] = useState<number | null>(initialConvId);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputText, setInputText] = useState('');
  const [loadingConvs, setLoadingConvs] = useState(true);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const apiUrl = (import.meta as any).env.VITE_API_URL || 'http://localhost:8000';

  // Scroll al final al recibir o cargar mensajes
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Cargar lista de conversaciones
  const fetchConversations = useCallback(async () => {
    if (!token) return;
    try {
      setLoadingConvs(true);
      const res = await fetch(`${apiUrl}/api/v1/chat/conversations/`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        const convList: Conversation[] = Array.isArray(data) ? data : data.results || [];
        setConversations(convList);

        if (!activeConvId && convList.length > 0) {
          setActiveConvId(convList[0].id);
        }
      }
    } catch (e) {
      console.error('Error fetching conversations', e);
    } finally {
      setLoadingConvs(false);
    }
  }, [token, apiUrl, activeConvId]);

  useEffect(() => {
    fetchConversations();
  }, [fetchConversations]);

  // Cargar mensajes de la conversación activa
  const fetchMessages = useCallback(async (convId: number) => {
    if (!token) return;
    try {
      setLoadingMessages(true);
      const res = await fetch(`${apiUrl}/api/v1/chat/messages/?conversation=${convId}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        const msgList: ChatMessage[] = Array.isArray(data) ? data : data.results || [];
        setMessages(msgList);
      }
    } catch (e) {
      console.error('Error fetching messages', e);
    } finally {
      setLoadingMessages(false);
    }
  }, [token, apiUrl]);

  useEffect(() => {
    if (activeConvId) {
      fetchMessages(activeConvId);
      setSearchParams({ conversationId: String(activeConvId) });
    }
  }, [activeConvId, fetchMessages, setSearchParams]);

  // Callback de WebSocket para nuevos mensajes entrantes
  const handleMessageReceived = useCallback((newMsg: ChatMessage) => {
    if (newMsg.conversation === activeConvId) {
      setMessages((prev) => {
        // Evitar duplicados por id
        if (prev.some((m) => m.id === newMsg.id)) return prev;
        return [...prev, newMsg];
      });
    }

    // Actualizar el último mensaje en la lista de conversaciones
    setConversations((prev) =>
      prev.map((c) =>
        c.id === newMsg.conversation
          ? { ...c, last_message: newMsg, updated_at: newMsg.created_at }
          : c
      )
    );
  }, [activeConvId]);

  const { isConnected, sendMessage, markRead } = useChatWebSocket({
    conversationId: activeConvId,
    onMessageReceived: handleMessageReceived,
  });

  // Marcar como leído al entrar
  useEffect(() => {
    if (activeConvId && isConnected) {
      markRead();
    }
  }, [activeConvId, isConnected, markRead]);

  const handleSend = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const text = inputText.trim();
    if (!text || !activeConvId) return;

    const sent = sendMessage(text);
    if (sent) {
      setInputText('');
    } else {
      // Fallback REST si WebSocket no está conectado
      fetch(`${apiUrl}/api/v1/chat/messages/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          conversation: activeConvId,
          text,
        }),
      })
        .then((res) => res.json())
        .then((data) => {
          setMessages((prev) => [...prev, data]);
          setInputText('');
        })
        .catch(console.error);
    }
  };

  // Obtener el interlocutor de la conversación activa
  const activeConversation = conversations.find((c) => c.id === activeConvId);
  const otherParticipant = activeConversation?.participants_details?.find(
    (p) => p.id !== user?.id
  );

  const filteredConversations = conversations.filter((c) => {
    if (!searchQuery) return true;
    const other = c.participants_details?.find((p) => p.id !== user?.id);
    const name = other?.username?.toLowerCase() || '';
    return name.includes(searchQuery.toLowerCase());
  });

  return (
    <div className="max-w-7xl mx-auto py-4 px-2 sm:px-4">
      <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl overflow-hidden border border-gray-100 dark:border-gray-700 flex flex-col md:flex-row h-[calc(100vh-140px)] min-h-[500px]">
        {/* ── Barra Lateral: Lista de Conversaciones ── */}
        <div className="w-full md:w-80 lg:w-96 border-r border-gray-200 dark:border-gray-700 flex flex-col bg-gray-50/50 dark:bg-gray-800/50">
          <div className="p-4 border-b border-gray-200 dark:border-gray-700">
            <h1 className="text-xl font-bold text-gray-900 dark:text-white flex items-center justify-between">
              <span>Mensajes</span>
              <span className="text-xs font-medium px-2.5 py-1 rounded-full bg-teal-100 text-teal-800 dark:bg-teal-900/40 dark:text-teal-300">
                {conversations.length} {conversations.length === 1 ? 'chat' : 'chats'}
              </span>
            </h1>
            <div className="mt-3">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Buscar conversación..."
                className="w-full text-sm rounded-xl border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-700 dark:text-white focus:ring-teal-500 focus:border-teal-500 py-2 px-3"
              />
            </div>
          </div>

          <div className="flex-1 overflow-y-auto divide-y divide-gray-100 dark:divide-gray-700/50">
            {loadingConvs ? (
              <div className="flex justify-center items-center p-8">
                <Spinner size="md" color="info" />
              </div>
            ) : filteredConversations.length === 0 ? (
              <div className="p-6 text-center text-sm text-gray-500 dark:text-gray-400">
                No tienes conversaciones activas. Conecta con amigos desde la sección de{' '}
                <button
                  onClick={() => navigate('/friends')}
                  className="text-teal-600 hover:underline font-medium"
                >
                  Amigos
                </button>{' '}
                o visita sus perfiles para chatear.
              </div>
            ) : (
              filteredConversations.map((c) => {
                const other = c.participants_details?.find((p) => p.id !== user?.id);
                const isActive = c.id === activeConvId;
                const lastMsg = c.last_message;

                return (
                  <button
                    key={c.id}
                    onClick={() => setActiveConvId(c.id)}
                    className={`w-full text-left p-3.5 flex items-center space-x-3 transition-colors ${
                      isActive
                        ? 'bg-teal-50 dark:bg-teal-900/20 border-l-4 border-teal-500'
                        : 'hover:bg-gray-100/60 dark:hover:bg-gray-700/40'
                    }`}
                  >
                    <div className="relative">
                      {other?.avatar ? (
                        <img
                          src={other.avatar}
                          alt={other.username}
                          className="w-12 h-12 rounded-full object-cover border border-gray-200 dark:border-gray-600"
                        />
                      ) : (
                        <div className="w-12 h-12 rounded-full bg-teal-600 text-white flex items-center justify-center font-bold text-lg shadow-sm">
                          {other?.username?.[0]?.toUpperCase() || 'U'}
                        </div>
                      )}
                      {isActive && isConnected && (
                        <span className="absolute bottom-0 right-0 w-3.5 h-3.5 bg-emerald-500 border-2 border-white dark:border-gray-800 rounded-full" />
                      )}
                    </div>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between">
                        <p className="text-sm font-semibold text-gray-900 dark:text-white truncate">
                          {other?.username || `Conversación #${c.id}`}
                        </p>
                        {lastMsg && (
                          <span className="text-xs text-gray-400">
                            {new Date(lastMsg.created_at).toLocaleTimeString([], {
                              hour: '2-digit',
                              minute: '2-digit',
                            })}
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-gray-500 dark:text-gray-400 truncate mt-0.5">
                        {lastMsg ? lastMsg.text : 'Conversación iniciada'}
                      </p>
                    </div>

                    {c.unread_count && c.unread_count > 0 ? (
                      <span className="inline-flex items-center justify-center w-5 h-5 text-xs font-bold text-white bg-teal-600 rounded-full">
                        {c.unread_count}
                      </span>
                    ) : null}
                  </button>
                );
              })
            )}
          </div>
        </div>

        {/* ── Panel Principal: Hilo de Chat ── */}
        <div className="flex-1 flex flex-col bg-white dark:bg-gray-900">
          {activeConvId ? (
            <>
              {/* Encabezado del chat */}
              <div className="p-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between bg-white dark:bg-gray-800 shadow-sm z-10">
                <div className="flex items-center space-x-3">
                  {otherParticipant?.avatar ? (
                    <img
                      src={otherParticipant.avatar}
                      alt={otherParticipant.username}
                      className="w-10 h-10 rounded-full object-cover"
                    />
                  ) : (
                    <div className="w-10 h-10 rounded-full bg-teal-600 text-white flex items-center justify-center font-bold shadow-sm">
                      {otherParticipant?.username?.[0]?.toUpperCase() || 'U'}
                    </div>
                  )}
                  <div>
                    <h2
                      onClick={() =>
                        otherParticipant && navigate(`/users/${otherParticipant.id}`)
                      }
                      className="text-base font-bold text-gray-900 dark:text-white cursor-pointer hover:underline flex items-center gap-2"
                    >
                      {otherParticipant?.username || 'Usuario'}
                    </h2>
                    <div className="flex items-center gap-1.5 text-xs">
                      <span
                        className={`w-2 h-2 rounded-full ${
                          isConnected ? 'bg-emerald-500' : 'bg-amber-400 animate-pulse'
                        }`}
                      />
                      <span className="text-gray-500 dark:text-gray-400">
                        {isConnected ? 'En tiempo real' : 'Conectando...'}
                      </span>
                    </div>
                  </div>
                </div>

                {otherParticipant && (
                  <button
                    onClick={() => navigate(`/users/${otherParticipant.id}`)}
                    className="text-xs font-medium text-teal-600 hover:text-teal-700 dark:text-teal-400 px-3 py-1.5 rounded-lg border border-teal-200 dark:border-teal-800 hover:bg-teal-50 dark:hover:bg-teal-900/30 transition-colors"
                  >
                    Ver Perfil
                  </button>
                )}
              </div>

              {/* Contenedor de mensajes con scroll */}
              <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-4 bg-gray-50/50 dark:bg-gray-900">
                {loadingMessages ? (
                  <div className="flex justify-center items-center h-full">
                    <Spinner size="lg" color="info" />
                  </div>
                ) : messages.length === 0 ? (
                  <div className="flex flex-col items-center justify-center h-full text-center text-gray-400 p-6">
                    <div className="w-16 h-16 rounded-full bg-teal-100 dark:bg-teal-900/30 text-teal-600 flex items-center justify-center text-2xl mb-3">
                      💬
                    </div>
                    <p className="text-base font-medium text-gray-700 dark:text-gray-300">
                      ¡Saluda a {otherParticipant?.username || 'tu amigo'}!
                    </p>
                    <p className="text-xs text-gray-500 mt-1 max-w-sm">
                      Comparte recomendaciones de libros, comenta lecturas o intercambia opiniones literarias.
                    </p>
                  </div>
                ) : (
                  messages.map((m) => {
                    const isMine = m.sender === user?.id;
                    return (
                      <div
                        key={m.id}
                        className={`flex flex-col ${isMine ? 'items-end' : 'items-start'}`}
                      >
                        <div
                          className={`max-w-[80%] sm:max-w-[70%] rounded-2xl px-4 py-2.5 shadow-sm text-sm ${
                            isMine
                              ? 'bg-teal-600 text-white rounded-br-none'
                              : 'bg-white dark:bg-gray-800 text-gray-900 dark:text-white border border-gray-100 dark:border-gray-700 rounded-bl-none'
                          }`}
                        >
                          <p className="whitespace-pre-wrap break-words">{m.text}</p>
                        </div>
                        <div className="flex items-center gap-1 mt-1 text-[11px] text-gray-400 px-1">
                          <span>
                            {new Date(m.created_at).toLocaleTimeString([], {
                              hour: '2-digit',
                              minute: '2-digit',
                            })}
                          </span>
                          {isMine && (
                            <span>{m.read ? '• Leído' : '• Enviado'}</span>
                          )}
                        </div>
                      </div>
                    );
                  })
                )}
                <div ref={messagesEndRef} />
              </div>

              {/* Formulario de envío */}
              <div className="p-3 sm:p-4 bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700">
                <form onSubmit={handleSend} className="flex items-center space-x-2">
                  <input
                    type="text"
                    value={inputText}
                    onChange={(e) => setInputText(e.target.value)}
                    placeholder="Escribe un mensaje literario..."
                    className="flex-1 text-sm rounded-xl border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-700 dark:text-white focus:ring-teal-500 focus:border-teal-500 py-2.5 px-4"
                  />
                  <button
                    type="submit"
                    disabled={!inputText.trim()}
                    className="bg-teal-600 hover:bg-teal-700 disabled:opacity-50 text-white font-medium rounded-xl px-5 py-2.5 text-sm transition-all shadow-md shadow-teal-600/20 flex items-center gap-1.5"
                  >
                    <span>Enviar</span>
                    <span>➔</span>
                  </button>
                </form>
              </div>
            </>
          ) : (
            <div className="flex flex-col items-center justify-center h-full text-center p-8 text-gray-400">
              <div className="w-20 h-20 rounded-full bg-teal-50 dark:bg-teal-900/20 text-teal-600 flex items-center justify-center text-4xl mb-4">
                📚
              </div>
              <h2 className="text-xl font-bold text-gray-800 dark:text-white">
                Bandeja de Mensajes
              </h2>
              <p className="text-sm text-gray-500 mt-2 max-w-sm">
                Selecciona una conversación a la izquierda o inicia un chat con tus amigos desde sus perfiles.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
