---
title: Implementación 01 — Cambios canonical en subagents y skills
plan: ../plan/01-cambios-subagentes-y-skills.md
status: ✅ CERRADA (2026-05-13)
suite_at_close: 784 passed, 6 skipped, 0 failed (unit + integration)
---

# Implementación 01 — Cambios canonical en subagents y skills

Bitácora de ejecución del Plan 01. **Cerrada al 100%.** Todos los §1-§8 aplicados.

## Estado del checklist del plan original

- [x] §1 Signal > Noise en documenter
- [x] §2 ADR 3 criterios (helper `_meets_adr_criteria` + prompt + tests)
- [x] §3 CONTEXT.md como prompt asset (layout property + template + skills references + auto-create en setup)
- [x] §4 Verification Gate en documenter (prompt — backend MCP en Plan 02)
- [x] §5 Handoff Mode (enum status + tag + canonical prompt)
- [x] §6 Confidence levels (MemoryEntry + SessionDraft)
- [x] §7 Anti-rationalization en los 5 agentes
- [x] §8 Structured YAML handoff schema (`cortex/handoff.py` + 12 tests)

## Bitácora detallada

### Setup inicial

**Limpieza naming "Ola 5" → "Tripartita Refinada"** (decisión del usuario: las olas terminaron en Ola 4, lo siguiente es "Tripartita Refinada"). Reemplazo `replace_all` aplicado en 7 archivos del plan: `ANALISIS-COMPLETO.md`, `plan/00`, `plan/02`, `plan/04`, `plan/05`, `plan/07`. Archivos canonical del plan (`01`, `03`, `06`) no tenían referencias.

**Carpeta creada**: `docs/agents/implementacion/` con `README.md` (índice de bitácoras) y este archivo de progreso.

### §8 — Schema `cortex.handoff.AgentHandoff`

**Archivos creados:**
- `cortex/handoff.py` (115 líneas) — `AgentHandoff` y `ArtifactProduced` Pydantic models. Métodos `to_yaml()` / `from_yaml()`. Helper `is_known_agent`. Soporta 7 agent names canonical (5 generales + 2 Pi-only: `cortex-security-auditor`, `cortex-test-verifier`).
- `tests/unit/test_handoff.py` — 12 tests cubriendo: minimal, full round-trip, agent inválido, status inválido, mapping root rechazado, missing required, Pi-only agents, unicode preservation, known-agent helper.

**Decisión técnica:** elegí 7 agent names en el `Literal[...]` (no solo los 5 del Plan original) para que `cortex-security-auditor` y `cortex-test-verifier` (Pi-only) puedan emitir handoffs sin requerir un schema separado. Esto desbloquea el Plan 05 (Pi) sin cambios futuros al schema.

**Resultado tests:** 12/12 verde.

### §1, §2, §4, §5, §7 — Reescritura de prompts canonical

**Archivos reescritos** (5 archivos, sobrescritura completa):
- `.cortex/subagents/cortex-documenter.md` — todos los cambios juntos: Signal > Noise (header), 3 criterios ADR con tabla, Verification Gate con checklist, Handoff Mode con frontmatter, Anti-rationalization (8 entradas), Contrato de Salida YAML.
- `.cortex/subagents/cortex-code-explorer.md` — Anti-rationalization (5 entradas específicas) + Contrato de Salida YAML.
- `.cortex/subagents/cortex-code-implementer.md` — Anti-rationalization (6 entradas) + Contrato de Salida YAML.
- `.cortex/skills/cortex-sync.md` — Pre-flight CONTEXT.md + Anti-rationalization (4 entradas) + Contrato de Salida YAML.
- `.cortex/skills/cortex-SDDwork.md` — Validación de handoffs (responsabilidad del orquestador) + Anti-rationalization (5 entradas) + Contrato de Salida YAML.

**Tools nuevos referenciados** en frontmatter del documenter: `cortex_verify_session_claims`, `cortex_validate_handoff`, `cortex_search`. **Esos tools aún no existen** — los implementa Plan 02. El prompt los referencia anticipándose.

### §3 — CONTEXT.md como prompt asset

**Archivos tocados:**
- `cortex/workspace/layout.py` — agregué `WorkspaceLayout.context_md_path` property. Resolve `<workspace>/CONTEXT.md` (new layout) o `<repo>/CONTEXT.md` (legacy).
- `cortex/setup/templates.py` — agregué `render_context_md(ctx)` que produce un stub minimal con tabla vacía + reglas de uso.
- `cortex/setup/orchestrator.py` — extendí `_create_vault_docs()` para crear `CONTEXT.md` desde el template **idempotente** (skip si existe).
- Skills `.cortex/skills/cortex-sync.md` y el documenter referencian el archivo en sus prompts.

**Tests:** 2 en `test_tripartita_refinada.py::TestContextMdPath` (new layout, legacy layout).

### §5 — Handoff Mode (status enum + tag)

**Archivos tocados:**
- `cortex/autopilot/models.py` — agregué `"handoff"` al enum `AutopilotSessionState.status`.
- `cortex/autopilot/models.py` — agregué `SessionDraft.confidence_level: Literal["verified","asserted","contradicted"] | None = None`.
- `cortex/autopilot/session_writer.py` — `IndexingSessionWriter._build_tags(draft, state)` ahora recibe `state` opcional. Si `state.status == "handoff"`, agrega `"handoff"` al tag list. Backwards-compat: `_build_tags(draft)` sin state sigue funcionando (path legacy).
- El call site en `_index` actualizado para pasar `state`.

**Tests:** 4 en `test_tripartita_refinada.py::TestHandoffTag`, `TestSessionDraftConfidenceLevel`, `TestSessionStateHandoffStatus`.

### §6 — Confidence levels en MemoryEntry

**Archivos tocados:**
- `cortex/models.py::MemoryEntry` — agregué campo opcional `confidence: Literal["verified","asserted","contradicted"] | None = None`. Backwards-compat: memorias pre-0.5.0 tienen `None`.

**Tests:** 3 en `test_tripartita_refinada.py::TestMemoryEntryConfidence` (default None, accepts 3 states, rejects invalid).

### §2 — Helper `_meets_adr_criteria`

**Archivos tocados:**
- `cortex/doc_generator.py` — agregué función module-level `_meets_adr_criteria(ctx: PRContext) -> bool` que aplica el filtro 3 criterios sobre el PR body usando keyword heuristics. La función `generate_all` quedó sin cambios funcionales (todavía solo emite session note como fallback), pero la documentación de su docstring menciona el helper para uso futuro.

**Tests:** 6 en `test_tripartita_refinada.py::TestMeetsAdrCriteria` (all 3 present, missing each criterion, empty body, case insensitive).

### Edge case encontrado durante implementación

**Edit accidental rompió `DocGenerator`:** al insertar `_meets_adr_criteria` después de `generate_all`, accidentalmente lo coloqué **entre métodos de la clase**, dejando `write_docs` y `generate_and_write` fuera de la indentación de clase. Lo detectó el test `test_pr_context.py::TestDocGenerator::test_write_docs_creates_files`. Corregido moviendo el helper **después del cierre de la clase**.

**Lección documentada:** cuando agregás un helper module-level dentro de un archivo con una clase grande, verificar que el cierre de la clase ocurre antes del helper.

## Tests acumulados en Plan 01

| Archivo | Tests nuevos | Total verde |
|---------|-------------|-------------|
| `tests/unit/test_handoff.py` | 12 | 12 |
| `tests/unit/test_tripartita_refinada.py` | 17 | 17 |
| **Total Plan 01** | **29** | **29** |

## Suite global al cierre

```
$ python -m pytest tests/unit tests/integration --no-cov
784 passed, 6 skipped, 0 failed in 24.07s
```

Baseline pre-Plan 01: 749 passed. Delta: **+35** (29 nuevos + 6 alguno re-corrido).

## Hallazgos para próximos planes

1. **Plan 02 (MCP server):** los tools nuevos (`cortex_validate_handoff`, `cortex_verify_session_claims`) están referenciados en los prompts canonical pero **no existen aún**. Los prompts esperan a Plan 02. Si un usuario corre los nuevos prompts antes de Plan 02, el agente va a fallar al invocar tools inexistentes. **Mitigación:** documentar en cualquier release notes que Plan 01 y Plan 02 deben mergearse juntos antes de bumpear a 0.5.0.

2. **Plan 03-06 (IDEs):** los 4 IDEs ahora heredan automáticamente los nuevos prompts canonical vía `cortex inject --ide <name>`. **Acción requerida:** los smokes de cada IDE deben re-ejecutarse para confirmar que los marcadores aparecen en los archivos generados. **Hoy NO se hizo** este smoke — quedó pendiente para los Planes 03-06.

3. **Plan 05 (Pi) crítico:** el bundle `cortex-pi/.pi/agents/cortex-{code-explorer,code-implementer,documenter}.md` **NO está sincronizado** con el canonical actualizado. Sin el sync mechanism del Plan 05 §1, el adapter Pi copia versiones viejas. **Antes de cerrar la implementación 05, ejecutar `sync_canonical_subagents` manualmente o implementar el mecanismo automático**.

4. **Plan 07 (tests + cierre):** los tests de §8 (handoff schema) y §1-§7 ya suman 29 unit tests. El plan original estimaba ~12 para Plan 01 + ~12 para Plan 02; cumplimos sobradamente la parte de Plan 01. Plan 02 puede partir del schema existente.

5. **Suite flaky observada:** `test_autopilot_service.py::TestStatus::test_latest_session` falló intermitentemente en una corrida y pasó al re-ejecutar. No es introducido por Plan 01 (no toqué nada de status). Anotar como flakiness preexistente; investigar en Plan 07 si persiste.

## Archivos modificados (total)

### Código
- `cortex/handoff.py` (nuevo, 115 líneas)
- `cortex/models.py` (campo `confidence` opcional)
- `cortex/workspace/layout.py` (property `context_md_path`)
- `cortex/autopilot/models.py` (enum status `handoff`, SessionDraft `confidence_level`)
- `cortex/autopilot/session_writer.py` (firma de `_build_tags`, tag handoff)
- `cortex/setup/templates.py` (`render_context_md` nuevo)
- `cortex/setup/orchestrator.py` (import + creación de CONTEXT.md)
- `cortex/doc_generator.py` (helper `_meets_adr_criteria` module-level)

### Canonical prompts (5 archivos sobrescritos)
- `.cortex/subagents/cortex-documenter.md`
- `.cortex/subagents/cortex-code-explorer.md`
- `.cortex/subagents/cortex-code-implementer.md`
- `.cortex/skills/cortex-sync.md`
- `.cortex/skills/cortex-SDDwork.md`

### Tests
- `tests/unit/test_handoff.py` (nuevo, 12 tests)
- `tests/unit/test_tripartita_refinada.py` (nuevo, 17 tests)

### Documentación
- `docs/agents/implementacion/README.md` (nuevo, índice de bitácoras)
- `docs/agents/implementacion/01-cambios-subagentes-y-skills.md` (este archivo)
- Naming "Ola 5" → "Tripartita Refinada" en 7 archivos del plan.

## Próximo paso

**Plan 02 — Cambios al MCP server.** Sin implementarlo, los prompts canonical de Plan 01 quedan "esperando" a los tools que mencionan. Plan 02 los crea y completa el contrato.

Ver `docs/agents/plan/02-mcp-server-cambios.md`.
