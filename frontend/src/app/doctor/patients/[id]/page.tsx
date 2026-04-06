"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { InfoPanel, PageHero, TriagePill } from "@/components/experience/ui";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { chatEpisodes, clinicalSummary, patientTimeline } from "@/services/clinicMockData";

export default function DoctorPatientDetailPage() {
  const params = useParams<{ id: string }>();

  return (
    <div className="space-y-6">
      <PageHero
        eyebrow="Ficha paciente"
        title={`Visión 360 preparada para revisión clínica de ${clinicalSummary.patientName}.`}
        description={`Identificador frontend: ${params.id}. Esta ficha unifica resumen clínico, episodios recientes, validación y siguiente acción sin depender todavía del backend nuevo.`}
        actions={
          <>
            <Button asChild className="rounded-full">
              <Link href={`/doctor/clinical-history/${params.id}`}>Ver historial estructurado</Link>
            </Button>
            <Button asChild variant="outline" className="rounded-full">
              <Link href="/doctor/appointments">Crear o revisar cita</Link>
            </Button>
          </>
        }
      />
      <section className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
        <Card className="clinical-shell">
          <CardContent className="space-y-4 p-6">
            <div className="flex flex-wrap items-center gap-3">
              <TriagePill level={clinicalSummary.triageLevel} />
              <span className="text-sm text-muted-foreground">{clinicalSummary.validationStatus}</span>
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              <InfoPanel title="Contexto actual" description={clinicalSummary.context} />
              <InfoPanel title="Última recomendación" description={clinicalSummary.lastRecommendation} />
              <InfoPanel title="Alergias" description={clinicalSummary.allergies} />
              <InfoPanel title="Medicaciones" description={clinicalSummary.medications} />
            </div>
          </CardContent>
        </Card>
        <Card className="clinical-shell">
          <CardContent className="space-y-4 p-6">
            <h3 className="text-xl font-semibold tracking-tight">Línea temporal reciente</h3>
            {patientTimeline.map((entry) => (
              <div key={entry.id} className="rounded-3xl border border-border/80 bg-background p-4">
                <p className="text-sm font-semibold">{entry.title}</p>
                <p className="mt-1 text-sm leading-7 text-muted-foreground">{entry.description}</p>
                <p className="mt-2 text-xs uppercase tracking-[0.14em] text-primary">{entry.dateLabel}</p>
              </div>
            ))}
          </CardContent>
        </Card>
      </section>
      <Card className="clinical-shell">
        <CardContent className="space-y-4 p-6">
          <h3 className="text-xl font-semibold tracking-tight">Episodios chatbot recientes</h3>
          {chatEpisodes.map((episode) => (
            <div key={episode.id} className="rounded-3xl border border-border/80 bg-background p-4">
              <div className="flex flex-wrap items-center gap-3">
                <TriagePill level={episode.triageLevel} />
                <span className="text-sm text-muted-foreground">{episode.dateLabel}</span>
              </div>
              <p className="mt-3 font-medium">{episode.recommendation}</p>
              <p className="mt-2 text-sm leading-7 text-muted-foreground">{episode.summary}</p>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
