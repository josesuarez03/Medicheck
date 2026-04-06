"use client";

import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useSocketIO } from "@/hooks/useWs";
import { useAuth } from "@/hooks/useAuth";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  TbAlertTriangle,
  TbArchive,
  TbCircleDot,
  TbClipboardText,
  TbDotsVertical,
  TbFileDescription,
  TbLock,
  TbMicrophone,
  TbPaperclip,
  TbPlugConnected,
  TbRefresh,
  TbRestore,
  TbSend,
  TbTrash,
} from "react-icons/tb";
import {
  archiveConversation,
  deleteConversation,
  getConversation,
  getConversations,
  recoverConversation,
} from "@/services/chatApi";
import type {
  ChatResponsePayload,
  ConversationDetail,
  ConversationSummary,
  LifecycleStatus,
  Message,
} from "@/types/messages";
import { ROUTES } from "@/routes/routePaths";

const RESPONSE_TIMEOUT_MS = 25000;
const CHAT_SELECTED_SESSION_KEY = "chat_selected_session_id";
const FALLBACK_QUICK_REPLIES = [
  "Tengo fiebre desde ayer",
  "Tambien me duele la garganta",
  "Debo ir a urgencias?",
];

const createMessageId = () => `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;

const formatTime = (isoDate: string) =>
  new Date(isoDate).toLocaleTimeString("es-ES", { hour: "2-digit", minute: "2-digit" });

const normalizeLifecycleStatus = (session?: Pick<ConversationSummary, "lifecycle_status" | "active">): LifecycleStatus => {
  const status = String(session?.lifecycle_status || "").toLowerCase();
  if (status === "archived" || status === "deleted" || status === "active") return status;
  if (session?.active === false) return "archived";
  return "active";
};

const triageBadgeClass = (triajeLevel?: string) => {
  const value = (triajeLevel || "").toLowerCase();
  if (value.includes("urgente")) return "bg-red-100 text-red-800 border-red-300 dark:bg-red-950/40 dark:text-red-200 dark:border-red-800";
  if (value.includes("moderad")) return "bg-amber-100 text-amber-900 border-amber-300 dark:bg-amber-900/40 dark:text-amber-200 dark:border-amber-800";
  if (!value) return "bg-slate-100 text-slate-800 border-slate-300 dark:bg-slate-800 dark:text-slate-100 dark:border-slate-600";
  return "bg-emerald-100 text-emerald-900 border-emerald-300 dark:bg-emerald-950/40 dark:text-emerald-200 dark:border-emerald-800";
};

const extractSuggestions = (payload?: ChatResponsePayload) => {
  const quickReplies = payload?.quick_replies;
  if (Array.isArray(quickReplies) && quickReplies.length > 0) {
    return quickReplies.filter((v): v is string => typeof v === "string" && v.trim().length > 0).slice(0, 4);
  }
  return FALLBACK_QUICK_REPLIES;
};

const mapConversationMessages = (conversation: ConversationDetail): Message[] => {
  if (!Array.isArray(conversation.messages)) return [];
  return conversation.messages
    .filter((item) => item && typeof item.content === "string")
    .map((item, index) => ({
      id: `${conversation._id}-${index}`,
      content: item.content,
      sender: item.role === "user" ? "user" : "bot",
      status: "sent",
      timestamp: conversation.timestamp || new Date().toISOString(),
    }));
};

const sessionTitle = (session: ConversationSummary) => {
  if (Array.isArray(session.symptoms) && session.symptoms.length > 0) return session.symptoms.join(", ");
  const firstUserMessage = session.messages?.find((msg) => msg.role === "user")?.content;
  if (firstUserMessage) return firstUserMessage.slice(0, 50);
  return "Sesión de triaje";
};

const sessionPreview = (session: ConversationSummary) => {
  const firstAssistantMessage = session.messages?.find((msg) => msg.role === "assistant")?.content;
  if (firstAssistantMessage) return firstAssistantMessage.slice(0, 80);
  return "Sin vista previa";
};

export default function Chatbot() {
  const { isAuthenticated } = useAuth();
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [isWaitingBot, setIsWaitingBot] = useState(false);
  const [pendingMessageId, setPendingMessageId] = useState<string | null>(null);
  const [chatError, setChatError] = useState<string | null>(null);
  const [inputRows, setInputRows] = useState(1);
  const [sessions, setSessions] = useState<ConversationSummary[]>([]);
  const [loadingSessions, setLoadingSessions] = useState(true);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [activeConversationStatus, setActiveConversationStatus] = useState<LifecycleStatus>("active");
  const [quickReplies, setQuickReplies] = useState<string[]>(FALLBACK_QUICK_REPLIES);
  const [activeTriageLevel, setActiveTriageLevel] = useState("");
  const [sessionActionBusy, setSessionActionBusy] = useState<string | null>(null);
  const responseTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const lastProcessedSocketIndexRef = useRef(-1);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const socketUrl = process.env.NEXT_PUBLIC_SOCKETIO_URL || "http://localhost:5000";
  const {
    messages: socketMessages,
    sendMessage,
    isConnected,
    isConnecting,
    connectionError,
    socketError,
    reauthenticate,
    reconnect,
  } = useSocketIO(socketUrl, isAuthenticated);

  const activeSession = useMemo(
    () => sessions.find((session) => session._id === activeConversationId) || null,
    [sessions, activeConversationId]
  );
  const isArchivedConversation = activeConversationStatus === "archived";

  const refreshSessions = useCallback(async () => {
    const items = await getConversations("all");
    const sorted = [...items].sort((a, b) => {
      const ta = new Date(a.timestamp || 0).getTime();
      const tb = new Date(b.timestamp || 0).getTime();
      return tb - ta;
    });
    setSessions(sorted);
  }, []);

  const startNewConversation = useCallback(() => {
    setActiveConversationId(null);
    setActiveConversationStatus("active");
    setMessages([]);
    setChatError(null);
    setActiveTriageLevel("");
    setQuickReplies(FALLBACK_QUICK_REPLIES);
    if (typeof window !== "undefined") {
      sessionStorage.removeItem(CHAT_SELECTED_SESSION_KEY);
    }
    lastProcessedSocketIndexRef.current = socketMessages.length - 1;
  }, [socketMessages.length]);

  const selectConversation = useCallback(
    async (conversationId: string) => {
      try {
        setChatError(null);
        const detail = await getConversation(conversationId);
        if (!detail) {
          setChatError("No se pudo abrir la conversación seleccionada.");
          return;
        }
        setActiveConversationId(conversationId);
        setActiveConversationStatus(normalizeLifecycleStatus(detail));
        setMessages(mapConversationMessages(detail));
        setActiveTriageLevel(detail.triaje_level || "");
        setQuickReplies(FALLBACK_QUICK_REPLIES);
        lastProcessedSocketIndexRef.current = socketMessages.length - 1;
      } catch {
        setChatError("Error al cargar la conversación.");
      }
    },
    [socketMessages.length]
  );

  useEffect(() => {
    if (isAuthenticated && isConnected) reauthenticate();
  }, [isAuthenticated, isConnected, reauthenticate]);

  useEffect(() => {
    const fetchSessions = async () => {
      try {
        setLoadingSessions(true);
        await refreshSessions();
      } catch {
        setChatError("No se pudo cargar el historial de sesiones.");
      } finally {
        setLoadingSessions(false);
      }
    };
    if (isAuthenticated) void fetchSessions();
  }, [isAuthenticated, refreshSessions]);

  useEffect(() => {
    if (loadingSessions || sessions.length === 0 || typeof window === "undefined") return;
    const storedSessionId = sessionStorage.getItem(CHAT_SELECTED_SESSION_KEY);
    if (storedSessionId && storedSessionId !== activeConversationId) {
      void selectConversation(storedSessionId);
      sessionStorage.removeItem(CHAT_SELECTED_SESSION_KEY);
    }
  }, [loadingSessions, sessions, activeConversationId, selectConversation]);

  useEffect(() => {
    if (socketMessages.length === 0) return;
    const lastIndex = socketMessages.length - 1;
    if (lastProcessedSocketIndexRef.current === lastIndex) return;
    lastProcessedSocketIndexRef.current = lastIndex;
    const payload = socketMessages[lastIndex];
    const eventType = typeof payload.event === "string" ? payload.event : "";

    if (eventType === "session_warning") {
      setMessages((prev) => [
        ...prev,
        {
          id: createMessageId(),
          content: typeof payload.message === "string" && payload.message.trim()
            ? payload.message
            : "Se cerrará en 3 min por inactividad. ¿Algo más que añadir?",
          sender: "system",
          status: "sent",
          timestamp: new Date().toISOString(),
        },
      ]);
      return;
    }

    if (eventType === "session_timeout") {
      setMessages((prev) => [
        ...prev,
        {
          id: createMessageId(),
          content: typeof payload.message === "string" && payload.message.trim()
            ? payload.message
            : "La sesión se ha cerrado por inactividad.",
          sender: "system",
          status: "sent",
          timestamp: new Date().toISOString(),
        },
      ]);
      setIsWaitingBot(false);
      setPendingMessageId(null);
      setChatError("La sesión se cerró por inactividad. Inicia una nueva conversación para continuar.");
      return;
    }

    const responseText =
      payload.ai_response ||
      payload.response ||
      (typeof payload.message === "string" ? payload.message : "");
    if (!responseText?.trim()) return;

    if (responseTimeoutRef.current) {
      clearTimeout(responseTimeoutRef.current);
      responseTimeoutRef.current = null;
    }

    setMessages((prev) => [
      ...prev,
      {
        id: createMessageId(),
        content: responseText,
        sender: "bot",
        status: "sent",
        timestamp: new Date().toISOString(),
      },
    ]);

    if (typeof payload.final_chat_summary === "string" && payload.final_chat_summary.trim()) {
      setMessages((prev) => [
        ...prev,
        {
          id: createMessageId(),
          content: `${payload.final_chat_summary_title || "Resumen final"}\n\n${payload.final_chat_summary}`,
          sender: "system",
          status: "sent",
          timestamp: new Date().toISOString(),
        },
      ]);
    }

    setQuickReplies(extractSuggestions(payload));

    if (payload.triaje_level) setActiveTriageLevel(payload.triaje_level);

    if (payload.conversation_id && payload.conversation_id !== activeConversationId) {
      setActiveConversationId(payload.conversation_id);
      setActiveConversationStatus("active");
      setSessions((prev) => {
        const exists = prev.some((item) => item._id === payload.conversation_id);
        if (exists) return prev;
        return [
          {
            _id: payload.conversation_id,
            timestamp: new Date().toISOString(),
            triaje_level: payload.triaje_level,
            lifecycle_status: "active",
            messages: [
              { role: "user", content: payload.user_message || "" },
              { role: "assistant", content: responseText },
            ],
          },
          ...prev,
        ];
      });
    }

    if (pendingMessageId) {
      setMessages((prev) =>
        prev.map((message) =>
          message.id === pendingMessageId && message.status === "pending"
            ? { ...message, status: "sent" }
            : message
        )
      );
      setPendingMessageId(null);
    }

    setIsWaitingBot(false);
    setChatError(null);
    void refreshSessions();
  }, [socketMessages, pendingMessageId, activeConversationId, refreshSessions]);

  useEffect(() => {
    if (!socketError) return;
    if (responseTimeoutRef.current) {
      clearTimeout(responseTimeoutRef.current);
      responseTimeoutRef.current = null;
    }
    if (pendingMessageId) {
      setMessages((prev) =>
        prev.map((message) =>
          message.id === pendingMessageId ? { ...message, status: "error" } : message
        )
      );
      setPendingMessageId(null);
    }
    setIsWaitingBot(false);

    if (socketError.includes("conversation_archived")) {
      setChatError("Esta conversación está archivada. Recupérala para enviar mensajes.");
      if (activeConversationId) setActiveConversationStatus("archived");
    } else {
      setChatError(socketError);
    }
  }, [socketError, pendingMessageId, activeConversationId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isWaitingBot]);

  useEffect(() => {
    return () => {
      if (responseTimeoutRef.current) clearTimeout(responseTimeoutRef.current);
    };
  }, []);

  const connectionLabel = useMemo(() => {
    if (isConnected) return "Conectado";
    if (isConnecting) return "Conectando";
    if (connectionError) return "Sin conexión";
    return "Desconectado";
  }, [isConnected, isConnecting, connectionError]);

  const submitMessage = () => {
    const trimmed = input.trim();
    if (!trimmed || !isConnected || isArchivedConversation) return;

    const userMessageId = createMessageId();
    const userMessage: Message = {
      id: userMessageId,
      content: trimmed,
      sender: "user",
      status: "pending",
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setPendingMessageId(userMessageId);
    setIsWaitingBot(true);
    setChatError(null);

    const messagePayload = {
      context: {},
      conversation_id: activeConversationId,
    };

    const success = sendMessage(trimmed, messagePayload);
    if (!success) {
      setMessages((prev) =>
        prev.map((message) => (message.id === userMessageId ? { ...message, status: "error" } : message))
      );
      setPendingMessageId(null);
      setIsWaitingBot(false);
      setChatError("No se pudo enviar el mensaje. Revisa la conexión e intenta otra vez.");
      return;
    }

    responseTimeoutRef.current = setTimeout(() => {
      setMessages((prev) =>
        prev.map((message) => (message.id === userMessageId ? { ...message, status: "error" } : message))
      );
      setPendingMessageId(null);
      setIsWaitingBot(false);
      setChatError("No se recibio respuesta del asistente. Intenta enviar nuevamente.");
    }, RESPONSE_TIMEOUT_MS);

    setInput("");
    setInputRows(1);
  };

  const handleSendMessage = (event: React.FormEvent) => {
    event.preventDefault();
    submitMessage();
  };

  const handleComposerKeyDown = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      submitMessage();
    }
  };

  const handleInputChange = (value: string) => {
    setInput(value);
    const lines = value.split("\n").length;
    setInputRows(Math.min(5, Math.max(1, lines)));
  };

  const applySuggestion = (suggestion: string) => {
    if (isArchivedConversation) return;
    setInput(suggestion);
    setInputRows(Math.min(5, Math.max(1, suggestion.split("\n").length)));
  };

  const handleArchiveCurrent = async () => {
    if (!activeConversationId) return;
    try {
      setSessionActionBusy(`${activeConversationId}:archive`);
      await archiveConversation(activeConversationId);
      setActiveConversationStatus("archived");
      await refreshSessions();
    } catch {
      setChatError("No se pudo archivar la conversación.");
    } finally {
      setSessionActionBusy(null);
    }
  };

  const handleRecoverCurrent = async () => {
    if (!activeConversationId) return;
    try {
      setSessionActionBusy(`${activeConversationId}:recover`);
      await recoverConversation(activeConversationId);
      setActiveConversationStatus("active");
      await refreshSessions();
    } catch {
      setChatError("No se pudo recuperar la conversación.");
    } finally {
      setSessionActionBusy(null);
    }
  };

  const handleDeleteCurrent = async () => {
    if (!activeConversationId) return;
    if (!window.confirm("¿Eliminar esta sesión? Se ocultará y se conservará por 30 días.")) return;
    try {
      setSessionActionBusy(`${activeConversationId}:delete`);
      await deleteConversation(activeConversationId);
      await refreshSessions();
      startNewConversation();
    } catch {
      setChatError("No se pudo eliminar la conversación.");
    } finally {
      setSessionActionBusy(null);
    }
  };

  return (
    <div className="h-[calc(100vh-8rem)] rounded-[1.75rem] border border-border/80 bg-card shadow-sm overflow-hidden">
      <section className="flex h-full flex-col">
        <div className="border-b border-border/70 bg-card px-4 py-3 md:px-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-primary/12 text-primary font-semibold">🤖</div>
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <p className="text-xl font-semibold leading-none">Hipo</p>
                  <span className={`rounded-full border px-3 py-1 text-xs font-semibold ${triageBadgeClass(activeTriageLevel)}`}>
                    {activeTriageLevel || "Sin clasificación"}
                  </span>
                  {isArchivedConversation && (
                    <span className="rounded-full border border-amber-300 bg-amber-100 px-3 py-1 text-xs font-semibold text-amber-900 dark:border-amber-700 dark:bg-amber-900/30 dark:text-amber-200">
                      Archivada
                    </span>
                  )}
                </div>
                <p className="mt-1 flex items-center gap-2 text-sm text-muted-foreground">
                  <TbPlugConnected className="h-4 w-4 text-primary" />
                  {connectionLabel} · Asistente de triaje
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Button onClick={startNewConversation} className="min-h-10 rounded-full px-4">
                + Nueva sesión
              </Button>
              <Button asChild variant="outline" size="icon" className="rounded-full" aria-label="Historial de sesiones">
                <Link href={ROUTES.PROTECTED.CHAT_SESSIONS}>
                  <TbFileDescription className="h-4 w-4" />
                </Link>
              </Button>
              <Button variant="outline" size="icon" className="rounded-full" onClick={reconnect} disabled={isConnecting} aria-label="Reconectar">
                <TbRefresh className="h-4 w-4" />
              </Button>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="outline" size="icon" className="rounded-full" aria-label="Opciones de la conversación">
                    <TbDotsVertical className="h-4 w-4" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="rounded-xl">
                  {activeConversationId && activeConversationStatus === "active" && (
                    <DropdownMenuItem onClick={handleArchiveCurrent} disabled={sessionActionBusy === `${activeConversationId}:archive`}>
                      <TbArchive className="h-4 w-4" />
                      Archivar conversación
                    </DropdownMenuItem>
                  )}
                  {activeConversationId && activeConversationStatus === "archived" && (
                    <DropdownMenuItem onClick={handleRecoverCurrent} disabled={sessionActionBusy === `${activeConversationId}:recover`}>
                      <TbRestore className="h-4 w-4" />
                      Recuperar conversación
                    </DropdownMenuItem>
                  )}
                  {activeConversationId && (
                    <DropdownMenuItem
                      onClick={handleDeleteCurrent}
                      disabled={sessionActionBusy === `${activeConversationId}:delete`}
                      className="text-red-600 focus:text-red-600 dark:text-red-300"
                    >
                      <TbTrash className="h-4 w-4" />
                      Eliminar conversación
                    </DropdownMenuItem>
                  )}
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </div>

          <div className="mt-3 rounded-2xl border border-border/70 bg-muted/40 px-4 py-3">
            <p className="font-medium">
              {loadingSessions ? "Cargando historial..." : activeSession ? sessionTitle(activeSession) : "Nueva conversación"}
            </p>
            <p className="mt-1 text-sm text-muted-foreground">
              {activeSession ? sessionPreview(activeSession) : "El chat es el foco principal. El historial se consulta desde la vista de documento."}
            </p>
          </div>
        </div>

        <div className="flex-1 space-y-4 overflow-y-auto bg-[linear-gradient(180deg,rgba(37,131,204,0.03),transparent_24%),rgba(148,163,184,0.06)] p-4 md:p-6 dark:bg-[linear-gradient(180deg,rgba(37,131,204,0.06),transparent_24%),rgba(15,23,42,0.3)]" aria-live="polite">
          {isArchivedConversation && activeConversationId && (
            <div className="flex items-center justify-between gap-3 rounded-2xl border border-amber-300 bg-amber-50 p-4 text-amber-900 dark:border-amber-700 dark:bg-amber-900/25 dark:text-amber-100">
              <div className="flex items-center gap-2 text-sm">
                <TbLock className="h-4 w-4" />
                Esta conversación está archivada. El envío de mensajes está desactivado.
              </div>
              <Button size="sm" className="rounded-full" onClick={handleRecoverCurrent}>
                <TbRestore className="h-4 w-4" />
                Recuperar
              </Button>
            </div>
          )}

          {messages.length === 0 && !isWaitingBot && !chatError && (
            <div className="flex h-full items-center justify-center">
              <div className="max-w-md rounded-[1.75rem] border border-border/70 bg-card p-6 text-center shadow-sm">
                <p className="font-semibold">Inicia una conversación con Hipo</p>
                <p className="mt-2 text-sm text-muted-foreground">
                  Escribe tu primer síntoma para comenzar el triaje. El historial de sesiones se consulta desde la vista de historial.
                </p>
              </div>
            </div>
          )}

          {messages.map((message) => (
            <div key={message.id} className={`flex ${message.sender === "user" ? "justify-end" : "justify-start"}`}>
              <div
                className={`max-w-[92%] rounded-[1.5rem] px-4 py-3 md:max-w-[78%] ${
                  message.sender === "user"
                    ? "bg-primary text-primary-foreground shadow-sm"
                    : message.sender === "system"
                      ? "border border-red-200 bg-red-50 text-red-800 dark:border-red-800 dark:bg-red-950/40 dark:text-red-200"
                      : "border border-slate-200 bg-slate-50 text-slate-900 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
                }`}
              >
                <p className="whitespace-pre-wrap break-words text-[15px] leading-7">{message.content}</p>
                <div className="mt-2 flex items-center justify-between gap-4">
                  <span
                    className={`text-xs ${
                      message.sender === "user"
                        ? "text-primary-foreground/80"
                        : message.sender === "system"
                          ? "text-red-700/90 dark:text-red-200/90"
                          : "text-slate-500 dark:text-slate-300"
                    }`}
                  >
                    {formatTime(message.timestamp)}
                  </span>
                  {message.status === "pending" && <span className="text-xs text-primary-foreground/80">Enviando...</span>}
                  {message.status === "error" && (
                    <span className="flex items-center gap-1 text-xs text-red-600 dark:text-red-300">
                      <TbAlertTriangle className="h-3.5 w-3.5" />
                      Error
                    </span>
                  )}
                </div>
              </div>
            </div>
          ))}

          {isWaitingBot && (
            <div className="flex justify-start">
              <div className="max-w-[92%] rounded-[1.5rem] border border-slate-200 bg-slate-50 px-4 py-3 md:max-w-[78%] dark:border-slate-700 dark:bg-slate-800">
                <div className="flex items-center gap-2">
                  <span className="h-2 w-2 rounded-full bg-slate-500 animate-bounce dark:bg-slate-300" />
                  <span className="h-2 w-2 rounded-full bg-slate-500 animate-bounce [animation-delay:0.15s] dark:bg-slate-300" />
                  <span className="h-2 w-2 rounded-full bg-slate-500 animate-bounce [animation-delay:0.3s] dark:bg-slate-300" />
                </div>
              </div>
            </div>
          )}

          {chatError && (
            <div className="flex justify-start">
              <div className="max-w-[92%] rounded-[1.5rem] border border-red-200 bg-red-50 px-4 py-3 text-red-800 md:max-w-[78%] dark:border-red-800 dark:bg-red-950/40 dark:text-red-200">
                <p className="text-sm">{chatError}</p>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        <div className="space-y-3 border-t border-border/70 bg-card px-4 py-4">
          {!isArchivedConversation && (
            <div className="flex flex-wrap gap-2">
              {quickReplies.map((item) => (
                <button
                  key={item}
                  type="button"
                  className="rounded-full border border-input bg-background px-3 py-1.5 text-sm text-foreground transition hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  onClick={() => applySuggestion(item)}
                >
                  {item}
                </button>
              ))}
            </div>
          )}

          <form onSubmit={handleSendMessage} className="w-full">
            <div className="flex items-end gap-2 rounded-[1.75rem] border border-border/80 bg-background px-3 py-3 shadow-sm transition focus-within:border-primary/40 focus-within:ring-2 focus-within:ring-primary/15">
              <div className="flex items-center gap-1 pb-1">
                <Button type="button" size="icon" variant="ghost" className="rounded-full" aria-label="Adjuntar archivo" disabled={isArchivedConversation}>
                  <TbPaperclip className="h-5 w-5" />
                </Button>
                <Button type="button" size="icon" variant="ghost" className="rounded-full" aria-label="Dictado de voz" disabled={isArchivedConversation}>
                  <TbMicrophone className="h-5 w-5" />
                </Button>
              </div>
              <Textarea
                value={input}
                onChange={(event) => handleInputChange(event.target.value)}
                onKeyDown={handleComposerKeyDown}
                rows={inputRows}
                placeholder={
                  isArchivedConversation
                    ? "Esta conversación está archivada"
                    : isConnected
                      ? "Escribe tu mensaje aquí..."
                      : isConnecting
                        ? "Conectando..."
                        : "Sin conexión con el servidor"
                }
                className="min-h-[48px] max-h-36 resize-none border-0 bg-transparent px-1 py-2 shadow-none focus-visible:ring-0"
                disabled={!isConnected || isWaitingBot || isArchivedConversation}
                aria-label="Mensaje para el asistente"
              />
              <Button
                type="submit"
                size="icon"
                className="h-12 w-12 rounded-full"
                disabled={!isConnected || !input.trim() || isWaitingBot || isArchivedConversation}
                title={!isConnected ? "No conectado al servidor" : "Enviar mensaje"}
                aria-label="Enviar mensaje"
              >
                <TbSend className="h-5 w-5" />
              </Button>
            </div>
          </form>

          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <TbCircleDot className="h-4 w-4 text-primary" />
            Hipo orienta y prioriza. El diagnostico definitivo siempre lo da un profesional sanitario.
            <TbClipboardText className="ml-1 h-4 w-4" />
          </div>
        </div>
      </section>
    </div>
  );
}
