"use client";

import { useState } from "react";
import Link from "next/link";
import { PageHero } from "@/components/experience/ui";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { ROUTES } from "@/routes/routePaths";

export default function NewAppointmentPage() {
  const [submitted, setSubmitted] = useState(false);

  return (
    <div className="space-y-6">
      <PageHero
        eyebrow="Nueva cita"
        title="Solicita una cita con un flujo claro y de baja fricción."
        description="Esta pantalla queda lista para integrarse después con backend. Por ahora prepara el recorrido, el lenguaje y los estados de la experiencia."
      />
      <Card className="clinical-shell">
        <CardHeader>
          <CardTitle>Resumen de solicitud</CardTitle>
        </CardHeader>
        <CardContent className="space-y-5">
          {submitted ? (
            <div className="rounded-3xl border border-emerald-200 bg-emerald-50 p-5 text-sm leading-7 text-emerald-900">
              Tu solicitud quedó preparada en frontend. Cuando llegue el backend de citas, este flujo enviará disponibilidad, prioridad y motivo de consulta.
            </div>
          ) : (
            <>
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="motivo">Motivo de consulta</Label>
                  <Input id="motivo" placeholder="Ej. Revisión de síntomas respiratorios" />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="preferencia">Preferencia</Label>
                  <Input id="preferencia" placeholder="Ej. Videoconsulta esta semana" />
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="detalle">Contexto adicional</Label>
                <Textarea id="detalle" rows={5} placeholder="Añade cualquier detalle que ayude al profesional a priorizar la cita." />
              </div>
              <div className="flex flex-wrap gap-3">
                <Button className="rounded-full" onClick={() => setSubmitted(true)}>Preparar solicitud</Button>
                <Button asChild variant="outline" className="rounded-full">
                  <Link href={ROUTES.PROTECTED.APPOINTMENTS}>Volver a citas</Link>
                </Button>
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
