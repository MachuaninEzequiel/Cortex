# 14 — HERDR COMPANION (Obra 08, stream B)

> Estado: RESUELTO por obra 08 stream B (2026-08-28) — G-B1…G-B6 PASS, ver specs/planes/ledgers. Original: ESPECIFICACIÓN aprobada por el dueño (2026-08-27).
> Obra 08 = dos streams: A (`13-MODO-COMPOSED-Y-SKILLS-EXPERTAS.md`) + B (este doc).
> Aditivo: cortex funciona exactamente igual sin `cortex-companion` y sin herdr.
> Regla rectora: **agregar, casi nunca cambiar**.

## 0. Por qué y para qué

Cortex tiene muchas piezas útiles (27 familias de comandos, TUI, MCP,
brain, Action Engine) pero **están dispersas**: el dev no recuerda que
existen ni para qué sirve cada una. El objetivo de esta obra es un
**Cortex Companion**: una superficie única, siempre visible, **mouse-first**,
agnóstica al dev, donde el agente local (con conocimiento preciso de Cortex
y del proyecto) ayuda en cada cosa — sin que el dev necesite acordarse de
cómo funciona cada parte.

Forma elegida por el dueño: **plugin para herdr** (terminal workspace
manager "mouse-first TUI", v0.8.2 instalada y verificada en la máquina del
dueño) + **binario nuevo `cortex-companion`** que también corre standalone
(agnóstico: tmux, kitty, terminal pelada).

NO es el Companion Engine P13 (`11-COMPANION-ENGINE-P13.md`): ese es
offload de cómputo a un mini-PC por LAN. Este doc es UI local first. P13
aporta piezas reutilizables a futuro (`/brain/chat` SSE, patrones), pero no
es prerequisito.

## 1. Datos verificados de herdr (2026-08-27)

- **herdr 0.8.2 instalada** en `~/.local/bin/herdr`, server/cliente activos
  (sockets en `~/.config/herdr/`), integración con Claude Code vía hook
  (`herdr-agent-state.sh`). "Terminal based agent runtime for coding
  agents", **mouse-first TUI**.
- **Plugins** (docs oficiales 0.8.2, verificadas): directorio con manifest
  `herdr-plugin.toml` + comandos argv (cualquier lenguaje — incluido un
  binario Rust). Toda la CLI de herdr es la API del plugin
  (`HERDR_BIN_PATH`). Plugin v1: acciones, eventos, panes y link handlers
  declarativos; SIN UI no-terminal nativa ni registro runtime de acciones.
- Manifest: `id`, `name`, `version`, `min_herdr_version` obligatorios;
  `[[build]]`, `[[startup]]`, `[[actions]]` (id/title/contexts/command),
  `[[events]]` (on/command), `[[panes]]` (id/title/placement/command),
  `[[link_handlers]]`.
- `herdr plugin link <path>` (local) / `install owner/repo` (GitHub).
- `herdr plugin action list|invoke`; `herdr plugin pane open --placement
  overlay|split|tab|zoomed`.
- herdr detecta estados de agentes (idle/working/blocked) por pane e
  integra Claude Code, Pi, OpenCode, Codex, Cursor y otros — el ecosistema
  de agentes del dueño está cubierto.

## 2. Arquitectura

### 2.1 Crate nuevo `cortex-companion` (bin + lib)

```
rust/crates/cortex-companion/
  src/
    lib.rs          — tipos compartidos (UiRequest, Screen, eventos)
    app.rs          — máquina ELM-lite (state / action / effect / update)
    engine.rs       — trait Backend + impl InProcess (servicios nativos)
    approval.rs     — flujo de aprobación de mutaciones + auditoría
    brain_panel.rs  — chat con el brain (router determinista + LLM opcional)
    menu.rs         — catálogo de capacidades (anti-olvido)
    widgets.rs      — panel/lista/button mínimos (mouse-first)
    bin/companion.rs — entrypoint
```

**Decisión: sin dependencia de `cortex-tui`.** El TUI actual está en WIP
activo (P8d/TUI, árbol sucio) y sus snapshots están gateados. El Companion
duplica widgets mínimos (~200 LOC) y reusa solo `cortex-branding` +
servicios. Refactor a reuso cuando el TUI se estabilice (post-cierre,
fuera de alcance). Scopes disjuntos garantizados con el WIP.

Deps: ratatui + crossterm ya en el workspace. **Cero deps nuevas.**

### 2.2 Backend in-process (no MCP, no subprocess)

El Companion inyecta los **mismos servicios que usa el CLI** (patrón ya
establecido por cortex-tui): `SessionService`, motor de búsqueda híbrida
(`cortex-app::context`), `cortex-actions` (scheduler/runner), `cortex-doctor`
checks, `cortex-config`. Salida byte-idéntica al CLI **por construcción**
(mismo código). El `Backend` trait deja la costura para un futuro backend
MCP/remoto (P13) sin tocar la UI (fase 2, fuera de alcance).

**Enrutamiento de tools del brain**: el brain como librería hoy delega sus
tools al CLI por subprocess (`run_cli`). En el Companion, las tools del brain
se enrutan por el engine in-process con un **mapa 1:1** (memory.search →
search engine, session.current → SessionService, actions.propose →
scheduler, cortex.health → doctor, vault.stats → stats). Tool sin mapping en
v1 ⇒ fallo explícito (P6/P9), nunca subprocess silencioso. Esto elimina el
subprocess del brain dentro del Companion AUNQUE el brain binary standalone
siga usándolo (sin cambios ahí).

### 2.3 El agente local híbrido (decisión del dueño)

El brain entra **como librería** (`cortex-brain`: router determinista,
catálogo de tools, `LlmBackend` con `DeterministicBackend` default y
`LlamaChatBackend` opcional under feature `llama` — LFM2.5 GGUF local).

| Tier | Tools | Comportamiento |
|---|---|---|
| **Read** | search, context, session status, docs, health, next (propuestas) | ejecución **directa in-process, sin aprobación** |
| **Mutate** | session checkpoint/close/finish, remember, docs write, aprobar acción de `next` | el brain las **propone** (filosofía "propone, nunca muta" intacta); el Companion las muestra con botón **[Ejecutar]** → **modal de aprobación** (mouse) → ejecuta in-process → resultado visible |

Cada mutación aprobada queda **auditada** en `.cortex/action_log` (mismo
runner que `cortex next`). Denegada ⇒ no se ejecuta, sin excepción.

## 3. La interfaz (6 paneles, mouse-first)

| Panel | Contenido | Input primario |
|---|---|---|
| **Home** | proyecto, rama (HEAD), sesión activa o botón "abrir sesión", próxima acción sugerida por el Action Engine, doctor-lite, conteos de memoria | click |
| **Menu (sidebar)** | **anti-olvido**: 27 familias del CLI agrupadas por dominio (Sesiones, Memoria, Búsqueda, Docs, CI, Setup, Enterprise). Click → ejecuta el comando y muestra salida `--json` en panel. v1 = lista fija canónica (NO un shell) | click |
| **Sessions** | lista en vivo (filtro por status), detalle, tareas; cerrar con modal de aprobación | click |
| **Actions** | propuestas `cortex next --json` (score/costo/reversibilidad); aprobar por clic; lote auto-ok (reversible + instant) con un botón | click |
| **Search** | misma pipeline híbrida del CLI; feedback "útil" (y) por clic | click + teclado |
| **Brain** | chat con el agente local; respuestas con botón **[Ejecutar]** para mutaciones → modal de aprobación | click + teclado |

Interacción: **mouse-first** (ratatui+crossterm: clicks, rueda, hover);
teclado completo como accesibilidad (misma máquina de input, mapeo dual).
Presupuesto de render <50 ms (patrón del gate P10).

## 4. Plugin herdr (`integrations/herdr/` dentro del repo)

```toml
# integrations/herdr/herdr-plugin.toml
id = "cortex.companion"
name = "Cortex Companion"
version = "0.1.0"
min_herdr_version = "0.8.0"
description = "Companion de Cortex: sesiones, acciones, búsqueda y brain en un pane"
platforms = ["linux", "macos"]

[[panes]]
id = "companion"
title = "Cortex"
placement = "overlay"          # sticky sobre los panes del dev
command = ["cortex-companion"]

[[actions]]
id = "open"
title = "Open Cortex Companion"
contexts = ["workspace"]
command = ["herdr", "plugin", "pane", "open", "--plugin", "cortex.companion", "--entrypoint", "companion", "--placement", "overlay"]

[[actions]]
id = "next"
title = "Cortex: next actions"
contexts = ["workspace"]
command = ["cortex", "next", "--json"]

[[actions]]
id = "status"
title = "Cortex: session status"
contexts = ["workspace"]
command = ["cortex", "session", "current", "--json"]

[[actions]]
id = "doctor"
title = "Cortex: doctor"
contexts = ["workspace"]
command = ["cortex", "doctor"]

# NOTA: sin acción "search" en el manifest — herdr invoca acciones sin
# argumentos y `cortex search` exige query; la búsqueda vive en el panel
# Search del Companion (con input propio) y en el Menu.
```

- Instalación: `herdr plugin link <repo>/integrations/herdr` (local) o
  install desde GitHub. `INSTALL.md` documenta ambos + standalone.
- Sin herdr: `cortex-companion` corre solo en cualquier terminal.
- herdr reenvía eventos de mouse al pane que los pide; el Companion los usa
  como input primario. Si un pane overlay no entrega mouse en alguna
  versión de herdr, fallback `--placement split` (nada bloqueante).

## 5. Datos, errores, seguridad

- **Fuente de verdad intacta**: vault + `.cortex/` + `config.yaml`. El
  Companion no escribe nada que no pase por los mismos servicios del CLI ⇒
  gobernanza intacta (sync_ticket antes de create_spec, quality gates,
  action_log).
- **Sin sesión activa**: Home lo indica y ofrece botones (`setup agent`,
  abrir sesión) — el onboarding sale del olvido.
- **Fallo explícito (P6/P9)**: cualquier operación no ejecutable muestra
  mensaje con rc y sugerencia; nunca silencio, nunca paridad fingida.
- **Aprobaciones**: ninguna mutación se ejecuta sin clic explícito en el
  modal; el modal muestra el comando/efecto exacto; auditado en
  `action_log`.
- **Seguridad**: mismo modelo de confianza que el CLI (corre como el dev,
  nada remoto en v1, sin token, sin red). El plugin herdr es código que
  corre con los permisos del dev (modelo de confianza de herdr, documentado
  en INSTALL.md).
- **Doctor**: los checks `pm_companion_*` de P13 quedan fuera (ese addon es
  remoto); el Companion usa el doctor LOCAL existente tal cual.

## 6. Verificación (gates estilo Obra 07 — un gate por commit)

| Gate | Contenido | Criterio de pase |
|---|---|---|
| G-B1 | Scaffolding + backend in-process | `session list`, `search`, `next` desde el engine == salida del CLI subprocess (paridad por construcción, test explícito); RSS medido y documentado (objetivo ~15-25 MB) |
| G-B2 | Render Home + Menu (snapshots) + eventos de mouse simulados | click → acción esperada (crossterm events inyectados); presupuesto render <50 ms |
| G-B3 | Flujo de aprobación | mutación SIN aprobación: NO ejecuta (assert en action_log); CON aprobación: ejecuta y audita; denegación: no ejecuta |
| G-B4 | Brain híbrido | lectura directa sin modal; mutación propuesta → aprobar/denegar → comportamiento correcto; router determinista sin modelo (cero tokens) y con ScriptedBackend en CI (patrón brain existente) |
| G-B5 | Plugin herdr | `herdr plugin link` + `herdr plugin list` + `herdr plugin action list` OK contra el manifest real (validación del formato 0.8.x); pane open probado en sesión herdr real del dueño (manual, scripta en INSTALL.md) |
| G-B6 | Docs | INSTALL.md (herdr + standalone) + ESTADO-ACTUAL/HANDOFF/14 resuelto |

Cierre de paquete (convención del repo): metadatos, red/green de tests,
gates PASS, oráculo intacto, cold start N=20, revisión Approved, registro.

## 7. Estimación y archivos tocados

~2.500–3.500 LOC Rust (crate nuevo) + manifest + gates. Cero deps nuevas
(ratatui, crossterm ya presentes; cortex-brain como lib ya existe).

| Ámbito | Archivos |
|---|---|
| Crate nuevo | `rust/crates/cortex-companion/` (app, engine, approval, brain_panel, menu, widgets, bin) |
| Workspace | `rust/Cargo.toml` (member nuevo — append-only, validar cargo metadata) |
| Plugin | `integrations/herdr/herdr-plugin.toml` + `INSTALL.md` |
| Docs | `docs/transformacion/ESTADO-ACTUAL.md`, `HANDOFF.md`, este doc |

## 8. Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| API de plugins herdr joven (0.8.x) | panes overlay/split/tab + actions declarativas cubren el caso v1; validación temprana en G-B5; fallback placement |
| Duplicación de widgets vs cortex-tui | acotada (~200 LOC), refactor post-cierre del TUI |
| Scope creep del Menu | v1 lista fija canónica agrupada; NO shell |
| Brain en proceso carga memoria | medición honesta en G-B1; embeddings ONNX solo on-demand (lazy, patrón CliSearchAdapter) |
| Colisión con WIP P8d/TUI | scopes disjuntos: Companion no toca cortex-tui ni cortex-setup |
| herdr ausente en otra máquina | `cortex-companion` standalone; plugin es solo el adaptador |

## 9. Fase 2 (fuera de alcance, documentada)

1. Web Hub localhost (axum, patrón webgraph-server): la interfaz
   "definitiva" mouse-first en browser; reusa `serve_http` + `/brain/chat`
   SSE de P13.
2. Backend MCP/remoto del Companion (costura del trait `Backend`) — apuntar
   a un node P13 sin tocar la UI.
3. Brain 100% in-process (sin subprocess a CLI) — el Companion ya lo
   logra para sus tools (§2.2); el brain binary standalone queda para
   otra obra. Refactor ya anotado en el plan 08; prerequisito del chat
   contextual profundo.
4. Reuso de widgets de cortex-tui (post-estabilización).
5. `cortex overview` (one-pager) como parche de descubribilidad CLI.

## 10. Qué NO cambia

- El CLI, el TUI existente, el MCP server, el brain binary, los gates
  vigentes.
- Ningún contrato congelado (list_tools, goldens) se recaptura.
- El modelo de confianza (todo local, sin red en v1).
- La filosofía "propone, nunca muta" del brain (la aprobación vive en la
  superficie, no en el brain).