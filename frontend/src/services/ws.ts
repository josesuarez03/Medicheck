import type { ChatResponsePayload } from "@/types/messages";
import { getAccessToken, refreshAccessToken } from "@/services/authTokens";

const buildWebSocketUrl = (rawUrl: string): string => {
  if (!rawUrl) return "";
  if (rawUrl.startsWith("ws://") || rawUrl.startsWith("wss://")) {
    return rawUrl.endsWith("/ws") ? rawUrl : `${rawUrl.replace(/\/$/, "")}/ws`;
  }
  const normalized = rawUrl.replace(/\/$/, "");
  if (normalized.startsWith("http://")) {
    return `${normalized.replace(/^http:\/\//, "ws://")}/ws`;
  }
  if (normalized.startsWith("https://")) {
    return `${normalized.replace(/^https:\/\//, "wss://")}/ws`;
  }
  return `ws://${normalized}/ws`;
};

class SocketIOService {
  private socket: WebSocket | null = null;
  private listeners: ((payload: ChatResponsePayload) => void)[] = [];
  private errorListeners: ((message: string) => void)[] = [];
  private closeListeners: ((code: number, reason: string) => void)[] = [];
  private url: string;
  private authenticated = false;
  private authInFlight: Promise<boolean> | null = null;
  private connectInFlight: Promise<void> | null = null;
  private intentionalClose = false;

  constructor(url: string) {
    this.url = buildWebSocketUrl(url);
  }

  async connect(): Promise<void> {
    if (!this.url) {
      throw new Error("URL de websocket no configurada");
    }
    if (this.socket && this.socket.readyState === WebSocket.OPEN) return;
    if (this.connectInFlight) {
      return this.connectInFlight;
    }
    if (this.socket && this.socket.readyState === WebSocket.CONNECTING) {
      return;
    }

    this.connectInFlight = new Promise<void>((resolve, reject) => {
      this.socket = new WebSocket(this.url);
      this.intentionalClose = false;

      this.socket.onopen = () => {
        this.authenticated = false;
        void this.authenticateSocket();
        resolve();
      };

      this.socket.onerror = () => {
        if (this.intentionalClose) {
          return;
        }
        reject(new Error("Error de conexión con el websocket"));
      };

      this.socket.onmessage = async (event: MessageEvent<string>) => {
        await this.handleIncomingMessage(event.data);
      };

      this.socket.onclose = (event) => {
        this.authenticated = false;
        this.connectInFlight = null;
        this.closeListeners.forEach((listener) => listener(event.code, event.reason));
        if (!this.intentionalClose && event.code !== 1000) {
          this.handleIncomingError(`Conexión websocket cerrada (${event.code || 1006}).`);
        }
      };
    });

    try {
      await this.connectInFlight;
    } finally {
      if (this.socket?.readyState !== WebSocket.CONNECTING) {
        this.connectInFlight = null;
      }
    }
  }

  private sendRaw(payload: Record<string, unknown>): void {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) return;
    this.socket.send(JSON.stringify(payload));
  }

  private async authenticateSocket(forceRefresh = false): Promise<boolean> {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
      return false;
    }
    if (this.authInFlight) {
      return this.authInFlight;
    }

    this.authInFlight = (async () => {
      let token = forceRefresh ? null : getAccessToken();
      if (!token) {
        token = await refreshAccessToken();
      }
      if (!token) {
        this.authenticated = false;
        this.handleIncomingError("La sesión ha expirado. Vuelve a iniciar sesión.");
        if (this.socket?.readyState === WebSocket.OPEN) {
          this.intentionalClose = true;
          this.socket.close();
        }
        return false;
      }
      this.sendRaw({ type: "authenticate", token });
      return true;
    })();

    try {
      return await this.authInFlight;
    } finally {
      this.authInFlight = null;
    }
  }

  private async handleIncomingMessage(data: string): Promise<void> {
    let payload: ChatResponsePayload;
    try {
      payload = JSON.parse(data) as ChatResponsePayload;
    } catch {
      payload = { response: data };
    }

    if (payload.event === "connection_success" || payload.status === "authenticated") {
      this.authenticated = true;
      return;
    }

    if (payload.event === "connection_pending") {
      if (!this.authenticated && !this.authInFlight) {
        await this.authenticateSocket();
      }
      return;
    }

    if (payload.event === "auth_required") {
      this.authenticated = false;
      if (await this.authenticateSocket(true)) {
        return;
      }
      this.handleIncomingError(payload.detail || "Se requiere autenticación.");
      return;
    }

    if (payload.event === "auth_error" || payload.event === "auth_timeout" || payload.event === "rate_limit_exceeded") {
      if (payload.event === "auth_timeout") {
        this.authenticated = false;
        if (await this.authenticateSocket(true)) {
          return;
        }
      }
      this.handleIncomingError(payload.detail || payload.message || "Error en comunicación con el asistente");
      return;
    }

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
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN || !this.authenticated) return false;

    this.sendRaw({
      type: "chat",
      message,
      timestamp: new Date().toISOString(),
      ...additionalData,
    });
    return true;
  }

  reauthenticate(): void {
    if (this.socket?.readyState === WebSocket.OPEN) {
      void this.authenticateSocket();
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

  addCloseListener(listener: (code: number, reason: string) => void): void {
    this.closeListeners.push(listener);
  }

  removeCloseListener(listener: (code: number, reason: string) => void): void {
    this.closeListeners = this.closeListeners.filter((l) => l !== listener);
  }

  isConnected(): boolean {
    return this.socket?.readyState === WebSocket.OPEN && this.authenticated;
  }

  getConnectionState(): "no_socket" | "connected" | "disconnected" | "connecting" {
    if (!this.socket) return "no_socket";
    if (this.socket.readyState === WebSocket.CONNECTING) return "connecting";
    if (this.socket.readyState === WebSocket.OPEN && this.authenticated) return "connected";
    return "disconnected";
  }

  disconnect(): void {
    if (this.socket) {
      this.intentionalClose = true;
      this.socket.close();
      this.socket = null;
      this.authenticated = false;
      this.connectInFlight = null;
    }
  }
}

export default SocketIOService;
