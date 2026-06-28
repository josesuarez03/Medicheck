"use client";

import { useParams } from "next/navigation";
import { PageHero, TriagePill } from "@/components/experience/ui";
import { Card, CardContent } from "@/components/ui/card";
import { clinicalSummary, patientTimeline } from "@/services/clinicMockData";

export default function ClinicalHistoryPage() {
  const params = useParams<{ patientId: string }>();

  return (
    <div className="space-y-6">
      <PageHero
        eyebrow="Historial clínico estructurado"
        title="Expediente longitudinal diseñado para leer, validar y decidir."
        description={`Vista preparada para el paciente ${params.patientId}. Esta experiencia organiza antecedentes, contexto, validación y eventos recientes con una estructura clara.`}
      />
      <section className="grid gap-4 xl:grid-cols-[1fr_1fr]">
        <Card className="clinical-shell">
          <CardContent className="space-y-4 p-6">
            <div className="flex flex-wrap items-center gap-3">
              <TriagePill level={clinicalSummary.triageLevel} />
              <span className="text-sm text-muted-foreground">{clinicalSummary.validationStatus}</span>
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              <div className="rounded-3xl bg-background p-4">
                <p className="text-sm font-medium text-muted-foreground">Paciente</p>
                <p className="mt-2 font-semibold">{clinicalSummary.patientName}</p>
                <p className="text-sm text-muted-foreground">{clinicalSummary.ageLabel} · {clinicalSummary.occupation}</p>
              </div>
              <div className="rounded-3xl bg-background p-4">
                <p className="text-sm font-medium text-muted-foreground">Contexto clínico</p>
                <p className="mt-2 text-sm leading-7 text-foreground">{clinicalSummary.context}</p>
              </div>
              <div className="rounded-3xl bg-background p-4">
                <p className="text-sm font-medium text-muted-foreground">Alergias y medicación</p>
                <p className="mt-2 text-sm leading-7 text-foreground">{clinicalSummary.allergies}</p>
                <p className="mt-2 text-sm leading-7 text-foreground">{clinicalSummary.medications}</p>
              </div>
              <div className="rounded-3xl bg-background p-4">
                <p className="text-sm font-medium text-muted-foreground">Antecedentes</p>
                <p className="mt-2 text-sm leading-7 text-foreground">{clinicalSummary.medicalHistory}</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="clinical-shell">
          <CardContent className="space-y-4 p-6">
            <h3 className="text-xl font-semibold tracking-tight">Timeline clínico</h3>
            {patientTimeline.map((entry) => (
              <div key={entry.id} className="rounded-3xl border border-border/80 bg-background p-4">
                <p className="font-medium">{entry.title}</p>
                <p className="mt-2 text-sm leading-7 text-muted-foreground">{entry.description}</p>
                <p className="mt-2 text-xs uppercase tracking-[0.14em] text-primary">{entry.dateLabel}</p>
              </div>
            ))}
          </CardContent>
        </Card>
      </section>
    </div>
  );
}
