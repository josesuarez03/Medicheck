# Plan de Mejoras Frontend — Hipo PWA (ejecución con skills)

**Base:** actualización del plan frontend original para que Codex ejecute cada mejora con skills de forma consistente.  
**Stack:** Next.js + React + TypeScript + Tailwind + WebSocket + accesibilidad + rendimiento

---

## 1. Regla general de ejecución con skills

No ejecutes una mejora frontend con un prompt genérico tipo:

```text
Implementa la mejora F-XX del plan frontend.
```

Usa siempre este patrón:

```text
Implementa la mejora F-XX del plan frontend de Hipo.

Antes de tocar código:
1. $next-best-practices revisa la estructura de la mejora en Next.js
2. $vercel-react-best-practices define el patrón correcto de componentes, estado y rendimiento
3. $reducing-entropy evita duplicación y respeta la arquitectura actual
4. Si hay bugs o comportamiento raro, usa $systematic-debugging antes de parchear
5. Al final, usa $commit-work para proponer commits claros
6. Si la mejora toca flujo visual o componentes generados con Stitch, usa $stitch-loop solo para iteración visual/estructura de UI, no para lógica de negocio

Implementa solo la mejora pedida. No rehagas partes no relacionadas. 
Al terminar, verifica que no rompes el flujo WebSocket, accesibilidad ni responsive móvil.
```

---

## 2. Skills recomendadas para frontend Hipo

### Skills base que deberías usar casi siempre
- `$next-best-practices`
- `$vercel-react-best-practices`
- `$reducing-entropy`
- `$systematic-debugging`
- `$commit-work`
- `$session-handoff`

### Skills secundarias según el tipo de tarea
- `$stitch-loop` → para pantallas nuevas, refinar estructura UI a partir de mockups o ideas
- `$web-design-guidelines` → solo cuando el problema sea claramente visual, jerarquía, layout o consistencia
- `$debugging-strategies` → cuando el fallo no esté claro y haya que acotar hipótesis
- `$next-cache-components` → cuando la mejora toque render, caché, separación server/client o performance fina

---

## 3. Matriz rápida: qué skill usar según el problema

| Tipo de tarea | Skills principales |
|---|---|
| Arquitectura de componentes Next.js | `$next-best-practices`, `$vercel-react-best-practices` |
| Rendimiento del chat | `$vercel-react-best-practices`, `$next-cache-components`, `$reducing-entropy` |
| Componente visual nuevo | `$stitch-loop`, `$vercel-react-best-practices`, `$web-design-guidelines` |
| Estado global / Zustand | `$vercel-react-best-practices`, `$reducing-entropy` |
| WebSocket UI / estados de conexión | `$vercel-react-best-practices`, `$systematic-debugging` |
| Accesibilidad / ARIA / foco / contraste | `$web-design-guidelines`, `$vercel-react-best-practices` |
| Errores raros en el chat | `$systematic-debugging`, `$debugging-strategies` |
| Refactor sin cambiar comportamiento | `$reducing-entropy` |
| Cierre de trabajo | `$commit-work`, `$session-handoff` |

---

## 4. Skills por bloque del plan frontend

### Bloque 1 — Sistema de diseño y tokens
Mejoras: `F-01`, `F-02`, `F-03`

**Skills recomendadas:**
- `$stitch-loop` → si primero iteras visualmente tokens y consistencia
- `$web-design-guidelines` → semántica visual, contraste, jerarquía
- `$vercel-react-best-practices` → implementación limpia de componentes y theme helpers
- `$reducing-entropy` → evitar tokens duplicados en Tailwind, CSS y componentes

**Prompt base:**
```text
Implementa la mejora F-01/F-02/F-03 del plan frontend de Hipo.

Usa:
1. $web-design-guidelines para validar semántica visual y accesibilidad
2. $vercel-react-best-practices para implementar tokens/componentes sin anti-patterns
3. $reducing-entropy para centralizar estilos y evitar duplicación
4. $commit-work al final
```

---

### Bloque 2 — Componentes core del chat
Mejoras: `F-04`, `F-05`, `F-06`, `F-07`

**Skills recomendadas:**
- `$vercel-react-best-practices`
- `$next-best-practices`
- `$systematic-debugging` si el evento WebSocket o el estado visual no cuadra
- `$web-design-guidelines` solo para acabado visual del badge/banner

**Prompt base:**
```text
Implementa la mejora F-04/F-05/F-06/F-07 del plan frontend de Hipo.

Usa:
1. $next-best-practices para ubicar bien componentes client/server
2. $vercel-react-best-practices para estado, props, composición y rendimiento
3. $systematic-debugging si hay desalineación entre eventos WebSocket y UI
4. $commit-work al final
```

---

### Bloque 3 — UX del flujo de triaje
Mejoras: `F-08`, `F-09`, `F-10`, `F-11`

**Skills recomendadas:**
- `$stitch-loop` → para iterar pantallas nuevas como onboarding o resultado
- `$web-design-guidelines`
- `$vercel-react-best-practices`
- `$systematic-debugging` → para timeout warning y flujos reales de sesión

**Prompt base:**
```text
Implementa la mejora F-08/F-09/F-10/F-11 del plan frontend de Hipo.

Usa:
1. $stitch-loop si hace falta iterar la pantalla o estructura de UI
2. $web-design-guidelines para claridad visual en entorno médico
3. $vercel-react-best-practices para implementar el componente final
4. $systematic-debugging si el flujo depende del estado WebSocket o timeout
5. $commit-work al final
```

---

### Bloque 4 — Accesibilidad
Mejoras: `F-12`, `F-13`, `F-14`

**Skills recomendadas:**
- `$web-design-guidelines`
- `$vercel-react-best-practices`
- `$systematic-debugging` si accesibilidad y comportamiento chocan

**Prompt base:**
```text
Implementa la mejora F-12/F-13/F-14 del plan frontend de Hipo.

Usa:
1. $web-design-guidelines para contraste, foco, jerarquía y accesibilidad
2. $vercel-react-best-practices para aplicarlo bien en React
3. $systematic-debugging si aparece una regresión de interacción o navegación
4. $commit-work al final
```

---

### Bloque 5 — Rendimiento Next.js
Mejoras: `F-15`, `F-16`, `F-17`, `F-18`

**Skills recomendadas:**
- `$next-best-practices`
- `$vercel-react-best-practices`
- `$next-cache-components` → si el problema entra en render/caché/server-client boundaries
- `$reducing-entropy`

**Prompt base:**
```text
Implementa la mejora F-15/F-16/F-17/F-18 del plan frontend de Hipo.

Usa:
1. $next-best-practices para estructura y decisiones de Next.js
2. $vercel-react-best-practices para rendimiento de componentes
3. $next-cache-components si aplica separación server/client o estrategias de caché/render
4. $reducing-entropy para evitar complejidad accidental
5. $commit-work al final
```

---

### Bloque 6 — PWA y offline
Mejoras: `F-19`, `F-20`, `F-21`

**Skills recomendadas:**
- `$next-best-practices`
- `$vercel-react-best-practices`
- `$systematic-debugging` → para SW, manifest y estados offline raros

**Prompt base:**
```text
Implementa la mejora F-19/F-20/F-21 del plan frontend de Hipo.

Usa:
1. $next-best-practices para integrar bien PWA/offline en Next.js
2. $vercel-react-best-practices para los componentes y estados de UI
3. $systematic-debugging si el service worker o el modo offline falla
4. $commit-work al final
```

---

### Bloque 7 — Buenas prácticas Next.js
Mejoras: `F-22`, `F-23`, `F-24`, `F-25`, `F-26`

**Skills recomendadas:**
- `$next-best-practices`
- `$vercel-react-best-practices`
- `$reducing-entropy`
- `$systematic-debugging`

**Prompt base:**
```text
Implementa la mejora F-22/F-23/F-24/F-25/F-26 del plan frontend de Hipo.

Usa:
1. $next-best-practices para arquitectura App Router y separación server/client
2. $vercel-react-best-practices para formularios, estado, errores y testing de componentes
3. $reducing-entropy para mantener la base de código limpia
4. $systematic-debugging si hay comportamientos raros
5. $commit-work al final
```

---

## 5. Skills recomendadas por mejora

### 🔴 Críticas
- `F-01 Design tokens globales` → `$web-design-guidelines`, `$vercel-react-best-practices`, `$reducing-entropy`
- `F-04 ChatBubble con source indicator` → `$vercel-react-best-practices`, `$next-best-practices`
- `F-05 TriageLevelIndicator persistente` → `$vercel-react-best-practices`, `$systematic-debugging`
- `F-06 EmergencyBanner` → `$vercel-react-best-practices`, `$web-design-guidelines`
- `F-09 Pantalla de resultado` → `$stitch-loop`, `$web-design-guidelines`, `$vercel-react-best-practices`
- `F-11 Session timeout warning` → `$vercel-react-best-practices`, `$systematic-debugging`
- `F-12 Contraste y touch targets` → `$web-design-guidelines`, `$vercel-react-best-practices`

### 🟡 Importantes
- `F-02 Tipografía accesible` → `$web-design-guidelines`, `$vercel-react-best-practices`
- `F-07 TypingIndicator + estados WS` → `$vercel-react-best-practices`, `$systematic-debugging`
- `F-08 ChatInput con keyword detection` → `$vercel-react-best-practices`
- `F-10 Onboarding 3 pasos` → `$stitch-loop`, `$web-design-guidelines`, `$vercel-react-best-practices`
- `F-13 ARIA y navegación por teclado` → `$web-design-guidelines`, `$vercel-react-best-practices`
- `F-15 Code splitting del chat` → `$next-best-practices`, `$vercel-react-best-practices`
- `F-17 Optimización de imágenes` → `$next-best-practices`
- `F-19 Service Worker next-pwa` → `$next-best-practices`, `$systematic-debugging`
- `F-20 Banner modo offline` → `$vercel-react-best-practices`
- `F-21 Manifest.json` → `$next-best-practices`
- `F-22 Server vs Client Components` → `$next-best-practices`, `$next-cache-components`
- `F-23 Error boundaries` → `$vercel-react-best-practices`, `$next-best-practices`
- `F-24 Estado global Zustand` → `$vercel-react-best-practices`, `$reducing-entropy`
- `F-25 RHF + Zod` → `$vercel-react-best-practices`

### ⚪ Mejora
- `F-03 Modo oscuro` → `$web-design-guidelines`, `$vercel-react-best-practices`
- `F-14 Reducción de movimiento` → `$web-design-guidelines`
- `F-16 Virtualización de mensajes` → `$vercel-react-best-practices`, `$next-best-practices`
- `F-18 Web Vitals custom` → `$next-best-practices`
- `F-26 Testing` → `$vercel-react-best-practices`, `$systematic-debugging`

---

## 6. Prompts listos para pegar en Codex

### Prompt listo — F-04 ChatBubble con source indicator
```text
Implementa la mejora F-04 del plan frontend de Hipo: ChatBubble con source indicator.

Contexto:
- proyecto en Next.js + React + TypeScript
- el backend ya devuelve response_source: expert | llm | hybrid
- el componente debe ser limpio, reutilizable, accesible y no romper el chat actual

Usa este flujo:
1. $next-best-practices revisa dónde debe vivir el componente y su relación con App Router
2. $vercel-react-best-practices implementa el componente, props, composición y render correcto
3. $reducing-entropy evita duplicar estilos/lógica con otros componentes del chat
4. $systematic-debugging revisa edge cases de source vacío, confidence baja y triageLevel opcional
5. $commit-work genera commits claros al final

Implementa solo esta mejora y valida que no rompes el flujo del chat.
```

### Prompt listo — F-11 Session timeout warning
```text
Implementa la mejora F-11 del plan frontend de Hipo: Session timeout warning.

Contexto:
- la UI debe reaccionar al evento session_warning del WebSocket
- el warning debe ser claro, accesible y no intrusivo
- no cambies backend ni otros flujos no relacionados

Usa este flujo:
1. $next-best-practices revisa dónde integrar el listener del evento WS en la app
2. $vercel-react-best-practices implementa el componente y el estado asociado
3. $systematic-debugging valida timers, re-render, reconexión y cierre de sesión
4. $reducing-entropy evita meter lógica duplicada de estado en varios componentes
5. $commit-work genera commits claros al final
```

### Prompt listo — F-22 Server vs Client Components
```text
Implementa la mejora F-22 del plan frontend de Hipo: separar correctamente Server Components y Client Components.

Contexto:
- el proyecto usa Next.js App Router
- el chat y WebSocket requieren client components
- el resto debe moverse a server components siempre que no necesite estado o APIs del navegador

Usa este flujo:
1. $next-best-practices propone la estructura correcta
2. $next-cache-components revisa implicaciones de render, caché y boundaries
3. $vercel-react-best-practices implementa la separación sin anti-patterns
4. $reducing-entropy limpia imports, props y estructura
5. $commit-work genera commits claros al final
```

---

## 7. Reglas prácticas para no liarte

- Usa `$stitch-loop` solo para pantallas nuevas o iteración visual, no para resolver estado, sockets o arquitectura.
- Usa `$web-design-guidelines` cuando el problema sea de claridad visual, accesibilidad, contraste, jerarquía o consistencia.
- Usa `$next-best-practices` cuando la tarea toque App Router, server/client components, imports dinámicos, PWA o estructura.
- Usa `$vercel-react-best-practices` casi siempre que vayas a tocar componentes, hooks, props, estado o rendimiento React.
- Usa `$systematic-debugging` antes de parchear un bug raro de WebSocket, hydration, render o timeouts.
- Usa `$reducing-entropy` cuando Codex empiece a meter lógica repetida o componentes demasiado acoplados.
- Cierra cada bloque importante con `$commit-work`.
- Si dejas trabajo a medias, termina con `$session-handoff`.

---

## 8. Orden recomendado de ejecución con skills

### Primer bloque ideal
1. `F-01 Design tokens globales`
2. `F-12 Contraste y touch targets`
3. `F-04 ChatBubble con source indicator`
4. `F-05 TriageLevelIndicator`
5. `F-06 EmergencyBanner`
6. `F-11 Session timeout warning`

### Segundo bloque
7. `F-07 TypingIndicator + estados WS`
8. `F-22 Server vs Client Components`
9. `F-24 Estado global Zustand`
10. `F-23 Error boundaries`

### Tercer bloque
11. `F-09 Pantalla de resultado`
12. `F-10 Onboarding`
13. `F-15 Code splitting`
14. `F-17 Optimización de imágenes`

---

## 9. Prompt maestro reutilizable para cualquier mejora frontend

```text
Implementa la mejora F-XX del plan frontend de Hipo.

Contexto:
- proyecto en Next.js + React + TypeScript + Tailwind
- interfaz médica móvil con WebSocket y requisitos de accesibilidad
- no rehagas partes no relacionadas
- mantén responsive, accesibilidad y consistencia visual

Flujo obligatorio:
1. $next-best-practices revisa la integración en Next.js
2. $vercel-react-best-practices implementa la solución con buenas prácticas React
3. $web-design-guidelines úsala solo si la mejora afecta UX/UI, jerarquía visual o accesibilidad
4. $stitch-loop úsala solo si hace falta iterar una pantalla o componente visual nuevo
5. $reducing-entropy limpia duplicaciones y acoplamientos innecesarios
6. $systematic-debugging valida edge cases si aparece comportamiento raro
7. $commit-work genera commits claros al final

Al terminar:
- explica qué archivos cambiaste
- qué decisiones tomaste
- qué comprobaste
- qué queda pendiente si algo no se pudo verificar
```
