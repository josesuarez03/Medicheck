"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { Search } from "lucide-react";
import { TbArchive, TbArrowRight, TbRefresh, TbRestore, TbTrash } from "react-icons/tb";
import { PageHero } from "@/components/experience/ui";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  archiveConversation,
  deleteConversation,
  getConversations,
  recoverConversation,
} from "@/services/chatApi";
import type { ConversationSummary } from "@/types/messages";
import { ROUTES } from "@/routes/routePaths";

const CHAT_SELECTED_SESSION_KEY = "chat_selected_session_id";

const sessionTitle = (session: ConversationSummary) => {
  if (Array.isArray(session.symptoms) && session.symptoms.length > 0) return session.symptoms.join(", ");
  const firstUserMessage = session.messages?.find((msg) => msg.role === "user")?.content;
  return firstUserMessage?.slice(0, 64) || "Sesión de triaje";
};

const sessionPreview = (session: ConversationSummary) => {
  const firstAssistantMessage = session.messages?.find((msg) => msg.role === "assistant")?.content;
  return firstAssistantMessage?.slice(0, 90) || "Sin vista previa disponible.";
};

const triageClass = (level?: string) => {
  const value = String(level || "").toLowerCase();
  if (value.includes("urg")) return "border-red-300 bg-red-50 text-red-800 dark:border-red-800 dark:bg-red-950/40 dark:text-red-200";
  if (value.includes("mod")) return "border-amber-300 bg-amber-50 text-amber-900 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-200";
  return "border-emerald-300 bg-emerald-50 text-emerald-900 dark:border-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-200";
};

export default function ChatSessionsPage() {
  const [tab, setTab] = useState<"active" | "archived">("active");
  const [query, setQuery] = useState("");
  const [sessions, setSessions] = useState<ConversationSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionBusy, setActionBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadSessions = async (view: "active" | "archived") => {
    try {
      setLoading(true);
      setError(null);
      const data = await getConversations(view);
      setSessions(data);
    } catch {
      setError("No se pudieron cargar las sesiones.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadSessions(tab);
  }, [tab]);

  const filtered = useMemo(() => {
    const term = query.trim().toLowerCase();
    if (!term) return sessions;
    return sessions.filter((session) => {
      return sessionTitle(session).toLowerCase().includes(term) || sessionPreview(session).toLowerCase().includes(term);
    });
  }, [sessions, query]);

  const openInChat = (conversationId: string) => {
    sessionStorage.setItem(CHAT_SELECTED_SESSION_KEY, conversationId);
  };

  const handleArchive = async (conversationId: string) => {
    try {
      setActionBusy(`${conversationId}:archive`);
      await archiveConversation(conversationId);
      await loadSessions(tab);
    } finally {
      setActionBusy(null);
    }
  };

  const handleRecover = async (conversationId: string) => {
    try {
      setActionBusy(`${conversationId}:recover`);
      await recoverConversation(conversationId);
      await loadSessions(tab);
    } finally {
      setActionBusy(null);
    }
  };

  const handleDelete = async (conversationId: string) => {
    if (!window.confirm("¿Eliminar esta conversación?")) return;
    try {
      setActionBusy(`${conversationId}:delete`);
      await deleteConversation(conversationId);
      await loadSessions(tab);
    } finally {
      setActionBusy(null);
    }
  };

  return (
    <div className="space-y-6">
      <PageHero
        eyebrow="Historial de sesiones"
        title="Consulta sesiones activas y archivadas sin quitar protagonismo al chat."
        description="Las sesiones del chat viven en una vista separada para que la conversación siga siendo el foco principal y las acciones de gestión no compitan con ella."
        actions={
          <>
            <Button asChild className="rounded-full">
              <Link href={ROUTES.PROTECTED.CHAT}>Volver al chat</Link>
            </Button>
            <Button variant="outline" className="rounded-full" onClick={() => void loadSessions(tab)}>
              <TbRefresh className="h-4 w-4" />
              Actualizar
            </Button>
          </>
        }
      />

      <Card className="clinical-shell">
        <CardContent className="space-y-5 p-6">
          <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <div className="flex gap-2">
              <Button size="sm" variant={tab === "active" ? "default" : "outline"} className="rounded-full" onClick={() => setTab("active")}>
                Activas
              </Button>
              <Button size="sm" variant={tab === "archived" ? "default" : "outline"} className="rounded-full" onClick={() => setTab("archived")}>
                Archivadas
              </Button>
            </div>
            <label className="flex min-h-11 items-center gap-3 rounded-2xl border border-input bg-background px-4 md:w-[22rem]">
              <Search className="h-4 w-4 text-muted-foreground" />
              <Input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                className="border-0 bg-transparent p-0 shadow-none focus-visible:ring-0"
                placeholder={`Buscar sesión ${tab === "active" ? "activa" : "archivada"}...`}
                aria-label="Buscar sesión"
              />
            </label>
          </div>

          {error && (
            <div className="rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-800 dark:border-red-800 dark:bg-red-950/40 dark:text-red-200">
              {error}
            </div>
          )}

          {loading ? (
            <div className="rounded-2xl border border-border/70 bg-background p-6 text-sm text-muted-foreground">
              Cargando sesiones...
            </div>
          ) : filtered.length === 0 ? (
            <div className="rounded-2xl border border-border/70 bg-background p-6">
              <p className="font-medium">{tab === "active" ? "Sin sesiones activas" : "Sin sesiones archivadas"}</p>
              <p className="mt-2 text-sm text-muted-foreground">
                {tab === "active"
                  ? "Cuando completes un triaje, aparecerá aquí."
                  : "Archiva una conversación para verla en esta bandeja."}
              </p>
            </div>
          ) : (
            <div className="grid gap-4">
              {filtered.map((session) => (
                <div key={session._id} className="rounded-[1.6rem] border border-border/80 bg-background p-5 shadow-sm">
                  <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
                    <div className="space-y-3">
                      <div className="flex flex-wrap items-center gap-3">
                        <span className={`rounded-full border px-3 py-1 text-xs font-semibold ${triageClass(session.triaje_level)}`}>
                          {session.triaje_level || "Sin clasificación"}
                        </span>
                        <span className="text-sm text-muted-foreground">
                          {session.timestamp ? new Date(session.timestamp).toLocaleString("es-ES") : "Sin fecha"}
                        </span>
                      </div>
                      <div>
                        <h3 className="text-xl font-semibold tracking-tight">{sessionTitle(session)}</h3>
                        <p className="mt-2 max-w-3xl text-sm leading-7 text-muted-foreground">{sessionPreview(session)}</p>
                      </div>
                    </div>

                    <div className="flex flex-wrap gap-2">
                      <Button asChild variant="outline" className="rounded-full" onClick={() => openInChat(session._id)}>
                        <Link href={ROUTES.PROTECTED.CHAT}>
                          Abrir en chat
                          <TbArrowRight className="h-4 w-4" />
                        </Link>
                      </Button>
                      {tab === "active" ? (
                        <Button
                          variant="outline"
                          className="rounded-full"
                          onClick={() => void handleArchive(session._id)}
                          disabled={actionBusy === `${session._id}:archive`}
                        >
                          <TbArchive className="h-4 w-4" />
                          Archivar
                        </Button>
                      ) : (
                        <Button
                          variant="outline"
                          className="rounded-full"
                          onClick={() => void handleRecover(session._id)}
                          disabled={actionBusy === `${session._id}:recover`}
                        >
                          <TbRestore className="h-4 w-4" />
                          Recuperar
                        </Button>
                      )}
                      <Button
                        variant="danger"
                        className="rounded-full"
                        onClick={() => void handleDelete(session._id)}
                        disabled={actionBusy === `${session._id}:delete`}
                      >
                        <TbTrash className="h-4 w-4" />
                        Eliminar
                      </Button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
