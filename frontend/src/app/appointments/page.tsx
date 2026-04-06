"use client";

import Link from "next/link";
import { PageHero } from "@/components/experience/ui";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { patientAppointments } from "@/services/clinicMockData";
import { ROUTES } from "@/routes/routePaths";

export default function AppointmentsPage() {
  return (
    <div className="space-y-6">
      <PageHero
        eyebrow="Citas"
        title="Gestiona el siguiente paso sin salir del flujo clínico."
        description="La agenda del paciente se prepara desde frontend para conectar recomendaciones del chat con una cita clara, visible y fácil de entender."
        actions={
          <Button asChild className="rounded-full">
            <Link href={ROUTES.PROTECTED.APPOINTMENT_NEW}>Solicitar nueva cita</Link>
          </Button>
        }
      />
      <div className="grid gap-4">
        {patientAppointments.map((appointment) => (
          <Card key={appointment.id} className="clinical-shell">
            <CardContent className="grid gap-2 p-6 md:grid-cols-[1fr_auto] md:items-center">
              <div>
                <h3 className="text-lg font-semibold tracking-tight">{appointment.reason}</h3>
                <p className="mt-2 text-sm text-muted-foreground">
                  {appointment.dateLabel} · {appointment.timeLabel} · {appointment.mode} · {appointment.professional}
                </p>
              </div>
              <span className="pill border border-primary/15 bg-primary/10 text-primary">{appointment.status}</span>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
