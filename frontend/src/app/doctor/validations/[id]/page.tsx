"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import { PageHero, TriagePill } from "@/components/experience/ui";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { validationQueue } from "@/services/clinicMockData";

export default function DoctorValidationDetailPage() {
  const params = useParams<{ id: string }>();
  const item = validationQueue.find((entry) => entry.id === params.id) || validationQueue[0];
  const [status, setStatus] = useState("Pendiente");

  return (
    <div className="space-y-6">
      <PageHero
        eyebrow="Detalle de validación"
        title="Valida, ajusta o marca seguimiento desde una misma pantalla."
        description="Esta vista deja preparado el comportamiento médico para cuando existan endpoints específicos de aprobación y revisión."
      />
      <Card className="clinical-shell">
        <CardContent className="space-y-4 p-6">
          <div className="flex flex-wrap items-center gap-3">
            <TriagePill level={item.triageLevel} />
            <span className="text-sm text-muted-foreground">{item.timestamp}</span>
            <span className="pill bg-slate-100 text-slate-800">{status}</span>
          </div>
          <div>
            <h3 className="text-2xl font-semibold tracking-tight">{item.patientName}</h3>
            <p className="mt-3 text-sm leading-7 text-muted-foreground">{item.summary}</p>
          </div>
          <div className="rounded-3xl border border-primary/10 bg-primary/10 p-5 text-sm leading-7 text-foreground dark:border-primary/20 dark:bg-primary/10">
            {item.actionHint}
          </div>
          <div className="flex flex-wrap gap-3">
            <Button className="rounded-full" onClick={() => setStatus("Aprobada en frontend")}>Aprobar</Button>
            <Button variant="outline" className="rounded-full" onClick={() => setStatus("Pendiente de edición")}>Editar y aprobar</Button>
            <Button variant="secondary" className="rounded-full" onClick={() => setStatus("Seguimiento sugerido")}>Marcar seguimiento</Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
