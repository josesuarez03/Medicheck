'use client';

import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useSocketIO } from '@/hooks/useWs';
import { useAuth } from '@/hooks/useAuth';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
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
  TbSearch,
  TbSend,
  TbTrash,
} from 'react-icons/tb';
import {
  archiveConversation,
  deleteAllConversations,
  deleteConversation,
  getConversation,
  getConversations,
  recoverConversation,
} from '@/services/chatApi';
import type {
  ChatResponsePayload,
  ConversationDetail,
  ConversationSummary,
  LifecycleStatus,
  Message,
} from '@/types/messages';

const RESPONSE_TIMEOUT_MS = 25000;
const FALLBACK_QUICK_REPLIES = [
  'Tengo fiebre desde ayer',
  'También me duele la garganta',
  '¿Debo ir a urgencias?',
];

const createMessageId = () => `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;

const formatTime = (isoDate: string) =>
  new Date(isoDate).toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' });

const relativeDate = (isoDate?: string) => {
  if (!isoDate) return '';
  const now = Date.now();
  const then = new Date(isoDate).getTime();
  const diff = Math.max(0, now - then);
  const days = Math.floor(diff / 86400000);
  if (days <= 0) return 'Hoy';
  if (days === 1) return 'Ayer';
  return `Hace ${days}d`;
};

const normalizeLifecycleStatus = (session?: Pick<ConversationSummary, 'lifecycle_status' | 'active'>): LifecycleStatus => {
  const status = String(session?.lifecycle_status || '').toLowerCase();
  if (status === 'archived' || status === 'deleted' || status === 'active') {
    return status;
  }
  if (session?.active === false) return 'archived';
  return 'active';
};

const triageBadgeClass = (triajeLevel?: string) => {
  const value = (triajeLevel || '').toLowerCase();
  if (value.includes('urgente')) return 'bg-red-100 text-red-800 border-red-300 dark:bg-red-950/40 dark:text-red-200 dark:border-red-800';
  if (value.includes('moderad')) return 'bg-amber-100 text-amber-900 border-amber-300 dark:bg-amber-900/40 dark:text-amber-200 dark:border-amber-800';
  if (!value) return 'bg-slate-100 text-slate-800 border-slate-300 dark:bg-slate-800 dark:text-slate-100 dark:border-slate-600';
  return 'bg-emerald-100 text-emerald-900 border-emerald-300 dark:bg-emerald-950/40 dark:text-emerald-200 dark:border-emerald-800';
};

const extractSuggestions = (payload?: ChatResponsePayload) => {
  const quickReplies = payload?.quick_replies;
  if (Array.isArray(quickReplies) && quickReplies.length > 0) {
    return quickReplies.filter((v): v is string => typeof v === 'string' && v.trim().length > 0).slice(0, 4);
  }
  return FALLBACK_QUICK_REPLIES;
};

const mapConversationMessages = (conversation: ConversationDetail): Message[] => {
  if (!Array.isArray(conversation.messages)) return [];
  return conversation.messages
    .filter((item) => item && typeof item.content === 'string')
    .map((item, index) => ({
      id: `${conversation._id}-${index}`,
      content: item.content,
      sender: item.role === 'user' ? 'user' : 'bot',
      status: 'sent',
      timestamp: conversation.timestamp || new Date().toISOString(),
    }));
};

const sessionTitle = (session: ConversationSummary) => {
  if (Array.isArray(session.symptoms) && session.symptoms.length > 0) {
    return session.symptoms.join(', ');
  }
  const firstUserMessage = session.messages?.find((msg) => msg.role === 'user')?.content;
  if (firstUserMessage) {
    return firstUserMessage.slice(0, 45);
  }
  return 'Sesión de triaje';
};

const sessionPreview = (session: ConversationSummary) => {
  const firstAssistantMessage = session.messages?.find((msg) => msg.role === 'assistant')?.content;
  if (firstAssistantMessage) return firstAssistantMessage.slice(0, 60);
  return 'Sin vista previa';
};

type SessionView = 'active' | 'archived';

export default function Chatbot() {
  const { user, isAuthenticated } = useAuth();
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [isWaitingBot, setIsWaitingBot] = useState(false);
  const [pendingMessageId, setPendingMessageId] = useState<string | null>(null);
  const [chatError, setChatError] = useState<string | null>(null);
  const [inputRows, setInputRows] = useState(1);
  const [sessions, setSessions] = useState<ConversationSummary[]>([]);
  const [loadingSessions, setLoadingSessions] = useState(true);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [activeConversationStatus, setActiveConversationStatus] = useState<LifecycleStatus>('active');
  const [searchTerm, setSearchTerm] = useState('');
  const [quickReplies, setQuickReplies] = useState<string[]>(FALLBACK_QUICK_REPLIES);
  const [activeTriageLevel, setActiveTriageLevel] = useState<string>('');
  const [sessionView, setSessionView] = useState<SessionView>('active');
  const [sessionActionBusy, setSessionActionBusy] = useState<string | null>(null);
  const [bulkActionBusy, setBulkActionBusy] = useState(false);
  const responseTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const lastProcessedSocketIndexRef = useRef(-1);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const socketUrl = process.env.NEXT_PUBLIC_SOCKETIO_URL || 'http://localhost:5000';
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

  const refreshSessions = useCallback(
    async (view: SessionView = sessionView) => {
      const items = await getConversations(view);
      const sorted = [...items].sort((a, b) => {
        const ta = new Date(a.timestamp || 0).getTime();
        const tb = new Date(b.timestamp || 0).getTime();
        return tb - ta;
      });
      setSessions(sorted);
    },
    [sessionView]
  );

  useEffect(() => {
    if (isAuthenticated && isConnected) {
      reauthenticate();
    }
  }, [isAuthenticated, isConnected, reauthenticate]);

  useEffect(() => {
    const fetchSessions = async () => {
      try {
        setLoadingSessions(true);
        await refreshSessions(sessionView);
      } catch {
        setChatError('No se pudo cargar el historial de sesiones.');
      } finally {
        setLoadingSessions(false);
      }
    };

    if (isAuthenticated) fetchSessions();
  }, [isAuthenticated, sessionView, refreshSessions]);

  useEffect(() => {
    if (socketMessages.length === 0) return;
    const lastIndex = socketMessages.length - 1;
    if (lastProcessedSocketIndexRef.current === lastIndex) return;
    lastProcessedSocketIndexRef.current = lastIndex;
    const payload = socketMessages[lastIndex];
    const responseText =
      payload.ai_response ||
      payload.response ||
      (typeof payload.message === 'string' ? payload.message : '');
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
        sender: 'bot',
        status: 'sent',
        timestamp: new Date().toISOString(),
      },
    ]);

    setQuickReplies(extractSuggestions(payload));

    if (payload.triaje_level) {
      setActiveTriageLevel(payload.triaje_level);
    }

    if (payload.conversation_id && payload.conversation_id !== activeConversationId) {
      setActiveConversationId(payload.conversation_id);
      setActiveConversationStatus('active');
      setSessions((prev) => {
        const exists = prev.some((item) => item._id === payload.conversation_id);
        if (exists) return prev;
        return [
          {
            _id: payload.conversation_id,
            timestamp: new Date().toISOString(),
            triaje_level: payload.triaje_level,
            lifecycle_status: 'active',
            messages: [
              { role: 'user', content: payload.user_message || '' },
              { role: 'assistant', content: responseText },
            ],
          },
          ...prev,
        ];
      });
    }

    if (pendingMessageId) {
      setMessages((prev) =>
        prev.map((message) =>
          message.id === pendingMessageId && message.status === 'pending'
            ? { ...message, status: 'sent' }
            : message
        )
      );
      setPendingMessageId(null);
    }

    setIsWaitingBot(false);
    setChatError(null);
  }, [socketMessages, pendingMessageId, activeConversationId]);

  useEffect(() => {
    if (!socketError) return;
    if (responseTimeoutRef.current) {
      clearTimeout(responseTimeoutRef.current);
      responseTimeoutRef.current = null;
    }
    if (pendingMessageId) {
      setMessages((prev) =>
        prev.map((message) =>
          message.id === pendingMessageId ? { ...message, status: 'error' } : message
        )
      );
      setPendingMessageId(null);
    }
    setIsWaitingBot(false);

    if (socketError.includes('conversation_archived')) {
      setChatError('Esta conversación está archivada. Recupérala para enviar mensajes.');
      if (activeConversationId) {
        setActiveConversationStatus('archived');
      }
    } else {
      setChatError(socketError);
    }
  }, [socketError, pendingMessageId, activeConversationId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isWaitingBot]);

  useEffect(() => {
    return () => {
      if (responseTimeoutRef.current) clearTimeout(responseTimeoutRef.current);
    };
  }, []);

  const connectionLabel = useMemo(() => {
    if (isConnected) return 'Conectado';
    if (isConnecting) return 'Conectando';
    if (connectionError) return 'Sin conexión';
    return 'Desconectado';
  }, [isConnected, isConnecting, connectionError]);

  const filteredSessions = useMemo(() => {
    const term = searchTerm.trim().toLowerCase();
    if (!term) return sessions;
    return sessions.filter((session) => {
      const title = sessionTitle(session).toLowerCase();
      const preview = sessionPreview(session).toLowerCase();
      return title.includes(term) || preview.includes(term);
    });
  }, [sessions, searchTerm]);

  const isArchivedConversation = activeConversationStatus === 'archived';

  const startNewConversation = () => {
    setActiveConversationId(null);
    setActiveConversationStatus('active');
    setMessages([]);
    setChatError(null);
    setActiveTriageLevel('');
    setQuickReplies(FALLBACK_QUICK_REPLIES);
    lastProcessedSocketIndexRef.current = socketMessages.length - 1;
  };

  const selectConversation = async (conversationId: string) => {
    try {
      setChatError(null);
      const detail = await getConversation(conversationId);
      if (!detail) {
        setChatError('No se pudo abrir la conversación seleccionada.');
        return;
      }
      setActiveConversationId(conversationId);
      setActiveConversationStatus(normalizeLifecycleStatus(detail));
      setMessages(mapConversationMessages(detail));
      setActiveTriageLevel(detail.triaje_level || '');
      setQuickReplies(FALLBACK_QUICK_REPLIES);
      lastProcessedSocketIndexRef.current = socketMessages.length - 1;
    } catch {
      setChatError('Error al cargar la conversación.');
    }
  };

  const handleArchiveConversation = async (conversationId: string) => {
    try {
      setSessionActionBusy(`${conversationId}:archive`);
      setChatError(null);
      await archiveConversation(conversationId);
      if (activeConversationId === conversationId) {
        setActiveConversationStatus('archived');
        setSessionView('archived');
      }
      await refreshSessions(activeConversationId === conversationId ? 'archived' : sessionView);
    } catch {
      setChatError('No se pudo archivar la conversación.');
    } finally {
      setSessionActionBusy(null);
    }
  };

  const handleRecoverConversation = async (conversationId: string) => {
    try {
      setSessionActionBusy(`${conversationId}:recover`);
      setChatError(null);
      await recoverConversation(conversationId);
      if (activeConversationId === conversationId) {
        setActiveConversationStatus('active');
        setSessionView('active');
      }
      await refreshSessions(activeConversationId === conversationId ? 'active' : sessionView);
    } catch {
      setChatError('No se pudo recuperar la conversación.');
    } finally {
      setSessionActionBusy(null);
    }
  };

  const handleDeleteConversation = async (conversationId: string) => {
    if (!window.confirm('¿Eliminar esta sesión? Se ocultará y se conservará por 30 días.')) return;
    try {
      setSessionActionBusy(`${conversationId}:delete`);
      setChatError(null);
      await deleteConversation(conversationId);
      if (activeConversationId === conversationId) {
        startNewConversation();
      }
      await refreshSessions(sessionView);
    } catch {
      setChatError('No se pudo eliminar la conversación.');
    } finally {
      setSessionActionBusy(null);
    }
  };

  const handleDeleteAll = async () => {
    if (!window.confirm('¿Eliminar todas las sesiones visibles? Se ocultarán y se conservarán por 30 días.')) return;
    try {
      setBulkActionBusy(true);
      setChatError(null);
      await deleteAllConversations();
      startNewConversation();
      await refreshSessions(sessionView);
    } catch {
      setChatError('No se pudieron eliminar todas las sesiones.');
    } finally {
      setBulkActionBusy(false);
    }
  };

  const submitMessage = () => {
    const trimmed = input.trim();
    if (!trimmed || !isConnected || isArchivedConversation) return;

    const userMessageId = createMessageId();
    const userMessage: Message = {
      id: userMessageId,
      content: trimmed,
      sender: 'user',
      status: 'pending',
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setPendingMessageId(userMessageId);
    setIsWaitingBot(true);
    setChatError(null);

    const messagePayload = {
      message: trimmed,
      timestamp: new Date().toISOString(),
      context: {},
      conversation_id: activeConversationId,
    };

    const success = sendMessage(JSON.stringify(messagePayload));
    if (!success) {
      setMessages((prev) =>
        prev.map((message) => (message.id === userMessageId ? { ...message, status: 'error' } : message))
      );
      setPendingMessageId(null);
      setIsWaitingBot(false);
      setChatError('No se pudo enviar el mensaje. Revisa la conexión e intenta otra vez.');
      return;
    }

    responseTimeoutRef.current = setTimeout(() => {
      setMessages((prev) =>
        prev.map((message) => (message.id === userMessageId ? { ...message, status: 'error' } : message))
      );
      setPendingMessageId(null);
      setIsWaitingBot(false);
      setChatError('No se recibió respuesta del asistente. Intenta enviar nuevamente.');
    }, RESPONSE_TIMEOUT_MS);

    setInput('');
    setInputRows(1);
  };

  const handleSendMessage = (event: React.FormEvent) => {
    event.preventDefault();
    submitMessage();
  };

  const handleComposerKeyDown = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      submitMessage();
    }
  };

  const handleInputChange = (value: string) => {
    setInput(value);
    const lines = value.split('\n').length;
    setInputRows(Math.min(5, Math.max(1, lines)));
  };

  const applySuggestion = (suggestion: string) => {
    if (isArchivedConversation) return;
    setInput(suggestion);
    setInputRows(Math.min(5, Math.max(1, suggestion.split('\n').length)));
  };

  return (
    <div className="h-[calc(100vh-8rem)] rounded-2xl border border-border/70 bg-card shadow-sm overflow-hidden grid grid-cols-1 lg:grid-cols-[320px_1fr]">
      <aside className="border-r border-border/70 bg-card/80 flex flex-col min-h-0">
        <div className="p-4 border-b border-border/70">
          <h3 className="text-2xl font-semibold tracking-tight">Sesiones</h3>
          <div className="mt-3 flex gap-2">
            <Button
              size="sm"
              variant={sessionView === 'active' ? 'default' : 'outline'}
              onClick={() => setSessionView('active')}
            >
              Activas
            </Button>
            <Button
              size="sm"
              variant={sessionView === 'archived' ? 'default' : 'outline'}
              onClick={() => setSessionView('archived')}
            >
              Archivadas
            </Button>
          </div>
          <div className="mt-3 relative">
            <TbSearch className="h-4 w-4 text-muted-foreground absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              className="w-full rounded-xl border border-input bg-background py-2 pl-9 pr-3 text-sm outline-none focus:ring-2 focus:ring-ring"
              placeholder={`Buscar sesión ${sessionView === 'active' ? 'activa' : 'archivada'}...`}
              value={searchTerm}
              onChange={(event) => setSearchTerm(event.target.value)}
            />
          </div>
        </div>

        <div className="p-3 space-y-2 overflow-y-auto min-h-0">
          {loadingSessions ? (
            <div className="text-sm text-muted-foreground px-2 py-3">Cargando sesiones...</div>
          ) : filteredSessions.length === 0 ? (
            <div className="rounded-xl border border-border/60 bg-background p-4">
              <p className="font-medium">{sessionView === 'active' ? 'Sin sesiones activas' : 'Sin sesiones archivadas'}</p>
              <p className="text-sm text-muted-foreground mt-1">
                {sessionView === 'active'
                  ? 'Cuando completes un triaje, aparecerá aquí.'
                  : 'Archiva una sesión activa para verla aquí.'}
              </p>
            </div>
          ) : (
            filteredSessions.map((session) => {
              const lifecycle = normalizeLifecycleStatus(session);
              const isBusyArchive = sessionActionBusy === `${session._id}:archive`;
              const isBusyRecover = sessionActionBusy === `${session._id}:recover`;
              const isBusyDelete = sessionActionBusy === `${session._id}:delete`;
              return (
                <div
                  key={session._id}
                  className={`w-full rounded-xl border p-3 text-left transition ${
                    activeConversationId === session._id
                      ? 'border-blue-300 bg-blue-100/70 dark:border-blue-700 dark:bg-blue-950/30'
                      : 'border-border/60 bg-background hover:bg-muted/40 dark:hover:bg-muted/60'
                  }`}
                >
                  <button className="w-full text-left" onClick={() => selectConversation(session._id)}>
                    <div className="flex items-center justify-between gap-2">
                      <p className="font-semibold truncate">{sessionTitle(session)}</p>
                      <span className="text-xs text-muted-foreground shrink-0">{relativeDate(session.timestamp)}</span>
                    </div>
                    <p className="text-sm text-muted-foreground truncate mt-1">{sessionPreview(session)}</p>
                    <p className="text-xs mt-2 font-medium text-blue-700 dark:text-blue-300">
                      {session.triaje_level || 'Sin clasificación'}
                      {lifecycle === 'archived' ? ' · Archivada' : ''}
                    </p>
                  </button>
                  <div className="mt-3 flex items-center gap-2">
                    {lifecycle === 'active' ? (
                      <Button size="sm" variant="outline" onClick={() => handleArchiveConversation(session._id)} disabled={isBusyArchive}>
                        <TbArchive className="h-4 w-4" />
                        Archivar
                      </Button>
                    ) : (
                      <Button size="sm" variant="outline" onClick={() => handleRecoverConversation(session._id)} disabled={isBusyRecover}>
                        <TbRestore className="h-4 w-4" />
                        Recuperar
                      </Button>
                    )}
                    <Button size="sm" variant="danger" onClick={() => handleDeleteConversation(session._id)} disabled={isBusyDelete}>
                      <TbTrash className="h-4 w-4" />
                      Eliminar
                    </Button>
                  </div>
                </div>
              );
            })
          )}
        </div>

        <div className="p-3 border-t border-border/70 space-y-2">
          {sessionView === 'active' && (
            <Button className="w-full" onClick={startNewConversation}>
              + Nueva sesión
            </Button>
          )}
          <Button className="w-full" variant="danger" onClick={handleDeleteAll} disabled={bulkActionBusy}>
            <TbTrash className="h-4 w-4" />
            Eliminar todas
          </Button>
        </div>
      </aside>

      <section className="min-h-0 flex flex-col">
        <div className="h-16 border-b border-border/70 px-4 md:px-5 flex items-center justify-between bg-card">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center font-semibold">🤖</div>
            <div>
              <p className="font-semibold text-xl leading-none">Hipo</p>
              <p className="text-sm text-muted-foreground flex items-center gap-2 mt-1">
                <TbPlugConnected className="h-4 w-4 text-blue-500" />
                {connectionLabel} · Asistente de triaje
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className={`text-xs font-semibold rounded-full px-3 py-1 border ${triageBadgeClass(activeTriageLevel)}`}>
              {activeTriageLevel || 'Sin clasificación'}
            </span>
            {isArchivedConversation && (
              <span className="text-xs font-semibold rounded-full px-3 py-1 border border-amber-300 bg-amber-100 text-amber-900 dark:bg-amber-900/30 dark:text-amber-200 dark:border-amber-700">
                Archivada
              </span>
            )}
            <Button variant="outline" size="icon" aria-label="Resumen">
              <TbFileDescription className="h-4 w-4" />
            </Button>
            <Button variant="outline" size="icon" onClick={reconnect} disabled={isConnecting} aria-label="Reconectar">
              <TbRefresh className="h-4 w-4" />
            </Button>
            <Button variant="outline" size="icon" aria-label="Opciones">
              <TbDotsVertical className="h-4 w-4" />
            </Button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-4 md:p-6 space-y-4 bg-muted/30 dark:bg-slate-900/20" aria-live="polite">
          {isArchivedConversation && activeConversationId && (
            <div className="rounded-xl border border-amber-300 bg-amber-50 text-amber-900 dark:bg-amber-900/25 dark:border-amber-700 dark:text-amber-100 p-4 flex items-center justify-between gap-3">
              <div className="text-sm flex items-center gap-2">
                <TbLock className="h-4 w-4" />
                Esta conversación está archivada. El envío de mensajes está desactivado.
              </div>
              <Button size="sm" onClick={() => handleRecoverConversation(activeConversationId)}>
                <TbRestore className="h-4 w-4" />
                Recuperar conversación
              </Button>
            </div>
          )}

          {messages.length === 0 && !isWaitingBot && !chatError && (
            <div className="h-full flex items-center justify-center">
              <div className="max-w-md text-center rounded-2xl border border-border/70 bg-card p-6">
                <p className="font-semibold">Inicia una conversación con Hipo</p>
                <p className="text-sm text-muted-foreground mt-2">
                  Escribe tu primer síntoma para comenzar el triaje. Si no tienes sesiones previas, esta será tu primera.
                </p>
              </div>
            </div>
          )}

          {messages.map((message) => (
            <div key={message.id} className={`flex ${message.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div
                className={`max-w-[90%] md:max-w-[78%] rounded-2xl px-4 py-3 ${
                  message.sender === 'user'
                    ? 'bg-blue-600 text-white shadow-sm dark:bg-blue-600 dark:text-white'
                    : message.sender === 'system'
                      ? 'bg-red-50 border border-red-200 text-red-800 dark:bg-red-950/40 dark:border-red-800 dark:text-red-200'
                      : 'bg-slate-50 border border-slate-200 text-slate-900 dark:bg-slate-800 dark:border-slate-700 dark:text-slate-100'
                }`}
              >
                <p className="whitespace-pre-wrap break-words text-[15px] leading-7">{message.content}</p>
                <div className="mt-2 flex items-center justify-between gap-4">
                  <span
                    className={`text-xs ${
                      message.sender === 'user'
                        ? 'text-blue-100'
                        : message.sender === 'system'
                          ? 'text-red-700/90 dark:text-red-200/90'
                          : 'text-slate-500 dark:text-slate-300'
                    }`}
                  >
                    {formatTime(message.timestamp)}
                  </span>
                  {message.status === 'pending' && <span className="text-xs text-blue-100/95">Enviando...</span>}
                  {message.status === 'error' && (
                    <span className="text-xs text-red-600 dark:text-red-300 flex items-center gap-1">
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
              <div className="max-w-[90%] md:max-w-[78%] rounded-2xl px-4 py-3 bg-slate-50 border border-slate-200 dark:bg-slate-800 dark:border-slate-700">
                <div className="flex items-center gap-2">
                  <span className="h-2 w-2 rounded-full bg-slate-500 dark:bg-slate-300 animate-bounce" />
                  <span className="h-2 w-2 rounded-full bg-slate-500 dark:bg-slate-300 animate-bounce [animation-delay:0.15s]" />
                  <span className="h-2 w-2 rounded-full bg-slate-500 dark:bg-slate-300 animate-bounce [animation-delay:0.3s]" />
                </div>
              </div>
            </div>
          )}

          {chatError && (
            <div className="flex justify-start">
              <div className="max-w-[90%] md:max-w-[78%] rounded-2xl px-4 py-3 bg-red-50 border border-red-200 text-red-800 dark:bg-red-950/40 dark:border-red-800 dark:text-red-200">
                <p className="text-sm">{chatError}</p>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        <div className="border-t border-border/70 bg-card px-4 py-3 space-y-3">
          {!isArchivedConversation && (
            <div className="flex flex-wrap gap-2">
              {quickReplies.map((item) => (
                <button
                  key={item}
                  type="button"
                  className="rounded-full border border-input bg-background px-3 py-1.5 text-sm text-foreground hover:bg-muted transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  onClick={() => applySuggestion(item)}
                >
                  {item}
                </button>
              ))}
            </div>
          )}

          <form onSubmit={handleSendMessage} className="w-full flex items-end gap-2">
            <Textarea
              value={input}
              onChange={(event) => handleInputChange(event.target.value)}
              onKeyDown={handleComposerKeyDown}
              rows={inputRows}
              placeholder={
                isArchivedConversation
                  ? 'Esta conversación está archivada'
                  : isConnected
                    ? 'Escribe tu mensaje aquí...'
                    : isConnecting
                      ? 'Conectando...'
                      : 'Sin conexión con el servidor'
              }
              className="min-h-[44px] max-h-36 resize-none bg-background/95"
              disabled={!isConnected || isWaitingBot || isArchivedConversation}
              aria-label="Mensaje para el asistente"
            />
            <div className="flex items-center gap-1">
              <Button type="button" size="icon" variant="ghost" aria-label="Adjuntar archivo" disabled={isArchivedConversation}>
                <TbPaperclip className="h-5 w-5" />
              </Button>
              <Button type="button" size="icon" variant="ghost" aria-label="Dictado de voz" disabled={isArchivedConversation}>
                <TbMicrophone className="h-5 w-5" />
              </Button>
              <Button
                type="submit"
                size="icon"
                disabled={!isConnected || !input.trim() || isWaitingBot || isArchivedConversation}
                title={!isConnected ? 'No conectado al servidor' : 'Enviar mensaje'}
                aria-label="Enviar mensaje"
              >
                <TbSend className="h-5 w-5" />
              </Button>
            </div>
          </form>
          <div className="text-xs text-muted-foreground flex items-center gap-2">
            <TbCircleDot className="h-4 w-4 text-blue-500" />
            Hipo orienta y prioriza. El diagnóstico definitivo siempre lo da un profesional sanitario.
            <TbClipboardText className="h-4 w-4 ml-1" />
          </div>
        </div>
      </section>
    </div>
  );
}
