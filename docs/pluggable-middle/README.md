# Pluggable Middle Architecture

Esta carpeta contiene la arquitectura activa de Cortex (modelo Pluggable
Middle, ya no "tripartito") y los planes de implementación de cada fase.

## Contenido

| Archivo | Contenido |
|---|---|
| [`ARQUITECTURA-PLUGGABLE-MIDDLE.md`](ARQUITECTURA-PLUGGABLE-MIDDLE.md) | **Documento maestro.** Diseño completo de la arquitectura, principios, diagramas, decisiones. |
| [`fases/`](fases/) | **Plan de implementación.** Desglose por fases secuenciales con detalle ejecutable. |

## Cómo navegar esta documentación

### Si nunca leíste nada: empezá por la arquitectura

1. Leé `ARQUITECTURA-PLUGGABLE-MIDDLE.md` completa.
2. Después leé `fases/README.md`.
3. Después abrí la fase que corresponda según el estado actual.

### Si vas a implementar (agente autónomo)

1. Leé `fases/README.md` (Quality Charter + Context Loading Protocol).
2. Identificá la fase actual ejecutando los chequeos descritos en `fases/README.md`.
3. Leé la fase correspondiente (ej. `fases/00-FOUNDATIONS.md`).
4. Seguí el flujo definido en esa fase.

### Si querés revisar una decisión histórica

- Las decisiones de diseño viven en `ARQUITECTURA-PLUGGABLE-MIDDLE.md` §12 (Decisiones tomadas).
- El razonamiento de prioridades/dependencias entre fases vive en `fases/README.md`.

## Estado actual

- **Diseño:** consolidado (v1.0).
- **Implementación core (Fases 00–04):** ✅ **Completa** (2026-05-17). Los 3 modos (Managed / Observed / BYO) operativos; documenter interactive disponible; doctor exhaustivo; CHANGELOG + migration guide cerrados.
- **Suite al cierre de Fase 04:** 1743 passed, 15 skipped, 0 failed. mypy strict clean en módulos nuevos. ruff clean.
- **Roadmap post-MVP (Fases 05–07):** 3 fases planeadas, **pendientes**. Son aditivas — no bloquean ningún flujo actual. Pueden ejecutarse en paralelo si hay capacidad, o secuencialmente.
- **Próxima referencia para nuevos contribuyentes:** `docs/architecture/pluggable-middle-overview.md` (3 páginas) y `docs/architecture/session-primitive.md` (referencia técnica).
- **Migración desde el modelo tripartito:** ver `MIGRATION-FROM-TRIPARTITO.md`.

> Esta tabla es la única fuente de verdad sobre el progreso global. Pluggable Middle es **el** modelo de Cortex; ya no se trata de una "propuesta".

## Tabla de progreso

### Core (00–04) — ✅ Completas

| Fase | Nombre | Estado | Output |
|---|---|---|---|
| 00 | Foundations (Session primitive) | ✅ Completa | `cortex.session` module · 5 MCP tools · `cortex session ...` CLI · doctor section · setup integration · NoteService rename · docs (106 tests, **100% coverage**, mypy strict) |
| 01 | Documenter Reconstruction Mode (BYO) | ✅ Completa | Verification hooks · `cortex.documenter` module · `cortex finish-session` CLI + MCP tool · subagent/skill prompts actualizados · E2E BYO tests (5 escenarios) — **100% coverage** `cortex.documenter`, 64 tests del módulo |
| 02 | SDDwork Migration (Managed unified) | ✅ Completa | SDDwork/explorer/implementer emiten checkpoints (no YAML) · documenter en modo enriquecido por mode · agent_guidelines actualizadas · cortex_validate_handoff deprecated · E2E managed flow (4 escenarios) |
| 03 | Autopilot Fusion + Observed Mode | ✅ Completa | Autopilot refactor sobre Sessions · `policies.py` consolidado · `cortex/session/hooks/` + 3 adapters (Claude Code, Cursor/git, Pi) · `cortex session hooks list/install/uninstall/status` · `cortex session checkpoint` CLI · doctor extensions · E2E Observed (3 escenarios) · README + session-primitive docs actualizadas |
| 04 | Interactive Mode + Final Polish | ✅ Completa | `cortex.documenter.interactive` (`InteractiveSession` + `rich` UI) · flag `cortex finish-session --interactive` · config `documenter.default_mode` · `cortex doctor` exhaustivo (`pm_*` checks) · CHANGELOG `[Unreleased]` · `MIGRATION-FROM-TRIPARTITO.md` · `docs/architecture/pluggable-middle-overview.md` · Legacy YAML deprecated (docstring + subagent) · cleanup deuda Fase 03 (17 archivos legacy eliminados) |

### Roadmap post-MVP (05–09) — ⏸ Pendientes

Cinco fases planeadas. **Orden recomendado de ejecución: 08 → 06 → 09 → 05 → 07.**
Ver [`HANDOFF-POST-MVP.md`](fases/HANDOFF-POST-MVP.md) para la justificación
detallada del orden, las coordinaciones críticas entre fases, y la pre-flight
checklist del próximo agente ejecutor.

| Fase | Nombre | Prioridad | Estado | Esfuerzo | Output esperado |
|---|---|---:|---|---|---|
| 08 | Managed Quality Gates restaurados | **1º** | ✅ Completa (2026-05-17) | ~1.5 sem | Rollback transaccional en `NoteService.create` · `cortex_review_checkpoint` MCP tool + `cortex.session.quality_gates` · self-review del draft en `DocumenterPersister` · `cortex.context_enricher.budget_resolver` · `session.md.j2` condicional por `task_type`. **+36 tests netos (1779 passed total).** Sin breaking changes. |
| 06 | Sessions TUI con `rich` | **2º** | ✅ Completa (2026-05-17) | ~2 sem | `cortex session watch [ID] [--refresh N]` + `cortex session show --watch`. `cortex/cli/session_tui.py` (render puro + run loop) + `cortex/cli/_unicode_fallback.py`. Layout 3-cols adaptativo (collapses a 2-col / vertical en terminales angostos). 42 unit tests + 2 E2E (no-TTY exit + subprocess SIGINT cross-platform). |
| 09 | SDD Refinement (proposal + design + tasks) | **3º** | ✅ Completa (2026-05-17) | ~3-4 sem | **09.A**: `--proposal-mode` (optional/required/skip) + cortex-sync addendum. **09.B**: subagent `cortex-code-designer` + `DocType.DESIGN` + `write_design_note_canonical` MCP tool + Deep Track 4-pasos. **09.C**: `Task` model + `SessionRecord.tasks` + CLI `cortex session task ...` + MCP tools task_list/_update + `--with-tasks` flag + documenter `% completion` summary. Sin breaking changes. |
| 05 | Opencode hook adapter | **4º** | ✅ Completa (2026-05-17) | ~1 sem | `cortex/session/hooks/adapters/opencode.py` (markdown-block en `.opencode/hooks.md`) registrado en `default_installer`. 14 unit tests + 3 CLI tests + research note interno. mypy strict + ruff clean. |
| 07 | CI Plugin (3 niveles incrementales) | **5º** | ✅ Completa (2026-05-17) | ~3-4 sem | **N1**: `cortex ci validate-pr` + 2 templates YAML (GitHub Actions + GitLab CI) + cortex/ci/ módulo (validator, session_matcher, diff_io, result). **N2**: `--format pr-comment` + Markdown emitter con sentinel marker `<!-- cortex-pr-summary -->`. **N3**: `CheckpointSource.CI_BOT` + `SessionMode.CI_REVIEW` + 3 commands (open-review/report-checkpoint/close-review). 34 unit tests. mypy strict + ruff clean. |

> Leyenda: ⏸ Pendiente · 🟡 En progreso · ✅ Completa · ⚠️ Bloqueada

**Tiempo total estimado:** ~11-13 semanas en serie; ~6-7 semanas con 2 ejecutores en paralelo (ver §3 del handoff).
