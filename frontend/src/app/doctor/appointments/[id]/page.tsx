"use client";

import { useParams } from "next/navigation";
import { PageHero } from "@/components/experience/ui";
import { Card, CardContent } from "@/components/ui/card";
import { doctorAppointments } from "@/services/clinicMockData";

export default function DoctorAppointmentDetailPage() {
  const params = useParams<{ id: string }>();
  const appointment = doctorAppointments.find((item) => item.id === params.id) || doctorAppointments[0];

  return (
    <div className="space-y-6">
      <PageHero
        eyebrow="Detalle de cita"
        title="Revisa contexto, prioridad y modalidad antes de confirmar."
        description="La vista de detalle prioriza comprensión rápida y queda lista para sincronizarse después con disponibilidad real."
      />
      <Card className="clinical-shell">
        <CardContent className="space-y-3 p-6">
          <h3 className="text-2xl font-semibold tracking-tight">{appointment.patientName}</h3>
          <p className="text-sm text-muted-foreground">{appointment.dateLabel} · {appointment.timeLabel} · {appointment.mode}</p>
          <p className="text-sm leading-7 text-muted-foreground">{appointment.reason}</p>
          <div className="pill w-fit border border-primary/15 bg-primary/10 text-primary">{appointment.status}</div>
        </CardContent>
      </Card>
    </div>
  );
}
