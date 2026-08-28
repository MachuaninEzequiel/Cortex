# PROMPT — HANDOFF PARA OTRO AGENTE (Obra 08 completada)

> Este prompt es para un agente que retoma el repositorio con OTRA tarea.
> Su propósito: que el agente lea los planes de la Obra 08, sepa que **todo
> lo que esos planes describen ya está implementado, revisado y mergeado**,
> y tenga el contexto suficiente para NO rehacer nada y trabajar en lo
> nuevo con precisión.

---

## Contexto que debe saber el agente

Estás trabajando en el repositorio Cortex (`/home/chucho/Cortex`), rama
`feature/transformacion-2026-08`. La **Obra 08** (dos streams: A = Modo
COMPOSED y skills expertas; B = Herdr Companion) está **COMPLETA**:

- **Leé estos planes como REFERENCIA de lo que se construyó** (NO como
  lista de tareas pendientes): `docs/transformacion/PLAN-OBRA08-STREAM-A.md`
  y `docs/transformacion/PLAN-OBRA08-STREAM-B.md`.
- **Specs (autoridad de diseño)**: `docs/transformacion/13-MODO-COMPOSED-Y-SKILLS-EXPERTAS.md`
  y `docs/transformacion/14-HERDR-COMPANION.md` — ambas marcadas RESUELTO.
- **TODOS los pasos/checkboxes de los planes están cumplidos.** Cada task
  (A1–A13 y B1–B10) fue implementada con TDD, revisada por un revisor
  independiente (spec + calidad) y aprobada. Hubo 5 rondas de fix en total
  entre ambos streams; todo cerrado.
- **Estado git**: las ramas `feature/obra08-streamA` y
  `feature/obra08-streamB` se mergearon a `feature/transformacion-2026-08`
  el 2026-08-28 (merge commits `efe2849` y `123a041`) y se borraron. Los
  worktrees fueron eliminados.
- **Verificación del árbol mergeado**: `cargo test --workspace` →
  **759 passed / 0 failed / 1 ignored** (el ignore es `rss_measure`,
  manual); `cargo clippy --workspace --all-targets -- -D warnings` y
  `cargo fmt --check` limpios.
- Nota de historia: el commit `8149bfd` preserva el WIP previo del dueño
  (P8d IDE adapters + TUI + t2 memoria) que vivía en el árbol — es byte-
  exacto y reversible (`git reset --soft HEAD~1`); además hay archivos
  untracked de ese WIP (cortex-tui/*, cortex-mcp/src/backends/*) que
  compilan y están al día con la Obra 08 (incluyen los arms `Composed`).

## Qué quedó construido (resumen operativo)

**Stream A — Modo COMPOSED:**
- `Checkpoint.phase: Option<CheckpointPhase>` (grill/spec/plan/implement/
  review/close) + `SessionMode::Composed` (serializa `"composed"`).
- Barra de calidad por fase (`quality_gates::check_phase_gate`), validación
  dura en `SessionService::checkpoint` + MCP (mensaje canónico).
- Documenter: sección `## Fases` + evidencia por fase (template SSoT
  `cortex/documentation/templates/session.md.j2`, condicional).
- Skills de la tríada reestructuradas: thin + craft on-demand (formato
  plano, Ruling R10 — la migración a `references/` es obra POST-baja del
  oráculo Python; NO la hagas antes).
- `cortex setup composed`: familia de 8 skills + bloque `## Agent skills`
  (marcadores dedicados `COMPOSED_MARKER_*` — coexiste con codex).
- Acción `session.suggest_next_phase` en el Action Engine (11 acciones).

**Stream B — Herdr Companion:**
- Crate `cortex-companion` (TUI ratatui mouse-first, 6 paneles, Backend
  in-process con paridad JSON byte-idéntica vs CLI, `run_guarded` con
  auditoría, brain híbrido read/mutate-con-aprobación, menú anti-olvido de
  27 familias).
- Plugin herdr en `integrations/herdr/` — **linkeado y verificado en la
  máquina del dueño** (herdr 0.7.3, `min_herdr_version = "0.7.0"`):
  `herdr plugin list` muestra `cortex.companion enabled [local:/home/
  chucho/Cortex/integrations/herdr]`.
- Desacople del embedder ONNX en `cortex-cli::memory` (stats ya no carga
  ~90 MB).

## Reglas duras que NO debés violar

1. **Paridad-como-contrato**: el oráculo Python (`cortex/`, `tests/`,
   `pyproject.toml`) está CONGELADO (2552 tests). No lo toques ni corras
   pytest en el árbol sin decisión explícita del dueño (baja física
   pendiente). Salvo templates de datos SSoT (`.md.j2`, `workspace_files/`)
   con test embed==disco, donde el cambio debe ser output-neutral para
   entradas sin fase (precedente R9).
2. **No recapturar goldens** (bench/parity/archive, MCP list_tools, etc.)
   sin decisión del dueño. Los cambios de schema son Rust-only con
   divergencia declarada en `ESTADO-ACTUAL.md`.
3. **No rehacer la Obra 08**: si una tarea tuya parece solaparse con lo
   descrito arriba, primero preguntá en el repo (está mergeado en esta
   rama) antes de reimplementar.
4. Convenciones: commits Conventional en español con scope de obra,
   `cargo test -p <crate>` + clippy `-D warnings` + `cargo fmt --check`
   antes de commitear; un gate por commit; verificación con evidencia.
5. `rust/` es el root de cargo. `#![forbid(unsafe_code)]` en lógica nueva.
   Cero deps nuevas sin ADR.

## Decisiones abiertas del dueño (pueden afectar tu tarea)

- **Step 4b de A13** (divergencia #5 en ESTADO-ACTUAL): correr
  `cortex setup composed` sobre el propio repo (`.cortex/skills/composed/`
  + bloque AGENTS.md en el repo) — pendiente de decisión post-merge.
- **Borrado físico del Python** (cortex/ + tests/ + pyproject.toml) —
  requiere mover la verificación a Rust puro; decisión del dueño.
- **`cortex finish`** no está wireado (R13): los flujos reales de cierre
  son `cortex autopilot finish` / `cortex session abandon` + documenter.
  Strings "finish-session" residuales en 3 contratos congelados (MCP
  goldens `handlers_finish.rs:264`, `handlers_spec.rs:865`,
  `session_hooks/pi.rs:31`) — NO tocarlos sin recaptura.
- **herdr**: el pane open y la navegación por clic son verificación manual
  del dueño (INSTALL.md §Verificar/§Uso). La fase 2 del Companion (Web Hub
  localhost, backend MCP/remoto P13, reuso de widgets post-estabilización)
  está documentada en `14-HERDR-COMPANION.md` §9.
- **WIP P8d/TUI del dueño** (commit `8149bfd` + archivos untracked de
  cortex-tui y cortex-mcp/backends) está al día con la Obra 08 (arms
  `Composed` incluidos) — no lo reescribas; si tu tarea lo toca, coordiná.

## Tu tarea

> **[AQUÍ VA LA NUEVA TAREA QUE EL DUEÑO TE DA]**

## Al terminar

Reportá: qué cambiaste, verificación ejecutada con salidas reales
(comandos + números), y cualquier decisión de diseño que hayas tomado.