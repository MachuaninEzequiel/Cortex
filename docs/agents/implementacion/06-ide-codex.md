---
title: Implementación 06 — Materialización en Codex CLI
plan: ../plan/06-ide-codex.md
status: ✅ CERRADA (2026-05-14)
suite_at_close: 814 passed, 6 skipped, 0 failed (unit + integration)
delta_vs_plan_05_baseline: +3 tests
---

# Implementación 06 — Materialización en Codex CLI

Bitácora de ejecución del Plan 06 (Tripartita Refinada — IDE Codex).
**Cerrada al 100% de items automatizables.** El smoke manual queda como verificación
opcional del usuario antes del release de 0.5.0.

Plan 06 es el más sencillo del bloque IDE (Planes 03-06): replica el patrón de Plan 03
(Claude Code) sobre el adapter Codex. Codex no requiere mecanismo de sync canonical (igual
que Claude Code y OpenCode, consume `.cortex/subagents/` directamente vía
`get_subagent_prompt`), no tiene un toggle de tools por agent (a diferencia de OpenCode),
y no tiene un bundle congelado (a diferencia de Pi). El cambio principal es el template
de `.codex/AGENTS.md`.

## Estado del checklist del plan original

- [x] `.codex/AGENTS.md` template actualizado con 4 reglas
- [x] Test del template + tests de inheritance
- [x] `docs/guides/ide-codex.md` extendida con sección Tripartita Refinada + nota sobre delegación por convención
- [ ] Smoke manual `cortex inject --ide codex` — pendiente del usuario

## Bitácora detallada

### Cambio 1 — `.codex/AGENTS.md` template ampliado

**Archivos tocados:**
- `cortex/ide/adapters/codex.py::inject_profiles` — el bloque que escribe `.codex/AGENTS.md` (líneas ~95-115) ahora incluye una sección nueva `## Tripartita Refinada — verifiable contracts` con 4 reglas:
  1. **Verification Gate.** El documenter debe usar `cortex_verify_session_claims` antes de `cortex_save_session` y etiquetar memorias con `confidence`.
  2. **Handoff schema.** Cada handoff debe ser YAML validado por `cortex_validate_handoff`. **Particularidad de Codex:** la nota explícita "Codex has no native `Task` tool, so the handoff is the agent's last message — the next agent (or the user re-prompting in a new role) consumes that YAML as input." Esto explicita el workaround por convención que el plan §3 menciona.
  3. **Status `handoff` first-class.** Cerrar con `handoff` (no `completed`) si una verificación falla.
  4. **CONTEXT.md awareness.** Consultar antes de inventar términos; sugerir vía `suggested_context_terms`.

**Decisión técnica:** las 4 reglas viven en una sección dedicada (mismo patrón que Plan 03 en `CLAUDE.md`) para que un adopter pueda saltar directo al contrato Tripartita Refinada sin re-leer las reglas pre-existentes. La nota sobre la ausencia de `Task` nativo es **específica de Codex** y no aparece en CLAUDE.md ni en el AGENTS.md de Pi — explica explícitamente el workaround del Plan 06 §3 (delegación por convención, no por tool).

### Cambios 2-5 — Inheritance, delegación, hook autopilot, MCP discovery (sin código)

**Sin cambios de código en estos 4 puntos.** Plan 06 explícitamente los marca como "no acción" porque:

- **Cambio 2** — los archivos en `.codex/skills/*.md` y `.codex/agents/*.md` heredan automáticamente del canonical vía `get_subagent_prompt`. Verificación: tests de inheritance entregados (ver "Tests entregados" abajo).
- **Cambio 3** — la delegación por convención no requiere código; se documenta en `AGENTS.md` (sección nueva, ver Cambio 1) y en la doc-guide (sección "Nota sobre delegación en Codex").
- **Cambio 4** — `.codex/autopilot.md` con marker `AUTOPILOT-CODEX` ya soporta `status: handoff` automáticamente porque el autopilot service lo persiste en `state.json` (Plan 01 §5).
- **Cambio 5** — los 2 tools nuevos del MCP server (`cortex_validate_handoff`, `cortex_verify_session_claims`) se exponen vía MCP discovery; Codex los descubre sin configuración manual.

**Decisión técnica:** entregué los tests de inheritance acá (en vez de diferirlos a Plan 07). Cubren exactamente lo que el smoke manual buscaría detectar (drift entre canonical y materializado), y dejarlo en Plan 07 implicaría llevar contexto de Plan 06 hasta el último plan. Mismo razonamiento que apliqué en Plan 03.

### Doc-guide actualizada

**Archivos tocados:**
- `docs/guides/ide-codex.md` — agregué sección `## Tripartita Refinada (0.5.0)` con 4 sub-secciones (mismas que CLAUDE.md/OpenCode) + una sub-sección extra **"Nota sobre delegación en Codex"** que explica el flujo de turnos manual (Codex sin `Task` nativo) y sugiere considerar Claude Code u OpenCode si el usuario siente que la cadena es burocrática.

La sección queda posicionada antes de "Próximos pasos" para que un adopter vea primero los contratos nuevos antes de los pasos generales.

## Edge cases encontrados durante implementación

**Aserción de la nota sobre `Task` nativo:** quería verificar en el test que el AGENTS.md menciona explícitamente la ausencia de `Task` nativo en Codex (porque es la información crítica para que el adopter entienda el flujo de turnos). Lo verifico con un OR de dos formas posibles ("no native `Task`" o "Codex has no native") para tolerar pequeñas variaciones futuras del wording sin romper el test.

**Sin cambios al `inject_mcp`:** el plan §5 menciona que los 2 tools nuevos del MCP se exponen automáticamente. Verifiqué que el adapter no necesita modificaciones — ya pasa `--project-root <abs>` al `cortex mcp-server --stdio`, y el server expone todos los tools que registra en `_setup_tools` (Plan 02 §1 y §2). El test `test_codex_adapter_inject_mcp_uses_absolute_path` pre-existente sigue cubriendo esa parte sin cambios.

## Tests acumulados en Plan 06

| Archivo | Tests nuevos | Total verde |
|---------|-------------|-------------|
| `tests/unit/test_ide_adapters.py` | 3 (`TestCodexTripartitaRefinada`) | 32 |
| **Total Plan 06** | **+3** | **+3** vs baseline |

Tests nuevos:
- `TestCodexTripartitaRefinada::test_agents_md_mentions_verification_gate` — los 6 markers + la nota sobre `Task` nativo.
- `TestCodexTripartitaRefinada::test_documenter_agent_inherits_canonical_markers` — los 6 markers Plan 01 en `.codex/agents/cortex-documenter.md`.
- `TestCodexTripartitaRefinada::test_explorer_and_implementer_inherit_anti_rationalization` — markers en los 2 agents restantes.

## Suite global al cierre

```
$ python -m pytest tests/unit tests/integration --no-cov
814 passed, 6 skipped, 0 failed in 22.18s
```

Baseline pre-Plan 06 (cierre de Plan 05): 811 passed. Delta: **+3** (los 3 tests nuevos).

## Hallazgos para próximos planes

### Para Plan 07 (tests + cierre + bump 0.5.0)

1. **Bloque IDE (Planes 03-06) cerrado al 100%.** Los 4 IDEs target (Claude Code, OpenCode, Pi, Codex) tienen sus contratos Tripartita Refinada materializados y testeados. Plan 07 puede arrancar con la confianza de que el bloque IDE está completo.

2. **Tests de inheritance distribuidos en Planes 03 y 06.** Originalmente el plan 03 difería esos tests a Plan 07; los entregué tanto en Plan 03 (Claude Code) como en Plan 06 (Codex) porque eran la cobertura natural del cambio. Plan 07 puede agregar un test e2e cross-IDE que verifique los 4 IDEs juntos en una sola corrida — eso sería el cierre simbólico del bloque IDE.

3. **`MemoryEntry.confidence` empieza a tener consumidores reales.** Plan 02 lo introdujo en respuestas del MCP server; Plan 05 lo mencionó en el skill cortex-vault de Pi; Plan 06 lo menciona en la doc-guide de Codex. Plan 07 puede agregar un test e2e que persiste una memoria con `confidence: verified` y verifica que aparece en una búsqueda subsiguiente con el label correcto.

4. **Suite a esperar al cierre Plan 07:** ~875+ tests vs 814 hoy. El delta esperado depende del scope de tests e2e del Plan 07.

5. **Bump a 0.5.0:** Plan 07 §X debería bumpear `pyproject.toml` y `cortex/__init__.py` de 0.4.0 a 0.5.0 como último paso, una vez que toda la suite (incluyendo cualquier test e2e nuevo) está verde.

## Archivos modificados (total)

### Código
- `cortex/ide/adapters/codex.py` — bloque AGENTS.md ampliado con sección "Tripartita Refinada — verifiable contracts" + 4 reglas (incluye nota explícita sobre Codex sin `Task` nativo).

### Tests
- `tests/unit/test_ide_adapters.py` — clase nueva `TestCodexTripartitaRefinada` con 3 tests + helper `_setup_canonical` (idéntico al de Plan 03).

### Documentación
- `docs/agents/plan/06-ide-codex.md` — frontmatter status, todos los checkboxes marcados (excepto smoke manual).
- `docs/agents/implementacion/README.md` — entrada 06 marcada CERRADA.
- `docs/agents/implementacion/06-ide-codex.md` — este archivo.
- `docs/guides/ide-codex.md` — sección "Tripartita Refinada (0.5.0)" agregada con 4 sub-secciones + "Nota sobre delegación en Codex".

## Próximo paso

**Plan 07 — Tests, cierre y bump a 0.5.0.** El último plan de Tripartita Refinada. Scope esperado:

- Test e2e cross-IDE que verifica los 4 IDEs target heredan los markers Plan 01 en una sola corrida.
- Test e2e de la cascade `cortex_save_session` con `handoff=True` end-to-end (no solo el forward de kwargs en el MCP layer).
- Eventual heurística de negación para el bucket `contradicted` del `cortex_verify_session_claims` (Plan 02 §2 dejó el bucket vacío).
- Hook automático de `validate_handoff`/`expected_input_agent` en una extensión Pi futura — opcional, puede quedar como roadmap post-0.5.0.
- Bump de versión en `pyproject.toml` y `cortex/__init__.py` de 0.4.0 → 0.5.0.
- Actualización de `CHANGELOG.md` con entry de Tripartita Refinada.

Ver `docs/agents/plan/07-tests-y-cierre.md`.
