"use client";

import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import API from "@/services/api";
import axios from "axios";
import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";
import { ROUTES } from "@/routes/routePaths";
import {
  TbActivityHeartbeat,
  TbAlertTriangle,
  TbArrowRight,
  TbCalendarEvent,
  TbChecklist,
  TbDroplet,
  TbFileText,
  TbMessageCircle,
  TbMoonStars,
  TbPill,
  TbRefresh,
  TbReportMedical,
} from "react-icons/tb";

type HistoryEntry = {
  id: string;
  created_at?: string;
  notes?: string | null;
  triaje_level?: string | null;
  medical_context?: string | null;
};

type HistoryResponse = {
  count?: number;
  results?: HistoryEntry[];
};

type PatientSummary = {
  triaje_level?: string | null;
  last_chatbot_analysis?: string | null;
  history_count?: number;
  medications?: string | null;
  data_validated_at?: string | null;
};

const relativeTimeEs = (isoDate?: string) => {
  if (!isoDate) return "Sin actividad reciente";
  const now = new Date().getTime();
  const then = new Date(isoDate).getTime();
  const delta = Math.max(0, now - then);
  const minutes = Math.floor(delta / 60000);
  if (minutes < 1) return "Hace unos segundos";
  if (minutes < 60) return `Hace ${minutes} min`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `Hace ${hours} h`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `Hace ${days} d`;
  const months = Math.floor(days / 30);
  return `Hace ${months} mes${months > 1 ? "es" : ""}`;
};

const triageClass = (level?: string | null) => {
  const value = (level || "").toLowerCase();
  if (value.includes("urgent") || value.includes("urgente")) {
    return "bg-red-100 text-red-800 border-red-300 dark:bg-red-950/40 dark:text-red-200 dark:border-red-800";
  }
  if (value.includes("moderad")) {
    return "bg-amber-100 text-amber-900 border-amber-300 dark:bg-amber-900/30 dark:text-amber-200 dark:border-amber-800";
  }
  return "bg-emerald-100 text-emerald-900 border-emerald-300 dark:bg-emerald-950/40 dark:text-emerald-200 dark:border-emerald-800";
};

const entryTitle = (entry: HistoryEntry) => {
  const fromNotes = entry.notes?.trim();
  if (fromNotes && !fromNotes.toLowerCase().includes("actualización automática")) return fromNotes;
  const fromContext = entry.medical_context?.trim();
  if (fromContext) return fromContext;
  return "Actualización clínica";
};

const nextCheckupLabel = (validatedAt?: string | null) => {
  if (!validatedAt) return "Programa tu revisión";
  const currentDate = new Date(validatedAt);
  currentDate.setMonth(currentDate.getMonth() + 6);
  return currentDate.toLocaleDateString("es-ES", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
};

export default function DashboardPage() {
  const router = useRouter();
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [initialLoadDone, setInitialLoadDone] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [historyCount, setHistoryCount] = useState(0);
  const [patient, setPatient] = useState<PatientSummary | null>(null);
  const requestInFlightRef = useRef(false);

  const loadDashboard = useCallback(
    async ({ silent = false }: { silent?: boolean } = {}) => {
      if (requestInFlightRef.current) return;
      requestInFlightRef.current = true;
      try {
        if (silent) {
          setRefreshing(true);
        } else {
          setLoading(true);
        }
        setError(null);

        if (user?.tipo !== "patient") {
          setPatient(null);
          setHistory([]);
          setHistoryCount(0);
          return;
        }

        const historyTokenResponse = await API.get("patients/me/history/token/");
        const historyToken = historyTokenResponse.data?.token;

        const [patientRes, historyRes] = await Promise.allSettled([
          API.get("patients/me/"),
          API.get("patients/me/history/", {
            params: { page_size: 6, token: historyToken },
          }),
        ]);

        let patientData: PatientSummary | null = null;
        if (patientRes.status === "fulfilled") {
          patientData = patientRes.value.data ?? null;
        } else {
          const patientStatus = axios.isAxiosError(patientRes.reason)
            ? patientRes.reason.response?.status
            : undefined;
          if (patientStatus !== 404) {
            throw patientRes.reason;
          }
        }

        let historyData: HistoryResponse | HistoryEntry[] = [];
        if (historyRes.status === "fulfilled") {
          historyData = historyRes.value.data;
        } else {
          const historyStatus = axios.isAxiosError(historyRes.reason)
            ? historyRes.reason.response?.status
            : undefined;
          if (historyStatus !== 404) {
            throw historyRes.reason;
          }
        }

        const entries = Array.isArray(historyData)
          ? historyData
          : Array.isArray(historyData.results)
            ? historyData.results
            : [];

        const sortedEntries = [...entries].sort((a, b) => {
          const first = a.created_at ? new Date(a.created_at).getTime() : 0;
          const second = b.created_at ? new Date(b.created_at).getTime() : 0;
          return second - first;
        });

        setPatient(patientData);
        setHistory(sortedEntries);

        const countFromHistory = Array.isArray(historyData)
          ? historyData.length
          : Number(historyData.count ?? sortedEntries.length);
        const safeCount = Number.isFinite(countFromHistory)
          ? countFromHistory
          : Number(patientData?.history_count ?? sortedEntries.length);

        setHistoryCount(safeCount);
      } catch {
        setError("Error al cargar el dashboard. Revisa la conexión e inténtalo de nuevo.");
      } finally {
        setLoading(false);
        setRefreshing(false);
        setInitialLoadDone(true);
        requestInFlightRef.current = false;
      }
    },
    [user?.tipo]
  );

  useEffect(() => {
    if (!user?.id) return;
    void loadDashboard({ silent: false });
  }, [user?.id, user?.tipo]);

  useEffect(() => {
    if (!user?.id || user?.tipo !== "patient") return;

    const refreshSilently = () => loadDashboard({ silent: true });
    const handleVisibility = () => {
      if (document.visibilityState === "visible") refreshSilently();
    };

    window.addEventListener("focus", refreshSilently);
    document.addEventListener("visibilitychange", handleVisibility);
    const refreshInterval = window.setInterval(refreshSilently, 45000);

    return () => {
      window.removeEventListener("focus", refreshSilently);
      document.removeEventListener("visibilitychange", handleVisibility);
      window.clearInterval(refreshInterval);
    };
  }, [loadDashboard, user?.id, user?.tipo]);

  const latestEntry = useMemo(() => history[0], [history]);
  const latestTriage = patient?.triaje_level || latestEntry?.triaje_level || null;
  const latestActivity = patient?.last_chatbot_analysis || latestEntry?.created_at;
  const isEmpty = historyCount === 0;
  const hasMedications = Boolean(patient?.medications?.trim());
  const hasRenderableData = Boolean(patient) || history.length > 0 || historyCount > 0;

  const triageBadgeClass = latestTriage
    ? triageClass(latestTriage)
    : "bg-slate-100 text-slate-800 border-slate-300 dark:bg-slate-800 dark:text-slate-100 dark:border-slate-600";

  if (loading && !initialLoadDone) {
    return (
      <div className="space-y-6">
        <section className="rounded-3xl overflow-hidden bg-gradient-to-r from-blue-800 via-blue-700 to-blue-600 p-6 md:p-8">
          <Skeleton className="h-4 w-28 bg-white/25" />
          <Skeleton className="h-12 w-80 mt-4 bg-white/30" />
          <Skeleton className="h-5 w-[28rem] mt-4 bg-white/25" />
          <div className="mt-6 flex gap-3">
            <Skeleton className="h-10 w-44 bg-white/30" />
            <Skeleton className="h-10 w-40 bg-white/20" />
          </div>
        </section>

        <section className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Skeleton className="h-28 rounded-2xl" />
          <Skeleton className="h-28 rounded-2xl" />
          <Skeleton className="h-28 rounded-2xl" />
        </section>

        <section className="grid grid-cols-1 xl:grid-cols-[1.45fr_1fr] gap-4">
          <Skeleton className="h-72 rounded-2xl" />
          <Skeleton className="h-72 rounded-2xl" />
        </section>
      </div>
    );
  }

  if (error && !hasRenderableData) {
    return (
      <div className="space-y-4">
        <Card className="rounded-2xl border border-red-200 bg-red-50 dark:border-red-900 dark:bg-red-950/40">
          <CardContent className="py-4 text-red-800 dark:text-red-200">{error}</CardContent>
        </Card>
        <Button onClick={() => loadDashboard()}>
          <TbRefresh className="h-4 w-4 mr-2" />
          Reintentar
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <section className="rounded-3xl overflow-hidden bg-gradient-to-r from-blue-800 via-blue-700 to-blue-600 text-white p-6 md:p-8 shadow-lg relative">
        <div className="absolute inset-0 pointer-events-none bg-[radial-gradient(circle_at_20%_80%,rgba(255,255,255,0.09),transparent_35%),radial-gradient(circle_at_80%_20%,rgba(255,255,255,0.09),transparent_30%)]" />
        <div className="relative z-10 flex flex-col md:flex-row md:items-center md:justify-between gap-6">
          <div>
            <p className="uppercase tracking-[0.1em] text-blue-200 text-xs md:text-sm font-semibold">Dashboard</p>
            <h2 className="text-3xl md:text-5xl font-bold tracking-tight mt-1">
              Bienvenido, <span className="text-blue-200">{user?.first_name || "Usuario"}</span>
            </h2>
            <p className="mt-3 text-blue-100 max-w-xl">
              {isEmpty
                ? "Empieza tu primer triaje para activar tu historial y métricas reales."
                : "Tus métricas se actualizan automáticamente con tu actividad de triaje."}
            </p>
            <p className="mt-3 text-xs text-blue-100/90">
              {refreshing ? "Actualizando datos..." : "Panel sincronizado"}
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
            <Button className="bg-white text-blue-800 hover:bg-blue-50" onClick={() => router.push(ROUTES.PROTECTED.CHAT)}>
              <TbMessageCircle className="h-4 w-4 mr-2" />
              {isEmpty ? "Iniciar primer triaje" : "Iniciar triaje"}
            </Button>
            <Button
              variant="outline"
              className="bg-white/15 border-white/60 text-white hover:bg-white/25 hover:text-white"
              onClick={() => router.push(ROUTES.PROTECTED.MEDICAL_DATA)}
            >
              <TbReportMedical className="h-4 w-4 mr-2" />
              Ver datos médicos
            </Button>
          </div>
        </div>
      </section>

      {!!error && (
        <Card className="rounded-2xl border border-amber-300 bg-amber-50 dark:border-amber-800 dark:bg-amber-950/40">
          <CardContent className="py-3 text-sm text-amber-900 dark:text-amber-100 flex items-center gap-2">
            <TbRefresh className="h-4 w-4" />
            {error}
          </CardContent>
        </Card>
      )}

      <section className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="card-elevated rounded-2xl">
          <CardContent className="pt-5 flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-200 flex items-center justify-center">
              <TbActivityHeartbeat className="h-6 w-6" />
            </div>
            <div>
              <p className="text-3xl font-bold text-foreground">{historyCount}</p>
              <p className="text-sm text-muted-foreground">Triajes realizados</p>
            </div>
          </CardContent>
        </Card>
        <Card className="card-elevated rounded-2xl">
          <CardContent className="pt-5 flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-200 flex items-center justify-center">
              <TbChecklist className="h-6 w-6" />
            </div>
            <div>
              <span className={`inline-flex text-base md:text-lg font-semibold rounded-full px-3 py-1 border ${triageBadgeClass}`}>
                {latestTriage || "Sin clasificación"}
              </span>
              <p className="text-sm text-muted-foreground mt-1">Último nivel de triaje</p>
            </div>
          </CardContent>
        </Card>
        <Card className="card-elevated rounded-2xl">
          <CardContent className="pt-5 flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-200 flex items-center justify-center">
              <TbCalendarEvent className="h-6 w-6" />
            </div>
            <div>
              <p className="text-2xl font-bold text-foreground">{relativeTimeEs(latestActivity)}</p>
              <p className="text-sm text-muted-foreground">Última actividad</p>
            </div>
          </CardContent>
        </Card>
      </section>

      <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          {
            label: "Hablar con Hipo",
            subtitle: "Inicia un nuevo triaje",
            icon: <TbMessageCircle className="h-5 w-5" />,
            action: () => router.push(ROUTES.PROTECTED.CHAT),
          },
          {
            label: "Mi historial",
            subtitle: "Revisa registros anteriores",
            icon: <TbFileText className="h-5 w-5" />,
            action: () => router.push(ROUTES.PROTECTED.MEDICAL_DATA),
          },
          {
            label: "Medicamentos",
            subtitle: hasMedications ? "Ver medicamentos guardados" : "Completa tus datos médicos",
            icon: <TbPill className="h-5 w-5" />,
            action: () => router.push(ROUTES.PROTECTED.MEDICAL_DATA),
          },
          {
            label: "Próxima revisión",
            subtitle: nextCheckupLabel(patient?.data_validated_at),
            icon: <TbCalendarEvent className="h-5 w-5" />,
            action: () => router.push(ROUTES.PROTECTED.MEDICAL_DATA),
          },
        ].map((item) => (
          <button
            key={item.label}
            onClick={item.action}
            className="card-elevated rounded-2xl bg-card p-5 text-left hover:shadow-md transition border border-border/70"
          >
            <div className="w-11 h-11 rounded-xl bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-200 flex items-center justify-center">
              {item.icon}
            </div>
            <p className="font-semibold mt-4 text-foreground">{item.label}</p>
            <p className="text-sm text-muted-foreground mt-1">{item.subtitle}</p>
          </button>
        ))}
      </section>

      <section className="grid grid-cols-1 xl:grid-cols-[1.45fr_1fr] gap-4">
        <Card className="card-elevated rounded-2xl">
          <CardContent className="pt-5">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-2xl font-semibold tracking-tight">Historial de triajes</h3>
              <Button variant="ghost" className="text-blue-700 dark:text-blue-300" onClick={() => router.push(ROUTES.PROTECTED.MEDICAL_DATA)}>
                Ver todos
                <TbArrowRight className="h-4 w-4 ml-1" />
              </Button>
            </div>
            {history.length === 0 ? (
              <div className="rounded-xl border border-border/70 p-5 bg-background/80">
                <p className="font-medium">Aún no tienes triajes registrados.</p>
                <p className="text-sm text-muted-foreground mt-1">
                  Cuando completes tu primer triaje, aquí aparecerá tu historial real.
                </p>
                <Button className="mt-4" onClick={() => router.push(ROUTES.PROTECTED.CHAT)}>
                  Iniciar primer triaje
                </Button>
              </div>
            ) : (
              <div className="space-y-3">
                {history.map((item) => (
                  <div key={item.id} className="rounded-xl border border-border/70 p-4 bg-background/80 flex items-center gap-3">
                    <span className="w-2.5 h-2.5 rounded-full bg-blue-500" />
                    <div className="flex-1 min-w-0">
                      <p className="font-medium truncate">{entryTitle(item)}</p>
                      <p className="text-sm text-muted-foreground">{relativeTimeEs(item.created_at)}</p>
                    </div>
                    <span className={`text-xs font-semibold rounded-full px-3 py-1 border ${triageClass(item.triaje_level)}`}>
                      {item.triaje_level || "Sin clasificación"}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="card-elevated rounded-2xl">
          <CardContent className="pt-5">
            <h3 className="text-2xl font-semibold tracking-tight mb-4">Consejos preventivos</h3>
            <div className="space-y-3">
              <div className="rounded-xl border border-border/70 p-4 bg-background/80">
                <p className="font-semibold text-foreground flex items-center gap-2">
                  <span className="inline-flex h-7 w-7 items-center justify-center rounded-full bg-cyan-100 text-cyan-700 dark:bg-cyan-900/40 dark:text-cyan-200">
                    <TbDroplet className="h-4 w-4" />
                  </span>
                  Hidratación
                </p>
                <p className="text-sm text-muted-foreground mt-2">
                  Mantén una ingesta regular de agua durante el día para apoyar tu recuperación.
                </p>
              </div>
              <div className="rounded-xl border border-border/70 p-4 bg-background/80">
                <p className="font-semibold text-foreground flex items-center gap-2">
                  <span className="inline-flex h-7 w-7 items-center justify-center rounded-full bg-indigo-100 text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-200">
                    <TbMoonStars className="h-4 w-4" />
                  </span>
                  Descanso
                </p>
                <p className="text-sm text-muted-foreground mt-2">
                  Prioriza 7-8 horas de sueño para reducir fatiga y mejorar la respuesta del organismo.
                </p>
              </div>
              <div className="rounded-xl border border-border/70 p-4 bg-background/80">
                <p className="font-semibold text-foreground flex items-center gap-2">
                  <span className="inline-flex h-7 w-7 items-center justify-center rounded-full bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-200">
                    <TbAlertTriangle className="h-4 w-4" />
                  </span>
                  Recuerda
                </p>
                <p className="text-sm text-muted-foreground mt-2">
                  Hipo orienta y clasifica. El diagnóstico definitivo siempre debe hacerlo un profesional médico.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </section>
    </div>
  );
}
