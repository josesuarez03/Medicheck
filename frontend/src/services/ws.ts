import { io, Socket } from "socket.io-client";
import type { ChatResponsePayload } from "@/types/messages";
import { getAccessToken, refreshAccessToken } from "@/services/authTokens";

class SocketIOService {
  private socket: Socket | null = null;
  private listeners: ((payload: ChatResponsePayload) => void)[] = [];
  private errorListeners: ((message: string) => void)[] = [];
  private url: string;
  private authenticated = false;

  constructor(url: string) {
    this.url = url;
  }

  async connect(): Promise<void> {
    if (this.socket && this.socket.connected) return;

    const token = getAccessToken();

    this.socket = io(this.url, {
      transports: ["websocket", "polling"],
      reconnection: true,
      reconnectionAttempts: 8,
      reconnectionDelay: 1200,
      timeout: 20000,
      autoConnect: true,
      forceNew: false,
    });

    this.socket.on("connect", () => {
      this.authenticated = false;
      if (token) {
        this.socket?.emit("authenticate", { token });
      }
    });

    this.socket.on("reconnect", () => {
      this.authenticated = false;
      const currentToken = getAccessToken();
      if (currentToken) {
        this.socket?.emit("authenticate", { token: currentToken });
      }
    });

    this.socket.on("authenticated", () => {
      this.authenticated = true;
    });

    this.socket.on("chat_response", (data: unknown) => {
      this.handleIncomingMessage(data);
    });

    this.socket.on("error", (data: unknown) => {
      this.handleIncomingError(data);
    });

    this.socket.on("connect_error", (error: Error) => {
      this.handleIncomingError(error?.message || "Error de conexión con el socket");
    });

    this.socket.on("connection_error", (data: unknown) => {
      this.handleIncomingError(data);
    });

    this.socket.on("auth_required", async (data: unknown) => {
      this.authenticated = false;
      const refreshedToken = await refreshAccessToken();
      if (refreshedToken) {
        this.socket?.emit("authenticate", { token: refreshedToken });
        return;
      }
      this.handleIncomingError(data);
    });
  }

  private handleIncomingMessage(data: unknown): void {
    let payload: ChatResponsePayload;

    if (typeof data === "string") {
      payload = { ai_response: data };
    } else if (data && typeof data === "object") {
      payload = data as ChatResponsePayload;
    } else {
      payload = { ai_response: String(data) };
    }

    const text =
      payload.ai_response ||
      payload.response ||
      (typeof payload.message === "string" ? payload.message : "");

    if (!text.trim()) return;
    this.listeners.forEach((listener) => listener(payload));
  }

  private handleIncomingError(data: unknown): void {
    const message =
      (data && typeof data === "object" && typeof (data as { error?: unknown }).error === "string"
        ? (data as { error: string }).error
        : typeof data === "string"
          ? data
          : "Error en comunicación con el asistente") || "Error en comunicación con el asistente";
    this.errorListeners.forEach((listener) => listener(message));
  }

  sendMessage(message: string, additionalData?: Record<string, unknown>): boolean {
    if (!this.socket?.connected || !this.authenticated) return false;

    let messageData: unknown = message;
    try {
      messageData = JSON.parse(message);
    } catch {
      messageData = {
        message,
        timestamp: new Date().toISOString(),
        ...additionalData,
      };
    }

    this.socket.emit("chat_message", messageData);
    return true;
  }

  reauthenticate(): void {
    const token = getAccessToken();
    if (this.socket?.connected && token) {
      this.socket.emit("authenticate", { token });
    }
  }

  addMessageListener(listener: (payload: ChatResponsePayload) => void): void {
    this.listeners.push(listener);
  }

  removeMessageListener(listener: (payload: ChatResponsePayload) => void): void {
    this.listeners = this.listeners.filter((l) => l !== listener);
  }

  addErrorListener(listener: (message: string) => void): void {
    this.errorListeners.push(listener);
  }

  removeErrorListener(listener: (message: string) => void): void {
    this.errorListeners = this.errorListeners.filter((l) => l !== listener);
  }

  isConnected(): boolean {
    return this.socket?.connected ?? false;
  }

  getConnectionState(): "no_socket" | "connected" | "disconnected" | "connecting" {
    if (!this.socket) return "no_socket";
    if (this.socket.connected) return "connected";
    if (this.socket.disconnected) return "disconnected";
    return "connecting";
  }

  disconnect(): void {
    if (this.socket) {
      this.socket.removeAllListeners();
      this.socket.disconnect();
      this.socket = null;
    }
  }
}

export default SocketIOService;
