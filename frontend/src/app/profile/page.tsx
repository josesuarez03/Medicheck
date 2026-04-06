"use client";

import React, { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  TbEdit,
  TbUser,
  TbPhone,
  TbCalendar,
  TbMapPin,
  TbBriefcase,
  TbAlertTriangle,
  TbStethoscope,
  TbLicense,
  TbShieldCheck,
  TbLock,
  TbTrash,
} from "react-icons/tb";
import { ROUTES } from "@/routes/routePaths";

function InfoRow({ label, value, icon }: { label: string; value: string; icon: React.ReactNode }) {
  return (
    <div tabIndex={0} className="surface-card-interactive p-3 flex items-start gap-3 outline-none">
      <span className="mt-1 text-muted-foreground">{icon}</span>
      <div>
        <p className="text-[11px] uppercase tracking-[0.08em] text-muted-foreground">{label}</p>
        <p className="font-medium mt-1">{value}</p>
      </div>
    </div>
  );
}

export default function UserProfile() {
  const router = useRouter();
  const { user, loading: authLoading } = useAuth();

  useEffect(() => {
    if (!authLoading && !user) router.push(ROUTES.PUBLIC.LOGIN);
  }, [user, authLoading, router]);

  if (authLoading) {
    return <div className="flex justify-center items-center h-screen text-muted-foreground">Cargando perfil...</div>;
  }

  if (!user) {
    return (
      <div className="text-center p-8">
        <Alert>
          <AlertDescription>
            Debes iniciar sesión para ver tu perfil.
            <Button onClick={() => router.push(ROUTES.PUBLIC.LOGIN)} className="ml-4">
              Iniciar sesión
            </Button>
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  const formatDate = (dateString: string | undefined) => {
    if (!dateString) return "No especificado";
    return new Date(dateString).toLocaleDateString("es-ES", { day: "numeric", month: "long", year: "numeric" });
  };

  return (
    <div className="space-y-5 max-w-6xl mx-auto">
      <Card className="surface-card overflow-hidden">
        <CardHeader className="border-b bg-gradient-to-r from-primary via-primary to-primary/90 text-white">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div className="flex items-center gap-4">
              <div className="flex items-center justify-center w-14 h-14 rounded-full bg-white/20 text-white text-2xl">
                <TbUser />
              </div>
              <div>
                <CardTitle className="text-3xl font-semibold">
                  {user.first_name} {user.last_name}
                </CardTitle>
                <p className="text-white/80">{user.email}</p>
                <span className="pill mt-2 bg-white/20 text-white border border-white/30">
                  {user.tipo === "patient" ? "Paciente" : "Doctor"}
                </span>
              </div>
            </div>
            <Button
              onClick={() => router.push(ROUTES.PROTECTED.PROFILE_EDIT)}
              className="bg-white text-primary hover:bg-white/90"
            >
              <TbEdit className="mr-2 h-4 w-4" />
              Editar perfil
            </Button>
          </div>
        </CardHeader>

        <CardContent className="pt-6 grid grid-cols-1 lg:grid-cols-2 gap-6">
          <section className="space-y-3">
            <h3 className="section-title">Información personal</h3>
            <InfoRow label="Fecha de nacimiento" value={formatDate(user.fecha_nacimiento)} icon={<TbCalendar />} />
            <InfoRow
              label="Género"
              value={user.genero ? user.genero.charAt(0).toUpperCase() + user.genero.slice(1) : "No especificado"}
              icon={<TbUser />}
            />
            <InfoRow label="Teléfono" value={user.telefono || "No especificado"} icon={<TbPhone />} />
            <InfoRow label="Dirección" value={user.direccion || "No especificada"} icon={<TbMapPin />} />
          </section>

          <section className="space-y-3">
            <h3 className="section-title">{user.tipo === "patient" ? "Información médica" : "Información profesional"}</h3>
            {user.tipo === "patient" ? (
              <>
                <InfoRow label="Ocupación" value={user.patient?.ocupacion || "No especificada"} icon={<TbBriefcase />} />
                <InfoRow
                  label="Alergias"
                  value={user.patient?.allergies || "Ninguna alergia registrada"}
                  icon={<TbAlertTriangle />}
                />
                <InfoRow
                  label="Perfil clínico"
                  value={user.is_profile_completed ? "Completo y activo" : "Pendiente de completar"}
                  icon={<TbShieldCheck />}
                />
              </>
            ) : (
              <>
                <InfoRow
                  label="Especialidad"
                  value={user.doctor?.especialidad || "No especificada"}
                  icon={<TbStethoscope />}
                />
                <InfoRow
                  label="Número de licencia"
                  value={user.doctor?.numero_licencia || "No especificado"}
                  icon={<TbLicense />}
                />
              </>
            )}
          </section>
        </CardContent>
      </Card>

      <Card className="surface-card">
        <CardContent className="py-5 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <p className="text-sm text-muted-foreground">Miembro desde {formatDate(user.date_joined)}</p>
          <div className="flex flex-col sm:flex-row gap-3">
            <Button variant="outline" onClick={() => router.push(ROUTES.PROTECTED.PROFILE_CHANGE_PASSWORD)}>
              <TbLock className="h-4 w-4 mr-2" />
              Cambiar contraseña
            </Button>
            <Button variant="danger" onClick={() => router.push(ROUTES.PROTECTED.PROFILE_DELETE_ACCOUNT)}>
              <TbTrash className="h-4 w-4 mr-2" />
              Eliminar cuenta
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
