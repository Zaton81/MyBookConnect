import { useEffect, useRef, useState, useCallback } from 'react';
import { useAuthStore } from '../store/auth';

export interface ChatMessage {
  id: number;
  conversation: number;
  sender: number;
  sender_details?: {
    id: number;
    username: string;
    avatar?: string;
  };
  client_message_id?: string | null;
  text: string;
  image?: string | null;
  created_at: string;
  read: boolean;
  is_duplicate?: boolean;
}

interface UseChatWebSocketOptions {
  conversationId: number | null;
  onMessageReceived?: (message: ChatMessage) => void;
  onMessagesRead?: (
    conversationId: number,
    readerId?: number,
    lastReadMessageId?: number | null
  ) => void;
}

export function useChatWebSocket({
  conversationId,
  onMessageReceived,
  onMessagesRead,
}: UseChatWebSocketOptions) {
  const token = useAuthStore((s) => s.token);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<any>(null);
  const heartbeatIntervalRef = useRef<any>(null);
  const retryCountRef = useRef(0);

  const connect = useCallback(async () => {
    if (!conversationId || !token) return;

    if (wsRef.current) {
      wsRef.current.close();
    }

    const apiUrl = (import.meta as any).env.VITE_API_URL || 'http://localhost:8000';
    const wsProtocol = apiUrl.startsWith('https') ? 'wss' : 'ws';
    const wsHost = apiUrl.replace(/^https?:\/\//, '');

    // Intentar obtener un ticket efímero de un solo uso (RFC 6455 / OWASP)
    let authQuery = `token=${encodeURIComponent(token)}`;
    try {
      const ticketRes = await fetch(`${apiUrl}/api/v1/auth/ws-ticket/`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });
      if (ticketRes.ok) {
        const ticketData = await ticketRes.json();
        if (ticketData?.ticket) {
          authQuery = `ticket=${encodeURIComponent(ticketData.ticket)}`;
        }
      }
    } catch {
      // Fallback a token directo si no se puede obtener el ticket
    }

    const wsUrl = `${wsProtocol}://${wsHost}/ws/chat/${conversationId}/?${authQuery}`;

    try {
      const socket = new WebSocket(wsUrl);
      wsRef.current = socket;

      socket.onopen = () => {
        setIsConnected(true);
        setError(null);
        retryCountRef.current = 0;

        // Iniciar Heartbeat cada 30 segundos para mantener la conexión viva y detectar stale sockets
        if (heartbeatIntervalRef.current) clearInterval(heartbeatIntervalRef.current);
        heartbeatIntervalRef.current = setInterval(() => {
          if (socket.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify({ action: 'ping', timestamp: new Date().toISOString() }));
          }
        }, 30000);
      };

      socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.event === 'pong') {
            // Heartbeat ACK recibido correctamente
            return;
          }
          if (data.event === 'message') {
            onMessageReceived?.(data);
          } else if (data.event === 'read') {
            onMessagesRead?.(data.conversation, data.reader_id, data.last_read_message_id);
          }
        } catch (e) {
          console.error('Error parsing WebSocket message', e);
        }
      };

      socket.onerror = (e) => {
        console.warn('WebSocket error', e);
        setError('Error en la conexión en tiempo real');
      };

      socket.onclose = (event) => {
        setIsConnected(false);
        if (heartbeatIntervalRef.current) {
          clearInterval(heartbeatIntervalRef.current);
          heartbeatIntervalRef.current = null;
        }

        // Si no fue cierre intencionado ni error fatal de autenticación (4001/4003), reconectar con backoff exponencial
        if (event.code !== 1000 && event.code !== 4001 && event.code !== 4003) {
          const backoffDelay = Math.min(
            1000 * Math.pow(1.5, retryCountRef.current) + Math.random() * 500,
            15000
          );
          retryCountRef.current += 1;
          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, backoffDelay);
        }
      };
    } catch (err: any) {
      setError(err.message || 'No se pudo iniciar el socket');
    }
  }, [conversationId, token, onMessageReceived, onMessagesRead]);

  useEffect(() => {
    connect();

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (heartbeatIntervalRef.current) {
        clearInterval(heartbeatIntervalRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close(1000, 'Component unmounted');
        wsRef.current = null;
      }
    };
  }, [connect]);

  const sendMessage = useCallback((text: string, clientMessageId?: string) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      const generatedId =
        clientMessageId || `${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
      wsRef.current.send(
        JSON.stringify({
          action: 'send_message',
          text,
          client_message_id: generatedId,
        })
      );
      return true;
    }
    return false;
  }, []);

  const markRead = useCallback(() => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(
        JSON.stringify({
          action: 'mark_read',
        })
      );
    }
  }, []);

  return {
    isConnected,
    error,
    sendMessage,
    markRead,
  };
}
