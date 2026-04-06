"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { Search } from "lucide-react";
import { TbArrowRight, TbCalendarPlus, TbFilter } from "react-icons/tb";
import { PageHero, TriagePill } from "@/components/experience/ui";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { chatEpisodes } from "@/services/clinicMockData";
import { ROUTES } from "@/routes/routePaths";

export default function TriageHistoryPage() {
  const [query, setQuery] = useState("");

  const filteredEpisodes = useMemo(() => {
    const term = query.trim().toLowerCase();
    if (!term) return chatEpisodes;

    return chatEpisodes.filter((episode) => {
      return (
        episode.recommendation.toLowerCase().includes(term) ||
        episode.summary.toLowerCase().includes(term) ||
        episode.triageLevel.toLowerCase().includes(term) ||
        episode.dateLabel.toLowerCase().includes(term)
      );
    });
  }, [query]);

  return (
    <div className="space-y-6">
      <PageHero
        eyebrow="Historial de triajes"
        title="Revisa tus episodios clínicos y vuelve a cualquier recomendación importante."
        description="Esta vista mantiene el histórico de episodios de triaje como recorrido clínico del paciente. Las sesiones del chat se consultan aparte desde el propio chat."
        actions={
          <>
            <Button asChild className="rounded-full">
              <Link href={ROUTES.PROTECTED.CHAT}>Iniciar nuevo triaje</Link>
            </Button>
            <Button asChild variant="outline" className="rounded-full">
              <Link href={ROUTES.PROTECTED.APPOINTMENT_NEW}>
                <TbCalendarPlus className="h-4 w-4" />
                Solicitar cita
              </Link>
            </Button>
          </>
        }
      />

      <Card className="clinical-shell">
        <CardContent className="space-y-5 p-6">
          <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <label className="flex min-h-11 items-center gap-3 rounded-2xl border border-input bg-background px-4 md:w-[24rem]">
              <Search className="h-4 w-4 text-muted-foreground" />
              <Input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                className="border-0 bg-transparent p-0 shadow-none focus-visible:ring-0"
                placeholder="Buscar por nivel, recomendación o resumen..."
                aria-label="Buscar triajes"
              />
            </label>
            <Button variant="outline" className="rounded-full">
              <TbFilter className="h-4 w-4" />
              Filtrar episodios
            </Button>
          </div>

          {filteredEpisodes.length === 0 ? (
            <div className="rounded-2xl border border-border/70 bg-background p-6">
              <p className="font-medium">Sin episodios para mostrar</p>
              <p className="mt-2 text-sm text-muted-foreground">
                Cuando completes más triajes, aparecerán aquí con su recomendación y prioridad.
              </p>
            </div>
          ) : (
            <div className="grid gap-4">
              {filteredEpisodes.map((episode) => (
                <div key={episode.id} className="rounded-[1.6rem] border border-border/80 bg-background p-5 shadow-sm">
                  <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
                    <div className="space-y-3">
                      <div className="flex flex-wrap items-center gap-3">
                        <TriagePill level={episode.triageLevel} />
                        <span className="text-sm text-muted-foreground">{episode.dateLabel}</span>
                      </div>
                      <div>
                        <h3 className="text-xl font-semibold tracking-tight">{episode.recommendation}</h3>
                        <p className="mt-2 max-w-3xl text-sm leading-7 text-muted-foreground">{episode.summary}</p>
                        <p className="mt-3 text-sm font-medium text-primary">
                          Prioridad sugerida: {episode.suggestedPriority}
                        </p>
                      </div>
                    </div>

                    <Button asChild variant="outline" className="rounded-full">
                      <Link href={`/chat/result/${episode.id}`}>
                        Ver resultado
                        <TbArrowRight className="h-4 w-4" />
                      </Link>
                    </Button>
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
