---
title: Implementación 03 — Materialización en Claude Code
plan: ../plan/03-ide-claude-code.md
status: ✅ CERRADA (2026-05-14)
suite_at_close: 802 passed, 6 skipped, 0 failed (unit + integration)
delta_vs_plan_02_baseline: +3 tests
---

# Implementación 03 — Materialización en Claude Code

Bitácora de ejecución del Plan 03 (Tripartita Refinada — IDE Claude Code).
**Cerrada al 100% de items automatizables.** El smoke manual queda como verificación
opcional del usuario antes del release de 0.5.0.

## Estado del checklist del plan original

- [x] `CLAUDE.md` template actualizado con 4 nuevas reglas
- [x] Test `test_claude_md_mentions_verification_gate` verde
- [x] Tests de inheritance entregados (en vez de diferirlos a Plan 07)
- [x] `docs/guides/ide-claude-code.md` extendido con sección Tripartita Refinada
- [ ] Smoke manual `cortex inject --ide claude-code` — pendiente del usuario

## Bitácora detallada

### Cambio 1 — CLAUDE.md template ampliado

**Archivos tocados:**
- `cortex/ide/adapters/claude_code.py::inject_profiles` — el bloque que escribe `CLAUDE.md` ahora incluye una nueva sección `## Tripartita Refinada — verifiable contracts` con 4 reglas de gobernanza:
  1. El documenter debe pasar el **Verification Gate** antes de invocar `cortex_save_session` y debe usar `cortex_verify_session_claims` para etiquetar las memorias con `confidence`.
  2. Cada handoff entre subagents debe ser un YAML validado por `cortex_validate_handoff` contra el schema `AgentHandoff` (prosa libre rechazada).
  3. `status: handoff` es first-class — si una verificación falla, cerrar con `handoff`, no con `completed`.
  4. CONTEXT.md awareness — consultar antes de inventar términos de dominio.

**Decisión técnica:** las 4 reglas viven en una sección dedicada (en vez de mezcladas con las reglas pre-existentes) para que un futuro adopter pueda saltar directamente al contrato Tripartita Refinada sin re-leer los fundamentos.

**Tests:** `TestClaudeCodeTripartitaRefinada::test_claude_md_mentions_verification_gate` verifica que aparezcan los 6 markers requeridos (`Verification Gate`, `cortex_validate_handoff`, `cortex_verify_session_claims`, `AgentHandoff`, `CONTEXT.md`, y `handoff` en algún form).

### Cambios 2-3 — Inheritance de skills y agents (sin código)

**Sin cambios de código.** El adapter Claude Code ya consume el canonical de `.cortex/skills/` y `.cortex/subagents/` vía `get_subagent_prompt`. Después de Plan 01, los archivos canonical contienen los 8 markers nuevos (`HIGH-SIGNAL`, `VERIFICATION GATE`, `Modo Handoff`, `Anti-rationalization`, `Contrato de Salida`, etc.) y se materializan automáticamente al correr `cortex inject --ide claude-code`.

**Tests entregados en lugar del smoke manual:**

- `TestClaudeCodeTripartitaRefinada::test_documenter_agent_inherits_canonical_markers` — fabrica un canonical sintético con los 6 markers del documenter, corre `inject_profiles`, y verifica que `.claude/agents/cortex-documenter.md` los contenga todos.
- `TestClaudeCodeTripartitaRefinada::test_explorer_and_implementer_inherit_anti_rationalization` — verifica que los dos agents restantes hereden `Anti-rationalization` y `Contrato de Salida`.

**Decisión técnica:** el plan original difería el "test automatizado de inheritance" al Plan 07. Lo entregué acá porque cubre exactamente la regresión que el smoke manual buscaría detectar (drift entre canonical y materializado), y dejarlo en Plan 07 implicaría llevar contexto de Plan 03 hasta el último plan.

### Cambio 4 — Toggle de tools MCP nuevos (sin código)

Plan 03 §4 indica que las tools MCP nuevas (`cortex_validate_handoff`, `cortex_verify_session_claims`) se exponen automáticamente vía MCP discovery — Claude Code no requiere configuración por tool. **Verificación implícita** vía Plan 02 §6 (tests de `MCP_TO_CLI` ya verifican que los tools están registrados en el server).

### Cambio 5 — CONTEXT.md awareness (sin código)

Plan 03 §5 indica que el CONTEXT.md awareness vive en el prompt canonical del skill `cortex-sync`, que ya fue actualizado en Plan 01 §3. El adapter Claude Code lo materializa sin modificación al correr inject_profiles. **Sin trabajo extra acá.**

### Doc-guide actualizada

**Archivos tocados:**
- `docs/guides/ide-claude-code.md` — agregué una sección `## Tripartita Refinada (0.5.0)` con 4 sub-secciones que describen al adopter:
  1. Qué cambió en `CLAUDE.md`.
  2. Qué tools nuevas aparecen en el MCP server.
  3. Cómo se ven las sesiones marcadas como handoff (frontmatter, secciones nuevas).
  4. Qué significa el label `[verified]`/`[asserted]`/`[contradicted]` en respuestas de búsqueda.

La sección quedó posicionada **antes** de "Próximos pasos" para que un adopter que llega a la guía vea primero los contratos nuevos antes de los pasos generales de webgraph/memory-report.

## Edge cases encontrados durante implementación

**Asserción de `status: handoff` en CLAUDE.md fue tricky:** la frase exacta `status: handoff` aparece en el body como `\`status: handoff\``. La aserción del test la matchea con `.lower()` y un OR para aceptar ambas formas (`status: handoff` o `\`handoff\``), evitando falsos negativos por variación de comillas/markdown.

**El test `test_documenter_agent_inherits_canonical_markers` requiere setup canonical sintético:** no podemos depender del canonical real del repo (`.cortex/subagents/cortex-documenter.md`) porque el test correría con paths del repo de desarrollo y leakearía estado. La fixture `_setup_canonical` fabrica un canonical mínimo con todos los markers, garantizando independencia del estado actual del repo.

## Tests acumulados en Plan 03

| Archivo | Tests nuevos | Total verde |
|---------|-------------|-------------|
| `tests/unit/test_ide_adapters.py` | 3 | 21 |
| **Total Plan 03** | **+3** | **+3** vs baseline |

Tests nuevos:
- `TestClaudeCodeTripartitaRefinada::test_claude_md_mentions_verification_gate`
- `TestClaudeCodeTripartitaRefinada::test_documenter_agent_inherits_canonical_markers`
- `TestClaudeCodeTripartitaRefinada::test_explorer_and_implementer_inherit_anti_rationalization`

## Suite global al cierre

```
$ python -m pytest tests/unit tests/integration --no-cov
802 passed, 6 skipped, 0 failed in 22.62s
```

Baseline pre-Plan 03 (cierre de Plan 02): 799 passed. Delta: **+3** (los 3 tests nuevos).

## Hallazgos para próximos planes

### Para Plan 04 (OpenCode)

1. **Patrón replicable.** OpenCode tiene un adapter análogo (`cortex/ide/adapters/opencode.py`). Debería replicar el mismo cambio: agregar las 4 reglas Tripartita Refinada al equivalente del CLAUDE.md (probablemente el AGENTS.md o el system prompt del adapter). Verificar que el adapter ya consume canonical de `.cortex/subagents/` (lo hace, según los tests pre-existentes).

2. **Diferencias a tener en cuenta.** OpenCode usa `~/.config/opencode/opencode.json` (home dir, no project root) para el MCP config. El bloque equivalente al CLAUDE.md template podría estar en `system_prompt` del config, no en un archivo separado. Leer Plan 04 antes de inferir.

### Para Plan 05 (Pi)

1. **CRITICAL recordatorio:** Pi NO consume canonical de `.cortex/subagents/` directamente — copia desde el bundle `cortex-pi/.pi/agents/`. El bundle no está sincronizado. Plan 05 §1 implementa el `sync_canonical_subagents` mecanismo. **Sin ese mecanismo Plan 05 va a fallar silenciosamente.**

### Para Plan 06 (Codex)

1. **AGENTS.md es el equivalente de CLAUDE.md.** El adapter Codex (`cortex/ide/adapters/codex.py`) escribe `.codex/AGENTS.md`. El test `test_codex_adapter_inject_profiles` ya verifica markers básicos (`cortex-sync`, `cortex_create_spec`). Replicar el patrón de Plan 03: agregar las 4 reglas Tripartita Refinada al AGENTS.md template y un test análogo a `test_claude_md_mentions_verification_gate`.

### Para Plan 07 (tests + cierre)

1. **Tests de inheritance ya entregados** (originalmente diferidos a Plan 07). Plan 07 §X queda con menos scope.

2. **Suite a esperar al cierre Plan 07:** ~875+ tests vs 802 hoy.

## Archivos modificados (total)

### Código
- `cortex/ide/adapters/claude_code.py` — bloque CLAUDE.md ampliado con sección "Tripartita Refinada — verifiable contracts" + 4 reglas.

### Tests
- `tests/unit/test_ide_adapters.py` — clase nueva `TestClaudeCodeTripartitaRefinada` con 3 tests + helper `_setup_canonical`.

### Documentación
- `docs/agents/plan/03-ide-claude-code.md` — frontmatter status, todos los checkboxes marcados (excepto smoke manual que queda al usuario).
- `docs/agents/implementacion/README.md` — entrada 03 marcada CERRADA.
- `docs/agents/implementacion/03-ide-claude-code.md` — este archivo.
- `docs/guides/ide-claude-code.md` — sección "Tripartita Refinada (0.5.0)" agregada con 4 sub-secciones.

## Próximo paso

**Plan 04 — IDE OpenCode.** Replicar el patrón de Plan 03 sobre el adapter OpenCode: identificar dónde se materializa el equivalente del CLAUDE.md (probablemente system_prompt en `opencode.json`), agregar las 4 reglas Tripartita Refinada, y agregar un test equivalente a `test_claude_md_mentions_verification_gate`.

Ver `docs/agents/plan/04-ide-opencode.md`.
