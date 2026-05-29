# Pi Cockpit UX — overhaul de la TUI para Pi 2.5+net

Diseño y plan de implementación de la nueva capa de UX para Pi 2.5+net. El
objetivo es que un developer pueda usar Pi como CLI principal sin
memorizar slash commands, vocabulario de roles, ni tipos de mensaje:
todo lo opera desde una TUI con info en vivo dentro de la terminal.

> Alcance estricto: **todo el código vive en `cortex-pi/`**. Sin cambios
> al backend Python ni al adapter. La docs es la única excepción y vive
> acá.

---

## 1. Por qué este overhaul

La explicación previa de cómo usar Pi 2.5+net dejaba 8 fricciones
concretas (ver `docs/multi-ide-mcp-hardening/PI-2.5-NET-UPGRADE.md` y
las decisiones de diseño en el chat de implementación):

1. Decisión multi-terminal upfront sin información para tomarla.
2. Hub rechaza envíos a peers ausentes — restricción dura.
3. Vocabulario doble (agent name vs role name vs slash command).
4. `/system` ciego, sin contexto del estado actual.
5. Auto-reply implícita contraintuitiva.
6. Estado de sesión / peers / tráfico invisible.
7. 5 tipos de mensaje × 7 roles = 35 combinaciones a recordar.
8. Cierre manual fácil de olvidar.

La solución elegida: **una TUI que muestra estado en vivo y dispara
acciones directamente** (sin agent intermediario que sugiera comandos).
El estado es calculado, no predicho; las acciones son determinísticas;
cero tokens para navegación.

## 2. Arquitectura

Cinco extensiones TS + un singleton compartido, todas dentro de
`cortex-pi/.pi/extensions/`. Cada extension se puede activar o
desactivar de forma independiente vía `settings.json`.

```
┌──────────────────────────── Pi process (cada terminal) ────────────────────────────┐
│                                                                                    │
│  ┌── cortex-net.ts (extendida en F3) ────────────────────────────────────┐         │
│  │   Hub + clients + nuevas: status pings, broadcast, peer events        │         │
│  │   Escribe estado al singleton (peers, myRole, isMaster, sessionId)    │         │
│  └────┬──────────────────────────────────────────────────────────────────┘         │
│       │                                                                            │
│  ┌────▼── _cortex-state.ts (singleton) ────────────────────────────────────┐       │
│  │   Estado central: sessionId, myRole, isMaster, peers, suggestion        │       │
│  │   Pub/sub: subscribers se notifican cuando cambia el estado             │       │
│  └────┬──────────────────────────────────────────────────────────────────┘         │
│       │                                                                            │
│  ┌────▼── cortex-cockpit.ts (F1) ────────────────────────────────────────┐         │
│  │   setWidget("cortex-cockpit", ...) persistente arriba                  │         │
│  │   setStatus("cortex-session" / "cortex-role" / "cortex-peers")         │         │
│  │   Suscriptor del singleton; re-renderiza cuando cambia                 │         │
│  └────────────────────────────────────────────────────────────────────────┘        │
│                                                                                    │
│  ┌── cortex-autopilot.ts (F2) ───────────────────────────────────────────┐         │
│  │   on("tool_call") — gates de gobernanza                                │         │
│  │   on("input") — hotkeys virtuales (:n, :t, :d, ...)                    │         │
│  │   on("before_agent_start") — hints                                     │         │
│  │   on("session_shutdown") — confirmación de cierre + cleanup            │         │
│  └────────────────────────────────────────────────────────────────────────┘        │
│                                                                                    │
│  ┌── cortex-panel.ts (F4) ───────────────────────────────────────────────┐         │
│  │   /cortex command → ctx.ui.custom() con Component grande               │         │
│  │   Vista MASTER (acciones completas) vs WORKER (limitada)               │         │
│  │   Sub-paneles: mandar mensaje, transcript, audit log                   │         │
│  └────────────────────────────────────────────────────────────────────────┘        │
│                                                                                    │
│  ┌── cortex-team.ts (F5) ────────────────────────────────────────────────┐         │
│  │   Auto-spawn de terminales cross-OS (wt.exe / tmux / clipboard)       │         │
│  │   Tracking en .pi/agent-sessions/team.json                             │         │
│  │   Coordinated shutdown via flag                                        │         │
│  └────────────────────────────────────────────────────────────────────────┘        │
└────────────────────────────────────────────────────────────────────────────────────┘
```

## 3. Decisiones de diseño cerradas

| Decisión | Elección | Justificación |
|---|---|---|
| Modo principal de uso | **Multi-terminal** | El usuario explicitó que Pi 2.5+net usa la red como modo default. |
| Quién decide acciones | **TUI calculada**, no LLM | Determinístico, sin tokens, sin latencia de inferencia. |
| Vista en hijas vs master | **B — diferenciada** | Master tiene panel completo; workers tienen vista limitada (sin "cerrar sesión", sin "agregar peers"). |
| Hotkeys virtuales | **Prefijo `:`** | `:n`, `:t`, `:d` etc. — el `:` evita chocar con texto natural. |
| Nombre del panel | **`/cortex`** | Punto único de entrada. Aliases (`/cortex-net`, `/cortex-mode`, `/cortex-role`) quedan por compat. |
| Auto-spawn portable | **Universal + fallback clipboard** | wt.exe en Windows, tmux/alacritty/gnome-terminal/iTerm en *nix, clipboard fallback siempre. |
| Composición del panel | **Un Component custom por panel** | API de Pi no documenta focus routing entre sub-componentes; codeamos focus state interno. |
| Estado compartido | **Singleton `_cortex-state.ts`** | Un solo dueño del estado, pub/sub a múltiples extensiones suscriptoras. |
| Backend Cortex | **No se toca** | Todo lo necesario ya vive en `.cortex/session.lock`, MCP tools existentes, y SessionStorage en disco. |

## 4. Plan de fases

| Fase | Pieza | Estado | Esfuerzo |
|---|---|---|---|
| **F1** | Singleton + Cockpit widget read-only | ✅ completa | bajo |
| **F2** | Autopilot (gates + hotkeys virtuales) | ✅ completa | bajo |
| **F3** | Bonus cortex-net (status pings, broadcast, events) | ✅ completa | bajo |
| **F4** | Panel `/cortex` on-demand | ✅ completa | medio |
| **F5** | `/cortex-team` auto-spawn portable | ✅ completa | medio |

Cada fase tiene su doc dedicada en este directorio (`F1.md`...`F5.md`).

## 4.1. UX integrada final

Para un usuario nuevo del proyecto, el flujo cotidiano queda así:

1. **Arrancar Pi en master**: `just cortex` en una terminal del proyecto.
2. **Cockpit aparece arriba** con estado standby + status bar abajo con
   "⬡ standby". Autopilot notifica `:?` para ver hotkeys.
3. **Tipear la tarea** en el chat. Pi activa `cortex-sync` por default.
   El cockpit lo muestra como "sync (B' anchor — fuera de la red)".
4. **Sync emite proposal + spec**. La sesión se abre. El cockpit pasa a
   mostrar `2026-05-28_login · sync · MASTER`.
5. **Cambiar al medio**: `/system cortex-SDDwork`. El cockpit refresca:
   `sddwork · MASTER · 0 peers`.
6. **Abrir el team multi-terminal**: `/cortex-team` (o hotkey `:t`).
   SelectList con presets. Elegir "Deep Track full". 3 terminales se
   abren con designer / implementer / documenter. Los peers aparecen
   en el cockpit en vivo (push events de F3).
7. **Coordinar in-flight**: `/cortex` abre el panel. Elegir "Mandar
   mensaje a un peer" → SelectList con destinatario, tipo, mensaje.
8. **Cerrar**: `/system cortex-documenter` (o navegar el panel a
   "Cambiar a documenter"). El documenter llama briefing + transcript
   y cierra con `cortex_close_session`. El cockpit vuelve a standby.

Cero comandos memorizados. Toda la interacción es navegación visual o
hotkeys de 2 caracteres.

## 5. Primitivas Pi confirmadas

Antes de codear, validamos las primitivas con búsqueda dirigida al
repo `badlogic/pi-mono`. Resultados:

- **`ctx.ui.setWidget(id, render, {placement})`** — widget persistente
  arriba (`aboveEditor`) o abajo (`belowEditor`) del editor.
  Read-only en la práctica (no captura input).
- **`ctx.ui.setStatus(key, text?)`** — múltiples keys coexisten en el
  footer. Cada key se actualiza independiente.
- **`ctx.ui.custom<T>(callback, options?)`** — TUI modal grande. El
  callback recibe `(tui, theme, keybindings, done)` y devuelve un
  `Component`. `options.overlay` y `KeybindingsManager` disponibles.
- **`pi.on("input", handler)`** — intercepta input del usuario antes
  del agent. Puede retornar `{action: "transform"|"handled"|"continue"}`.
  Es la herramienta clave para hotkeys virtuales y gates.
- **`pi.on("tool_call", handler)`** — intercepta tool calls.
- 27 eventos documentados en total (session, agent, turn, message,
  tool, provider, context, etc.).

Sources clave: `badlogic/pi-mono/packages/coding-agent/docs/{extensions,tui}.md`,
ejemplos en `examples/extensions/`, repo npm `@mariozechner/pi-coding-agent`.

## 6. Gaps conocidos (no bloqueantes)

- **Focus routing entre sub-componentes interactivos en un Container**:
  no documentado. Workaround: cada sub-panel es un Component custom con
  focus state propio.
- **Widgets persistentes no reciben keyboard**: el editor captura todo.
  Workaround: hotkeys virtuales via `pi.on("input")`.
- **`overlay: true` en `ctx.ui.custom`**: comportamiento exacto no
  validado, lo confirmamos al implementar F4.

## 7. Convenciones del código

- **Naming**: archivos prefijados con `cortex-` para alinearse con las
  extensiones existentes. El singleton interno usa `_` al inicio
  (`_cortex-state.ts`) por convención **pero el autoloader de Pi lo
  carga igual** — por eso el módulo exporta un `default function`
  no-op al final. Ver §8.
- **Imports**: tipos desde `@mariozechner/pi-coding-agent` y
  `@mariozechner/pi-tui`. Imports relativos entre extensiones del
  bundle (`./_cortex-state`) los resuelve bun/jiti al cargar.
- **Estado mutable**: solo dentro del singleton. Las extensiones leen
  y escriben pero NO duplican estado en closures.
- **Idempotencia**: registros, suscripciones y setIntervals limpiables
  en `session_shutdown`.
- **Best-effort**: errores de IO (lock file ausente, hub caído, etc.)
  no rompen el lifecycle de Pi. Log debug + degrade UX.

## 8. Descubrimientos runtime

Cosas que **no estaban documentadas** en el API de Pi y aprendimos al
ejecutar el bundle en un adopter real:

- **Prefijo `_` NO evita autoload**. Pi escanea todos los `.ts` de
  `.pi/extensions/` independiente del nombre. Cada uno debe exportar
  una factory `default function (pi: ExtensionAPI) {...}` o falla con
  `Extension does not export a valid factory function`. Solución
  aplicada: `_cortex-state.ts` exporta un default no-op que satisface
  el contrato sin registrar nada.
- **Pi crashea con uncaughtException si un widget renderiza una línea
  que excede el width de la terminal** (`Rendered line N exceeds
  terminal width (W > T)`). La doc menciona `visibleWidth()` y
  `truncateToWidth()` de `@mariozechner/pi-tui` para esto, pero los
  ejemplos no las usan en `setWidget`. Solución aplicada: ambos
  widgets (cockpit + panel) mapean cada línea con `truncateToWidth`
  al final del render. Aplicado para terminales chicas (≤80 cols).
- **`session.lock` aparece DESPUÉS de `session_start`** en el flujo
  típico. Pi arranca con el default agent (cortex-sync), el usuario
  escribe la tarea, sync llama `cortex_create_spec` y recién ahí el
  backend MCP escribe el lock. Si cortex-net solo escucha
  `session_start`, nunca levanta el hub. Solución aplicada:
  `cortex-net.ts` extrae la lógica de init a `tryInitNetwork(ctx)` y
  la llama desde (a) `session_start` para el camino feliz, (b) un
  `subscribe` al singleton cuando otra extensión actualiza
  `sessionId`, (c) el polling de respaldo cada 15s. El primer trigger
  que detecte el lock dispara el setup (idempotente vía guards
  `hub !== null || client !== null`).
- **Cockpit MASTER/WORKER es ambiguo cuando no estás en la red**.
  Si `myRole === null` (sync activo o lock todavía no detectado por
  cortex-net), mostrar "STANDBY" en vez de "WORKER" para no confundir
  al usuario. Aplicado al render del cockpit y a los guards de
  `/cortex-team`.
- **Pi v0.77 NO dispara `before_agent_start` con `event.agentName`
  cuando el "agent persona" lo gestiona `system-select.ts`**. El
  hook se dispara pero `event.agentName` está `undefined`, por lo
  que cortex-cockpit / cortex-net nunca se enteran de qué agent
  está activo. Solución aplicada: `system-select.ts` escribe al
  singleton `cortexState.activeAgentName` y `myRole` cada vez que
  el usuario elige un agent (o vuelve a "ninguno"). El subscriber
  del singleton de cortex-net detecta el cambio de `myRole` y
  llama `ensureRegisteredAs` automáticamente. Sin esto, podés
  elegir cortex-SDDwork por `/system` pero el cockpit lo muestra
  como STANDBY y `/cortex-team` rechaza por "no estás registrado".
- **`cortexState.cwd` puede estar null cuando se invoca un slash
  command** aunque session_start del cockpit lo seteó. Causa raíz
  no clara (posible doble carga del módulo singleton por el
  autoloader de Pi + import relativo, o algún reset transitorio).
  Solución defensiva: `/cortex-team` (y `/cortex-team-status`)
  usan `cortexState.cwd ?? ctx.cwd` como fuente. Cockpit re-puebla
  cwd desde `ctx.cwd` en `turn_end` si está vacío.
- **Windows: Node.js no soporta Unix domain sockets en archivos
  `.sock`**. `listen()` falla con `EACCES: permission denied` sobre
  cualquier path que termine en `.sock`. Solución aplicada:
  cortex-net detecta `process.platform === "win32"` y usa
  **Windows Named Pipes** (`\\.\pipe\cortex-net-...`) en lugar de
  archivos. Se hashea el cwd con djb2 para que workspaces distintos
  no colisionen en el namespace global de pipes. También se
  skippean los `existsSync`/`rmSync` sobre paths de socket en
  Windows (los pipes son auto-cleanup al cierre del proceso).
  Linux/macOS siguen usando Unix domain sockets.
- **CRÍTICO: el singleton DEBE anclarse a `globalThis`**, NO
  guardarse en module-level scope. Pi v0.77 (bun/jiti) evalúa cada
  módulo importado **una vez por extension que lo importa** — el
  cache de módulos no funciona como el `require.cache` de Node.js
  estándar. Resultado: N copias del state, una por extension.
  Síntoma exacto: cortex-net dice "registrado como sddwork (hub)"
  pero cortex-cockpit muestra "STANDBY · agent: (ninguno)". Mover
  el archivo a `.pi/lib/` eliminó UNA fuente de duplicación (el
  autoload de `.pi/extensions/`) pero NO la del sandboxing del
  loader. Solución definitiva aplicada en `lib/cortex-state.ts`:
  el state, subscribers y lastUpdate viven en
  `globalThis["__cortex_pi_state_v1__"]`. Cada evaluación del
  módulo lo encuentra ya inicializado y refiere al mismo objeto.
  Patrón conocido como "global singleton" o "process-wide cache".
- **Pi v0.77 trata el prefijo `:` como bash** (similar a `!`). Los
  hotkeys virtuales `:n`, `:t`, `:d`, etc. quedan interpretados
  como comandos shell y fallan con
  `/usr/bin/bash: line 1: :? command not found`. Solución
  aplicada: reemplazados por slash commands cortos `/cx-next`,
  `/cx-team`, `/cx-role`, `/cx-mode`, `/cx-help`. Pi los enruta
  garantizado al handler registrado.

Si encontrás más, agregalas acá.
