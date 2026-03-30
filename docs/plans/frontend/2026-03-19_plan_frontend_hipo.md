# Plan de Mejoras Frontend — Hipo PWA
**Next.js · React · PWA · Chatbot médico de triaje**  
**7 bloques · 35 mejoras · UI · UX · Accesibilidad · Rendimiento**

---

## Contexto del proyecto

Hipo es una PWA de triaje médico (protocolo SET) con chat en tiempo real vía WebSocket. El usuario tipo es un paciente en situación de estrés que accede desde móvil. Eso define cada decisión de diseño: **claridad ante todo, velocidad, cero fricción en momentos críticos**.

---

## Herramientas de ideación recomendadas

### Nano Banana (Gemini 2.5 Flash Image)
Usar para generar mockups visuales de pantallas concretas antes de implementar. Especialmente útil para:
- Explorar variantes del chat bubble en modo emergencia vs. modo normal
- Generar el look visual del indicador de nivel SET (I–V) en distintos estilos
- Iterar sobre el onboarding sin abrir Figma

**Prompt tipo para Hipo:**
```
Design a mobile medical triage chat interface. Clean minimal healthcare UI.
White background, teal primary (#0d9488), red emergency accent.
Show: chat bubbles (bot left, user right), triage level badge (Level III - Urgent),
typing indicator, send button. iOS-style safe areas. Spanish language labels.
High resolution 4K mobile screen.
```

### Google Stitch (stitch.withgoogle.com)
Usar para generar el código frontend directamente desde mockups. Flujo recomendado:
1. Generar mockup visual con Nano Banana
2. Subir imagen a Stitch → extraer componentes React
3. Refinar código generado en Next.js
4. Exportar design system como `DESIGN.md` para mantener consistencia

**Prompt tipo para Stitch:**
```
Medical triage chatbot PWA. Mobile-first. Color palette: teal #0d9488 primary,
white background, red #dc2626 emergency. Components needed: chat interface,
triage level indicator (5 levels color-coded), offline banner, message bubbles
with source indicator (AI vs protocol). Accessible, WCAG AA compliant.
Export as React + Tailwind components.
```

---

## Bloque 1 — Sistema de diseño y tokens

### F-01 — Establecer design tokens globales

**Prioridad:** 🔴 CRÍTICO — todo lo demás depende de esto

Sin tokens consistentes cada componente tiene colores y espaciados arbitrarios. Un sistema médico necesita que el **color sea semántico**: el rojo siempre significa emergencia, el naranja urgencia, etc.

```typescript
// styles/tokens.ts
export const tokens = {
  colors: {
    // Niveles SET — semántica clínica fija
    triage: {
      level1: { bg: '#fef2f2', text: '#991b1b', border: '#fca5a5', label: 'Nivel I — Inmediata' },
      level2: { bg: '#fff7ed', text: '#9a3412', border: '#fdba74', label: 'Nivel II — Muy urgente' },
      level3: { bg: '#fefce8', text: '#854d0e', border: '#fde047', label: 'Nivel III — Urgente' },
      level4: { bg: '#f0fdf4', text: '#166534', border: '#86efac', label: 'Nivel IV — Menos urgente' },
      level5: { bg: '#f0f9ff', text: '#0c4a6e', border: '#7dd3fc', label: 'Nivel V — No urgente' },
    },
    brand:     { primary: '#0d9488', hover: '#0f766e', light: '#ccfbf1' },
    emergency: { primary: '#dc2626', bg: '#fef2f2', pulse: '#ef4444' },
    // Chat
    chat: {
      bot:  { bg: '#f8fafc', border: '#e2e8f0' },
      user: { bg: '#0d9488', text: '#ffffff' },
    },
  },
  spacing: {
    chatBubbleRadius: '18px 18px 4px 18px',   // user
    chatBubbleRadiusBot: '4px 18px 18px 18px', // bot
  },
  animation: {
    typingDuration: '1.4s',
    emergencyPulse: '2s',
    modeTransition: '300ms ease-in-out',
  },
}
```

**Archivos afectados:**
- `styles/tokens.ts` (nuevo)
- `tailwind.config.ts` → extender con los tokens
- `styles/globals.css` → CSS variables equivalentes para componentes no-Tailwind

---

### F-02 — Tipografía médica accesible

**Prioridad:** 🟡 IMPORTANTE

Las interfaces médicas necesitan tipografía con alta legibilidad, no decorativa.

```typescript
// next.config.ts — fuentes optimizadas con next/font
import { Inter, Source_Serif_4 } from 'next/font/google'

export const sans = Inter({
  subsets: ['latin'],
  variable: '--font-sans',
  display: 'swap',
})

// Para mensajes largos del bot (mejor legibilidad en párrafos)
export const serif = Source_Serif_4({
  subsets: ['latin'],
  variable: '--font-serif',
  display: 'swap',
})
```

Escala tipográfica:
```css
/* Tamaños mínimos para accesibilidad móvil */
--text-xs:   13px;  /* metadata, timestamps */
--text-sm:   15px;  /* mensajes secundarios */
--text-base: 16px;  /* mensajes del chat — MÍNIMO recomendado WCAG */
--text-lg:   18px;  /* títulos de sección */
--text-xl:   22px;  /* nivel de triaje en pantalla de resultado */
--text-2xl:  28px;  /* emergencia — máxima legibilidad */
```

---

### F-03 — Modo oscuro con semántica médica preservada

**Prioridad:** ⚪ MEJORA

El modo oscuro en un chatbot médico no puede simplemente invertir colores — el rojo de emergencia debe seguir siendo rojo, el verde de nivel V debe seguir siendo legible.

```typescript
// hooks/useColorScheme.ts
export function useColorScheme() {
  const [scheme, setScheme] = useState<'light' | 'dark'>('light')

  // Respetar preferencia del sistema
  useEffect(() => {
    const mq = window.matchMedia('(prefers-color-scheme: dark)')
    setScheme(mq.matches ? 'dark' : 'light')
    mq.addEventListener('change', e => setScheme(e.matches ? 'dark' : 'light'))
  }, [])

  return { scheme, toggle: () => setScheme(s => s === 'light' ? 'dark' : 'light') }
}
```

Regla para dark mode médico: los colores de alerta (rojo emergencia, amarillo urgencia) **nunca** cambian su tono, solo su saturación/brillo de fondo. Un paciente en urgencias no puede interpretar mal el color de su nivel de triaje.

---

## Bloque 2 — Componentes core del chat

### F-04 — ChatBubble con source indicator

**Prioridad:** 🔴 CRÍTICO — cumplimiento AI Act artículo 13

El payload del backend ya devuelve `response_source: 'expert' | 'llm' | 'hybrid'`. Mostrarlo visualmente es obligatorio por transparencia (AI Act) y además mejora la confianza del usuario.

```tsx
// components/chat/ChatBubble.tsx
interface ChatBubbleProps {
  message: string
  role: 'user' | 'bot'
  source?: 'expert' | 'llm' | 'hybrid'
  triageLevel?: 1 | 2 | 3 | 4 | 5
  timestamp: Date
  confidence?: number
}

const SOURCE_LABELS = {
  expert:  { label: 'Protocolo clínico',  icon: '⚕',  color: 'text-teal-700' },
  llm:     { label: 'IA asistida',         icon: '✦',  color: 'text-blue-600' },
  hybrid:  { label: 'Protocolo + IA',      icon: '⚕✦', color: 'text-purple-600' },
}

export function ChatBubble({ message, role, source, triageLevel, timestamp, confidence }: ChatBubbleProps) {
  const isBot = role === 'bot'
  const sourceInfo = source ? SOURCE_LABELS[source] : null

  return (
    <div className={`flex ${isBot ? 'justify-start' : 'justify-end'} mb-3 gap-2`}>
      {isBot && <BotAvatar />}

      <div className={`max-w-[80%] ${isBot ? 'items-start' : 'items-end'} flex flex-col gap-1`}>
        {/* Nivel de triaje inline si existe */}
        {triageLevel && isBot && (
          <TriageLevelBadge level={triageLevel} size="sm" />
        )}

        <div
          className={isBot
            ? 'bg-white border border-slate-200 text-slate-800 rounded-[4px_18px_18px_18px] px-4 py-3 text-base leading-relaxed'
            : 'bg-teal-600 text-white rounded-[18px_18px_4px_18px] px-4 py-3 text-base'
          }
        >
          {message}
        </div>

        {/* Footer del bubble */}
        <div className="flex items-center gap-2 px-1">
          <span className="text-xs text-slate-400">
            {format(timestamp, 'HH:mm')}
          </span>

          {sourceInfo && (
            <span className={`text-xs ${sourceInfo.color} flex items-center gap-1`}>
              <span aria-hidden="true">{sourceInfo.icon}</span>
              <span>{sourceInfo.label}</span>
            </span>
          )}

          {confidence !== undefined && confidence < 0.75 && (
            <span className="text-xs text-amber-600">
              Confianza baja — consulta presencial recomendada
            </span>
          )}
        </div>
      </div>
    </div>
  )
}
```

---

### F-05 — TriageLevelIndicator persistente

**Prioridad:** 🔴 CRÍTICO

El nivel de triaje actual debe estar siempre visible durante la conversación. Si escala, el usuario debe verlo inmediatamente sin leer el texto.

```tsx
// components/chat/TriageLevelIndicator.tsx
const TRIAGE_CONFIG = {
  1: { label: 'Nivel I', sublabel: 'Inmediata', bg: 'bg-red-50',    border: 'border-red-400',   text: 'text-red-800',   pulse: true  },
  2: { label: 'Nivel II', sublabel: 'Muy urgente', bg: 'bg-orange-50', border: 'border-orange-400', text: 'text-orange-800', pulse: true  },
  3: { label: 'Nivel III', sublabel: 'Urgente', bg: 'bg-yellow-50', border: 'border-yellow-400', text: 'text-yellow-800', pulse: false },
  4: { label: 'Nivel IV', sublabel: 'Menos urgente', bg: 'bg-green-50',  border: 'border-green-400',  text: 'text-green-800',  pulse: false },
  5: { label: 'Nivel V', sublabel: 'No urgente', bg: 'bg-blue-50',   border: 'border-blue-400',   text: 'text-blue-800',   pulse: false },
}

export function TriageLevelIndicator({ level, previousLevel }: { level: number, previousLevel?: number }) {
  const config = TRIAGE_CONFIG[level as keyof typeof TRIAGE_CONFIG]
  const escalated = previousLevel && level < previousLevel  // nivel más bajo = más urgente

  return (
    <div
      className={`
        flex items-center gap-3 px-4 py-2 rounded-xl border
        ${config.bg} ${config.border}
        ${escalated ? 'animate-pulse-once' : ''}
        transition-all duration-500
      `}
      role="status"
      aria-live="polite"
      aria-label={`Nivel de triaje actual: ${config.label}, ${config.sublabel}`}
    >
      {config.pulse && (
        <span className="relative flex h-3 w-3">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75" />
          <span className="relative inline-flex rounded-full h-3 w-3 bg-red-500" />
        </span>
      )}
      <div>
        <p className={`text-sm font-semibold ${config.text}`}>{config.label}</p>
        <p className={`text-xs ${config.text} opacity-75`}>{config.sublabel}</p>
      </div>
      {escalated && (
        <span className={`ml-auto text-xs font-medium ${config.text} bg-white/60 px-2 py-0.5 rounded-full`}>
          ↑ Actualizado
        </span>
      )}
    </div>
  )
}
```

---

### F-06 — EmergencyBanner con acción directa

**Prioridad:** 🔴 CRÍTICO — seguridad del paciente

Cuando `EmergencyGuard` dispara en el backend, el frontend debe mostrar un banner que no se puede ignorar y con acción inmediata.

```tsx
// components/chat/EmergencyBanner.tsx
export function EmergencyBanner({ onDismiss }: { onDismiss?: () => void }) {
  return (
    <div
      role="alert"
      aria-live="assertive"
      className="fixed top-0 left-0 right-0 z-50 bg-red-600 text-white px-4 py-4 shadow-lg"
    >
      <div className="max-w-lg mx-auto">
        <div className="flex items-start gap-3">
          <div className="shrink-0 mt-0.5">
            <svg className="w-6 h-6 animate-pulse" fill="currentColor" viewBox="0 0 24 24">
              <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"/>
            </svg>
          </div>
          <div className="flex-1">
            <p className="font-bold text-lg leading-tight">Posible emergencia detectada</p>
            <p className="text-red-100 text-sm mt-1">
              Los síntomas que describes pueden requerir atención inmediata.
            </p>
          </div>
        </div>

        <a
          href="tel:112"
          className="mt-3 flex items-center justify-center gap-2 w-full bg-white text-red-700 
                     font-bold py-3 px-4 rounded-xl text-lg active:scale-95 transition-transform"
        >
          <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
            <path d="M20.01 15.38c-1.23 0-2.42-.2-3.53-.56-.35-.12-.74-.03-1.01.24l-1.57 1.97c-2.83-1.35-5.48-3.9-6.89-6.83l1.95-1.66c.27-.28.35-.67.24-1.02-.37-1.11-.56-2.3-.56-3.53 0-.54-.45-.99-.99-.99H4.19C3.65 3 3 3.24 3 3.99 3 13.28 10.73 21 20.01 21c.71 0 .99-.63.99-1.18v-3.45c0-.54-.45-.99-.99-.99z"/>
          </svg>
          Llamar al 112
        </a>

        {onDismiss && (
          <button
            onClick={onDismiss}
            className="mt-2 w-full text-red-200 text-sm py-2 underline"
          >
            Continuar con el triaje (no es emergencia)
          </button>
        )}
      </div>
    </div>
  )
}
```

---

### F-07 — TypingIndicator y estados de conexión WebSocket

**Prioridad:** 🟡 IMPORTANTE

El usuario necesita feedback constante del estado del sistema. En un chatbot médico, el silencio genera ansiedad.

```tsx
// components/chat/ConnectionStatus.tsx
type WsStatus = 'connected' | 'connecting' | 'offline' | 'error'

const STATUS_CONFIG: Record<WsStatus, { label: string, color: string, dot: string }> = {
  connected:   { label: 'Conectado',     color: 'text-teal-700',  dot: 'bg-teal-500' },
  connecting:  { label: 'Conectando...', color: 'text-amber-700', dot: 'bg-amber-500 animate-pulse' },
  offline:     { label: 'Sin conexión · modo básico activo', color: 'text-slate-600', dot: 'bg-slate-400' },
  error:       { label: 'Error de conexión', color: 'text-red-700', dot: 'bg-red-500 animate-pulse' },
}

export function ConnectionStatus({ status }: { status: WsStatus }) {
  if (status === 'connected') return null  // no mostrar si todo va bien

  const cfg = STATUS_CONFIG[status]
  return (
    <div className={`flex items-center gap-2 px-3 py-1.5 text-xs ${cfg.color} bg-white/80 backdrop-blur-sm`}>
      <span className={`w-2 h-2 rounded-full ${cfg.dot}`} />
      {cfg.label}
    </div>
  )
}

// Typing indicator del bot
export function TypingIndicator() {
  return (
    <div className="flex justify-start mb-3 gap-2" aria-label="El asistente está escribiendo">
      <BotAvatar />
      <div className="bg-white border border-slate-200 rounded-[4px_18px_18px_18px] px-4 py-3">
        <div className="flex gap-1 items-center h-4">
          {[0, 1, 2].map(i => (
            <span
              key={i}
              className="w-2 h-2 bg-slate-400 rounded-full animate-bounce"
              style={{ animationDelay: `${i * 0.15}s` }}
            />
          ))}
        </div>
      </div>
    </div>
  )
}
```

---

## Bloque 3 — UX del flujo de triaje

### F-08 — Input con detección de intent (UX proactivo)

**Prioridad:** 🟡 IMPORTANTE

El textarea de chat puede dar feedback visual antes de enviar, detectando keywords de emergencia.

```tsx
// components/chat/ChatInput.tsx
const EMERGENCY_KEYWORDS = ['pecho', 'dificultad respirar', 'sin respiración', 
                             'no puedo respirar', 'inconsciente', 'síncope', 'convulsión']

export function ChatInput({ onSend, disabled }: ChatInputProps) {
  const [value, setValue] = useState('')
  const [hasEmergencyKeyword, setHasEmergencyKeyword] = useState(false)

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const text = e.target.value
    setValue(text)
    setHasEmergencyKeyword(
      EMERGENCY_KEYWORDS.some(kw => text.toLowerCase().includes(kw))
    )
  }

  return (
    <div className="relative">
      {/* Warning de keyword detectado */}
      {hasEmergencyKeyword && (
        <div className="absolute -top-10 left-0 right-0 bg-red-50 border border-red-200 
                        rounded-xl px-3 py-2 text-xs text-red-700 flex items-center gap-2">
          <span>⚠</span>
          Si es una emergencia, llama directamente al 112
        </div>
      )}

      <div className={`flex items-end gap-2 p-3 rounded-2xl border transition-colors
                       ${hasEmergencyKeyword 
                          ? 'border-red-300 bg-red-50' 
                          : 'border-slate-200 bg-white'}`}>
        <textarea
          value={value}
          onChange={handleChange}
          placeholder="Describe tus síntomas..."
          className="flex-1 resize-none bg-transparent outline-none text-base leading-relaxed 
                     max-h-32 min-h-[24px] text-slate-800 placeholder:text-slate-400"
          rows={1}
          aria-label="Mensaje al asistente de triaje"
          onKeyDown={e => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              if (value.trim()) onSend(value.trim())
              setValue('')
            }
          }}
        />
        <button
          onClick={() => { if (value.trim()) { onSend(value.trim()); setValue('') } }}
          disabled={disabled || !value.trim()}
          className="shrink-0 w-10 h-10 bg-teal-600 disabled:bg-slate-200 text-white 
                     rounded-xl flex items-center justify-center transition-colors
                     active:scale-95 disabled:cursor-not-allowed"
          aria-label="Enviar mensaje"
        >
          <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
            <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
          </svg>
        </button>
      </div>

      {/* Contador de caracteres solo cuando se acerca al límite */}
      {value.length > 400 && (
        <p className="text-xs text-slate-400 text-right mt-1">
          {500 - value.length} caracteres restantes
        </p>
      )}
    </div>
  )
}
```

---

### F-09 — Pantalla de resultado de triaje

**Prioridad:** 🔴 CRÍTICO — es la pantalla más importante del flujo

Cuando el sistema da el consejo final, el usuario debe ver el resultado de forma clara e imprimible/compartible.

```tsx
// app/triage/result/page.tsx
export function TriageResult({ result }: { result: TriageResult }) {
  const config = TRIAGE_CONFIG[result.level]

  return (
    <main className="min-h-screen bg-slate-50 p-4">
      <div className="max-w-lg mx-auto space-y-4">
        
        {/* Card principal del resultado */}
        <div className={`rounded-2xl border-2 ${config.border} ${config.bg} p-6`}>
          <div className="flex items-start justify-between mb-4">
            <div>
              <p className={`text-xs font-semibold uppercase tracking-widest ${config.text} opacity-60`}>
                Resultado del triaje
              </p>
              <h1 className={`text-2xl font-bold ${config.text} mt-1`}>
                {config.label}
              </h1>
              <p className={`text-lg ${config.text} opacity-80`}>
                {config.sublabel}
              </p>
            </div>
            <div className={`w-14 h-14 rounded-2xl ${config.text} bg-white/60 
                            flex items-center justify-center text-3xl font-bold`}>
              {result.level}
            </div>
          </div>

          {/* Consejo principal */}
          <div className="bg-white/70 rounded-xl p-4 mt-2">
            <p className="text-slate-800 text-base leading-relaxed">
              {result.advice}
            </p>
          </div>
        </div>

        {/* Acción recomendada */}
        <ActionCard level={result.level} />

        {/* Resumen clínico */}
        <details className="bg-white rounded-2xl border border-slate-200 p-4">
          <summary className="text-sm font-medium text-slate-700 cursor-pointer">
            Resumen de la consulta
          </summary>
          <div className="mt-3 space-y-2 text-sm text-slate-600">
            {result.symptoms && <p><strong>Síntomas:</strong> {result.symptoms}</p>}
            {result.duration && <p><strong>Evolución:</strong> {result.duration}</p>}
            {result.painScale && <p><strong>Dolor:</strong> {result.painScale}/10</p>}
          </div>
        </details>

        {/* Source del consejo — AI Act compliance */}
        <p className="text-xs text-center text-slate-400 px-4">
          Resultado generado mediante {result.source === 'expert' ? 'protocolo clínico SET' : 'protocolo SET + IA'}.
          Este sistema no sustituye la valoración médica profesional.
        </p>

        {/* Acciones */}
        <div className="flex gap-3">
          <button
            onClick={() => window.print()}
            className="flex-1 py-3 border border-slate-200 rounded-xl text-sm text-slate-600"
          >
            Guardar resultado
          </button>
          <button
            onClick={() => window.location.href = '/chat'}
            className="flex-1 py-3 bg-teal-600 text-white rounded-xl text-sm font-medium"
          >
            Nueva consulta
          </button>
        </div>
      </div>
    </main>
  )
}
```

---

### F-10 — Onboarding y contexto inicial

**Prioridad:** 🟡 IMPORTANTE

El usuario no sabe qué es el triaje SET. Necesita un onboarding breve (max 3 pasos) antes de la primera sesión.

```tsx
// components/onboarding/OnboardingFlow.tsx
const STEPS = [
  {
    icon: '⚕',
    title: 'Asistente de triaje médico',
    body: 'Hipo te ayuda a valorar la urgencia de tus síntomas siguiendo el protocolo SET, el estándar usado en urgencias hospitalarias.',
    action: 'Entendido',
  },
  {
    icon: '💬',
    title: 'Cuéntame cómo te encuentras',
    body: 'Describe tus síntomas con naturalidad, como si le hablaras a un médico. Cuanta más información, mejor.',
    action: 'De acuerdo',
  },
  {
    icon: '🚨',
    title: 'En emergencias, llama al 112',
    body: 'Si tienes dolor en el pecho, dificultad para respirar o pérdida de conciencia, llama al 112 directamente. No esperes al triaje.',
    action: 'Empezar',
    actionStyle: 'primary',
  },
]
```

Mostrar solo en primera visita (`localStorage.getItem('hipo:onboarded')`). Máximo 30 segundos de lectura total. Saltable desde el segundo paso.

---

### F-11 — Pantalla de sesión expirada y timeout

**Prioridad:** 🔴 CRÍTICO — relacionado con mejora #35 del backend

El frontend debe manejar el evento `session_warning` del WebSocket con un banner no intrusivo y el timeout final con transición suave.

```tsx
// components/chat/SessionTimeoutWarning.tsx
export function SessionTimeoutWarning({ secondsLeft, onExtend }: {
  secondsLeft: number
  onExtend: () => void
}) {
  return (
    <div
      role="alert"
      className="mx-4 mb-2 bg-amber-50 border border-amber-200 rounded-xl px-4 py-3 
                 flex items-center justify-between gap-3"
    >
      <div>
        <p className="text-sm font-medium text-amber-800">
          La sesión se cerrará en {secondsLeft} segundos
        </p>
        <p className="text-xs text-amber-600 mt-0.5">
          ¿Tienes algo más que añadir?
        </p>
      </div>
      <button
        onClick={onExtend}
        className="shrink-0 text-sm font-medium text-amber-700 bg-white 
                   border border-amber-300 px-3 py-1.5 rounded-lg"
      >
        Continuar
      </button>
    </div>
  )
}
```

---

## Bloque 4 — Accesibilidad (WCAG 2.1 AA)

### F-12 — Auditoría de contraste y targets táctiles

**Prioridad:** 🔴 CRÍTICO

Un sistema médico debe cumplir WCAG 2.1 nivel AA mínimo. Lista de verificación específica para Hipo:

**Contraste (criterio 1.4.3 — ratio mínimo 4.5:1):**
- Teal-600 (#0d9488) sobre blanco → ratio 3.8:1 ❌ — usar Teal-700 (#0f766e) → ratio 5.1:1 ✅
- Texto de nivel de triaje sobre su fondo coloreado → verificar cada uno con herramienta
- Timestamps grises sobre fondo blanco → no bajar de slate-500

**Touch targets (criterio 2.5.8 — mínimo 24×24px, recomendado 44×44px):**
```css
/* Regla global en globals.css */
button, a, [role="button"] {
  min-height: 44px;
  min-width: 44px;
}

/* Excepción solo para elementos inline de texto */
.inline-link { min-height: unset; }
```

**Focus visible (criterio 2.4.7):**
```css
:focus-visible {
  outline: 3px solid #0d9488;
  outline-offset: 2px;
  border-radius: 4px;
}
```

---

### F-13 — ARIA y navegación por teclado en el chat

**Prioridad:** 🟡 IMPORTANTE

```tsx
// components/chat/ChatContainer.tsx
export function ChatContainer() {
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const announcerRef = useRef<HTMLDivElement>(null)

  // Anunciar nuevos mensajes del bot a lectores de pantalla
  const announceMessage = (text: string) => {
    if (announcerRef.current) {
      announcerRef.current.textContent = text
      // Reset después de anuncio para que vuelva a disparar en próximo mensaje
      setTimeout(() => { if (announcerRef.current) announcerRef.current.textContent = '' }, 1000)
    }
  }

  return (
    <>
      {/* Región live para lectores de pantalla — invisible visualmente */}
      <div
        ref={announcerRef}
        role="status"
        aria-live="polite"
        aria-atomic="true"
        className="sr-only"
      />

      <main
        role="main"
        aria-label="Conversación de triaje médico"
      >
        <section
          aria-label="Mensajes"
          aria-live="polite"
          className="overflow-y-auto flex-1 p-4 space-y-1"
        >
          {/* mensajes */}
        </section>

        {/* Skip link para usuarios de teclado */}
        <a
          href="#chat-input"
          className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 
                     bg-teal-600 text-white px-4 py-2 rounded-xl z-50"
        >
          Ir al campo de mensaje
        </a>

        <div id="chat-input">
          <ChatInput />
        </div>
      </main>
    </>
  )
}
```

---

### F-14 — Reducción de movimiento

**Prioridad:** 🟡 IMPORTANTE

```css
/* globals.css — respetar preferencia del sistema */
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }

  /* Excepción: el indicador de typing DEBE verse incluso sin animación */
  .typing-indicator span {
    animation-duration: 0s !important;
    opacity: 0.6;
  }
}
```

---

## Bloque 5 — Rendimiento Next.js

### F-15 — Route-based code splitting del chat

**Prioridad:** 🟡 IMPORTANTE

El bundle inicial no debe incluir la lógica del chat si el usuario aún no está autenticado.

```typescript
// app/chat/page.tsx — dynamic import del componente pesado
import dynamic from 'next/dynamic'

const ChatInterface = dynamic(
  () => import('@/components/chat/ChatInterface'),
  {
    loading: () => <ChatSkeleton />,
    ssr: false,  // WebSocket no tiene SSR
  }
)

// Precargar cuando el usuario hace hover sobre "Iniciar triaje"
const prefetchChat = () => {
  import('@/components/chat/ChatInterface')
  import('@/lib/websocket')
}
```

---

### F-16 — Virtualización de mensajes

**Prioridad:** ⚪ MEJORA (importante a largo plazo)

Una conversación de triaje puede tener 30-50 mensajes. Sin virtualización el scroll se vuelve pesado en móviles de gama media.

```tsx
// Usar @tanstack/react-virtual para la lista de mensajes
import { useVirtualizer } from '@tanstack/react-virtual'

export function MessageList({ messages }: { messages: Message[] }) {
  const parentRef = useRef<HTMLDivElement>(null)

  const virtualizer = useVirtualizer({
    count: messages.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 80,          // altura estimada por mensaje
    overscan: 5,                     // mensajes pre-renderizados fuera de vista
  })

  // Auto-scroll al último mensaje
  useEffect(() => {
    virtualizer.scrollToIndex(messages.length - 1, { behavior: 'smooth' })
  }, [messages.length])

  return (
    <div ref={parentRef} className="overflow-y-auto flex-1">
      <div style={{ height: virtualizer.getTotalSize() }}>
        {virtualizer.getVirtualItems().map(item => (
          <div
            key={item.key}
            style={{ transform: `translateY(${item.start}px)`, position: 'absolute', width: '100%' }}
          >
            <ChatBubble {...messages[item.index]} />
          </div>
        ))}
      </div>
    </div>
  )
}
```

---

### F-17 — Optimización de imágenes y assets

**Prioridad:** 🟡 IMPORTANTE

```typescript
// next.config.ts
const config: NextConfig = {
  images: {
    formats: ['image/avif', 'image/webp'],
    deviceSizes: [390, 414, 768, 1024],  // tamaños reales de móvil
  },
  // Comprimir respuestas
  compress: true,
  // Headers de caché para assets estáticos
  async headers() {
    return [{
      source: '/_next/static/:path*',
      headers: [{ key: 'Cache-Control', value: 'public, max-age=31536000, immutable' }]
    }]
  }
}
```

---

### F-18 — Web Vitals y métricas específicas del chat

**Prioridad:** ⚪ MEJORA

Las métricas de Next.js por defecto no capturan lo que importa en un chatbot: tiempo de primera respuesta del bot, tiempo de escalado de triaje.

```typescript
// lib/analytics.ts — métricas custom
export function trackChatMetrics() {
  // Tiempo hasta primera respuesta del bot
  performance.mark('chat:message-sent')
  
  // Llamar cuando llega la respuesta
  performance.mark('chat:response-received')
  performance.measure('chat:response-time', 'chat:message-sent', 'chat:response-received')

  const [measure] = performance.getEntriesByName('chat:response-time')
  
  // Reportar a tu herramienta de analytics
  if (measure.duration > 3000) {
    console.warn(`Respuesta lenta del chatbot: ${measure.duration}ms`)
  }
}
```

---

## Bloque 6 — PWA y offline

### F-19 — Service Worker con next-pwa

**Prioridad:** 🟡 IMPORTANTE (relacionado con mejora del plan de backend)

```typescript
// next.config.ts
import withPWA from 'next-pwa'

export default withPWA({
  dest: 'public',
  register: true,
  skipWaiting: true,
  runtimeCaching: [
    // Shell de la app — siempre disponible
    {
      urlPattern: /^https:\/\/hipo\.app\/_next\/static\//,
      handler: 'CacheFirst',
      options: { cacheName: 'static-assets', expiration: { maxAgeSeconds: 7 * 24 * 60 * 60 } }
    },
    // Reglas del sistema experto — críticas para modo offline
    {
      urlPattern: /\/api\/expert-rules/,
      handler: 'CacheFirst',
      options: { cacheName: 'expert-rules', expiration: { maxAgeSeconds: 24 * 60 * 60 } }
    },
    // API del chat — network-first, fallback a respuesta offline
    {
      urlPattern: /\/api\/chat/,
      handler: 'NetworkFirst',
      options: {
        cacheName: 'chat-api',
        networkTimeoutSeconds: 3,
        expiration: { maxAgeSeconds: 5 * 60 }
      }
    }
  ]
})
```

---

### F-20 — Banner de modo offline con degradación elegante

**Prioridad:** 🟡 IMPORTANTE

```tsx
// components/ui/OfflineBanner.tsx
export function OfflineBanner({ isOffline }: { isOffline: boolean }) {
  if (!isOffline) return null

  return (
    <div
      role="status"
      className="bg-slate-700 text-white text-sm px-4 py-2 flex items-center gap-2"
    >
      <span className="w-2 h-2 bg-slate-400 rounded-full" />
      <span>Sin conexión · Modo básico activo · Los datos se sincronizarán al reconectar</span>
    </div>
  )
}
```

---

### F-21 — Manifest.json optimizado para móvil

**Prioridad:** 🟡 IMPORTANTE

```json
// public/manifest.json
{
  "name": "Hipo — Triaje médico",
  "short_name": "Hipo",
  "description": "Asistente de triaje médico basado en el protocolo SET",
  "start_url": "/chat",
  "display": "standalone",
  "orientation": "portrait",
  "theme_color": "#0d9488",
  "background_color": "#f8fafc",
  "icons": [
    { "src": "/icons/icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any maskable" },
    { "src": "/icons/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable" }
  ],
  "categories": ["health", "medical"],
  "screenshots": [
    { "src": "/screenshots/chat.png", "sizes": "390x844", "type": "image/png", "form_factor": "narrow" }
  ]
}
```

---

## Bloque 7 — Buenas prácticas Next.js

### F-22 — Server Components vs Client Components

**Prioridad:** 🟡 IMPORTANTE

Regla práctica para Hipo: todo lo que no necesite estado interactivo o WebSocket debe ser Server Component.

```
app/
├── layout.tsx          → Server Component (shell HTML)
├── page.tsx            → Server Component (landing)
├── auth/
│   └── login/page.tsx  → Server Component (formulario inicial)
└── chat/
    └── page.tsx        → Server Component (wrapper)
        └── ChatInterface.tsx → 'use client' (WebSocket, estado)
            ├── MessageList.tsx → 'use client' (virtualización)
            ├── ChatInput.tsx   → 'use client' (estado del input)
            └── TriageLevelIndicator.tsx → 'use client' (animaciones)
```

---

### F-23 — Error boundaries y manejo de fallos del WebSocket

**Prioridad:** 🟡 IMPORTANTE

```tsx
// components/chat/ChatErrorBoundary.tsx
'use client'

export class ChatErrorBoundary extends Component<
  { children: ReactNode },
  { error: Error | null }
> {
  state = { error: null }

  static getDerivedStateFromError(error: Error) {
    return { error }
  }

  render() {
    if (this.state.error) {
      return (
        <div className="flex flex-col items-center justify-center min-h-[400px] p-8 text-center">
          <div className="w-16 h-16 bg-red-50 rounded-full flex items-center justify-center mb-4">
            <svg className="w-8 h-8 text-red-500" fill="currentColor" viewBox="0 0 24 24">
              <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"/>
            </svg>
          </div>
          <h2 className="text-lg font-semibold text-slate-800 mb-2">
            Error en el chat
          </h2>
          <p className="text-slate-500 text-sm mb-6">
            Ha ocurrido un error inesperado. Si es urgente, llama al 112.
          </p>
          <button
            onClick={() => this.setState({ error: null })}
            className="bg-teal-600 text-white px-6 py-3 rounded-xl"
          >
            Reintentar
          </button>
        </div>
      )
    }
    return this.props.children
  }
}
```

---

### F-24 — Estado global con Zustand (mínimo y enfocado)

**Prioridad:** 🟡 IMPORTANTE

```typescript
// stores/chatStore.ts
import { create } from 'zustand'

interface ChatStore {
  messages: Message[]
  triageLevel: number | null
  previousTriageLevel: number | null
  wsStatus: 'connected' | 'connecting' | 'offline' | 'error'
  sessionMode: 'consultation' | 'triage'
  isOffline: boolean
  
  addMessage: (msg: Message) => void
  setTriageLevel: (level: number) => void
  setWsStatus: (status: ChatStore['wsStatus']) => void
  setSessionMode: (mode: ChatStore['sessionMode']) => void
}

export const useChatStore = create<ChatStore>((set) => ({
  messages: [],
  triageLevel: null,
  previousTriageLevel: null,
  wsStatus: 'connecting',
  sessionMode: 'consultation',
  isOffline: false,

  addMessage: (msg) => set(state => ({ messages: [...state.messages, msg] })),

  setTriageLevel: (level) => set(state => ({
    previousTriageLevel: state.triageLevel,
    triageLevel: level,
  })),

  setWsStatus: (status) => set({ wsStatus: status, isOffline: status === 'offline' }),
  setSessionMode: (mode) => set({ sessionMode: mode }),
}))
```

---

### F-25 — Formularios con React Hook Form + Zod

**Prioridad:** 🟡 IMPORTANTE

```typescript
// schemas/auth.schema.ts
import { z } from 'zod'

export const loginSchema = z.object({
  email: z.string().email('Email inválido'),
  password: z.string().min(8, 'Mínimo 8 caracteres'),
})

// components/auth/LoginForm.tsx
'use client'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'

export function LoginForm() {
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm({
    resolver: zodResolver(loginSchema)
  })

  return (
    <form onSubmit={handleSubmit(onSubmit)} noValidate>
      <div>
        <label htmlFor="email" className="block text-sm font-medium text-slate-700 mb-1">
          Email
        </label>
        <input
          id="email"
          type="email"
          autoComplete="email"
          aria-describedby={errors.email ? 'email-error' : undefined}
          aria-invalid={!!errors.email}
          {...register('email')}
          className={`w-full px-4 py-3 rounded-xl border text-base ${
            errors.email ? 'border-red-400 bg-red-50' : 'border-slate-200'
          }`}
        />
        {errors.email && (
          <p id="email-error" role="alert" className="mt-1 text-sm text-red-600">
            {errors.email.message}
          </p>
        )}
      </div>
    </form>
  )
}
```

---

### F-26 — Testing del frontend

**Prioridad:** ⚪ MEJORA

```bash
# Stack recomendado
pnpm add -D vitest @testing-library/react @testing-library/user-event
pnpm add -D @playwright/test  # E2E
```

```typescript
// __tests__/components/TriageLevelIndicator.test.tsx
import { render, screen } from '@testing-library/react'
import { TriageLevelIndicator } from '@/components/chat/TriageLevelIndicator'

describe('TriageLevelIndicator', () => {
  it('muestra el nivel correcto con texto accesible', () => {
    render(<TriageLevelIndicator level={1} />)
    expect(screen.getByRole('status')).toHaveAccessibleName(/Nivel I.*Inmediata/)
  })

  it('indica escalado cuando el nivel sube de gravedad', () => {
    render(<TriageLevelIndicator level={2} previousLevel={4} />)
    expect(screen.getByText('↑ Actualizado')).toBeInTheDocument()
  })
})
```

---

## Resumen de prioridades

### 🔴 CRÍTICO — hacer primero (impacto en seguridad clínica o flujo principal)

| # | Mejora | Tiempo est. |
|---|--------|------------|
| F-01 | Design tokens globales | 2h |
| F-04 | ChatBubble con source indicator (AI Act) | 3h |
| F-05 | TriageLevelIndicator persistente | 2h |
| F-06 | EmergencyBanner con llamada al 112 | 1h |
| F-09 | Pantalla de resultado de triaje | 4h |
| F-11 | Session timeout warning | 1h |
| F-12 | Contraste y touch targets WCAG | 2h |

**Total crítico:** ~15h

### 🟡 IMPORTANTE — hacer si hay tiempo

| # | Mejora | Tiempo est. |
|---|--------|------------|
| F-02 | Tipografía accesible con next/font | 1h |
| F-07 | TypingIndicator + estados WS | 2h |
| F-08 | ChatInput con keyword detection | 2h |
| F-10 | Onboarding 3 pasos | 3h |
| F-13 | ARIA y navegación por teclado | 3h |
| F-15 | Code splitting del chat | 1h |
| F-17 | Optimización de imágenes | 1h |
| F-19 | Service Worker next-pwa | 3h |
| F-20 | Banner modo offline | 1h |
| F-21 | Manifest.json | 30min |
| F-22 | Server vs Client Components | 2h |
| F-23 | Error boundaries | 1h |
| F-24 | Estado global Zustand | 2h |
| F-25 | Formularios con RHF + Zod | 2h |

**Total importante:** ~27h

### ⚪ MEJORA — pulido final

| # | Mejora | Tiempo est. |
|---|--------|------------|
| F-03 | Modo oscuro | 4h |
| F-14 | Reducción de movimiento | 30min |
| F-16 | Virtualización de mensajes | 3h |
| F-18 | Web Vitals custom | 2h |
| F-26 | Testing | 6h |

---

## Workflow con Nano Banana + Google Stitch

### Flujo recomendado para cada pantalla nueva:

```
1. NANO BANANA (AI Studio → Gemini 2.5 Flash Image)
   └── Generar mockup visual de la pantalla con prompt específico
       └── Iterar hasta tener dirección visual clara (3-5 variantes)

2. GOOGLE STITCH (stitch.withgoogle.com)
   └── Subir mockup de Nano Banana como referencia
   └── Pedir: "Convertir en componentes React con Tailwind"
   └── Exportar a Figma para revisar o directamente el código

3. REFINAR EN NEXT.JS
   └── Adaptar código de Stitch a la arquitectura existente
   └── Añadir lógica de WebSocket y estado Zustand
   └── Verificar accesibilidad con axe DevTools

4. DESIGN.MD (Stitch feature)
   └── Exportar design system como DESIGN.md
   └── Importar en próximas pantallas para mantener consistencia
```

### Prompt template para Nano Banana — pantallas de Hipo:

```
Medical triage PWA screen: [nombre de la pantalla]
Device: iPhone 14 Pro frame
Color system: teal #0d9488 primary, white bg, red #dc2626 emergency only
Typography: clean sans-serif, 16px minimum body
Components: [lista los componentes específicos]
Language: Spanish
Style: clinical minimal, trustworthy, calm — NOT sterile/cold
No gradients, no dark backgrounds except emergency states
WCAG AA compliant contrast ratios
```
