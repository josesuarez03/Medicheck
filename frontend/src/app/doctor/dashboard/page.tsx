"use client";

import Link from "next/link";
import { TbArrowRight } from "react-icons/tb";
import { MetricCard, PageHero } from "@/components/experience/ui";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { doctorDashboardSummary, validationQueue } from "@/services/clinicMockData";
import { ROUTES } from "@/routes/routePaths";

export default function DoctorDashboardPage() {
  return (
    <div className="space-y-6">
      <PageHero
        eyebrow="Dashboard médico"
        title="Prioriza validación, pacientes y próximos pasos desde un mismo panel."
        description="El dashboard profesional concentra métricas operativas, accesos rápidos y revisión clínica. En esta fase usa contratos frontend preparados para el backend futuro."
        actions={
          <>
            <Button asChild className="rounded-full">
              <Link href={ROUTES.DOCTOR.PATIENTS}>Buscar paciente</Link>
            </Button>
            <Button asChild variant="outline" className="rounded-full">
              <Link href={ROUTES.DOCTOR.VALIDATIONS}>Ir a validaciones</Link>
            </Button>
          </>
        }
      />
      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard label="Pacientes asignados" value={doctorDashboardSummary.assignedPatients} supporting="Base activa del panel médico." />
        <MetricCard label="Pendientes de validación" value={doctorDashboardSummary.pendingValidations} supporting="Entradas listas para revisar." />
        <MetricCard label="Citas pendientes" value={doctorDashboardSummary.pendingAppointments} supporting="Próximos pasos por confirmar." />
        <MetricCard label="Alertas recientes" value={doctorDashboardSummary.recentAlerts} supporting="Casos que requieren atención prioritaria." />
      </section>
      <Card className="clinical-shell">
        <CardContent className="p-6">
          <div className="flex items-center justify-between gap-3">
            <div>
              <h3 className="text-xl font-semibold tracking-tight">Bandeja de validaciones</h3>
              <p className="text-sm text-muted-foreground">Entradas generadas por el chatbot listas para revisión clínica.</p>
            </div>
            <Button asChild variant="outline" className="rounded-full">
              <Link href={ROUTES.DOCTOR.VALIDATIONS}>
                Ver cola completa
                <TbArrowRight className="h-4 w-4" />
              </Link>
            </Button>
          </div>
          <div className="mt-5 grid gap-3">
            {validationQueue.slice(0, 3).map((item) => (
              <div key={item.id} className="rounded-3xl border border-border/80 bg-background p-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="font-semibold">{item.patientName}</p>
                    <p className="text-sm text-muted-foreground">{item.summary}</p>
                  </div>
                  <Button asChild variant="ghost" className="rounded-full">
                    <Link href={`/doctor/validations/${item.id}`}>Abrir</Link>
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
