"use client";

import React, { useEffect } from "react";
import Link from "next/link";
import Image from "next/image";
import { useRouter } from "next/navigation";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { TbArrowRight, TbStethoscope, TbUser } from "react-icons/tb";
import { ROUTES } from "@/routes/routePaths";

export default function ProfileType() {
  const router = useRouter();
  const [selectedType, setSelectedType] = React.useState<string | null>(null);

  useEffect(() => {
    localStorage.removeItem("selectedProfileType");
  }, []);

  const handleSelect = (type: "patient" | "doctor") => {
    setSelectedType(type);
    localStorage.setItem("selectedProfileType", type);
  };

  const handleCreateAccount = () => {
    if (selectedType) {
      router.push(`${ROUTES.PUBLIC.REGISTER}?type=${selectedType}`);
    }
  };

  return (
    <div className="mx-auto max-w-4xl px-4 py-10">
      <section className="mx-auto max-w-2xl text-center">
        <div className="mx-auto flex h-28 w-28 items-center justify-center rounded-[1.8rem] border border-primary/15 bg-primary/10 shadow-sm">
          <Image src="/assets/img/logo.png" alt="Logo" width={84} height={84} className="rounded-xl" />
        </div>
        <p className="mt-6 text-xs font-semibold uppercase tracking-[0.18em] text-primary">Registro</p>
        <h1 className="mt-3 text-3xl font-semibold tracking-tight md:text-4xl">Elige cómo vas a usar MediCheck</h1>
        <p className="mt-3 text-sm leading-7 text-muted-foreground md:text-base">
          Selecciona el tipo de acceso para adaptar el registro y mantener una experiencia clara desde el primer paso.
        </p>
      </section>

      <div className="mt-10 grid gap-6 md:grid-cols-2">
        <Card
          className={`cursor-pointer rounded-[1.75rem] border p-6 transition-all ${
            selectedType === "patient"
              ? "border-primary/35 bg-primary/10 shadow-lg shadow-primary/10 ring-2 ring-primary/15"
              : "border-border/80 bg-card hover:border-primary/20 hover:shadow-sm"
          }`}
          onClick={() => handleSelect("patient")}
          role="button"
          tabIndex={0}
          onKeyDown={(event) => {
            if (event.key === "Enter" || event.key === " ") {
              event.preventDefault();
              handleSelect("patient");
            }
          }}
        >
          <div className="flex items-start justify-between gap-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-primary/12 text-primary">
              <TbUser className="h-6 w-6" />
            </div>
            <div
              className={`flex h-7 w-7 items-center justify-center rounded-full border ${
                selectedType === "patient" ? "border-primary bg-primary/15" : "border-border"
              }`}
              aria-hidden="true"
            >
              <span className={`h-3 w-3 rounded-full ${selectedType === "patient" ? "bg-primary" : "bg-transparent"}`} />
            </div>
          </div>
          <h2 className="mt-6 text-xl font-semibold tracking-tight">Soy paciente</h2>
          <p className="mt-2 text-sm leading-7 text-muted-foreground">
            Accede al chat de triaje, tu historial, tus datos clínicos y el seguimiento de citas desde una experiencia simple y guiada.
          </p>
        </Card>

        <Card
          className={`cursor-pointer rounded-[1.75rem] border p-6 transition-all ${
            selectedType === "doctor"
              ? "border-primary/35 bg-primary/10 shadow-lg shadow-primary/10 ring-2 ring-primary/15"
              : "border-border/80 bg-card hover:border-primary/20 hover:shadow-sm"
          }`}
          onClick={() => handleSelect("doctor")}
          role="button"
          tabIndex={0}
          onKeyDown={(event) => {
            if (event.key === "Enter" || event.key === " ") {
              event.preventDefault();
              handleSelect("doctor");
            }
          }}
        >
          <div className="flex items-start justify-between gap-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-primary/12 text-primary">
              <TbStethoscope className="h-6 w-6" />
            </div>
            <div
              className={`flex h-7 w-7 items-center justify-center rounded-full border ${
                selectedType === "doctor" ? "border-primary bg-primary/15" : "border-border"
              }`}
              aria-hidden="true"
            >
              <span className={`h-3 w-3 rounded-full ${selectedType === "doctor" ? "bg-primary" : "bg-transparent"}`} />
            </div>
          </div>
          <h2 className="mt-6 text-xl font-semibold tracking-tight">Soy profesional</h2>
          <p className="mt-2 text-sm leading-7 text-muted-foreground">
            Entra al panel clínico para revisar pacientes, validar entradas del chatbot y preparar la agenda asistencial.
          </p>
        </Card>
      </div>

      <div className="mt-8 text-center">
        <Button onClick={handleCreateAccount} disabled={!selectedType} className="min-h-12 w-full rounded-2xl md:w-80">
          Continuar con el registro
          <TbArrowRight className="h-4 w-4" />
        </Button>
        <p className="mt-5 text-sm text-muted-foreground">
          ¿Ya tienes una cuenta?
          <Link href={ROUTES.PUBLIC.LOGIN} className="ml-2 font-medium text-primary hover:underline">
            Inicia sesión aquí
          </Link>
        </p>
      </div>
    </div>
  );
}
