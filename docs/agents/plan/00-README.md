---
title: Plan de implementación — Tripartita refinada (Tripartita Refinada)
date: 2026-05-13
status: planificado
prerequisitos: Cortex 0.4.0 (Olas 0-4 cerradas). Feedback de los dos primeros adopters recopilado (opcional pero recomendado antes de arrancar).
target_release: 0.5.0 o 0.4.x feature flag
---

# Plan de implementación — Tripartita refinada

Este es el **plan ejecutable** de los 8 cambios identificados en `docs/agents/ANALISIS-COMPLETO.md`. Está dividido en 7 documentos, uno por superficie afectada:

| # | Doc | Alcance |
|---|-----|---------|
| 1 | `01-cambios-subagentes-y-skills.md` | Los 8 cambios al canonical (`.cortex/subagents/`, `.cortex/skills/`) |
| 2 | `02-mcp-server-cambios.md` | Cambios al MCP server: nuevos tools, schemas, validación |
| 3 | `03-ide-claude-code.md` | Cómo se materializa cada cambio en Claude Code |
| 4 | `04-ide-opencode.md` | Idem OpenCode |
| 5 | `05-ide-pi.md` | Idem Pi (caso especial: bundle `cortex-pi/` aparte) |
| 6 | `06-ide-codex.md` | Idem Codex |
| 7 | `07-tests-y-cierre.md` | Tests por capa + smoke 4×IDE + criterio de cierre Tripartita Refinada |

## Cómo leer este plan

1. **Empezá por `01`** — define los cambios canonical que el resto consume.
2. **Después `02`** — el MCP server enforcea el contrato de los cambios.
3. **Después `03-06` en cualquier orden** — los 4 IDEs heredan del canonical.
4. **`07` al final** — cierre.

## Convención de archivos a tocar

Cada doc lista archivos en el formato:

```
- cortex/<path>.py — descripción breve del cambio
- tests/<path>.py — tests requeridos
- docs/<path>.md — actualización de docs si aplica
```

## Convención de criterio de cierre

Cada doc termina con un checklist marcable. Cuando todos los ítems están en `[x]`, el doc está cerrado.

## Reglas operativas (aplicables a todo el plan)

1. **Canonical-first.** El archivo en `.cortex/subagents/` o `.cortex/skills/` es la única fuente de verdad. Los IDEs heredan vía `cortex inject --ide <name>`. Si hay drift, el canonical gana.
2. **No tocar el motor de retrieval.** Las 5 estrategias de context enricher, el RRF con `K=60`, el adaptive weighting, el entity index — **nada** de esto se toca en Tripartita Refinada. Si una propuesta requiere tocarlo, retroceder al análisis y reescribirla.
3. **Indexing transaccional preservado.** Los cambios al documenter no deben romper la invariante "archivo en disco ⇒ archivo indexado" que se cerró en Ola 0. Cualquier nuevo write path pasa por `SessionWriter` / `SpecService` / `PRService.write_pr_docs`.
4. **MCP guard preservado.** `cortex_create_spec` sigue requiriendo `cortex_sync_ticket` previo. No agregar nuevos tools que salteen el guard.
5. **Tests antes de docs.** Cada cambio canonical va con su test antes de actualizar las guías IDE. Razón: el guide miente si el código miente.
6. **Sin breaking changes públicos sin alerta.** Si cambia firma de un MCP tool o un CLI flag, va al CHANGELOG sección "Breaking changes" antes del cierre.
7. **Smoke por IDE al cierre.** No se considera cerrado un IDE sin haber probado al menos un caso end-to-end con el adapter regenerado.

## Esfuerzo total estimado

| Fase | Items | Esfuerzo |
|------|-------|----------|
| Fase 1 — Canonical + MCP | 01, 02 | 3-4 días |
| Fase 2 — IDE materializations | 03, 04, 05, 06 | 2-3 días |
| Fase 3 — Tests + cierre | 07 | 1-2 días |
| **Total** | | **6-9 días** |

## Versión target

Sugerido: **0.5.0**. Justificación:

- 4 cambios canonical son **breaking** para usuarios que tienen prompts customizados de los subagents (Signal>Noise reescribe la sección de objetivo). Hay que documentarlos en CHANGELOG.
- Nuevo MCP tool `cortex_validate_handoff` aumenta la API surface — feature minor.
- `MemoryEntry.metadata["confidence"]` opcional — backwards-compat preservado.
- `AutopilotSessionState.status` nuevo enum value `handoff` — breaking si algún consumidor externo hace match exhaustivo sobre el enum (poco probable, pero documentar).

Alternativa: **0.4.x con feature flags**. Si la urgencia es alta y no queremos esperar un minor release, los cambios canonical + MCP tool nuevo pueden ir con flag `--enable-tripartite-refined` por default off, activable por config. No recomendado salvo necesidad explícita del usuario.

## Pre-flight checks antes de arrancar

Antes de tocar nada de Tripartita Refinada:

- [ ] Confirmar que Olas 0-4 están **cerradas al 100%** y suite global verde.
- [ ] Confirmar feedback de los dos primeros adopters recopilado (si existe) — sus quejas reales sobre el documenter mandan más que la propuesta original.
- [ ] Confirmar versión target con el usuario (0.5.0 vs 0.4.x feature flag).
- [ ] Crear branch `feature/ola-5-tripartita-refinada` y trabajar ahí.
- [ ] Releer `docs/review/cortex-save-state.md` para el mapa mental del repo.

## Continuación post-cierre

Cuando Tripartita Refinada cierre:

1. Cerrar este plan: mover a `docs/olas/ola-5-tripartita-refinada.md` con el detalle final.
2. Actualizar `docs/review/cortex-save-state.md` con los cambios introducidos.
3. CHANGELOG 0.5.0 con las 4 áreas: cambios canonical, cambios MCP, cambios IDEs, breaking changes.
4. Bump `pyproject.toml` y `cortex/__init__.py` a `0.5.0`.
5. Si quedó deuda (cosas que no se cerraron en Tripartita Refinada), moverla a `docs/roadmap/post-adopters.md` o a un nuevo `docs/roadmap/0.6.x.md`.
