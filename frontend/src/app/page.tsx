import Link from "next/link";
import Image from "next/image";
import { TbArrowRight, TbCalendarEvent, TbChecklist, TbLayoutDashboard, TbMessages, TbShieldCheck, TbStethoscope } from "react-icons/tb";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { ROUTES } from "@/routes/routePaths";

const valueProps = [
  {
    title: "Recoge mejor la primera conversación",
    description: "MediCheck convierte la interacción inicial del paciente en contexto clínico más claro para el equipo sanitario.",
    icon: TbMessages,
  },
  {
    title: "Ordena la continuidad asistencial",
    description: "El triaje, el historial y la próxima acción quedan conectados en una sola experiencia de producto.",
    icon: TbChecklist,
  },
  {
    title: "Da visibilidad al profesional",
    description: "La vista médica prioriza validación, revisión de paciente y preparación del siguiente paso, incluida la cita.",
    icon: TbLayoutDashboard,
  },
];

const useCases = [
  "Clínicas privadas que quieren filtrar mejor la demanda antes de la consulta.",
  "Ambulatorios y centros de salud que necesitan una recogida inicial más ordenada.",
  "Equipos de salud laboral que requieren episodios, contexto y seguimiento longitudinal.",
  "Aseguradoras y redes médicas interesadas en encaminar al paciente hacia la siguiente acción adecuada.",
];

export default function HomePage() {
  return (
    <div className="relative isolate overflow-hidden">
      <div className="absolute inset-0 -z-10 bg-[radial-gradient(circle_at_top_left,rgba(37,131,204,0.28),transparent_26%),radial-gradient(circle_at_top_right,rgba(83,196,245,0.22),transparent_20%),linear-gradient(180deg,#f4f8fc_0%,#ffffff_44%,#eef5fb_100%)]" />
      <header className="page-container pb-0">
        <nav className="flex items-center justify-between rounded-full border border-white/80 bg-white/85 px-4 py-3 shadow-sm backdrop-blur md:px-6">
          <div className="flex items-center gap-3">
            <div className="relative h-11 w-11 overflow-hidden rounded-2xl bg-primary/10">
              <Image src="/assets/img/icon192.png" alt="Medicheck" fill className="object-cover" sizes="44px" />
            </div>
            <div>
              <p className="text-sm font-semibold tracking-tight text-foreground">Medicheck</p>
              <p className="text-xs text-muted-foreground">Frontend refresh · producto B2B sanitario</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button asChild variant="ghost" className="rounded-full">
              <Link href={ROUTES.PUBLIC.LOGIN}>Acceder</Link>
            </Button>
            <Button asChild className="rounded-full">
              <Link href={ROUTES.PUBLIC.LOGIN}>
                Solicitar demo
                <TbArrowRight className="h-4 w-4" />
              </Link>
            </Button>
          </div>
        </nav>
      </header>

      <main className="page-container space-y-16 py-10 md:py-16">
        <section className="grid gap-8 lg:grid-cols-[1.2fr_0.8fr] lg:items-center">
          <div className="space-y-6">
            <span className="inline-flex min-h-10 items-center rounded-full border border-primary/15 bg-primary/10 px-4 text-sm font-medium text-primary">
              Triaje conversacional, seguimiento clínico y siguiente acción en una sola experiencia
            </span>
            <div className="space-y-4">
              <h1 className="max-w-3xl text-balance text-4xl font-semibold tracking-tight text-slate-950 md:text-6xl">
                Ayuda a tu equipo a decidir más rápido qué hacer con cada paciente desde el primer contacto.
              </h1>
              <p className="max-w-2xl text-lg leading-8 text-slate-700">
                MediCheck combina chat de triaje, contexto clínico, historial de episodios y validación profesional para convertir conversaciones dispersas en información más útil para la atención.
              </p>
            </div>
            <div className="flex flex-wrap gap-3">
              <Button asChild size="lg" className="rounded-full">
                <Link href={ROUTES.PUBLIC.LOGIN}>
                  Ver la plataforma
                  <TbArrowRight className="h-4 w-4" />
                </Link>
              </Button>
              <Button asChild size="lg" variant="outline" className="rounded-full">
                <Link href="#como-funciona">Cómo funciona</Link>
              </Button>
            </div>
            <div className="grid gap-3 sm:grid-cols-3">
              {["Chat en tiempo real", "Clasificación inicial", "Historial y validación"].map((item) => (
                <div key={item} className="rounded-2xl border border-white/80 bg-white/75 px-4 py-4 text-sm font-medium text-slate-700 shadow-sm backdrop-blur">
                  {item}
                </div>
              ))}
            </div>
          </div>
          <Card className="overflow-hidden rounded-[2rem] border-white/80 bg-slate-950 text-white shadow-2xl shadow-primary/20">
            <CardContent className="space-y-5 p-6 md:p-8">
              <div className="rounded-3xl border border-white/10 bg-white/5 p-5">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-primary/80">Lo que ya existe en el TFG</p>
                <ul className="mt-4 space-y-3 text-sm text-slate-200">
                  <li className="flex gap-3"><TbMessages className="mt-0.5 h-5 w-5 text-primary/90" />Chat de triaje en tiempo real.</li>
                  <li className="flex gap-3"><TbShieldCheck className="mt-0.5 h-5 w-5 text-emerald-300" />Clasificación inicial y recomendaciones.</li>
                  <li className="flex gap-3"><TbStethoscope className="mt-0.5 h-5 w-5 text-cyan-300" />Perfiles diferenciados de paciente y doctor.</li>
                  <li className="flex gap-3"><TbCalendarEvent className="mt-0.5 h-5 w-5 text-amber-300" />Base preparada para validar, seguir y agendar el siguiente paso.</li>
                </ul>
              </div>
              <div className="rounded-3xl bg-gradient-to-br from-primary to-primary/55 p-[1px]">
                <div className="rounded-[1.45rem] bg-slate-950 p-5">
                  <p className="text-sm text-primary/80">
                    Diseñado para clínicas, ambulatorios, centros de salud y equipos que necesitan una experiencia más clara entre el primer contacto y la intervención profesional.
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </section>

        <section className="grid gap-4 md:grid-cols-3">
          {valueProps.map(({ title, description, icon: Icon }) => (
            <Card key={title} className="surface-card-interactive rounded-[1.75rem] border-white/70 bg-white/80">
              <CardContent className="p-6">
                <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-primary/10 text-primary">
                  <Icon className="h-6 w-6" />
                </div>
                <h2 className="mt-5 text-xl font-semibold tracking-tight text-slate-950">{title}</h2>
                <p className="mt-3 text-sm leading-7 text-slate-700">{description}</p>
              </CardContent>
            </Card>
          ))}
        </section>

        <section id="como-funciona" className="grid gap-8 lg:grid-cols-[0.9fr_1.1fr]">
          <div className="space-y-4">
            <p className="text-sm font-semibold uppercase tracking-[0.18em] text-primary">Cómo encaja en el flujo</p>
            <h2 className="text-3xl font-semibold tracking-tight text-slate-950 md:text-4xl">
              Una experiencia pensada para pasar de conversación a acción.
            </h2>
            <p className="text-base leading-8 text-slate-700">
              El paciente inicia una consulta o triaje, el sistema resume y clasifica, el profesional revisa la información y el siguiente paso puede convertirse en seguimiento o cita.
            </p>
          </div>
          <div className="grid gap-4">
            {[
              "Paciente inicia conversación y aporta síntomas o dudas.",
              "MediCheck organiza contexto, clasificación inicial e historial reciente.",
              "El profesional revisa, valida y decide la acción adecuada.",
              "La plataforma prepara el terreno para agendar una cita o continuar seguimiento.",
            ].map((step, index) => (
              <div key={step} className="flex gap-4 rounded-3xl border border-border/70 bg-white/80 p-5 shadow-sm">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground">
                  {index + 1}
                </div>
                <p className="text-sm leading-7 text-slate-700">{step}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="rounded-[2rem] border border-border/80 bg-white/80 p-6 shadow-sm md:p-8">
          <p className="text-sm font-semibold uppercase tracking-[0.18em] text-primary">Casos de uso</p>
          <div className="mt-4 grid gap-4 md:grid-cols-2">
            {useCases.map((item) => (
              <div key={item} className="rounded-2xl bg-slate-50 p-5 text-sm leading-7 text-slate-700">
                {item}
              </div>
            ))}
          </div>
        </section>

        <section className="rounded-[2rem] bg-slate-950 px-6 py-8 text-white shadow-xl md:px-8">
          <div className="flex flex-col gap-5 md:flex-row md:items-center md:justify-between">
            <div>
              <p className="text-sm font-semibold uppercase tracking-[0.18em] text-primary/80">Listo para evolucionar</p>
              <h2 className="mt-2 text-3xl font-semibold tracking-tight">La base ya conecta chat, contexto clínico y flujo profesional.</h2>
              <p className="mt-3 max-w-2xl text-sm leading-7 text-slate-300">
                Esta nueva etapa del frontend prepara la experiencia completa para paciente y doctor, sin depender todavía de nuevos endpoints backend.
              </p>
            </div>
            <Button asChild size="lg" className="rounded-full bg-white text-slate-950 hover:bg-slate-100">
              <Link href={ROUTES.PUBLIC.LOGIN}>Entrar al producto</Link>
            </Button>
          </div>
        </section>
      </main>
    </div>
  );
}
