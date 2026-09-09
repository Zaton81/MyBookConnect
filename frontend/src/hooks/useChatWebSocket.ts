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
  text: string;
  image?: string | null;
  created_at: string;
  read: boolean;
}

interface UseChatWebSocketOptions {
  conversationId: number | null;
  onMessageReceived?: (message: ChatMessage) => void;
  onMessagesRead?: (conversationId: number) => void;
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

  const connect = useCallback(() => {
    if (!conversationId || !token) return;

    if (wsRef.current) {
      wsRef.current.close();
    }

    const apiUrl = (import.meta as any).env.VITE_API_URL || 'http://localhost:8000';
    const wsProtocol = apiUrl.startsWith('https') ? 'wss' : 'ws';
    const wsHost = apiUrl.replace(/^https?:\/\//, '');
    const wsUrl = `${wsProtocol}://${wsHost}/ws/chat/${conversationId}/?token=${encodeURIComponent(token)}`;

    try {
      const socket = new WebSocket(wsUrl);
      wsRef.current = socket;

      socket.onopen = () => {
        setIsConnected(true);
        setError(null);
      };

      socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.event === 'message') {
            onMessageReceived?.(data);
          } else if (data.event === 'read') {
            onMessagesRead?.(data.conversation);
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
        if (event.code !== 1000 && event.code !== 4001 && event.code !== 4003) {
          // Reintentar reconexión automática tras 3s si no fue cierre intencionado o auth error
          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, 3000);
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
      if (wsRef.current) {
        wsRef.current.close(1000, 'Component unmounted');
        wsRef.current = null;
      }
    };
  }, [connect]);

  const sendMessage = useCallback((text: string) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(
        JSON.stringify({
          action: 'send_message',
          text,
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
