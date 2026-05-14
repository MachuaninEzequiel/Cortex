---
title: Fase 05 — Demos interactivos
doc_type: phase
phase: 5
status: pending
depends_on: [phase-04]
unlocks: [phase-06]
estimated_duration: 7 días-persona
---

# Fase 05 — Demos interactivos

## Objetivo

Construir la sección `#demos`: **3 demos navegables** que permiten al visitante experimentar Cortex sin instalar nada. Es la sección con **mayor riesgo técnico** y la que produce **mayor impacto en conversión**.

Los 3 demos:

1. **CLI Player** — replay tipográfico de una sesión real de `cortex save-session` + `cortex search`.
2. **WebGraph embebido** — visualización del knowledge graph de un proyecto real (snapshot).
3. **Autopilot Replay** — reproducción visual de una sesión Autopilot completa.

## Entregables

1. **Sección `#demos`** con tabs o segmented control para elegir demo.
2. **CLI Player** funcional con scripts grabados.
3. **WebGraph viewer embebido** con snapshot estático.
4. **Autopilot Replay** con timeline y events.
5. **Pipeline de actualización** de demos (snapshot WebGraph re-generado semanalmente).

## Tareas detalladas

### 5.1 Layout de la sección (0.5 día)

`src/sections/Demos.astro`:

- [ ] Eyebrow + H2 + body corto.
- [ ] **Segmented control** con 3 tabs: "CLI" · "WebGraph" · "Autopilot".
- [ ] Cada tab muestra un componente isla diferente.
- [ ] Indicador animado del tab activo.
- [ ] Persistencia del tab elegido en URL hash (`#demos-cli`, etc.).

### 5.2 CLI Player (2 días)

Decisión técnica: **Asciinema embedded** vs **Custom typewriter**.

| Criterio | Asciinema | Custom |
| --- | --- | --- |
| Fidelidad de terminal | Total | Aproximada |
| Bundle | ~30 KB | < 5 KB |
| Customización visual | Limitada | Total |
| Tiempo de desarrollo | Bajo | Medio |

**Decisión recomendada**: **Custom typewriter** para coherencia visual con el sistema de diseño + control total.

#### Componente `<TerminalPlayer>`

`src/components/islands/TerminalPlayer.tsx`:

```tsx
type Frame =
  | { type: 'type'; text: string; speedMs?: number }
  | { type: 'output'; text: string; delayMs?: number; color?: string }
  | { type: 'pause'; ms: number }
  | { type: 'clear' };

type Props = { frames: Frame[]; autoplay?: boolean; loop?: boolean };
```

Features:

- [ ] Renderiza terminal con `<pre>` mono, dark background, padding.
- [ ] Prompt: `$ ` en accent color.
- [ ] Cursor parpadeante mientras tipea.
- [ ] Highlighting de comandos (Shiki en SSR para syntax válido).
- [ ] Controles: Play/Pause, Restart, Speed (1x / 2x).
- [ ] Loop opcional al final.

#### Script del demo CLI

`src/data/demo-cli-script.ts`:

```ts
export const cliScript: Frame[] = [
  { type: 'type', text: 'cortex search "JWT refresh tokens"' },
  { type: 'pause', ms: 500 },
  { type: 'output', text: '🔍 Searching memory (local + enterprise)...\n', color: 'fg-muted' },
  { type: 'output', text: '\n[hit 1 · score 0.92 · local · 2026-04-15]\n', color: 'accent-primary' },
  { type: 'output', text: '  spec: Auth JWT — Refresh tokens implementation\n  → vault/specs/SPEC-042.md\n', color: 'fg-secondary' },
  { type: 'output', text: '\n[hit 2 · score 0.87 · enterprise · 2026-03-01]\n', color: 'accent-primary' },
  { type: 'output', text: '  decision: ADR-007 — Sliding window for token rotation\n  → vault-enterprise/decisions/ADR-007.md\n', color: 'fg-secondary' },
  { type: 'pause', ms: 1500 },
  { type: 'type', text: 'cortex create-spec --title "Add refresh token rotation"' },
  // ... continúa con save-session
];
```

#### Animación signature

- [ ] Typing delay con jitter realista (no constante).
- [ ] Cuando se "completa" un comando, fade-in del output bloque por bloque.
- [ ] Auto-scroll si el output supera el viewport del terminal.

### 5.3 WebGraph embebido (2 días)

#### Decisión: backend en vivo vs snapshot

**Decisión**: **Snapshot estático JSON** regenerado en build. Razón: no se requiere backend, performance previsible, demo siempre funciona.

#### Pipeline de snapshot

- [ ] Script `scripts/export-webgraph-snapshot.ts` que:
  1. Corre `cortex webgraph export --format json --output /tmp/snapshot.json` en un repo de ejemplo (puede ser el propio Cortex en su estado actual).
  2. Limpia datos sensibles (nombres reales de archivos, contenido).
  3. Reduce nodos a 30-50 para legibilidad.
  4. Guarda en `apps/landing/public/snapshots/webgraph.json`.
- [ ] Cron job mensual (GitHub Actions) que regenera el snapshot.

#### Componente `<WebGraphDemo>`

`src/components/islands/WebGraphDemo.tsx`:

Stack: **D3.js** para layout force-directed + React para UI.

Features:

- [ ] Carga `snapshot.json` lazy.
- [ ] Render con D3 force simulation (nodes + edges).
- [ ] Nodos coloreados por tipo (spec, decision, session, runbook, hu).
- [ ] Drag para mover nodos.
- [ ] Hover muestra label completo.
- [ ] Click expande info en panel lateral.
- [ ] **Filtros** (top bar):
  - Por tipo de documento (checkboxes).
  - Por scope (local/enterprise/all).
  - Por proyecto (dropdown).
- [ ] **Búsqueda**: input que filtra nodos por título.

#### Performance

- [ ] Limitar nodos visibles a ~50 con paginación o clustering en V1.
- [ ] Pausar simulación cuando la sección no está en viewport.
- [ ] WebWorker opcional para la simulación si V2 escala nodos.

#### Fallback

- [ ] Si el snapshot no carga, mostrar **screenshot estático** con caption.

### 5.4 Autopilot Replay (2 días)

#### Concepto

Reproducción visual de una sesión Autopilot real: el visitante ve cómo Autopilot detecta una tarea, enruta, ejecuta y cierra.

#### Componente `<AutopilotReplay>`

`src/components/islands/AutopilotReplay.tsx`:

- **Header**: nombre de la sesión, modo (assist/autopilot), duración total.
- **Timeline horizontal** con eventos discretos.
- **Panel inferior** que muestra el estado actual: detectores activos, política aplicada, archivos tocados.
- **Controles**: Play/Pause, Step forward, Step back, Speed.

#### Script del demo

`src/data/demo-autopilot-script.ts`:

```ts
export const autopilotScript: AutopilotEvent[] = [
  { t: 0, kind: 'start', label: 'cortex autopilot start --mode assist', desc: 'Sesión iniciada' },
  { t: 800, kind: 'detect', label: 'CodeChangeDetector', desc: 'task_type=feat, confidence=0.91' },
  { t: 1500, kind: 'detect', label: 'AmbiguousRequestDetector', desc: 'No ambiguity. Skipping.' },
  { t: 2200, kind: 'preflight', label: 'Pre-enrichment', desc: 'Loaded 8 memories, 2 specs related' },
  { t: 3500, kind: 'route', label: 'Deep Track selected', desc: 'Files: 4, Complexity: high' },
  { t: 5000, kind: 'subagent', label: 'cortex-code-explorer', desc: 'Investigating auth module' },
  { t: 8000, kind: 'checkpoint', label: 'Checkpoint #1', desc: 'Exploration complete' },
  // ...
  { t: 30000, kind: 'finish', label: 'Session note saved', desc: '/vault/sessions/2026-05-14-feat-auth.md' },
];
```

#### Visualización

- [ ] Cada evento es una "estación" en la timeline con su icono.
- [ ] Cuando el playhead alcanza un evento, se expande el panel inferior con detalle.
- [ ] Loop al final (con un segundo de pausa).

### 5.5 Pipeline de actualización (0.5 día)

`.github/workflows/snapshots.yml`:

- Trigger: cron mensual + manual.
- Acción: corre script que regenera `webgraph.json` y `cli-script.ts` (si aplica).
- PR automático con cambios.

## Criterios de aceptación

- ✅ Los 3 demos cargan sin errores.
- ✅ CLI Player tipea de forma natural y legible.
- ✅ WebGraph renderiza ≥ 30 nodos a 60fps.
- ✅ Autopilot Replay es comprensible en una sola pasada.
- ✅ Bundle total de las 3 islas < 150 KB gzipped.
- ✅ Lighthouse Performance se mantiene ≥ 90.

## Riesgos y mitigaciones

| Riesgo | Mitigación |
| --- | --- |
| D3 + React es overhead | Considerar `react-force-graph` o `vis-network` si tiempo apremia |
| Snapshot WebGraph queda obsoleto | Pipeline mensual + visual con timestamp "última actualización" |
| CLI Player aburrido visualmente | Agregar microanimación: "cursor blink", glow del comando ejecutado |
| Autopilot Replay difícil de entender | Test con 5 usuarios; si confunde, simplificar a 4-5 eventos máximo |

## Siguiente fase

→ [Fase 06 — Casos de uso](fase-06-casos-de-uso.md)
