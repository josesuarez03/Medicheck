"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { Search } from "lucide-react";
import { PageHero, TriagePill } from "@/components/experience/ui";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { doctorPatients } from "@/services/clinicMockData";

export default function DoctorPatientsPage() {
  const [query, setQuery] = useState("");
  const filtered = useMemo(
    () => doctorPatients.filter((patient) => patient.patientName.toLowerCase().includes(query.toLowerCase())),
    [query]
  );

  return (
    <div className="space-y-6">
      <PageHero
        eyebrow="Pacientes"
        title="Encuentra rápido el paciente correcto y entra con contexto."
        description="La tabla se diseña desde frontend con búsqueda accesible, lectura rápida y acciones claras para revisión clínica."
      />
      <Card className="clinical-shell">
        <CardContent className="p-6">
          <label className="flex min-h-12 items-center gap-3 rounded-2xl border border-input bg-background px-4">
            <Search className="h-4 w-4 text-muted-foreground" />
            <Input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              className="border-0 bg-transparent p-0 shadow-none focus-visible:ring-0"
              placeholder="Buscar por nombre de paciente"
              aria-label="Buscar paciente"
            />
          </label>
          <div className="mt-4 grid gap-3">
            {filtered.map((patient) => (
              <Link key={patient.id} href={`/doctor/patients/${patient.id}`} className="rounded-3xl border border-border/80 bg-background p-4 transition hover:border-primary/25 hover:shadow-sm">
                <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                  <div>
                    <p className="text-lg font-semibold">{patient.patientName}</p>
                    <p className="text-sm text-muted-foreground">{patient.ageLabel} · {patient.status} · {patient.lastActivity}</p>
                  </div>
                  <div className="flex flex-wrap items-center gap-3">
                    <TriagePill level={patient.triageLevel} />
                    <span className="text-sm text-muted-foreground">{patient.nextAction}</span>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
