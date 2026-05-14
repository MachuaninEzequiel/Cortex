---
title: Tripartita Refinada — Hardening post-adopters (0.5.0)
status: ✅ CERRADA AL 100% (2026-05-14)
prerequisitos: Olas 0-4 cerradas (Cortex 0.4.0)
sucede a: Olas 0-4 (pre-adopters)
suite_at_close: 831 passed, 6 skipped, 0 failed
ciclo: 7 planes (Plan 01-07)
---

# Tripartita Refinada — Hardening post-adopters (0.5.0)

Este documento es el **cierre simbólico** del ciclo Tripartita Refinada, ejecutado el 2026-05-13/14 sobre la base Cortex 0.4.0 (cerrada por Olas 0-4). A diferencia de las Olas — que eran trabajo pre-adopters orientado a "framework funcionando completamente" —, Tripartita Refinada es **hardening de la promesa central**: convertir los contratos entre subagents en artefactos verificables.

## Por qué "Tripartita Refinada" y no "Ola 5"

Decisión tomada el primer día del ciclo (2026-05-13): las olas pre-adopters terminaron en Ola 4. Lo que sigue se llama Tripartita Refinada porque la propuesta de fondo (`docs/agents/MEJORA-TRIPARTITO.md`) es **refinar el modelo tripartito** sync → SDDwork → documenter introduciendo:

1. Handoffs estructurados entre agents (no más prosa libre).
2. Verification Gate del documenter contra el git diff real.
3. Confidence labels en cada memoria persistida (`verified` / `asserted` / `contradicted`).
4. CONTEXT.md como prompt asset con términos canónicos del proyecto.
5. Anti-rationalization signals por agent (atajos mentales conocidos vs realidad vs acción).
6. Status `handoff` first-class para sesiones con trabajo abierto.

El nombre del ciclo se refleja también en el versionado (0.4.0 pre-adopters → 0.5.0 post-adopters / Tripartita Refinada).

## Resumen del cierre

**Ejecutado en 7 planes** bajo el ciclo `docs/agents/plan/<NN>-*.md` (planes ejecutables) + `docs/agents/implementacion/<NN>-*.md` (bitácoras de qué se hizo realmente):

| Plan | Scope | Suite delta |
|------|-------|-------------|
| 01 — Subagents y skills canonical | Schema `AgentHandoff`, prompts canonical, confidence en MemoryEntry, status handoff, CONTEXT.md template | +29 (con re-corrida) |
| 02 — MCP server | 2 tools nuevos, cascade `save_session(handoff=...)`, confidence en respuestas | +15 → 799 |
| 03 — IDE Claude Code | Template `CLAUDE.md` + 4 reglas + tests inheritance | +3 → 802 |
| 04 — IDE OpenCode | 2 tools handoff/verify en `cortex_profiles` + tests | +3 → 805 |
| 05 — IDE Pi (caso especial) | `sync_canonical_subagents`, 4 agents Pi-only, agent-chain hooks, damage-control rules, vault skill | +6 → 811 |
| 06 — IDE Codex | Template `.codex/AGENTS.md` + 4 reglas + tests inheritance | +3 → 814 |
| 07 — Tests cross-IDE, cierre, bump | Smoke parametrizado, MCP tools registrados, cascade end-to-end, CHANGELOG, bump 0.5.0 | +17 → 831 |

**Suite global al cierre:** `831 passed, 6 skipped, 0 failed in 22.58s` (vs Plan 01 baseline 749 → +82 nuevos).

## Decisiones estratégicas tomadas durante el ciclo

1. **Tripartita Refinada ≠ Ola 5.** Las olas son features pre-adopters (cerradas). Tripartita Refinada es hardening post-adopters. Bump 0.4.0 → 0.5.0.

2. **Schema `AgentHandoff` soporta 7 agent names** (5 generales + 2 Pi-only `cortex-security-auditor`, `cortex-test-verifier`). Decisión preventiva para evitar dos schemas duplicados — el schema único maneja todos los agents que pueden emitir handoffs.

3. **CONTEXT.md es opcional.** Auto-create idempotente en `setup full`. Si el adopter no lo edita, queda con tabla vacía y los skills lo leen sin problemas (lo encuentran pero no encuentran términos).

4. **`_meets_adr_criteria` es module-level, no método.** Filtro lógica pura sin estado, debería poder llamarse desde cualquier parte del codebase sin instanciar `DocGenerator`.

5. **Plan 01 + Plan 02 deben mergearse juntos antes de bumpear versión.** Plan 01 referencia tools que Plan 02 crea. Si un IDE corre el documenter de Plan 01 sin tener Plan 02 mergeado, el agente falla al invocar tool inexistente. Mitigación documentada en CHANGELOG y bitácoras.

6. **Tests de inheritance entregados en Planes 03 y 06**, no diferidos a Plan 07. Cubren exactamente lo que el smoke manual buscaría detectar; dejarlo en Plan 07 implicaría llevar contexto cross-plan.

7. **`agent-chain.yaml` keys declarativas.** Pi: `validate_handoff` + `expected_input_agent` por step son declarativas — la extensión Pi actual las ignora; el orquestador SDDwork hace la validación manualmente vía la sección "Validación de handoffs" del prompt. Cuando un futuro runtime Pi implemente el hook automático, las keys ya están listas para ser consumidas sin rework.

8. **Heurística de `cortex_verify_session_claims` es first-pass.** Solo distingue `verified` (≥2 tokens del claim aparecen en el diff) vs `asserted`. El bucket `contradicted` está declarado pero vacío — falta heurística de negación que no estaba en alcance. Nota como mejora futura (puede entrar en 0.6.x si los adopters lo piden).

## Smoke contractual (lo que el usuario debe hacer manualmente antes del release)

Los tests automatizados cubren todo lo automatizable, pero hay un smoke manual que solo el usuario puede ejecutar (es interactivo y depende del entorno local). El check-list para antes del anuncio de 0.5.0:

```bash
# 1. Crear repo limpio
mkdir /tmp/cortex-tripartita-smoke && cd /tmp/cortex-tripartita-smoke
git init && echo "# smoke" > README.md && git add . && git commit -m "init"

# 2. Setup full y verificar version
cortex --version                      # → cortex 0.5.0
cortex setup full --non-interactive --git-depth 1
cortex doctor --scope all             # → 0 FAIL/0 WARN

# 3. Inject los 4 IDEs target y verificar markers Tripartita Refinada
for ide in claude-code opencode codex pi; do
    cortex inject --ide $ide
done

# 4. Markers esperados (chequear con grep):
grep -l "Verification Gate" CLAUDE.md                      # claude-code
grep -l "cortex_validate_handoff" CLAUDE.md
grep -l "VERIFICATION GATE" .claude/agents/cortex-documenter.md
grep -l "Verification Gate" .codex/AGENTS.md               # codex
grep -l "Validación de handoffs" .pi/agents/cortex-SDDwork.md   # pi
grep -l "handoffRules" .pi/damage-control-rules.yaml
# OpenCode escribe a ~/.config/opencode/, no al proyecto.
```

Si todos los markers aparecen y `cortex doctor` está verde, Tripartita Refinada está empíricamente desplegado.

## Limitaciones honestas (lo que NO entró en Tripartita Refinada)

1. **Heurística de negación para `contradicted`.** El bucket existe pero ninguna memoria llega ahí. Mejora futura (0.6.x si los adopters lo piden).

2. **Hook automático de validate_handoff en Pi runtime.** Las keys `validate_handoff` + `expected_input_agent` están en `agent-chain.yaml` pero la extensión Pi actual las ignora. El orquestador SDDwork lo hace manualmente vía prompt. Mejora futura: extensión TypeScript que consuma las keys (0.6.x).

3. **Smoke nightly automatizado.** Existe el item #5 del roadmap post-adopters (`docs/roadmap/post-adopters.md`) que pide crear `tests/smoke/scenarios/*.py` + workflow CI nightly. Tripartita Refinada cerró la parte de Pi sync (mecanismo + tests) pero no el smoke nightly automatizado. Item permanece abierto.

4. **Benchmark de overhead.** Plan 07 §4 sugería medir overhead < 10% del ciclo tripartito. No se ejecutó porque requiere instrumentar tiempo real con un LLM corriendo, fuera del scope automatizable. Queda como verificación opcional pre-release.

## Cómo retomar después de Tripartita Refinada

Para el agente Cortex en una sesión futura:

1. **Releé `docs/agents/implementacion/HANDOFF-2026-05-14.md`** — handoff intencional cross-session escrito al cierre del Plan 02.
2. **Releé `docs/review/cortex-save-state.md`** para el mapa mental general.
3. **Si el feedback de los adopters trae nuevos requirements**, anclarlos en `docs/roadmap/post-adopters.md` y planearlos como nuevo ciclo (no más "Olas").
4. **Si surge un bug en el flujo tripartito**, releé las bitácoras `docs/agents/implementacion/01-07-*.md` para entender el diseño de cada pieza antes de tocar nada.

## Archivos modificados en Tripartita Refinada (consolidado)

### Código nuevo
- `cortex/handoff.py` (nuevo, 125 líneas) — schema `AgentHandoff` + `ArtifactProduced`.

### Código modificado
- `cortex/__init__.py` — bump 0.5.0.
- `cortex/cli/main.py` — flag `--sync-canonical/--no-sync-canonical`.
- `cortex/core.py` — `AgentMemory.save_session_note` con 5 nuevos kwargs.
- `cortex/doc_generator.py` — helper `_meets_adr_criteria`.
- `cortex/documentation.py` — `write_session_note` con handoff mode + 4 secciones nuevas condicionales.
- `cortex/ide/__init__.py` — `inject` con kwarg `sync_canonical`.
- `cortex/ide/adapters/{claude_code,codex,opencode,pi}.py` — los 4 adapters Tripartita-aware.
- `cortex/mcp/server.py` — 2 tools nuevos + cascade del save_session.
- `cortex/models.py` — `MemoryEntry.confidence` + `EnrichedItem.confidence` + propagación en prompts.
- `cortex/services/session_service.py` — cascade del create.
- `cortex/setup/orchestrator.py` y `cortex/setup/templates.py` — auto-create idempotente de CONTEXT.md.
- `cortex/workspace/layout.py` — property `context_md_path`.
- `cortex/autopilot/{models,session_writer}.py` — status `handoff` + tag automático.

### Canonical prompts (5 archivos)
- `.cortex/subagents/cortex-{code-explorer,code-implementer,documenter}.md`
- `.cortex/skills/cortex-{sync,SDDwork}.md`

### Bundle Pi (7 archivos)
- `cortex-pi/.pi/agents/cortex-{sync,SDDwork,security-auditor,test-verifier}.md`
- `cortex-pi/.pi/agents/agent-chain.yaml`
- `cortex-pi/.pi/damage-control-rules.yaml`
- `cortex-pi/.pi/skills/cortex-vault/SKILL.md`

### Tests (~82 nuevos)
- `tests/unit/test_handoff.py` (nuevo, 12 tests)
- `tests/unit/test_tripartita_refinada.py` (nuevo, 17 tests)
- `tests/unit/test_mcp_server.py` (+17 tests)
- `tests/unit/test_ide_adapters.py` (+22 tests)
- `tests/unit/test_documentation.py` (+3 tests)
- `tests/unit/cli/test_main.py` (1 modificado + 1 nuevo)
- `tests/e2e/test_artefact_integrity.py` (mapping actualizado)

### Documentación
- `docs/agents/MEJORA-TRIPARTITO.md` y `docs/agents/ANALISIS-COMPLETO.md` (análisis previo, ya existían).
- `docs/agents/plan/01-07-*.md` (7 planes ejecutables, ya existían — actualizados con frontmatter status y checkboxes).
- `docs/agents/implementacion/01-07-*.md` (7 bitácoras de implementación, nuevas).
- `docs/agents/implementacion/HANDOFF-2026-05-13.md` y `HANDOFF-2026-05-14.md` (continuidad cross-session, nuevos).
- `docs/agents/implementacion/README.md` (índice actualizado).
- `docs/guides/ide-{claude-code,opencode,pi,codex}.md` (sección Tripartita Refinada agregada).
- `docs/olas/tripartita-refinada.md` (este archivo).
- `CHANGELOG.md` (entrada `[0.5.0]`).

## Cierre

Tripartita Refinada está cerrada. Cortex 0.5.0 listo para los próximos onboardings. La promesa central — memoria limpia, agentes con contratos verificables — ya no es aspiracional: está testeada, documentada y materializada en los 4 IDEs target.
