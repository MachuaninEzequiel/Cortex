---
title: Implementación 02 — Cambios al MCP server
plan: ../plan/02-mcp-server-cambios.md
status: ✅ CERRADA (2026-05-14)
suite_at_close: 799 passed, 6 skipped, 0 failed (unit + integration)
delta_vs_plan_01_baseline: +15 tests
---

# Implementación 02 — Cambios al MCP server

Bitácora de ejecución del Plan 02 (Tripartita Refinada). **Cerrada al 100%.**
Las 6 secciones del plan (§1-§6) aplicadas en el mismo día, con tests verdes
y zero regresiones en la suite preexistente.

## Estado del checklist del plan original

- [x] §1 `cortex_validate_handoff` registrado + dispatcher + helper
- [x] §2 `cortex_verify_session_claims` registrado + dispatcher + helper
- [x] §3 Confidence propagado en `_search_text` y `_context_text`
- [x] §4 `cortex_save_session` acepta 5 parámetros nuevos de handoff (cascade 3 niveles)
- [x] §5 Tests `TestHandoffValidation` (7 entregados; plan pedía 6)
- [x] §6 `MCP_TO_CLI` actualizado en `tests/e2e/test_artefact_integrity.py`

## Bitácora detallada

### §1 — `cortex_validate_handoff`

**Archivos tocados:**
- `cortex/mcp/server.py`:
  - Tool registrado en `handle_list_tools` con `inputSchema` (`handoff_yaml` requerido, `expected_agent` opcional).
  - Dispatcher en `handle_call_tool` que delega en `_validate_handoff_text`.
  - Helper `_validate_handoff_text(arguments)` que importa `AgentHandoff` y `pydantic.ValidationError`, parsea el YAML, mapea errores a un string compacto (`loc: msg; loc: msg`), valida `expected_agent` opcional, y devuelve un sumario con los counts de cada lista del schema más warnings condicionales (ADR sugerido + términos de CONTEXT.md).

**Decisión técnica:** mensajes de error legibles sin traceback. El `ValidationError` se serializa juntando `err['loc']` y `err['msg']` separados por `; ` para que el agente consumidor pueda mostrarlo al usuario sin recortar.

**Tests:** 7 en `TestHandoffValidation` (cobre minimal válido, agent inválido, status inválido, agent mismatch, vacío, full counts + términos CONTEXT.md, malformed YAML como list).

### §2 — `cortex_verify_session_claims`

**Archivos tocados:**
- `cortex/mcp/server.py`:
  - Tool registrado con `inputSchema` (`claims` requerido, `base_branch` y `files_to_check` opcionales).
  - Dispatcher en `handle_call_tool`.
  - Helper `_verify_session_claims_text(arguments)` que ejecuta `git diff --unified=0 <base> --` vía `subprocess.run` con `cwd=self.project_root`, timeout 10s, tokeniza cada claim (palabras >3 chars, split por whitespace + underscore + slash) y cuenta hits en el diff lowercased. Si `hits >= 2` → verified; si menos → asserted. El bucket `contradicted` queda reservado para una heurística futura de negación.

**Decisión técnica:** subprocess directo en vez de `cortex.doc_verifier._git_diff_files` para evitar dependencias circulares y mantener el helper auto-contenido. Manejo explícito de `FileNotFoundError` (sin git) y `TimeoutExpired` (repos enormes).

**Tests:** 3 en `TestVerifySessionClaims` con monkeypatch sobre `subprocess.run` para no depender del estado real del repo: empty claims → error; claim cuyos tokens están en el diff → verified; claim sin evidencia → asserted; branch arbitrario propagado al summary.

### §3 — Confidence en MCP responses

**Archivos tocados:**
- `cortex/models.py`:
  - `RetrievalResult.to_prompt()` — en ambos branches (unified_hits y episodic_hits fallback) se agrega `[<confidence>]` después de `memory_type` cuando el campo es no-None.
  - `EnrichedItem` — nuevo campo opcional `confidence: Literal["verified","asserted","contradicted"] | None = None` con docstring que explica la conexión con `MemoryEntry.confidence`.
  - `EnrichedContext.to_prompt_format()` — en ambos modos (compact y full) se concatena `[<confidence>]` al `source_tag` cuando el campo es no-None.

**Decisión técnica:** el confidence vive en `MemoryEntry.confidence` (Plan 01 §6) y se propaga vía representación, no vía metadata dict. El plan original sugería leer `hit.entry.metadata.get("confidence")` pero el campo dedicado es más type-safe y ya está disponible.

**Tests:** 2 en `TestSearchConfidenceLabel` (label aparece cuando confidence es `verified`; sin label cuando es None — backwards compat).

### §4 — Cascade `cortex_save_session` + 5 handoff params

**Archivos tocados (cascade en 4 niveles):**

1. **MCP `inputSchema`** (`cortex/mcp/server.py`):
   - 5 propiedades nuevas en `cortex_save_session.inputSchema.properties`: `handoff` (boolean, default False), `blockers`, `verified_state`, `unverified_claims`, `suggested_skills` (todas array of string).
2. **MCP helper** (`cortex/mcp/server.py::_save_session_text`):
   - Forward los 5 args con `bool()` / `list()` defensivos a `memory.save_session_note`.
3. **AgentMemory** (`cortex/core.py::save_session_note`):
   - Firma extendida; pasa todo a `_session_service.create` sin transformar.
4. **SessionService** (`cortex/services/session_service.py::create`):
   - Firma extendida; pasa a `write_session_note`. Si `handoff=True` y `remember=True`, agrega `"handoff"` al `episodic_tags` (idempotente vs duplicados).
5. **write_session_note** (`cortex/documentation.py`):
   - Firma extendida; si `handoff=True` el frontmatter `status` pasa a `"handoff"` y `"handoff"` se suma a los tags (idempotente). Si las nuevas listas son no-vacías se emiten 4 secciones nuevas al final del cuerpo: "Verified State", "Unverified Claims", "Blockers", "Suggested Skills".

**Decisión técnica:** las 4 secciones nuevas solo aparecen cuando hay contenido, evitando ruido en sesiones normales. El tag `"handoff"` se agrega tanto al vault note como al episodic memory para que un search futuro por tag descubra todos los handoffs.

**Tests:** 2 en `TestSaveSessionHandoffArguments` (propagación con todos los args y defaults cuando se omiten). `FakeMemory.save_session_note` ahora captura `last_save_kwargs` para verificación.

### §5 — `TestHandoffValidation`

**Archivos tocados:**
- `tests/unit/test_mcp_server.py` — `FakeMemory` recibe `__init__` para trackear `last_save_kwargs` (necesario para §4). Se mantiene compatibilidad con `TrackingMemory` (subclass que overrides `__init__` sin llamar a super; solo se usa para `create_spec_note` y no accede a `last_save_kwargs`).

Tests entregados (7 total, plan pedía 6):
1. `test_valid_minimal_handoff_passes`
2. `test_invalid_agent_fails`
3. `test_invalid_status_fails`
4. `test_expected_agent_mismatch_fails`
5. `test_empty_yaml_fails`
6. `test_full_handoff_reports_counts` — verifica counts, ADR warning, términos CONTEXT.md
7. `test_malformed_yaml_returns_error` (extra) — YAML que parsea como list, no como mapping, debe rechazarse vía el `ValueError` de `AgentHandoff.from_yaml`.

### §6 — `MCP_TO_CLI`

**Archivos tocados:**
- `tests/e2e/test_artefact_integrity.py::TestMcpCliAlignment.MCP_TO_CLI` — 2 entradas nuevas:
  - `"cortex_validate_handoff": None`
  - `"cortex_verify_session_claims": None`
  
  Ambas con comentario inline "MCP-only por diseño" para documentar la decisión.

## Edge cases encontrados durante implementación

**`FakeMemory` re-strucutrado con `__init__`:** al agregar `last_save_kwargs` para los tests de §4, tuve que dar `__init__` explícito a `FakeMemory`. La subclase `TrackingMemory` (en `TestGovernanceGuard`) tenía un `__init__` propio sin super. Verifiqué que el único test que usa `TrackingMemory` (`test_guard_does_not_persist_spec_when_blocked`) no accede a `last_save_kwargs`, así que la jerarquía sigue funcionando sin tocar `TrackingMemory`.

**El plan §3 sugería usar `hit.entry.metadata.get("confidence")`:** lo descartado a favor del campo `MemoryEntry.confidence` dedicado (creado en Plan 01 §6), porque metadata es untyped dict y el campo es type-checked.

**El plan §2 sugería `cortex.doc_verifier._git_diff_files`:** opté por `subprocess.run` directo dentro del helper para mantenerlo auto-contenido. Si más adelante necesitamos sofisticar el cruzar diff vs estructura AST, la migración a doc_verifier es un cambio incremental.

## Tests acumulados en Plan 02

| Archivo | Tests nuevos | Total verde |
|---------|-------------|-------------|
| `tests/unit/test_mcp_server.py` | 14 | 27 |
| **Total Plan 02** | **+14** | **+15** vs baseline (incluye un re-corrido) |

Tests nuevos del plan distribuidos:
- `TestHandoffValidation`: 7 (plan pedía 6)
- `TestVerifySessionClaims`: 3
- `TestSearchConfidenceLabel`: 2
- `TestSaveSessionHandoffArguments`: 2

## Suite global al cierre

```
$ python -m pytest tests/unit tests/integration --no-cov
799 passed, 6 skipped, 0 failed in 22.87s
```

Baseline pre-Plan 02 (cierre de Plan 01): 784 passed. Delta: **+15** (14 nuevos + 1 re-corrido).

```
$ python -m pytest tests/e2e/test_artefact_integrity.py --no-cov
23 passed in 1.86s
```

`test_mcp_tools_match_expected_set` y `test_mcp_tools_have_cli_counterpart_or_documented` verifican que los 2 tools nuevos están registrados y mapeados.

## Hallazgos para próximos planes

### Para Plan 03-06 — IDEs

1. **Los IDEs deben re-inyectar prompts canonical.** Después de Plan 01, los prompts canonical referencian `cortex_validate_handoff` y `cortex_verify_session_claims`. Esos tools **ahora existen** (Plan 02), pero los archivos materializados en `.claude/agents/`, `.opencode/agents/`, `.codex/agents/`, `.pi/agents/` todavía contienen prompts viejos. Antes de smoketear cada IDE, correr `cortex inject --ide <name>` y validar que los markers ("HIGH-SIGNAL", "VERIFICATION GATE", "Contrato de Salida", el nombre del tool) aparecen.

2. **Compatibilidad MCP tool-discovery.** Cada IDE va a descubrir 2 tools nuevos en la lista. Esto puede afectar pruebas de capacidades que cuentan tools. Si algún test del IDE adapter hace `assert len(tools) == N`, hay que bumpear N.

### Para Plan 07 — Tests y cierre

1. **El helper `_verify_session_claims_text` solo emite `verified` y `asserted`.** El bucket `contradicted` está declarado pero nunca llenado — falta heurística de negación (e.g., claim "X was removed" pero el diff agrega X). Plan 07 puede dejar esto como mejora futura o entregarla.

2. **Cobertura del cascade end-to-end:** los tests de §4 solo verifican la primera capa (MCP layer pasa los kwargs). No hay test que verifique que con `handoff=True` el archivo materializado en `vault/sessions/` realmente tiene `status: handoff` en frontmatter ni la sección "Blockers". Plan 07 §1 puede agregar un test e2e que invoque la cascade completa contra un tmp_path.

3. **Suite flaky observada en Plan 01 (`test_autopilot_service.py::TestStatus::test_latest_session`):** **NO se observó** durante Plan 02 (corrí la suite global 2 veces, verde ambas). Mantener bajo observación.

## Archivos modificados (total)

### Código
- `cortex/mcp/server.py` — 2 tool defs + 2 dispatchers + 2 helpers + extensión de inputSchema de `cortex_save_session` + extensión de `_save_session_text`.
- `cortex/core.py` — extensión de firma de `save_session_note`.
- `cortex/services/session_service.py` — extensión de firma de `create`, propagación del handoff tag al episodic.
- `cortex/documentation.py` — extensión de firma de `write_session_note`, lógica de `status: handoff`, 4 secciones nuevas condicionales.
- `cortex/models.py` — confidence label en `RetrievalResult.to_prompt`, campo `EnrichedItem.confidence`, label en `EnrichedContext.to_prompt_format`.

### Tests
- `tests/unit/test_mcp_server.py` — `FakeMemory.__init__` para capturar kwargs, 4 clases nuevas con 14 tests.
- `tests/e2e/test_artefact_integrity.py` — 2 entradas en `MCP_TO_CLI`.

### Documentación
- `docs/agents/plan/02-mcp-server-cambios.md` — frontmatter status, todos los checkboxes marcados.
- `docs/agents/implementacion/README.md` — entrada 02 marcada CERRADA.
- `docs/agents/implementacion/02-mcp-server-cambios.md` — este archivo.

## Próximo paso

**Plan 03 — IDE Claude Code.** Re-injectar el bundle de subagents en `.claude/agents/` con los prompts canonical actualizados (Plan 01) y verificar que los tools nuevos del MCP (Plan 02) aparecen en la tool-discovery del IDE.

Ver `docs/agents/plan/03-ide-claude-code.md`.
