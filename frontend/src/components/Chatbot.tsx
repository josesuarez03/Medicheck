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
  TbActivityHeartbeat,
  TbAlertTriangle,
  TbArchive,
  TbChevronDown,
  TbChevronUp,
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
  TbSettings,
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
  ConversationState,
  ConversationSummary,
  DecisionFlags,
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
const STRUCTURED_SYMPTOM_OPTIONS = ["Fiebre", "Tos", "Mareo", "Nauseas", "Dolor de cabeza", "Dolor garganta"];
const DURATION_OPTIONS = ["< 24 horas", "1-2 dias", "3-7 dias", "> 1 semana"];

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

const extractDurationFromText = (text?: string) => {
  if (!text) return null;
  const match = text.match(/(\d+\s*(hora|horas|dia|dias|semana|semanas))/i);
  return match?.[0] || null;
};

const getTriageStateMeta = (triajeLevel?: string, waiting?: boolean) => {
  const value = (triajeLevel || "").toLowerCase();
  if (waiting) {
    return {
      label: "Evaluando sintomas",
      step: "Paso 2/5",
      tone: "border-amber-200 bg-amber-50 text-amber-900 dark:border-amber-800 dark:bg-amber-950/30 dark:text-amber-100",
      progress: 40,
    };
  }
  if (value.includes("sever") || value.includes("urgent")) {
    return {
      label: "Posible urgencia",
      step: "Paso 5/5",
      tone: "border-red-200 bg-red-50 text-red-800 dark:border-red-800 dark:bg-red-950/30 dark:text-red-100",
      progress: 100,
    };
  }
  if (value.includes("moderad")) {
    return {
      label: "Priorizando",
      step: "Paso 4/5",
      tone: "border-amber-200 bg-amber-50 text-amber-900 dark:border-amber-800 dark:bg-amber-950/30 dark:text-amber-100",
      progress: 78,
    };
  }
  if (value.includes("leve")) {
    return {
      label: "Leve",
      step: "Paso 5/5",
      tone: "border-emerald-200 bg-emerald-50 text-emerald-800 dark:border-emerald-800 dark:bg-emerald-950/30 dark:text-emerald-100",
      progress: 100,
    };
  }
  return {
    label: "Evaluando sintomas",
    step: "Paso 1/5",
    tone: "border-slate-200 bg-slate-50 text-slate-800 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100",
    progress: 18,
  };
};

const extractAlertSignals = (source?: string) => {
  if (!source) return [];
  const matches = [
    /dificultad respiratoria/i.test(source) && "Dificultad respiratoria",
    /fiebre\s*(alta|>?\s*39)/i.test(source) && "Fiebre alta",
    /vision borrosa|vision doble/i.test(source) && "Alteracion visual",
    /confusion/i.test(source) && "Confusion",
    /urgenc/i.test(source) && "Posible urgencia",
  ].filter(Boolean);
  return Array.from(new Set(matches as string[])).slice(0, 3);
};

const getProgressMeta = (conversationState?: ConversationState | null, waiting?: boolean, triajeLevel?: string) => {
  const selected = conversationState?.questions_selected?.length || 0;
  const missing = conversationState?.missing_questions?.length || 0;
  if (selected > 0 || missing > 0) {
    const total = Math.max(selected + missing, 1);
    const step = Math.min(selected + 1, total);
    return {
      stepLabel: `Paso ${step}/${total}`,
      progress: Math.round((selected / total) * 100),
      phase: waiting ? "Procesando respuesta" : missing > 0 ? "Evaluando sintomas" : "Evaluacion completa",
    };
  }

  const fallback = getTriageStateMeta(triajeLevel, waiting);
  return {
    stepLabel: fallback.step,
    progress: fallback.progress,
    phase: waiting ? "Procesando respuesta" : "Evaluando sintomas",
  };
};

const renderMessageContent = (content: string) => {
  const lines = content
    .split("\n")
    .map((line) => line.replace(/\*\*/g, "").trim())
    .filter((line) => line.length > 0);

  return lines.map((line, index) => {
    if (/^#{1,3}\s*/.test(line)) {
      return (
        <p key={`${line}-${index}`} className="text-sm font-semibold tracking-tight">
          {line.replace(/^#{1,3}\s*/, "")}
        </p>
      );
    }

    if (/^\d+\.\s/.test(line) || /^[-•]\s/.test(line)) {
      return (
        <div key={`${line}-${index}`} className="flex gap-2 text-sm leading-6">
          <span className="mt-1 h-1.5 w-1.5 rounded-full bg-current/70" />
          <span>{line.replace(/^\d+\.\s|^[-•]\s/, "")}</span>
        </div>
      );
    }

    return (
      <p key={`${line}-${index}`} className="text-sm leading-6">
        {line}
      </p>
    );
  });
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
  const [painScaleDraft, setPainScaleDraft] = useState<number>(5);
  const [durationDraft, setDurationDraft] = useState("");
  const [selectedSymptoms, setSelectedSymptoms] = useState<string[]>([]);
  const [loaderMessage, setLoaderMessage] = useState("Analizando sintomas...");
  const [activeConversationDetail, setActiveConversationDetail] = useState<ConversationDetail | null>(null);
  const [conversationState, setConversationState] = useState<ConversationState | null>(null);
  const [decisionFlags, setDecisionFlags] = useState<DecisionFlags | null>(null);
  // UI state for collapsible panels
  const [triageHeaderExpanded, setTriageHeaderExpanded] = useState(false);
  const [inputPanelExpanded, setInputPanelExpanded] = useState(false);
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
    setPainScaleDraft(5);
    setDurationDraft("");
    setSelectedSymptoms([]);
    setActiveConversationDetail(null);
    setConversationState(null);
    setDecisionFlags(null);
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
        setActiveConversationDetail(detail);
        setMessages(mapConversationMessages(detail));
        setActiveTriageLevel(detail.triaje_level || "");
        setQuickReplies(FALLBACK_QUICK_REPLIES);
        setConversationState(null);
        setDecisionFlags(null);
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
    if (!activeConversationId) {
      setActiveConversationDetail(null);
      return;
    }
    const hydrateConversation = async () => {
      try {
        const detail = await getConversation(activeConversationId);
        if (detail) setActiveConversationDetail(detail);
      } catch {
        // Best effort hydration for structured UI hints.
      }
    };
    void hydrateConversation();
  }, [activeConversationId, messages.length]);

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
    if (payload.conversation_state) setConversationState(payload.conversation_state);
    if (payload.decision_flags) setDecisionFlags(payload.decision_flags);

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
    if (!isWaitingBot) return;
    const loaderMessages = [
      "Analizando sintomas...",
      "Comparando con protocolos...",
      "Revisando senales de alarma...",
    ];
    let index = 0;
    setLoaderMessage(loaderMessages[0]);
    const interval = window.setInterval(() => {
      index = (index + 1) % loaderMessages.length;
      setLoaderMessage(loaderMessages[index]);
    }, 1300);
    return () => window.clearInterval(interval);
  }, [isWaitingBot]);

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

    const contextualFragments = [
      painScaleDraft ? `Intensidad ${painScaleDraft}/10.` : "",
      durationDraft ? `Duracion aproximada: ${durationDraft}.` : "",
      selectedSymptoms.length > 0 ? `Sintomas asociados: ${selectedSymptoms.join(", ")}.` : "",
    ].filter(Boolean);
    const enrichedMessage = contextualFragments.length > 0
      ? `${trimmed}\n\n${contextualFragments.join(" ")}`
      : trimmed;

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

    const success = sendMessage(enrichedMessage, messagePayload);
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

  const toggleStructuredSymptom = (symptom: string) => {
    setSelectedSymptoms((prev) =>
      prev.includes(symptom) ? prev.filter((item) => item !== symptom) : [...prev, symptom]
    );
  };

  const latestUserMessage = useMemo(
    () => [...messages].reverse().find((message) => message.sender === "user")?.content || "",
    [messages]
  );

  const detectedSymptoms = useMemo(() => {
    const fromSession = activeSession?.symptoms?.slice(0, 3) || [];
    if (fromSession.length > 0) return fromSession;
    if (selectedSymptoms.length > 0) return selectedSymptoms.slice(0, 3);
    return [];
  }, [activeSession?.symptoms, selectedSymptoms]);

  const detectedDuration = useMemo(
    () => durationDraft || extractDurationFromText(latestUserMessage) || null,
    [durationDraft, latestUserMessage]
  );

  const displayedPainScale = activeConversationDetail?.pain_scale || painScaleDraft;
  const triageState = useMemo(
    () => getTriageStateMeta(activeTriageLevel, isWaitingBot),
    [activeTriageLevel, isWaitingBot]
  );
  const progressMeta = useMemo(
    () => getProgressMeta(conversationState, isWaitingBot, activeTriageLevel),
    [conversationState, isWaitingBot, activeTriageLevel]
  );
  const structuredContextPreview = useMemo(() => {
    const parts = [
      `Intensidad ${painScaleDraft}/10`,
      durationDraft ? `Duracion ${durationDraft}` : "",
      selectedSymptoms.length > 0 ? selectedSymptoms.join(", ") : "",
    ].filter(Boolean);
    return parts.join(" · ");
  }, [durationDraft, painScaleDraft, selectedSymptoms]);
  const alertSignals = useMemo(() => {
    const systemText = messages
      .filter((message) => message.sender !== "user")
      .map((message) => message.content)
      .join(" ");
    const reasonText = decisionFlags?.reasons?.join(" ") || "";
    return extractAlertSignals(`${systemText} ${reasonText}`);
  }, [messages, decisionFlags]);

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
    <div className="flex h-[calc(100dvh-8.2rem)] min-h-[600px] flex-col overflow-hidden bg-background">

      {/* ── COMPACT HEADER ── */}
      <div className="shrink-0 rounded-t-[1rem] border-b border-border/50 bg-background">
        {/* Top bar: always visible */}
        <div className="flex items-center justify-between gap-3 px-4 py-2 md:px-5">
          <div className="flex min-w-0 items-center gap-3">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-primary/12 text-lg">🤖</div>
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-1.5">
                <p className="text-sm font-semibold leading-none">Hipo</p>
                <span className={`rounded-full border px-2 py-0.5 text-[11px] font-semibold ${triageBadgeClass(activeTriageLevel)}`}>
                  {activeTriageLevel || "Sin clasificación"}
                </span>
                {isArchivedConversation && (
                  <span className="rounded-full border border-amber-300 bg-amber-100 px-2 py-0.5 text-[11px] font-semibold text-amber-900 dark:border-amber-700 dark:bg-amber-900/30 dark:text-amber-200">
                    Archivada
                  </span>
                )}
              </div>
              <p className="mt-0.5 flex items-center gap-1.5 text-[11px] text-muted-foreground">
                <TbPlugConnected className="h-3 w-3 text-primary" />
                {connectionLabel} · Asistente de triaje
              </p>
            </div>
          </div>

          <div className="flex items-center gap-1.5">
            {/* Progress pill — always visible summary */}
            <button
              type="button"
              onClick={() => setTriageHeaderExpanded((v) => !v)}
              className="hidden items-center gap-1.5 rounded-full border border-border/60 bg-muted/50 px-3 py-1 text-xs font-medium text-muted-foreground transition hover:bg-accent sm:flex"
              aria-expanded={triageHeaderExpanded}
            >
              <TbActivityHeartbeat className="h-3.5 w-3.5 text-primary" />
              <span>{progressMeta.stepLabel}</span>
              {triageHeaderExpanded ? <TbChevronUp className="h-3 w-3" /> : <TbChevronDown className="h-3 w-3" />}
            </button>

            <Button onClick={startNewConversation} className="h-8 rounded-full px-3 text-xs">
              + Nueva sesión
            </Button>
            <Button asChild variant="outline" size="icon" className="h-8 w-8 rounded-full" aria-label="Historial">
              <Link href={ROUTES.PROTECTED.CHAT_SESSIONS}>
                <TbFileDescription className="h-3.5 w-3.5" />
              </Link>
            </Button>
            <Button variant="outline" size="icon" className="h-8 w-8 rounded-full" onClick={reconnect} disabled={isConnecting} aria-label="Reconectar">
              <TbRefresh className="h-3.5 w-3.5" />
            </Button>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" size="icon" className="h-8 w-8 rounded-full" aria-label="Opciones">
                  <TbDotsVertical className="h-3.5 w-3.5" />
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

        {/* Collapsible triage detail panel */}
        {triageHeaderExpanded && (
          <div className="border-t border-border/50 px-4 pb-3 pt-2 md:px-5">
            <div className="grid items-start gap-2 xl:grid-cols-[1.05fr_0.95fr]">
              {/* State card */}
              <div className={`rounded-2xl border px-3 py-2.5 ${triageState.tone}`}>
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <p className="text-[10px] font-semibold uppercase tracking-[0.16em] opacity-80">Estado actual</p>
                    <p className="mt-0.5 text-sm font-semibold">{triageState.label}</p>
                    <p className="text-[11px] opacity-80">{progressMeta.phase}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-xs font-semibold">{progressMeta.stepLabel}</p>
                    <p className="text-[11px] opacity-80">
                      {activeTriageLevel ? `Nivel: ${activeTriageLevel}` : "Recogiendo datos"}
                    </p>
                  </div>
                </div>
                <div className="mt-2 h-1.5 rounded-full bg-black/5 dark:bg-white/10">
                  <div
                    className="h-1.5 rounded-full bg-current/70 transition-all"
                    style={{ width: `${progressMeta.progress}%` }}
                  />
                </div>
                <div className="mt-2 grid gap-1.5 text-[11px] md:grid-cols-3">
                  <div className="rounded-xl bg-black/5 px-2.5 py-1.5 dark:bg-white/10">
                    <p className="font-semibold">Nivel</p>
                    <p className="opacity-80">{activeTriageLevel || "Sin clasificar"}</p>
                  </div>
                  <div className="rounded-xl bg-black/5 px-2.5 py-1.5 dark:bg-white/10">
                    <p className="font-semibold">Fase</p>
                    <p className="opacity-80">{progressMeta.phase}</p>
                  </div>
                  <div className="rounded-xl bg-black/5 px-2.5 py-1.5 dark:bg-white/10">
                    <p className="font-semibold">Modo</p>
                    <p className="opacity-80">Evaluacion guiada</p>
                  </div>
                </div>
              </div>

              {/* Analysis card */}
              <div className="rounded-2xl border border-border/70 bg-muted/40 px-3 py-2.5">
                <div className="flex items-center gap-2">
                  <TbActivityHeartbeat className="h-4 w-4 text-primary" />
                  <p className="text-sm font-semibold">Hipo esta analizando</p>
                </div>
                <div className="mt-2 grid gap-1.5 text-xs">
                  <div className="flex items-start justify-between gap-3">
                    <span className="text-muted-foreground">Sintomas detectados</span>
                    <span className="text-right font-medium">
                      {detectedSymptoms.length > 0 ? detectedSymptoms.join(", ") : "Pendiente"}
                    </span>
                  </div>
                  <div className="flex items-start justify-between gap-3">
                    <span className="text-muted-foreground">Duracion</span>
                    <span className="text-right font-medium">{detectedDuration || "Sin confirmar"}</span>
                  </div>
                  <div className="flex items-start justify-between gap-3">
                    <span className="text-muted-foreground">Intensidad</span>
                    <span className="text-right font-medium">{displayedPainScale ? `${displayedPainScale}/10` : "Sin confirmar"}</span>
                  </div>
                  <div className="flex items-start justify-between gap-3">
                    <span className="text-muted-foreground">Riesgo actual</span>
                    <span className="text-right font-medium">
                      {activeTriageLevel ? activeTriageLevel : isWaitingBot ? "En evaluacion" : "Sin clasificar"}
                    </span>
                  </div>
                  {alertSignals.length > 0 && (
                    <div className="flex items-start justify-between gap-3">
                      <span className="text-muted-foreground">Alertas</span>
                      <span className="text-right font-medium text-amber-700 dark:text-amber-300">{alertSignals.join(", ")}</span>
                    </div>
                  )}
                </div>
                <p className="mt-2 border-t border-border/60 pt-2 text-[11px] text-muted-foreground">
                  {loadingSessions ? "Cargando historial..." : activeSession ? sessionPreview(activeSession) : "Describe tus sintomas con el mayor detalle posible para orientar mejor la evaluacion."}
                </p>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* ── MESSAGES AREA ── */}
      <div
        className="flex-1 space-y-3 overflow-y-auto bg-background px-4 pb-3 pt-3 md:px-6"
        aria-live="polite"
      >
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
          <div className="flex min-h-[320px] items-center justify-center px-4 py-6">
            <div className="flex max-w-md flex-col items-center text-center">
              <div className="flex h-24 w-24 items-center justify-center rounded-full bg-primary/10 ring-8 ring-primary/5">
                <span className="text-5xl">🤖</span>
              </div>
              <h3 className="mt-5 text-3xl font-semibold tracking-tight">Hipo</h3>
              <p className="mt-2 max-w-sm text-sm leading-6 text-muted-foreground">
                Describe tus síntomas con el mayor detalle posible. Hipo te hará preguntas para orientar la prioridad clínica.
              </p>
            </div>
          </div>
        )}

        {messages.map((message) => (
          <div key={message.id} className={`flex ${message.sender === "user" ? "justify-end" : "justify-start"}`}>
            <div
              className={`max-w-[92%] rounded-[1.35rem] px-4 py-3 md:max-w-[82%] xl:max-w-[72%] ${
                message.sender === "user"
                  ? "bg-primary text-primary-foreground shadow-sm"
                  : message.sender === "system"
                    ? /resumen final|nivel de prioridad|resultado preliminar/i.test(message.content)
                      ? "border border-emerald-200 bg-emerald-50 text-emerald-900 dark:border-emerald-800 dark:bg-emerald-950/35 dark:text-emerald-100"
                      : "border border-red-200 bg-red-50 text-red-800 dark:border-red-800 dark:bg-red-950/40 dark:text-red-200"
                    : "border border-slate-200 bg-slate-50 text-slate-900 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
              }`}
            >
              {/resumen final|nivel de prioridad|resultado preliminar/i.test(message.content) ? (
                <div className="space-y-4">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-[0.14em] text-emerald-700 dark:text-emerald-300">Resultado preliminar</p>
                    <div className="mt-2 space-y-2 whitespace-pre-wrap break-words text-[14px] leading-6">
                      {renderMessageContent(message.content)}
                    </div>
                  </div>
                  {activeTriageLevel && (
                    <div className="rounded-2xl border border-emerald-200/80 bg-white/70 px-4 py-3 dark:border-emerald-800/70 dark:bg-emerald-950/20">
                      <p className="text-xs font-semibold uppercase tracking-[0.14em] text-emerald-700 dark:text-emerald-300">Prioridad</p>
                      <p className="mt-1 text-base font-semibold">{activeTriageLevel}</p>
                      {alertSignals.length > 0 && (
                        <p className="mt-2 text-sm text-emerald-900/80 dark:text-emerald-100/80">Alertas: {alertSignals.join(", ")}</p>
                      )}
                    </div>
                  )}
                  <div className="flex flex-wrap gap-2">
                    <Button asChild size="sm" className="rounded-full">
                      <Link href={ROUTES.PROTECTED.APPOINTMENTS_NEW}>Solicitar cita</Link>
                    </Button>
                    <Button asChild size="sm" variant="outline" className="rounded-full">
                      <Link href={ROUTES.PROTECTED.TRIAGE_HISTORY}>Ver seguimiento</Link>
                    </Button>
                  </div>
                </div>
              ) : (
                <div className="space-y-2 whitespace-pre-wrap break-words text-[13.5px] leading-6 sm:text-[14px]">
                  {renderMessageContent(message.content)}
                </div>
              )}
              <div className="mt-2 flex items-center justify-between gap-4">
                <span
                  className={`text-xs ${
                    message.sender === "user"
                      ? "text-primary-foreground/80"
                      : message.sender === "system"
                        ? /resumen final|nivel de prioridad|resultado preliminar/i.test(message.content)
                          ? "text-emerald-700/90 dark:text-emerald-200/90"
                          : "text-red-700/90 dark:text-red-200/90"
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
            <div className="max-w-[92%] rounded-[1.35rem] border border-slate-200 bg-slate-50 px-4 py-3 md:max-w-[82%] xl:max-w-[72%] dark:border-slate-700 dark:bg-slate-800">
              <div className="flex items-center gap-2">
                <span className="h-2 w-2 rounded-full bg-slate-500 animate-bounce dark:bg-slate-300" />
                <span className="h-2 w-2 rounded-full bg-slate-500 animate-bounce [animation-delay:0.15s] dark:bg-slate-300" />
                <span className="h-2 w-2 rounded-full bg-slate-500 animate-bounce [animation-delay:0.3s] dark:bg-slate-300" />
              </div>
              <p className="mt-3 text-sm text-muted-foreground">{loaderMessage}</p>
            </div>
          </div>
        )}

        {chatError && (
          <div className="flex justify-start">
            <div className="max-w-[92%] rounded-[1.35rem] border border-red-200 bg-red-50 px-4 py-3 text-red-800 md:max-w-[82%] xl:max-w-[72%] dark:border-red-800 dark:bg-red-950/40 dark:text-red-200">
              <p className="text-sm">{chatError}</p>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* ── COMPOSER AREA ── */}
      <div className="shrink-0 bg-transparent px-4 pb-2 pt-4 md:px-6">
        <div className="w-full rounded-[1.35rem] border border-primary/15 bg-background shadow-[0_10px_28px_rgba(37,131,204,0.10)]">

          {/* Collapsible structured input panel */}
          {!isArchivedConversation && (
            <div className="px-3 pt-2">
              <button
                type="button"
                onClick={() => setInputPanelExpanded((v) => !v)}
                className="flex w-full items-center justify-between rounded-xl border border-primary/10 bg-primary/[0.03] px-3 py-1.5 text-xs font-medium text-muted-foreground transition hover:bg-accent"
              >
                <div className="flex items-center gap-2">
                  <TbSettings className="h-3.5 w-3.5" />
                  <span>Contexto clínico</span>
                  {structuredContextPreview && (
                    <span className="rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-semibold text-primary">
                      {structuredContextPreview}
                    </span>
                  )}
                </div>
                {inputPanelExpanded ? <TbChevronUp className="h-3.5 w-3.5" /> : <TbChevronDown className="h-3.5 w-3.5" />}
              </button>

              {inputPanelExpanded && (
                <div className="mt-2 rounded-2xl border border-border/70 bg-muted/30 px-3 py-3">
                  <div className="grid gap-3 lg:grid-cols-[0.9fr_0.8fr_1.3fr]">
                    <label className="space-y-1.5">
                      <span className="text-[10px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">Intensidad</span>
                      <div className="rounded-xl bg-background px-3 py-2.5">
                        <input
                          type="range"
                          min={1}
                          max={10}
                          value={painScaleDraft}
                          onChange={(event) => setPainScaleDraft(Number(event.target.value))}
                          className="w-full accent-[hsl(var(--primary))]"
                        />
                        <div className="mt-1 flex items-center justify-between text-xs text-muted-foreground">
                          <span>1</span>
                          <span className="font-semibold text-foreground">{painScaleDraft}/10</span>
                          <span>10</span>
                        </div>
                      </div>
                    </label>

                    <label className="space-y-1.5">
                      <span className="text-[10px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">Duracion</span>
                      <select
                        value={durationDraft}
                        onChange={(event) => setDurationDraft(event.target.value)}
                        className="min-h-11 w-full rounded-xl border border-input bg-background px-3 text-sm text-foreground outline-none focus:border-primary"
                      >
                        <option value="">Seleccionar</option>
                        {DURATION_OPTIONS.map((option) => (
                          <option key={option} value={option}>
                            {option}
                          </option>
                        ))}
                      </select>
                    </label>

                    <div className="space-y-1.5">
                      <span className="text-[10px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">Sintomas rapidos</span>
                      <div className="flex flex-wrap gap-1.5">
                        {STRUCTURED_SYMPTOM_OPTIONS.map((symptom) => {
                          const active = selectedSymptoms.includes(symptom);
                          return (
                            <button
                              key={symptom}
                              type="button"
                              onClick={() => toggleStructuredSymptom(symptom)}
                              className={`rounded-full border px-2.5 py-1 text-xs transition ${
                                active
                                  ? "border-primary/30 bg-primary/12 text-primary"
                                  : "border-border bg-background text-muted-foreground hover:bg-accent"
                              }`}
                            >
                              {symptom}
                            </button>
                          );
                        })}
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Text input row */}
          <form onSubmit={handleSendMessage} className="w-full px-2 pb-2 pt-2">
            <div className="flex items-end gap-2 rounded-[1.3rem] bg-transparent px-1 py-0.5 transition focus-within:ring-0">
              <Textarea
                value={input}
                onChange={(event) => handleInputChange(event.target.value)}
                onKeyDown={handleComposerKeyDown}
                rows={inputRows}
                placeholder={
                  isArchivedConversation
                    ? "Esta conversación está archivada"
                    : isConnected
                      ? "Escribe tu mensaje..."
                      : isConnecting
                        ? "Conectando..."
                        : "Sin conexión con el servidor"
                }
                className="min-h-[44px] max-h-32 resize-none border-0 bg-transparent px-3 py-2 text-[14px] leading-6 text-foreground caret-primary shadow-none focus-visible:ring-0 sm:text-[15px]"
                disabled={!isConnected || isWaitingBot || isArchivedConversation}
                aria-label="Mensaje para el asistente"
              />
              <div className="flex items-center gap-1 pb-1">
                <Button
                  type="button"
                  size="icon"
                  variant="ghost"
                  className="rounded-full text-muted-foreground hover:bg-accent/70"
                  aria-label="Adjuntar archivo"
                  disabled={isArchivedConversation}
                >
                  <TbPaperclip className="h-5 w-5" />
                </Button>
                <Button
                  type="button"
                  size="icon"
                  variant="ghost"
                  className="rounded-full text-muted-foreground hover:bg-accent/70"
                  aria-label="Dictado de voz"
                  disabled={isArchivedConversation}
                >
                  <TbMicrophone className="h-5 w-5" />
                </Button>
                <Button
                  type="submit"
                  className="h-11 rounded-2xl px-4 text-sm font-semibold shadow-sm"
                  disabled={!isConnected || !input.trim() || isWaitingBot || isArchivedConversation}
                  title={!isConnected ? "No conectado al servidor" : "Enviar mensaje"}
                  aria-label="Enviar mensaje"
                >
                  <TbSend className="h-4 w-4" />
                  Enviar
                </Button>
              </div>
            </div>
          </form>
        </div>

        <div className="mt-2 flex items-center justify-center gap-2 text-center text-[11px] text-muted-foreground">
          <TbCircleDot className="h-3.5 w-3.5 text-primary" />
          Hipo orienta y prioriza. El diagnostico definitivo siempre lo da un profesional sanitario.
          <TbClipboardText className="ml-1 h-3.5 w-3.5" />
        </div>
      </div>
    </div>
  );
}
