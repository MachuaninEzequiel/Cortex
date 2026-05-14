---
title: Implementación 04 — Materialización en OpenCode
plan: ../plan/04-ide-opencode.md
status: ✅ CERRADA (2026-05-14)
suite_at_close: 805 passed, 6 skipped, 0 failed (unit + integration)
delta_vs_plan_03_baseline: +3 tests
---

# Implementación 04 — Materialización en OpenCode

Bitácora de ejecución del Plan 04 (Tripartita Refinada — IDE OpenCode).
**Cerrada al 100% de items automatizables.** El smoke manual queda como
verificación opcional del usuario antes del release de 0.5.0.

## Estado del checklist del plan original

- [x] Tools nuevos agregados a `cortex_profiles` en adapter
- [x] Test de presencia de los 2 tools nuevos por agent
- [x] `opencode.json` tiene los 2 tools nuevos por agent (verificado)
- [x] `docs/guides/ide-opencode.md` extendida con sección Tripartita Refinada
- [ ] Smoke manual `cortex inject --ide opencode` — pendiente del usuario

## Bitácora detallada

### Cambio 1 — Tools nuevos en `cortex_profiles`

**Archivos tocados:**
- `cortex/ide/adapters/opencode.py::inject_profiles` — el dict `cortex_profiles` (líneas ~85-115) ahora incluye dentro de `tools` para los dos primary agents:
  - `cortex_validate_handoff: True`
  - `cortex_verify_session_claims: True`

Comentarios inline explican **por qué** cada agent tiene cada tool:
- `cortex-sync` valida el handoff que recibe de SDDwork antes de cerrar su propio turno.
- `cortex-SDDwork` valida los handoffs de subagents delegated vía `Task` y verifica claims antes de pasarlos al documenter.

**Decisión técnica:** el toggle de tools por agent en OpenCode es explícito (whitelist). Si una tool no está en el dict, el agent ni siquiera la ve en su lista. Por eso era crítico agregar las dos tools nuevas — sin esto, los prompts canonical (que las referencian) las pedirían y OpenCode las rechazaría con error.

### Cambio 2 — Hook autopilot (sin código)

Plan 04 §2 indica que `.opencode/hooks.md` no necesita cambios — el `status: handoff` propaga vía `state.json` del autopilot. **Sin trabajo extra acá.**

### Cambio 3 — Inheritance de skills/subagents (sin código)

Plan 04 §3 indica que los archivos en `~/.config/opencode/skills/` y `~/.config/opencode/subagents/` heredan automáticamente del canonical vía `WorkspaceLayout.discover(project_root).subagents_dir`. Verificación se hace por smoke manual, no por test (el adapter sí copia, los tests del adapter ya cubrían eso pre-existente).

**Decisión técnica:** no agregué tests de inheritance acá porque los tests análogos en Plan 03 (Claude Code) ya cubren el patrón general (canonical → materializado). En Plan 04 el adapter usa la misma función `WorkspaceLayout.discover().subagents_dir` y la misma operación de copy. Si el patrón se rompiera, los tests de Plan 03 lo detectan primero. El smoke manual del usuario verifica el caso end-to-end.

### Doc-guide actualizada

**Archivos tocados:**
- `docs/guides/ide-opencode.md` — agregué sección `## Tripartita Refinada (0.5.0)` con 4 sub-secciones:
  1. Tools nuevas habilitadas en agents primary (con explicación de qué hace cada agent con cada tool).
  2. Subagents canonical actualizados (qué markers nuevos aparecen tras re-inject).
  3. Sesiones marcadas como handoff (frontmatter + parámetros nuevos).
  4. Confidence labels en respuestas de búsqueda.

La sección incluye una nota explícita sobre re-correr `cortex inject --ide opencode` al actualizar de 0.4.x a 0.5.0 — crítico porque OpenCode guarda el config en `~/.config/opencode/` (XDG global), no en el proyecto, y un upgrade silencioso del package no regenera el JSON automáticamente.

## Tests acumulados en Plan 04

| Archivo | Tests nuevos | Total verde |
|---------|-------------|-------------|
| `tests/unit/test_ide_adapters.py` | 3 | 24 |
| **Total Plan 04** | **+3** | **+3** vs baseline |

Tests nuevos:
- `TestOpenCodeTripartitaRefinada::test_sync_agent_has_new_handoff_tools`
- `TestOpenCodeTripartitaRefinada::test_sddwork_agent_has_new_handoff_tools`
- `TestOpenCodeTripartitaRefinada::test_pre_existing_tools_remain_enabled` — regression: el deep-merge no pisa los tools pre-existentes.

## Suite global al cierre

```
$ python -m pytest tests/unit tests/integration --no-cov
805 passed, 6 skipped, 0 failed in 22.79s
```

Baseline pre-Plan 04 (cierre de Plan 03): 802 passed. Delta: **+3** (los 3 tests nuevos).

## Hallazgos para próximos planes

### Para Plan 05 (Pi) — CRITICAL

1. **Pi NO consume canonical de `.cortex/subagents/`.** Copia desde `cortex-pi/.pi/agents/` (bundle congelado en el repo). El bundle está desactualizado vs canonical post-Plan 01. **Plan 05 §1 (`sync_canonical_subagents`) es el primer paso obligatorio**, antes de tocar el adapter Pi.

2. **Pi tiene 2 agents extra:** `cortex-security-auditor`, `cortex-test-verifier`. Ambos ya están soportados en el `AgentHandoff` schema (Plan 01 §8 los incluyó preventivamente). Cuando re-syncronicemos el bundle, esos agents heredarán los markers Tripartita Refinada como cualquier otro.

### Para Plan 06 (Codex)

1. **Patrón replicable.** El adapter Codex (`cortex/ide/adapters/codex.py`) tiene un AGENTS.md template análogo al CLAUDE.md de Claude Code. Replicar el patrón de Plan 03: agregar las 4 reglas Tripartita Refinada al template + test análogo a `test_claude_md_mentions_verification_gate`.

2. **Diferencia importante:** Codex no parece tener un equivalente al toggle `tools` por agent que tiene OpenCode (verificar al leer Plan 06). Si no lo tiene, Plan 06 es solo el cambio del AGENTS.md.

### Para Plan 07 (tests + cierre)

1. **Tests de inheritance siguen viniendo de Plan 03.** Si Plan 07 agrega un test e2e cross-IDE que verifica que **todos** los IDEs heredan los markers canonical, sería el cierre natural del bloque IDE-related (Planes 03-06).

2. **Suite a esperar al cierre Plan 07:** ~875+ tests vs 805 hoy.

## Archivos modificados (total)

### Código
- `cortex/ide/adapters/opencode.py` — `cortex_profiles` dict extendido con 2 tools nuevos por agent (sync y SDDwork) + comentarios inline que documentan el rol de cada tool.

### Tests
- `tests/unit/test_ide_adapters.py` — clase nueva `TestOpenCodeTripartitaRefinada` con 3 tests + helper `_inject` que inyecta y devuelve el JSON parseado.

### Documentación
- `docs/agents/plan/04-ide-opencode.md` — frontmatter status, todos los checkboxes marcados (excepto smoke manual).
- `docs/agents/implementacion/README.md` — entrada 04 marcada CERRADA.
- `docs/agents/implementacion/04-ide-opencode.md` — este archivo.
- `docs/guides/ide-opencode.md` — sección "Tripartita Refinada (0.5.0)" agregada con 4 sub-secciones.

## Próximo paso

**Plan 05 — IDE Pi (caso especial).** Implementar primero `sync_canonical_subagents` para sincronizar el bundle `cortex-pi/.pi/agents/` desde `.cortex/subagents/`, después adaptar el adapter Pi si requiere cambios extra. Pi tiene 2 agents adicionales (security-auditor, test-verifier) que ya están en el schema.

Ver `docs/agents/plan/05-ide-pi.md`.
