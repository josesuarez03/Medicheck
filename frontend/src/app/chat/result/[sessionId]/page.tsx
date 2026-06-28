"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { TbCalendarPlus, TbMessageCircle } from "react-icons/tb";
import { PageHero, TriagePill } from "@/components/experience/ui";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { chatEpisodes } from "@/services/clinicMockData";
import { ROUTES } from "@/routes/routePaths";

export default function ChatResultPage() {
  const params = useParams<{ sessionId: string }>();
  const episode = chatEpisodes.find((item) => item.id === params.sessionId) || chatEpisodes[0];

  return (
    <div className="space-y-6">
      <PageHero
        eyebrow="Resultado del episodio"
        title="El resumen final queda listo para decidir el siguiente paso."
        description="Esta pantalla traduce el cierre del chat en una salida accionable para el paciente: entender la recomendación, guardar el resumen y solicitar cita si corresponde."
        actions={
          <>
            <Button asChild className="rounded-full">
              <Link href={ROUTES.PROTECTED.APPOINTMENT_NEW}>
                <TbCalendarPlus className="h-4 w-4" />
                Solicitar cita
              </Link>
            </Button>
            <Button asChild variant="outline" className="rounded-full">
              <Link href={ROUTES.PROTECTED.CHAT}>
                <TbMessageCircle className="h-4 w-4" />
                Volver al chat
              </Link>
            </Button>
          </>
        }
      />
      <Card className="clinical-shell">
        <CardHeader>
          <div className="flex flex-wrap items-center gap-3">
            <TriagePill level={episode.triageLevel} />
            <span className="text-sm text-muted-foreground">Prioridad sugerida: {episode.suggestedPriority}</span>
          </div>
          <CardTitle className="text-2xl">{episode.recommendation}</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-2">
          <div className="rounded-3xl bg-slate-50 p-5 dark:bg-slate-900/50">
            <p className="text-sm font-medium text-muted-foreground">Resumen estructurado</p>
            <p className="mt-3 text-sm leading-7 text-foreground">{episode.summary}</p>
          </div>
          <div className="rounded-3xl border border-primary/10 bg-primary/10 p-5 dark:border-primary/20 dark:bg-primary/10">
            <p className="text-sm font-medium text-muted-foreground">Siguiente acción sugerida</p>
            <p className="mt-3 text-sm leading-7 text-foreground">
              El frontend queda preparado para enlazar esta recomendación con agenda y seguimiento clínico en cuanto el backend exponga ese flujo.
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
