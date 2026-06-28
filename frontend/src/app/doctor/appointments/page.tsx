"use client";

import Link from "next/link";
import { PageHero } from "@/components/experience/ui";
import { Card, CardContent } from "@/components/ui/card";
import { doctorAppointments } from "@/services/clinicMockData";

export default function DoctorAppointmentsPage() {
  return (
    <div className="space-y-6">
      <PageHero
        eyebrow="Agenda médica"
        title="Convierte la recomendación del flujo en una cita clara para el equipo."
        description="La agenda del profesional queda preparada para backend futuro, con énfasis en prioridad, motivo y rapidez de lectura."
      />
      <div className="grid gap-4">
        {doctorAppointments.map((appointment) => (
          <Link key={appointment.id} href={`/doctor/appointments/${appointment.id}`}>
            <Card className="clinical-shell transition hover:border-primary/25 hover:shadow-sm">
              <CardContent className="grid gap-2 p-6 md:grid-cols-[1fr_auto] md:items-center">
                <div>
                  <h3 className="text-lg font-semibold tracking-tight">{appointment.patientName}</h3>
                  <p className="mt-2 text-sm leading-7 text-muted-foreground">
                    {appointment.dateLabel} · {appointment.timeLabel} · {appointment.mode}
                  </p>
                  <p className="text-sm text-muted-foreground">{appointment.reason}</p>
                </div>
                <span className="pill border border-primary/15 bg-primary/10 text-primary">{appointment.status}</span>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
