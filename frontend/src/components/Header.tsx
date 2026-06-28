"use client";

import React from "react";
import Link from "next/link";
import { useAuth } from "@/hooks/useAuth";
import { usePathname } from "next/navigation";
import { TbBell, TbCalendarEvent, TbHelpCircle, TbMenu2 } from "react-icons/tb";
import { Button } from "@/components/ui/button";
import ThemeToggle from "@/components/theme-toggle";
import { ROUTES } from "@/routes/routePaths";

const resolvePageTitle = (pathname: string) => {
  if (pathname.startsWith("/doctor/clinical-history/")) return "Historial clínico";
  if (pathname.startsWith("/chat/sessions")) return "Historial de sesiones";
  if (pathname.startsWith("/doctor/patients/")) return "Ficha del paciente";
  if (pathname.startsWith("/doctor/validations/")) return "Detalle de validación";
  if (pathname.startsWith("/doctor/appointments/")) return "Detalle de cita";

  const titles: Record<string, string> = {
    "/dashboard": "Panel del paciente",
    "/chat": "Consulta y triaje",
    "/chat/sessions": "Historial de sesiones",
    "/triage-history": "Historial de triajes",
    "/appointments": "Mis citas",
    "/appointments/new": "Solicitar cita",
    "/profile": "Tu perfil",
    "/medical-data": "Ficha clínica",
    "/doctor/dashboard": "Dashboard médico",
    "/doctor/patients": "Pacientes",
    "/doctor/validations": "Validaciones",
    "/doctor/appointments": "Agenda médica",
  };

  return titles[pathname] || "Medicheck";
};

type HeaderProps = {
  onOpenMobileMenu?: () => void;
};

export default function Header({ onOpenMobileMenu }: HeaderProps) {
  const { user } = useAuth();
  const pathname = usePathname() || "";
  const pageTitle = resolvePageTitle(pathname);
  const name = user?.first_name || "Usuario";
  const isDoctorArea = pathname.startsWith("/doctor");
  const subtitle = isDoctorArea
    ? "Gestiona pacientes, validaciones y próximos pasos clínicos."
    : "Accede rápido a tus acciones importantes y continúa tu seguimiento.";

  return (
    <header className="border-b border-border/70 bg-card/95 px-4 py-3 backdrop-blur-md md:px-6">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div className="min-w-0">
          <div className="mb-2 flex items-center gap-2 md:hidden">
            <Button variant="outline" size="icon" aria-label="Abrir menú" onClick={onOpenMobileMenu}>
              <TbMenu2 className="h-4 w-4" />
            </Button>
          </div>

          <h1 className="text-lg md:text-2xl font-semibold tracking-tight">
            {pageTitle}
            <span className="text-primary"> · {name}</span>
          </h1>
          <p className="text-sm text-muted-foreground">{subtitle}</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {!isDoctorArea && (
            <Button asChild variant="outline" className="min-h-10 rounded-full">
              <Link href={ROUTES.PROTECTED.APPOINTMENT_NEW}>
                <TbCalendarEvent className="h-4 w-4" />
                Solicitar cita
              </Link>
            </Button>
          )}
        <Button variant="outline" size="icon" aria-label="Notificaciones">
          <TbBell className="h-4 w-4" />
        </Button>
        <Button variant="outline" size="icon" aria-label="Ayuda">
          <TbHelpCircle className="h-4 w-4" />
        </Button>
        <ThemeToggle />
        </div>
      </div>
    </header>
  );
}
