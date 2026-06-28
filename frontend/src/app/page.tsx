import Link from "next/link";
import Image from "next/image";
import {
  TbArrowRight,
  TbCalendarEvent,
  TbChecklist,
  TbLayoutDashboard,
  TbMessages,
  TbShieldCheck,
  TbStethoscope,
  TbBrain,
  TbHeartRateMonitor,
  TbUserCheck,
  TbClockHour4,
  TbBuildingHospital,
  TbCertificate,
  TbChevronRight,
} from "react-icons/tb";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ROUTES } from "@/routes/routePaths";

// ─── Data ───────────────────────────────────────────────────────────────────

const valueProps = [
  {
    title: "Primera conversación que no se pierde",
    description:
      "Hipo convierte lo que el paciente cuenta en contexto clínico estructurado. Sin resúmenes a mano, sin pérdidas entre turnos.",
    icon: TbMessages,
    color: "text-primary",
    bg: "bg-primary/10",
  },
  {
    title: "Triaje, historial y siguiente paso, juntos",
    description:
      "El flujo completo —clasificación inicial, historial de episodios y acción recomendada— en una sola experiencia coherente.",
    icon: TbChecklist,
    color: "text-emerald-600",
    bg: "bg-emerald-50",
  },
  {
    title: "Vista clínica preparada para actuar",
    description:
      "El profesional entra con el contexto listo: síntomas, prioridad y siguiente paso sugerido. Menos lectura, más decisión.",
    icon: TbLayoutDashboard,
    color: "text-cyan-600",
    bg: "bg-cyan-50",
  },
];

const useCases = [
  {
    icon: TbBuildingHospital,
    title: "Clínicas y consultas privadas",
    desc: "Filtra y organiza la demanda antes de que llegue al médico.",
  },
  {
    icon: TbUserCheck,
    title: "Centros de salud y ambulatorios",
    desc: "Recogida inicial más ordenada, menos carga administrativa.",
  },
  {
    icon: TbHeartRateMonitor,
    title: "Equipos de salud laboral",
    desc: "Episodios, contexto y seguimiento longitudinal para entornos de empresa.",
  },
  {
    icon: TbCertificate,
    title: "Aseguradoras y redes médicas",
    desc: "Encamina al paciente hacia la siguiente acción adecuada desde el primer contacto.",
  },
];

const steps = [
  {
    label: "01",
    title: "El paciente describe sus síntomas",
    desc: "Hipo recoge la información en lenguaje natural, sin formularios complejos ni esperas.",
  },
  {
    label: "02",
    title: "El sistema clasifica y estructura",
    desc: "Amazon Comprehend Medical y el protocolo SET procesan la conversación en contexto clínico útil.",
  },
  {
    label: "03",
    title: "El profesional revisa y decide",
    desc: "La vista médica presenta prioridad, historial y siguiente acción sugerida, lista para validar.",
  },
  {
    label: "04",
    title: "La atención continúa conectada",
    desc: "Seguimiento, cita o derivación: la plataforma prepara el terreno para que no haya huecos.",
  },
];

const trustHighlights = [
  {
    title: "Hipo convierte conversación en contexto útil",
    description:
      "Hipo recoge síntomas, ordena la conversación y la transforma en contexto clínico estructurado que luego puede revisarse y reutilizarse.",
    eyebrow: "Lo que aporta Hipo",
  },
  {
    title: "Arquitectura lista para operar",
    description:
      "Tiempo real, perfiles diferenciados y base para flujo paciente-profesional sin rehacer la experiencia cuando crezca el producto.",
    eyebrow: "Cómo está preparada",
  },
  {
    title: "Privacidad, trazabilidad y marco europeo",
    description:
      "Diseñada para entornos sanitarios donde importa quién accede, qué se registra y cómo se protege la información clínica y el uso de IA.",
    eyebrow: "Lo que transmite confianza",
  },
];

// ─── Component ───────────────────────────────────────────────────────────────

export default function HomePage() {
  return (
    <div className="relative isolate overflow-hidden bg-[#f4f8fc]">
      {/* ── Background gradient mesh ── */}
      <div
        aria-hidden
        className="pointer-events-none fixed inset-0 -z-10"
        style={{
          background:
            "radial-gradient(ellipse 80% 60% at 10% 0%, rgba(37,131,204,0.13) 0%, transparent 55%), radial-gradient(ellipse 60% 40% at 90% 5%, rgba(83,196,245,0.12) 0%, transparent 50%), linear-gradient(180deg, #f4f8fc 0%, #ffffff 55%, #eef5fb 100%)",
        }}
      />

      {/* ══════════════════════════════════════════
          NAVBAR
      ══════════════════════════════════════════ */}
      <header className="page-container pb-0 sticky top-0 z-50">
        <nav className="flex items-center justify-between rounded-full border border-white/90 bg-white/90 px-4 py-3 shadow-sm backdrop-blur-md md:px-6">
          <div className="flex items-center gap-3">
            <div className="relative h-10 w-10 overflow-hidden rounded-2xl bg-primary/10 ring-1 ring-primary/20">
              <Image
                src="/assets/img/icon192.png"
                alt="Medicheck"
                fill
                className="object-cover"
                sizes="40px"
              />
            </div>
            <div>
              <p className="text-sm font-semibold tracking-tight text-foreground">
                Medicheck
              </p>
              <p className="text-[11px] text-muted-foreground">
                Triaje inteligente · B2B sanitario
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button asChild variant="ghost" size="sm" className="rounded-full hidden sm:flex">
              <Link href={ROUTES.PUBLIC.LOGIN}>Acceder</Link>
            </Button>
            <Button asChild size="sm" className="rounded-full gap-1.5">
              <Link href={ROUTES.PUBLIC.LOGIN}>
                Solicitar demo
                <TbArrowRight className="h-3.5 w-3.5" />
              </Link>
            </Button>
          </div>
        </nav>
      </header>

      <main className="page-container space-y-20 py-12 md:py-20">

        {/* ══════════════════════════════════════════
            HERO
        ══════════════════════════════════════════ */}
        <section className="grid gap-10 lg:grid-cols-[1.15fr_0.85fr] lg:items-center">
          {/* Left */}
          <div className="space-y-7">
            <Badge
              variant="outline"
              className="rounded-full border-primary/20 bg-primary/8 px-4 py-1.5 text-xs font-semibold text-primary tracking-wide"
            >
              Triaje conversacional, seguimiento clínico y siguiente acción en una sola experiencia
            </Badge>

            <div className="space-y-4">
              <h1 className="max-w-2xl text-balance text-[2.6rem] font-bold leading-[1.15] tracking-tight text-slate-950 md:text-6xl">
                Del primer síntoma a la{" "}
                <span className="text-primary">acción clínica</span>, sin
                fricciones.
              </h1>
              <p className="max-w-xl text-lg leading-relaxed text-slate-600">
                Medicheck combina un chatbot de triaje, contexto clínico
                estructurado e historial de episodios para que tu equipo tome
                mejores decisiones desde el primer contacto con el paciente.
              </p>
            </div>

            <div className="flex flex-wrap gap-3">
              <Button asChild size="lg" className="rounded-full gap-2 px-7">
                <Link href={ROUTES.PUBLIC.LOGIN}>
                  Ver la plataforma
                  <TbArrowRight className="h-4 w-4" />
                </Link>
              </Button>
              <Button
                asChild
                size="lg"
                variant="outline"
                className="rounded-full px-7"
              >
                <Link href="#como-funciona">Cómo funciona</Link>
              </Button>
            </div>

            {/* Trust chips */}
            <div className="flex flex-wrap gap-2 pt-1">
              {["Chat en tiempo real", "Clasificación SET", "Historial clínico", "Validación médica"].map(
                (item) => (
                  <span
                    key={item}
                    className="inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-white px-3.5 py-1.5 text-xs font-medium text-slate-600 shadow-sm"
                  >
                    <span className="h-1.5 w-1.5 rounded-full bg-primary" />
                    {item}
                  </span>
                )
              )}
            </div>
          </div>

          {/* Right — product card */}
          <div className="relative">
            {/* Decorative glow */}
            <div
              aria-hidden
              className="absolute -inset-4 rounded-[2.5rem] bg-primary/10 blur-2xl"
            />

            {/*
              📸 IMAGEN HERO — Prompt para NanoBanana:
              "A clean, modern medical interface mockup on a laptop screen showing a chat
              conversation between a patient and an AI medical assistant named Hipo.
              The UI has a white and blue color scheme (#2583CC), with a sidebar navigation,
              a chat bubble interface, and a triage classification panel on the right.
              Professional, minimal, healthcare SaaS aesthetic. Soft studio lighting,
              slightly angled 3/4 perspective. No people visible, just the screen."
            */}
            <Card className="relative overflow-hidden rounded-[2rem] border-white/80 bg-slate-950 text-white shadow-2xl shadow-primary/25">
              {/* Decorative top bar */}
              <div className="flex items-center gap-1.5 border-b border-white/10 px-5 py-3">
                <span className="h-2.5 w-2.5 rounded-full bg-red-400/80" />
                <span className="h-2.5 w-2.5 rounded-full bg-amber-400/80" />
                <span className="h-2.5 w-2.5 rounded-full bg-emerald-400/80" />
                <span className="ml-3 text-xs text-white/40 font-mono">
                  medicheck · hipo
                </span>
              </div>

              <CardContent className="space-y-5 p-6 md:p-7">
                {/* Chat preview simulation */}
                <div className="space-y-3">
                  <div className="flex items-start gap-2.5">
                    <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-primary text-white text-[10px] font-bold">
                      H
                    </div>
                    <div className="rounded-2xl rounded-tl-sm bg-white/10 px-3.5 py-2.5 text-xs leading-relaxed text-slate-200 max-w-[85%]">
                      Hola, soy Hipo. ¿Qué síntomas tienes hoy?
                    </div>
                  </div>
                  <div className="flex items-start gap-2.5 justify-end">
                    <div className="rounded-2xl rounded-tr-sm bg-primary/70 px-3.5 py-2.5 text-xs leading-relaxed text-white max-w-[80%]">
                      Tengo fiebre desde ayer y me duele mucho la garganta.
                    </div>
                    <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-slate-600 text-white text-[10px] font-bold">
                      P
                    </div>
                  </div>
                  <div className="flex items-start gap-2.5">
                    <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-primary text-white text-[10px] font-bold">
                      H
                    </div>
                    <div className="rounded-2xl rounded-tl-sm bg-white/10 px-3.5 py-2.5 text-xs leading-relaxed text-slate-200 max-w-[85%]">
                      Entendido. ¿Cuánto mide la fiebre y tienes dificultad para tragar?
                    </div>
                  </div>
                </div>

                {/* Triage result */}
                <div className="rounded-2xl bg-emerald-500/15 border border-emerald-400/25 p-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-[10px] font-bold uppercase tracking-widest text-emerald-300">
                      Clasificación SET
                    </span>
                    <span className="rounded-full bg-amber-400/20 px-2 py-0.5 text-[10px] font-semibold text-amber-300">
                      Nivel 3 · Urgente
                    </span>
                  </div>
                  <p className="text-xs text-slate-300 leading-relaxed">
                    Síntomas compatibles con faringoamigdalitis. Recomendado: revisión en las próximas 2h.
                  </p>
                </div>

                {/* Feature list */}
                <div className="rounded-2xl border border-white/10 bg-white/5 p-4 space-y-2.5">
                  <p className="text-[10px] font-bold uppercase tracking-widest text-primary/70">
                    Lo que ya tienes disponible
                  </p>
                  <ul className="space-y-2 text-xs text-slate-300">
                    <li className="flex gap-2.5 items-start">
                      <TbMessages className="mt-0.5 h-4 w-4 text-primary/80 shrink-0" />
                      Chat de triaje en tiempo real con Hipo
                    </li>
                    <li className="flex gap-2.5 items-start">
                      <TbShieldCheck className="mt-0.5 h-4 w-4 text-emerald-400 shrink-0" />
                      Clasificación basada en protocolo SET
                    </li>
                    <li className="flex gap-2.5 items-start">
                      <TbStethoscope className="mt-0.5 h-4 w-4 text-cyan-400 shrink-0" />
                      Perfiles diferenciados paciente · médico
                    </li>
                    <li className="flex gap-2.5 items-start">
                      <TbCalendarEvent className="mt-0.5 h-4 w-4 text-amber-400 shrink-0" />
                      Base para validación, seguimiento y cita
                    </li>
                  </ul>
                </div>
              </CardContent>
            </Card>
          </div>
        </section>

        {/* ══════════════════════════════════════════
            VALUE PROPS
        ══════════════════════════════════════════ */}
        <section className="space-y-8">
          <div className="text-center space-y-2 max-w-2xl mx-auto">
            <p className="text-xs font-bold uppercase tracking-widest text-primary">
              Por qué MediCheck
            </p>
            <h2 className="text-3xl font-bold tracking-tight text-slate-950 md:text-4xl">
              Menos fricción. Más contexto. Mejor atención.
            </h2>
          </div>
          <div className="grid gap-5 md:grid-cols-3">
            {valueProps.map(({ title, description, icon: Icon, color, bg }) => (
              <Card
                key={title}
                className="surface-card-interactive rounded-[1.75rem] border-white/80 bg-white/85 group"
              >
                <CardContent className="p-6 space-y-4">
                  <div
                    className={`flex h-12 w-12 items-center justify-center rounded-2xl ${bg} ${color} transition-transform duration-300 group-hover:scale-110`}
                  >
                    <Icon className="h-6 w-6" />
                  </div>
                  <div className="space-y-2">
                    <h3 className="text-lg font-semibold tracking-tight text-slate-950 leading-snug">
                      {title}
                    </h3>
                    <p className="text-sm leading-7 text-slate-600">
                      {description}
                    </p>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </section>

        {/* ══════════════════════════════════════════
            HOW IT WORKS
        ══════════════════════════════════════════ */}
        <section
          id="como-funciona"
          className="grid gap-10 lg:grid-cols-[0.9fr_1.1fr] lg:items-start"
        >
          {/* Left copy */}
          <div className="space-y-5 lg:sticky lg:top-28">
            <p className="text-xs font-bold uppercase tracking-widest text-primary">
              Cómo funciona
            </p>
            <h2 className="text-3xl font-bold tracking-tight text-slate-950 md:text-4xl leading-snug">
              De conversación a acción clínica en cuatro pasos.
            </h2>
            <p className="text-base leading-8 text-slate-600">
              El paciente habla, el sistema estructura, el profesional decide.
              Un flujo limpio que elimina el ruido entre el primer contacto y
              la intervención adecuada.
            </p>

            {/*
              📸 IMAGEN HOW IT WORKS — Prompt para NanoBanana:
              "A minimalist flat illustration of a healthcare workflow diagram.
              Four connected steps shown as clean cards from left to right: 
              1) a speech bubble with a patient icon, 2) a brain/AI processing icon,
              3) a stethoscope doctor icon, 4) a calendar check icon.
              Color palette: white cards, #2583CC blue accents, soft light gray background.
              No text in the illustration. Isometric or flat style, very clean and modern."
            */}
            <div className="rounded-2xl overflow-hidden border border-slate-100 bg-gradient-to-br from-primary/5 to-cyan-50 h-48 flex items-center justify-center">
              <div className="text-center space-y-2">
                <TbBrain className="h-10 w-10 text-primary/40 mx-auto" />
                <p className="text-xs text-slate-400 font-medium">
                  [Ilustración del flujo — NanoBanana]
                </p>
              </div>
            </div>
          </div>

          {/* Steps */}
          <div className="space-y-4">
            {steps.map((step, i) => (
              <div
                key={step.label}
                className="flex gap-5 rounded-3xl border border-slate-100 bg-white/85 p-5 shadow-sm hover:shadow-md hover:border-primary/20 transition-all duration-200 group"
              >
                <div className="flex h-12 w-12 shrink-0 flex-col items-center justify-center rounded-2xl bg-primary text-white font-bold text-sm tabular-nums group-hover:scale-105 transition-transform duration-200">
                  {step.label}
                </div>
                <div className="space-y-1">
                  <p className="font-semibold text-slate-950">{step.title}</p>
                  <p className="text-sm leading-7 text-slate-600">{step.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* ══════════════════════════════════════════
            PATIENT / DOCTOR SPLIT
        ══════════════════════════════════════════ */}
        <section className="grid gap-5 md:grid-cols-2">
          {/* Patient */}
          <div className="rounded-[2rem] border border-slate-100 bg-white/85 p-7 shadow-sm space-y-5">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-primary/10 text-primary">
              <TbMessages className="h-6 w-6" />
            </div>
            <div className="space-y-2">
              <p className="text-xs font-bold uppercase tracking-widest text-primary">
                Para el paciente
              </p>
              <h3 className="text-xl font-bold tracking-tight text-slate-950">
                Habla con Hipo cuando lo necesites.
              </h3>
              <p className="text-sm leading-7 text-slate-600">
                Sin formularios largos, sin esperar al médico de guardia. Hipo
                recoge los síntomas, hace las preguntas necesarias y da una
                orientación inicial clara —las 24 horas, los 7 días de la semana.
              </p>
            </div>

            {/*
              📸 IMAGEN PACIENTE — Prompt para NanoBanana:
              "A friendly, clean illustration of a person using a smartphone to chat with
              a medical AI assistant. The phone screen shows a blue chat interface.
              The person looks calm and reassured. Flat or soft 3D style.
              Color palette: light blue (#2583CC), white, soft gray tones.
              Healthcare context, no text in the illustration."
            */}
            <div className="relative h-44 overflow-hidden rounded-2xl border border-slate-100 bg-gradient-to-br from-primary/5 to-sky-50">
              <Image
                src="/assets/img/patient.png"
                alt="Paciente usando Medicheck desde el móvil"
                fill
                className="object-contain p-4"
                sizes="(max-width: 768px) 100vw, 50vw"
              />
            </div>
          </div>

          {/* Doctor */}
          <div className="rounded-[2rem] border border-slate-100 bg-slate-950 p-7 shadow-xl space-y-5 text-white">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-primary/20 text-primary">
              <TbStethoscope className="h-6 w-6" />
            </div>
            <div className="space-y-2">
              <p className="text-xs font-bold uppercase tracking-widest text-primary/80">
                Para el profesional
              </p>
              <h3 className="text-xl font-bold tracking-tight">
                El contexto listo antes de entrar a la sala.
              </h3>
              <p className="text-sm leading-7 text-slate-400">
                La vista médica muestra síntomas organizados, nivel de prioridad
                SET y el historial del paciente. Valida, ajusta y decide en
                segundos —sin tener que reconstruir la historia desde cero.
              </p>
            </div>

            {/*
              📸 IMAGEN MÉDICO — Prompt para NanoBanana:
              "A clean dark-themed medical dashboard UI mockup displayed on a tablet.
              The screen shows a patient summary panel with a priority badge (orange, 'Urgente'),
              a list of symptoms, and a doctor action area. Professional, data-dense but
              readable layout. Color palette: dark navy background, #2583CC blue accents,
              white text. No real patient data visible. Flat or soft 3D style, no people."
            */}
            <div className="rounded-2xl bg-white/5 border border-white/10 h-40 flex items-center justify-center">
              <p className="text-xs text-slate-500 font-medium">
                [Ilustración dashboard médico — NanoBanana]
              </p>
            </div>
          </div>
        </section>

        {/* ══════════════════════════════════════════
            USE CASES
        ══════════════════════════════════════════ */}
        <section className="space-y-8">
          <div className="text-center space-y-2">
            <p className="text-xs font-bold uppercase tracking-widest text-primary">
              Casos de uso
            </p>
            <h2 className="text-3xl font-bold tracking-tight text-slate-950 md:text-4xl">
              Pensado para equipos que atienden personas.
            </h2>
          </div>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            {useCases.map(({ icon: Icon, title, desc }) => (
              <div
                key={title}
                className="rounded-[1.5rem] border border-slate-100 bg-white/85 p-5 shadow-sm hover:shadow-md hover:border-primary/20 transition-all duration-200 space-y-3 group"
              >
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10 text-primary group-hover:bg-primary group-hover:text-white transition-colors duration-200">
                  <Icon className="h-5 w-5" />
                </div>
                <p className="font-semibold text-slate-950 text-sm leading-snug">
                  {title}
                </p>
                <p className="text-xs leading-6 text-slate-500">{desc}</p>
              </div>
            ))}
          </div>
        </section>

        {/* ══════════════════════════════════════════
            TECH / TRUST STRIP
        ══════════════════════════════════════════ */}
        <section className="overflow-hidden rounded-[2rem] border border-slate-100 bg-white/85 p-7 shadow-sm md:p-8">
          <div className="grid gap-8 lg:grid-cols-[1.05fr_0.95fr]">
            <div className="space-y-5">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-xs font-bold uppercase tracking-widest text-primary">
                    Confianza operativa
                  </p>
                  <h3 className="mt-2 max-w-xl text-2xl font-bold tracking-tight text-slate-950 md:text-3xl">
                    Diseñado para que la primera conversación ya tenga valor clínico.
                  </h3>
                </div>
                <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-primary/10 text-primary">
                  <TbShieldCheck className="h-5 w-5" />
                </div>
              </div>

              <p className="max-w-2xl text-sm leading-7 text-slate-600">
                Medicheck no se presenta como una demo técnica. Se presenta
                como una capa de entrada clínica donde Hipo guía la primera
                conversación, ordena mejor lo que cuenta el paciente, deja
                trazabilidad y prepara la decisión del siguiente paso.
              </p>

              <div className="grid gap-3 sm:grid-cols-3">
                {trustHighlights.map((item) => (
                  <div
                    key={item.title}
                    className="rounded-[1.4rem] border border-slate-100 bg-slate-50/80 p-4"
                  >
                    <p className="text-[11px] font-bold uppercase tracking-[0.16em] text-primary/80">
                      {item.eyebrow}
                    </p>
                    <p className="mt-2 text-sm font-semibold text-slate-950">
                      {item.title}
                    </p>
                    <p className="mt-2 text-xs leading-6 text-slate-500">
                      {item.description}
                    </p>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-[1.7rem] border border-slate-100 bg-[linear-gradient(180deg,#f8fbfe_0%,#eef6fc_100%)] p-5">
              <p className="text-[11px] font-bold uppercase tracking-[0.16em] text-primary/80">
                Base tecnológica y normativa
              </p>
              <div className="mt-4 space-y-3">
                <div className="flex items-start gap-3 rounded-2xl bg-white/85 p-4 shadow-sm">
                  <div className="mt-0.5 h-2.5 w-2.5 rounded-full bg-primary shrink-0" />
                  <div>
                    <p className="text-sm font-semibold text-slate-950">
                      Hipo + IA clínica + protocolo de triaje
                    </p>
                    <p className="mt-1 text-xs leading-6 text-slate-500">
                      Hipo se apoya en Bedrock con Claude Haiku, Comprehend
                      Medical y Sistema Español de Triaje como base del flujo
                      actual.
                    </p>
                  </div>
                </div>
                <div className="flex items-start gap-3 rounded-2xl bg-white/85 p-4 shadow-sm">
                  <div className="mt-0.5 h-2.5 w-2.5 rounded-full bg-cyan-500 shrink-0" />
                  <div>
                    <p className="text-sm font-semibold text-slate-950">
                      Tiempo real y experiencia conectada
                    </p>
                    <p className="mt-1 text-xs leading-6 text-slate-500">
                      WebSockets para conversación continua, historial y flujo
                      conectado entre paciente y profesional.
                    </p>
                  </div>
                </div>
                <div className="flex items-start gap-3 rounded-2xl bg-white/85 p-4 shadow-sm">
                  <div className="mt-0.5 h-2.5 w-2.5 rounded-full bg-emerald-500 shrink-0" />
                  <div>
                    <p className="text-sm font-semibold text-slate-950">
                      Privacidad y marco regulatorio europeo
                    </p>
                    <p className="mt-1 text-xs leading-6 text-slate-500">
                      RGPD, LOPDGDD y una dirección alineada con la Ley de IA
                      de la Unión Europea para el uso responsable de sistemas
                      de apoyo clínico.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* ══════════════════════════════════════════
            CTA FINAL
        ══════════════════════════════════════════ */}
        <section className="relative overflow-hidden rounded-[2rem] border border-slate-900/70 bg-[linear-gradient(135deg,#020817_0%,#08152c_55%,#0d2440_100%)] px-7 py-10 text-white shadow-xl">
          {/* Decorative blob */}
          <div
            aria-hidden
            className="absolute -top-20 -right-20 h-72 w-72 rounded-full bg-primary/20 blur-3xl pointer-events-none"
          />
          <div
            aria-hidden
            className="absolute -bottom-16 -left-16 h-56 w-56 rounded-full bg-cyan-500/10 blur-3xl pointer-events-none"
          />

          <div className="relative grid gap-8 lg:grid-cols-[1.05fr_0.95fr] lg:items-center">
            <div className="space-y-4 max-w-2xl">
              <p className="text-xs font-bold uppercase tracking-widest text-primary/80">
                Siguiente paso
              </p>
              <h2 className="text-3xl font-bold tracking-tight leading-snug md:text-4xl">
                Una entrada clínica más ordenada, una revisión médica mejor preparada.
              </h2>
              <p className="text-sm leading-7 text-slate-300">
                Medicheck ya conecta a Hipo con la clasificación inicial, el
                contexto clínico y la continuidad del caso. El siguiente paso
                es convertir esa base en una operación más ágil para pacientes,
                médicos y centros sanitarios.
              </p>

              <div className="grid gap-3 sm:grid-cols-3">
                <div className="rounded-[1.35rem] border border-white/10 bg-white/5 px-4 py-4">
                  <p className="text-[11px] uppercase tracking-[0.16em] text-primary/75">
                    Paciente
                  </p>
                  <p className="mt-2 text-sm font-semibold">Consulta guiada con Hipo</p>
                  <p className="mt-1 text-xs leading-6 text-slate-400">
                    Mejor orientación desde el primer síntoma.
                  </p>
                </div>
                <div className="rounded-[1.35rem] border border-white/10 bg-white/5 px-4 py-4">
                  <p className="text-[11px] uppercase tracking-[0.16em] text-primary/75">
                    Profesional
                  </p>
                  <p className="mt-2 text-sm font-semibold">Revisión con contexto</p>
                  <p className="mt-1 text-xs leading-6 text-slate-400">
                    Menos lectura dispersa, más criterio clínico.
                  </p>
                </div>
                <div className="rounded-[1.35rem] border border-white/10 bg-white/5 px-4 py-4">
                  <p className="text-[11px] uppercase tracking-[0.16em] text-primary/75">
                    Centro
                  </p>
                  <p className="mt-2 text-sm font-semibold">Flujo más ordenado</p>
                  <p className="mt-1 text-xs leading-6 text-slate-400">
                    Base lista para seguimiento, validación y cita.
                  </p>
                </div>
              </div>
            </div>

            <div className="flex flex-col gap-4 rounded-[1.7rem] border border-white/10 bg-white/[0.04] p-5 backdrop-blur-sm">
              <div className="space-y-2">
                <p className="text-[11px] font-bold uppercase tracking-[0.16em] text-primary/80">
                  Qué puedes enseñar hoy
                </p>
                <p className="text-sm leading-7 text-slate-300">
                  Un producto donde Hipo conversa, prioriza, registra contexto
                  y prepara una revisión clínica mejor conectada.
                </p>
              </div>

              <div className="space-y-2 text-sm text-slate-200">
                <div className="flex items-center justify-between rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-3">
                  <span>Chat de triaje en tiempo real</span>
                  <span className="text-primary">Activo</span>
                </div>
                <div className="flex items-center justify-between rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-3">
                  <span>Contexto clínico estructurado</span>
                  <span className="text-primary">Disponible</span>
                </div>
                <div className="flex items-center justify-between rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-3">
                  <span>Flujo paciente · médico</span>
                  <span className="text-primary">Preparado</span>
                </div>
              </div>

              <div className="flex flex-col gap-3 sm:flex-row">
                <Button
                  asChild
                  size="lg"
                  className="rounded-full bg-white text-slate-950 hover:bg-slate-100 gap-2"
                >
                  <Link href={ROUTES.PUBLIC.LOGIN}>
                    Entrar al producto
                    <TbArrowRight className="h-4 w-4" />
                  </Link>
                </Button>
                <Button
                  asChild
                  size="lg"
                  variant="outline"
                  className="rounded-full border-white/25 bg-white/5 text-white hover:bg-white/10 hover:text-white gap-2"
                >
                  <Link href="#como-funciona">
                    Ver el recorrido
                    <TbChevronRight className="h-4 w-4" />
                  </Link>
                </Button>
              </div>
            </div>
          </div>
        </section>
      </main>

      {/* ══════════════════════════════════════════
          FOOTER
      ══════════════════════════════════════════ */}
      <footer className="page-container pt-0 pb-8">
        <div className="border-t border-slate-200 pt-6 flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <div className="relative h-6 w-6 overflow-hidden rounded-lg bg-primary/10">
              <Image
                src="/assets/img/icon192.png"
                alt="Medicheck"
                fill
                className="object-cover"
                sizes="24px"
              />
            </div>
            <span className="text-xs font-semibold text-slate-700">
              Medicheck
            </span>
          </div>
          <p className="text-xs text-slate-400 text-center">
            Sistema de triaje médico inteligente · RGPD · LOPDGDD ·{" "}
            <span className="text-primary font-medium">
              Hipo siempre apoya, nunca reemplaza al profesional sanitario.
            </span>
          </p>
        </div>
      </footer>
    </div>
  );
}
