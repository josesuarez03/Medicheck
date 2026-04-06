"use client";

import Link from "next/link";
import { PageHero, TriagePill } from "@/components/experience/ui";
import { Card, CardContent } from "@/components/ui/card";
import { validationQueue } from "@/services/clinicMockData";

export default function DoctorValidationsPage() {
  return (
    <div className="space-y-6">
      <PageHero
        eyebrow="Validaciones"
        title="Revisa las entradas del chatbot con una cola pensada para acción rápida."
        description="La UI prioriza lectura clara, contexto breve y acceso inmediato al detalle de validación."
      />
      <div className="grid gap-4">
        {validationQueue.map((item) => (
          <Link key={item.id} href={`/doctor/validations/${item.id}`}>
            <Card className="clinical-shell transition hover:border-primary/25 hover:shadow-md">
              <CardContent className="space-y-3 p-6">
                <div className="flex flex-wrap items-center gap-3">
                  <TriagePill level={item.triageLevel} />
                  <span className="text-sm text-muted-foreground">{item.timestamp}</span>
                </div>
                <div>
                  <h3 className="text-xl font-semibold tracking-tight">{item.patientName}</h3>
                  <p className="mt-2 text-sm leading-7 text-muted-foreground">{item.summary}</p>
                </div>
                <p className="text-sm font-medium text-primary">{item.actionHint}</p>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
