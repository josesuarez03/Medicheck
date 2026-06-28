import { useEffect, useState, useCallback, useRef } from "react";
import SocketIOService from "@/services/ws";
import type { ChatResponsePayload } from "@/types/messages";

export type ConnectionState = "connecting" | "connected" | "disconnected" | "error";

type SharedSocketEntry = {
  service: SocketIOService;
  refs: number;
  disconnectTimer: ReturnType<typeof setTimeout> | null;
};

const sharedSockets = new Map<string, SharedSocketEntry>();

const acquireSharedSocket = (url: string): SocketIOService => {
  const existing = sharedSockets.get(url);
  if (existing) {
    existing.refs += 1;
    if (existing.disconnectTimer) {
      clearTimeout(existing.disconnectTimer);
      existing.disconnectTimer = null;
    }
    return existing.service;
  }

  const entry: SharedSocketEntry = {
    service: new SocketIOService(url),
    refs: 1,
    disconnectTimer: null,
  };
  sharedSockets.set(url, entry);
  return entry.service;
};

const releaseSharedSocket = (url: string): void => {
  const entry = sharedSockets.get(url);
  if (!entry) return;

  entry.refs -= 1;
  if (entry.refs > 0) return;

  entry.disconnectTimer = setTimeout(() => {
    const latest = sharedSockets.get(url);
    if (!latest || latest.refs > 0) return;
    latest.service.disconnect();
    sharedSockets.delete(url);
  }, 1000);
};

export const useSocketIO = (url: string, isAuthenticated?: boolean) => {
  const [messages, setMessages] = useState<ChatResponsePayload[]>([]);
  const [socket, setSocket] = useState<SocketIOService | null>(null);
  const [connectionState, setConnectionState] = useState<ConnectionState>("disconnected");
  const [lastError, setLastError] = useState<string | null>(null);
  const [socketError, setSocketError] = useState<string | null>(null);
  const connectionCheckRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!url) {
      setLastError("URL de socket no configurada");
      setConnectionState("error");
      return;
    }

    if (isAuthenticated === false) {
      setConnectionState("disconnected");
      return;
    }

    setConnectionState("connecting");
    setLastError(null);

    const socketService = acquireSharedSocket(url);
    setSocket(socketService);

    const handleMessage = (payload: ChatResponsePayload) => {
      setMessages((prev) => [...prev, payload]);
      setSocketError(null);
    };

    const handleSocketError = (message: string) => {
      setSocketError(message);
    };

    const handleSocketClose = (code: number) => {
      if (connectionCheckRef.current) {
        clearInterval(connectionCheckRef.current);
        connectionCheckRef.current = null;
      }
      setConnectionState(code === 1000 ? "disconnected" : "error");
    };

    socketService.addMessageListener(handleMessage);
    socketService.addErrorListener(handleSocketError);
    socketService.addCloseListener(handleSocketClose);

    socketService
      .connect()
      .then(() => {
        if (connectionCheckRef.current) clearInterval(connectionCheckRef.current);
        connectionCheckRef.current = setInterval(() => {
          const connected = socketService.isConnected();
          setConnectionState(connected ? "connected" : "connecting");
        }, 800);
      })
      .catch((error: Error) => {
        setConnectionState("error");
        setLastError(error.message || "Error de conexión");
      });

    return () => {
      if (connectionCheckRef.current) clearInterval(connectionCheckRef.current);
      socketService.removeMessageListener(handleMessage);
      socketService.removeErrorListener(handleSocketError);
      socketService.removeCloseListener(handleSocketClose);
      releaseSharedSocket(url);
      setSocket(null);
      setConnectionState("disconnected");
    };
  }, [url, isAuthenticated]);

  useEffect(() => {
    if (!socket) return;

    const handleStorageChange = (event: StorageEvent) => {
      if (event.key === "access_token") {
        socket.reauthenticate();
      }
    };

    window.addEventListener("storage", handleStorageChange);
    return () => window.removeEventListener("storage", handleStorageChange);
  }, [socket]);

  const sendMessage = useCallback(
    (message: string, additionalData?: Record<string, unknown>) => {
      if (!socket || !socket.isConnected()) {
        setLastError("Socket no conectado");
        return false;
      }

      const sent = socket.sendMessage(message, additionalData);
      if (!sent) setLastError("No se pudo enviar el mensaje");
      return sent;
    },
    [socket]
  );

  const clearMessages = useCallback(() => setMessages([]), []);

  const reconnect = useCallback(() => {
    if (!socket) return;
    setConnectionState("connecting");
    setLastError(null);
    setSocketError(null);
    socket.disconnect();
    socket.connect().catch(() => {
      setConnectionState("error");
      setLastError("No se pudo reconectar");
    });
  }, [socket]);

  const reauthenticate = useCallback(() => {
    socket?.reauthenticate();
  }, [socket]);

  return {
    messages,
    sendMessage,
    clearMessages,
    reconnect,
    reauthenticate,
    socket,
    connectionState,
    lastError,
    socketError,
    isConnected: connectionState === "connected",
    isConnecting: connectionState === "connecting",
    connectionError: lastError,
  };
};
