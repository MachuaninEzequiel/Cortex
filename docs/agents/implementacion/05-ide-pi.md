---
title: Implementación 05 — Materialización en Pi Coding Agent
plan: ../plan/05-ide-pi.md
status: ✅ CERRADA (2026-05-14)
suite_at_close: 811 passed, 6 skipped, 0 failed (unit + integration)
delta_vs_plan_04_baseline: +6 tests
---

# Implementación 05 — Materialización en Pi Coding Agent

Bitácora de ejecución del Plan 05 (Tripartita Refinada — IDE Pi). **Cerrada al 100% de items automatizables.** El smoke manual queda como verificación opcional del usuario antes del release de 0.5.0.

Pi es el IDE más afectado por Tripartita Refinada porque (a) tiene 7 agents en lugar de 3, (b) trae infraestructura propia en `cortex-pi/` que históricamente driftea de los archivos canonical, y (c) tiene `agent-chain.yaml` declarativo y `damage-control-rules.yaml` que requieren cambios alineados.

## Estado del checklist del plan original

- [x] §1 `PiAdapter.sync_canonical_subagents` + `inject_profiles` refactor
- [x] §1 CLI flag `--sync-canonical / --no-sync-canonical`
- [x] §1 6 tests verdes (5 del adapter + 1 del CLI)
- [x] §2 Los 4 agents Pi-only actualizados (sync, SDDwork, security-auditor, test-verifier)
- [x] §3 `agent-chain.yaml` con keys declarativas `validate_handoff` + `expected_input_agent`
- [x] §4 `damage-control-rules.yaml` con sección `handoffRules`
- [x] §5 `cortex-vault/SKILL.md` con CONTEXT.md awareness + confidence labels
- [x] `docs/guides/ide-pi.md` extendida con sección Tripartita Refinada
- [ ] Smoke manual `cortex inject --ide pi` — pendiente del usuario

## Bitácora detallada

### §1 — `PiAdapter.sync_canonical_subagents` + CLI flag

**Archivos tocados:**

- `cortex/ide/adapters/pi.py`:
  - Constante module-level `_SHARED_AGENTS` con los 3 nombres (`cortex-code-explorer.md`, `cortex-code-implementer.md`, `cortex-documenter.md`).
  - Helper `_default_pi_bundle_dir()` que resuelve `cortex-pi/` desde `Path(__file__)` (4 parents up).
  - Método nuevo `sync_canonical_subagents(project_root, *, bundle_dir=None) -> list[Path]`. Si `.cortex/subagents/` no existe (proyecto fresco), retorna lista vacía sin escribir nada. Si `bundle_dir` es None, usa el path real; tests pasan tmp dir. Idempotente.
  - `inject_profiles` ampliado con kwarg `sync_canonical: bool = True`. Por default invoca `sync_canonical_subagents` antes de copiar. `sync_canonical=False` reproduce el comportamiento previo (raw bundle copy).
- `cortex/ide/__init__.py::inject` — ampliado con kwarg `sync_canonical=True`. Detecta el adapter por nombre (`adapter.name == "pi"`) y solo a Pi le pasa el flag — los otros adapters siguen llamándose vía `inject_all` sin cambios.
- `cortex/cli/main.py::inject` — flag Typer `--sync-canonical/--no-sync-canonical` (default True). Se pasa a `cortex_ide.inject` como kwarg.

**Decisión técnica:** elegí *detección por nombre* (`adapter.name == "pi"`) en vez de `isinstance(adapter, PiAdapter)` para evitar el import circular (cortex.ide.__init__ no puede importar cortex.ide.adapters.pi sin riesgo). El nombre es estable; si cambia, el test del adapter atrapa la regresión.

**Decisión de testabilidad:** el método acepta `bundle_dir` opcional para que los tests pasen `tmp_path` en lugar de mutar el bundle real del repo. Sin esto, los tests escribirían a `cortex-pi/.pi/agents/` durante la corrida y dejarían el repo en estado inconsistente.

**Tests entregados:**
- `TestPiSyncCanonicalSubagents::test_overwrites_bundle_with_canonical_content` — happy path, los 3 agents se copian con el contenido canonical.
- `TestPiSyncCanonicalSubagents::test_no_canonical_directory_returns_empty_list` — proyecto sin `.cortex/subagents/`, no escribe nada.
- `TestPiSyncCanonicalSubagents::test_partial_canonical_only_copies_what_exists` — si solo existe 1 de los 3, los otros no se tocan.
- `TestPiSyncCanonicalSubagents::test_inject_profiles_invokes_sync_by_default` — verifica que `inject_profiles()` llama a `sync_canonical_subagents`. Monkeypatchea `_default_pi_bundle_dir` con un dir noop para no copiar el bundle real al `tmp_path`.
- `TestPiSyncCanonicalSubagents::test_inject_profiles_skips_sync_when_disabled` — opt-out path: `sync_canonical=False` no invoca el sync.
- `tests/unit/cli/test_main.py::test_inject_no_sync_canonical_flag_propagates` — el flag CLI llega como kwarg a `cortex.ide.inject`.

**Edge case del test pre-existente:** `test_inject_uses_new_ide_module` mockeaba `cortex.ide.inject` con la firma vieja `(ide_name, project_root)`. Al agregar el kwarg, el mock fallaba con `TypeError: unexpected keyword argument 'sync_canonical'`. Lo arreglé extendiendo la firma del fake con `sync_canonical: bool = True` y un assert nuevo de que el default llega como `True`.

### §2 — 4 agents Pi-only actualizados

Cada uno recibió:
- **Sección "Anti-Rationalization Signals"** específica al rol — tabla de pensamientos comunes vs realidad vs acción correcta.
- **Sección "Contrato de Salida (Tripartita Refinada — Output Obligatorio)"** con bloque YAML conforme a `cortex.handoff.AgentHandoff`.

**Específicos por agent:**

- **`cortex-sync.md`**: además agregué sección "Pre-flight: cargar CONTEXT.md (Tripartita Refinada)" describiendo cuándo y cómo leer `CONTEXT.md` antes de invocar `cortex_sync_ticket`. El YAML incluye `suggested_context_terms` para términos nuevos detectados.

- **`cortex-SDDwork.md`**: además agregué sección "Validación de handoffs (orquestador)" que documenta cómo el SDDwork debe invocar `cortex_validate_handoff` con `expected_agent` antes de pasar al próximo step del chain. También documenta el comportamiento ante `status: blocked` (detener chain) vs `status: partial` (continuar pero marcar en `context_for_next`).

- **`cortex-security-auditor.md`** y **`cortex-test-verifier.md`**: el YAML está adaptado al rol — `verified_claims` debe listar exactamente qué herramientas corrieron (bandit, safety, pytest, mypy) y qué resultados dieron, no descripción vaga.

**Decisión técnica:** mantuve los mensajes finales originales al usuario (los `>` blockquotes) sin tocar — son contractos UX que no estaban en alcance de Tripartita Refinada. El YAML va **además** del mensaje, no en su lugar.

### §3 — `agent-chain.yaml`

Los 3 chains (`sddwork`, `hotfix`, `refactor`) recibieron 2 keys nuevas por step:
- `validate_handoff: true | false` — declara si el step espera handoff entrante (false solo para el primer step de cada chain).
- `expected_input_agent: <nombre>` — declara qué agent debe haber producido el handoff entrante.

**Decisión técnica:** estas keys son **declarativas** — la extensión Pi actual las ignora (yaml.load tolera campos extra). El orquestador `cortex-SDDwork` hace la validación manualmente vía la sección "Validación de handoffs" de su prompt. Cuando un futuro runtime Pi implemente el hook automático (e.g. via `validate_handoff` extension), las keys ya están listas para ser consumidas sin rework. Esto era exactamente la dualidad que el plan §3 contempla ("si Pi no soporta la key, dejar el formato actual + documentar en SDDwork").

Además, los `prompt:` de cada step ahora incluyen instrucciones explícitas: "Validá el handoff entrante" + "Cierre con bloque YAML AgentHandoff". El step de `cortex-documenter` agrega: "antes de cortex_save_session, ejecutá el Verification Gate (cortex_verify_session_claims)".

### §4 — `damage-control-rules.yaml`

Agregué sección nueva `handoffRules` (formato consistente con las secciones `bashToolPatterns` / `zeroAccessPaths` ya existentes) con 3 reglas:

- `handoff-malformed` (severity: block) — el chain DEBE detenerse si un YAML handoff falla `cortex_validate_handoff`.
- `handoff-status-mismatch` (severity: warn) — si declara `complete` pero `verified_claims` está vacío, persistir como `confidence: asserted`.
- `handoff-context-overflow` (severity: warn) — si `context_for_next` > ~2000 chars, truncar antes de pasar.

Cada regla tiene `description:` (multilinea explicando el motivo) y `action:` (lista de pasos a tomar). Compatible con el resto del archivo, no rompe los validators existentes.

### §5 — `cortex-vault/SKILL.md`

Agregué 2 secciones al final del skill:

- **CONTEXT.md awareness (Tripartita Refinada — 0.5.0)**: cómo leer y usar `CONTEXT.md` antes de buscar y antes de persistir. Aclara que NO se debe agregar términos directamente — se sugieren vía `suggested_context_terms` del handoff y el documenter decide.
- **Confidence labels en respuestas (Tripartita Refinada — 0.5.0)**: explica los labels `[verified]` / `[asserted]` / `[contradicted]` que aparecen en respuestas de `cortex search` y `cortex context` desde 0.5.0, y cómo interpretarlos (memorias sin label = pre-0.5.0, confianza media).

### Doc-guide actualizada

`docs/guides/ide-pi.md` ahora tiene una sección `## Tripartita Refinada (0.5.0)` con 5 sub-secciones que mapean uno-a-uno los §1-§5 del plan. Incluye ejemplo del flag `--no-sync-canonical` y explicación de cuándo usarlo.

## Edge cases encontrados durante implementación

**Test pre-existente roto por la nueva firma de `cortex.ide.inject`:** ya documentado en §1. Lo arreglé extendiendo el fake del mock con `sync_canonical: bool = True`.

**Detección isinstance vs nombre:** estuve a punto de hacer `isinstance(adapter, PiAdapter)` en `cortex.ide.__init__`, pero requiere importar `PiAdapter` ahí, lo que crea un riesgo de import circular (`pi.py` puede importar `cortex.ide.base` que importa `cortex.ide.__init__`). Detección por nombre es más simple y suficiente.

**Tests del adapter no deben mutar el bundle real:** los 5 tests usan `bundle_dir=tmp_path / "fake-bundle"` para `sync_canonical_subagents` directamente, y los 2 tests de `inject_profiles` monkeypatchan `_default_pi_bundle_dir` con un noop dir vacío. Esto fue crítico para que la suite no deje el repo en estado dirty después de correr (lo cual habría sido un bug ENORME — los tests escribirían al bundle del repo y futuras corridas verían contenido fabricado).

## Tests acumulados en Plan 05

| Archivo | Tests nuevos | Total verde |
|---------|-------------|-------------|
| `tests/unit/test_ide_adapters.py` | 5 (`TestPiSyncCanonicalSubagents`) | 29 |
| `tests/unit/cli/test_main.py` | 1 (`test_inject_no_sync_canonical_flag_propagates`) + 1 actualizado | (sin cambio en el total relevante para Plan 05) |
| **Total Plan 05** | **+6 nuevos** | **+6** vs baseline |

## Suite global al cierre

```
$ python -m pytest tests/unit tests/integration --no-cov
811 passed, 6 skipped, 0 failed in 22.98s
```

Baseline pre-Plan 05 (cierre de Plan 04): 805 passed. Delta: **+6** (5 del adapter + 1 del CLI).

## Hallazgos para próximos planes

### Para Plan 06 (Codex)

1. **Patrón de Plan 03 replicable.** El adapter Codex tiene `AGENTS.md` análogo al `CLAUDE.md` de Claude Code. Replicar: agregar sección Tripartita Refinada al template + test análogo a `test_claude_md_mentions_verification_gate`.

2. **Codex no requiere sync_canonical.** El adapter Codex copia desde `.cortex/subagents/` directamente (verificar leyendo el adapter), igual que Claude Code y OpenCode. Solo Pi tiene el problema del bundle congelado.

### Para Plan 07 (tests + cierre)

1. **`MemoryEntry.confidence` empieza a ser usado en serio.** El skill `cortex-vault` y los handoffs de Pi referencian los labels `[verified]`/`[asserted]`/`[contradicted]`. Plan 07 puede agregar tests e2e que verifiquen el flujo completo: implementador emite YAML → orquestador valida → documenter cruza claims → memoria persistida con confidence.

2. **`agent-chain.yaml` declarative keys quedan sin runtime support.** Plan 07 puede dejar como roadmap item: implementar el hook automático en una extensión Pi futura (TS) que consuma `validate_handoff` + `expected_input_agent`. No bloqueante para 0.5.0 — el orquestador ya hace la validación manualmente.

3. **Suite a esperar al cierre Plan 07:** ~875+ tests vs 811 hoy.

## Archivos modificados (total)

### Código
- `cortex/ide/adapters/pi.py` — `sync_canonical_subagents` + `inject_profiles` ampliado + helpers (`_SHARED_AGENTS`, `_default_pi_bundle_dir`).
- `cortex/ide/__init__.py::inject` — kwarg `sync_canonical` + detección por nombre del adapter Pi.
- `cortex/cli/main.py::inject` — flag CLI `--sync-canonical/--no-sync-canonical`.

### Tests
- `tests/unit/test_ide_adapters.py` — clase nueva `TestPiSyncCanonicalSubagents` con 5 tests + helper `_make_canonical`.
- `tests/unit/cli/test_main.py` — test nuevo `test_inject_no_sync_canonical_flag_propagates` + `test_inject_uses_new_ide_module` actualizado para reflejar la nueva firma.

### Bundle Pi (cortex-pi/)
- `cortex-pi/.pi/agents/cortex-sync.md` — Pre-flight CONTEXT.md + Anti-rationalization + Contrato YAML.
- `cortex-pi/.pi/agents/cortex-SDDwork.md` — Validación de handoffs + Anti-rationalization + Contrato YAML.
- `cortex-pi/.pi/agents/cortex-security-auditor.md` — Anti-rationalization + Contrato YAML.
- `cortex-pi/.pi/agents/cortex-test-verifier.md` — Anti-rationalization + Contrato YAML.
- `cortex-pi/.pi/agents/agent-chain.yaml` — keys `validate_handoff` + `expected_input_agent` en los 3 chains; prompts de cada step ampliados con instrucciones de validación.
- `cortex-pi/.pi/damage-control-rules.yaml` — sección `handoffRules` con 3 reglas.
- `cortex-pi/.pi/skills/cortex-vault/SKILL.md` — CONTEXT.md awareness + confidence labels.

### Documentación
- `docs/agents/plan/05-ide-pi.md` — frontmatter status, todos los checkboxes marcados (excepto smoke manual).
- `docs/agents/implementacion/README.md` — entrada 05 marcada CERRADA.
- `docs/agents/implementacion/05-ide-pi.md` — este archivo.
- `docs/guides/ide-pi.md` — sección "Tripartita Refinada (0.5.0)" con 5 sub-secciones.

## Próximo paso

**Plan 06 — IDE Codex.** Replicar el patrón de Plan 03 sobre el adapter Codex: agregar las 4 reglas Tripartita Refinada al template `AGENTS.md` (que el adapter renderiza para Codex) + test análogo a `test_claude_md_mentions_verification_gate`. Plan 06 no requiere mecanismo de sync (Codex consume canonical directamente, no tiene bundle congelado como Pi).

Ver `docs/agents/plan/06-ide-codex.md`.
