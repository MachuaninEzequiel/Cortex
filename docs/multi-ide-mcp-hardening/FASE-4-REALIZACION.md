# FASE 4 — REALIZACION

**Fecha de ejecucion:** 2026-05-15
**Output formal:** 5 adapters refactorizados/limpiados, 1 hibrido eliminado, 3 renders canonicos actualizados con pre-flight check, registry con metadata de validacion.
**Estado:** Completada. 13 tests nuevos + 19 actualizados + 14 eliminados (obsoletos por decisiones firmadas). Suite total: **255 tests pasando**, sin regresion. Linter `ruff` verde.

---

## 1. Tasks ejecutadas en orden

| Task | Descripcion | Archivo principal |
|---|---|---|
| 4.0 | Re-verificar docs oficiales de los 4 target IDEs (Claude Code, opencode, Codex, Cursor) | (WebFetch) |
| 4.6 | Inyectar pre-flight check `cortex_ping` en los 3 renders canonicos | `cortex/setup/cortex_workspace.py` |
| 4.1 | claude_code adapter: inyectar `tools` traducido en frontmatter | `cortex/ide/adapters/claude_code.py` |
| 4.2 | opencode adapter: migrar de `tools` legacy a `permission` moderno | `cortex/ide/adapters/opencode.py` |
| 4.4 | codex adapter: rediseno completo (AGENTS.md root + MCP TOML + sin agents/skills) | `cortex/ide/adapters/codex.py` |
| 4.3 | cursor adapter: rediseno con 3 subagents canonicos en `.cursor/agents/` | `cortex/ide/adapters/cursor.py` |
| 4.5 | Eliminar `cortex-SDDwork-cursor.md` + `build_cursor_prompts()` | `.cortex/skills/`, `cortex/ide/prompts.py`, `cortex/ide/__init__.py` |
| 4.7 | Marcar IDEs validados / no-validados en registry | `cortex/ide/registry.py` |
| 4.8 | Tests integrales por adapter (ortogonales a tests historicos) | `tests/unit/ide/test_adapters_phase4.py` |
| 4.9 | Documentacion + REALIZACION + actualizar README plan | (este documento) |

**Orden ejecutado:** Task 4.6 PRIMERO (modifica los archivos canonicos que los demas adapters van a leer). Luego Tasks 4.1, 4.2 (cambios pequenios primero), 4.4 y 4.3 (redisenos), 4.5 (cleanup), 4.7 (metadata), 4.8 (tests), 4.9 (docs).

---

## 2. Re-verificacion contra docs oficiales (Task 4.0)

Antes de tocar codigo, validacion contra docs vigentes — los hallazgos cambiaron el plan original significativamente:

### Claude Code — confirmado
- Path: `.claude/agents/<name>.md` (project) o `~/.claude/agents/<name>.md` (user).
- Frontmatter `tools:` comma-separated. MCP tools como `mcp__<server>__<tool>`.
- Si `tools:` se omite, hereda TODAS las del padre. Con restriccion, allowlist estricta.

### opencode — **HALLAZGO NUEVO**: `tools` esta DEPRECATED
> "tools is deprecated. Prefer the agent's permission field for new configs."

Reemplazado por `permission` con valores `allow|ask|deny`. Esto cambio el plan: en lugar de "limpiar el campo tools", se MIGRO a la API moderna. Los MCP tools NO van en `permission` (se descubren dinamicamente).

### Codex — confirmado
- AGENTS.md va al **project root**, NO `.codex/AGENTS.md`.
- NO soporta subagents personalizados.
- MCP en `.codex/config.toml` (TOML), key `[mcp_servers.<name>]` (snake_case), seccion separada `[mcp_servers.<name>.env]`.

### Cursor 2.4+ — **CORRECCION RESPECTO AL PLAN**: hay subagents nativos
- Path: `.cursor/agents/<name>.md` (project) o `~/.cursor/agents/<name>.md` (user) — confirmado en Cursor 2.4 (enero 2026).
- Frontmatter: `name`, `description`, `model`, `readonly`, `is_background`. **NO declara `tools:`** — heredan del padre.

---

## 3. Decisiones tomadas durante la realizacion

### 3.1 opencode: migracion a `permission` (no parche del legacy)

El plan original decia "limpiar el campo tools". La realidad post-WebFetch revelo que `tools` esta deprecated. Decision: **migrar a `permission`** en lugar de perpetuar el legacy.

Resultado:
- `cortex-sync`: `permission: {read: allow, write: deny, edit: deny, bash: deny}` (read-only).
- `cortex-SDDwork`: `permission: {read: allow, write: allow, edit: allow, bash: ask, task: allow}` (puede modificar; bash con confirmacion).
- Los MCP tools (`cortex_save_session`, etc.) **NO** se declaran (descubrimiento dinamico al conectarse al MCP server).

### 3.2 Codex: arquitectura inline-section con marcadores

El AGENTS.md de Codex va al project root y puede coexistir con AGENTS.md preexistente del adopter. Decision: usar **marcadores HTML comments** (`<!-- BEGIN CORTEX SECTION ... END CORTEX SECTION -->`) para localizar y reemplazar limpiamente solo el bloque Cortex.

Beneficios:
- Idempotente: re-inyectar reemplaza el bloque, no duplica.
- Coexistente: el AGENTS.md del adopter se preserva intacto fuera del bloque.
- Reversible: `uninstall()` quita solo el bloque marcado.

Mismo patron aplicado al `.codex/config.toml` con marcadores `# BEGIN CORTEX MCP / # END CORTEX MCP`.

### 3.3 Codex MCP TOML: serializer manual sin dependencia nueva

`tomli_w` no esta disponible en las dependencias actuales. Decision: serializar TOML manualmente (formato simple para `[mcp_servers.cortex]`). Sin nueva dependencia, sin reformat-friendly comments — un trade-off aceptable porque:
- El bloque es siempre el mismo (no parametrizado complejo).
- `tomllib` (Python 3.11+ stdlib) sigue siendo capaz de PARSEAR el output.
- Tests verifican que `tomllib.loads(output)` funciona y devuelve el shape esperado.

### 3.4 Cursor: 3 subagents canonicos NO declaran `tools:`

Docs de Cursor 2.4 indican que subagents heredan TODAS las tools del padre. Decision: NO inyectar `tools:` en frontmatter de Cursor. Las tools se gobiernan implicitamente por el contenido del prompt canonico (que enumera lo que el subagent debe usar). Esto difiere de Claude Code (donde SI inyectamos `tools:` allowlist).

`readonly: true` para `cortex-code-explorer` (read-only por contrato), `false` para los otros dos.

### 3.5 Pre-flight check inyectado en los renders, NO en cada adapter

El bloque pre-flight check (`cortex_ping` validation) se inyecta en `cortex_workspace.py` (los renders canonicos), NO en cada adapter. Esto garantiza:
- **Una sola fuente de verdad**: si el bloque cambia, se modifica en un solo lugar.
- **Heredan TODOS los IDEs validados**: claude_code, cursor, opencode (via skill prompts) automaticamente lo reciben.
- **Codex tiene su propio pre-flight inline en AGENTS.md** porque no hay subagent file separado.

### 3.6 Tests viejos del codex con `.codex/agents/`: ELIMINADOS

`TestCodexTripartitaRefinada::test_documenter_agent_inherits_canonical_markers` y similares verificaban archivos en `.codex/agents/cortex-documenter.md`. Esos archivos YA NO se generan (Codex no los lee). Decision: **eliminar** los tests obsoletos en lugar de "adaptarlos" a un comportamiento que ya no aplica. La cobertura del documenter en codex se obtiene del `AGENTS.md` (con sus markers de Verification Gate, etc.).

Tests eliminados (4) reemplazados con tests nuevos (5) que validan el nuevo comportamiento:
- `test_agents_md_describes_sequential_tripartite_flow`
- `test_agents_md_uses_cortex_section_markers`
- `test_agents_md_preserves_user_content_when_existing`
- `test_agents_md_replaces_cortex_block_idempotent`

### 3.7 Tests opencode con `tools["cortex_validate_handoff"] is True`: REEMPLAZADOS

Estos verificaban un comportamiento que el plan multi-IDE declara INCORRECTO (declarar MCP tools en `tools` viola las docs oficiales). Decision: **invertir la asercion** — en lugar de "tools incluye cortex_validate_handoff", el nuevo test es **regression guard**: "permission NO incluye ningun cortex_*".

### 3.8 Cursor `cortex-SDDwork-cursor.md` + `build_cursor_prompts`: ELIMINADOS

Cursor 2.4+ soporta subagents nativos. La arquitectura hibrida pre-2.4 (1 sola skill que combina explorer + implementer) es obsoleta. Decision: eliminar tanto el archivo `.cortex/skills/cortex-SDDwork-cursor.md` como la funcion `build_cursor_prompts()` y la rama especial `if ide_name == "cursor"` en `cortex/ide/__init__.py`. **Cero shims temporales**.

---

## 4. Cumplimiento del gate de cero deuda tecnica de Fase 4

| Item del gate | Estado |
|---|---|
| Cada adapter pasa sus tests | OK — 255 tests verdes, 13 nuevos especificos de Fase 4 + 19 historicos actualizados. |
| El cuerpo de los prompts canonicos NO se reescribe en ningun adapter | OK — los adapters consumen el body via `strip_markdown_frontmatter(get_subagent_prompt(...))` sin modificar contenido. |
| Pre-flight check aparece en los 3 subagents canonicos | OK — verificado en `test_renders_include_preflight_check`. |
| Smoke manual: codex inject en proyecto limpio genera AGENTS.md root + config.toml | OK — `test_smoke_inject_codex` cubre el flujo end-to-end. |
| Cero `cortex-SDDwork-cursor` en codigo fuente | OK — solo aparecen referencias en comentarios historicos justificados. |
| Cero `build_cursor_prompts` en codigo activo | OK — eliminado de prompts.py, __init__.py, test_ide_module.py. |
| Linter `ruff` verde | OK. |
| Cero TODOs nuevos | OK. |
| Cero shims temporales o flags transitorios | OK. |
| Decisiones firmadas registradas | OK — `MATRIZ-NATIVA-IDES.md` seccion 4 + esta REALIZACION. |

---

## 5. Adapters tocados — diff resumen

### `claude_code.py` (cambio acotado)
- Import: agregado `translate_list` + `split_markdown_frontmatter`.
- Helper nuevo: `_parse_canonical_tools(frontmatter_text) -> list[str]`.
- En `inject_profiles`: parsear frontmatter del canonico, traducir tools, inyectar `tools:` en frontmatter del archivo `.claude/agents/<name>.md` generado.

### `opencode.py` (mediano)
- Eliminado campo `tools` (legacy).
- Agregado campo `permission` con valores `allow|ask|deny`.
- Eliminadas todas las claves `cortex_*` del agent profile (descubrimiento dinamico).

### `codex.py` (rediseno completo)
- AGENTS.md va al project root con marcadores Cortex.
- MCP en `.codex/config.toml` (TOML, snake_case).
- Eliminada toda inyeccion de `.codex/agents/*.md` y `.codex/skills/*.md`.
- `uninstall()` ampliado para limpiar artefactos legacy del adapter pre-Fase 4.

### `cursor.py` (rediseno)
- 3 subagents canonicos en `.cursor/agents/` (project-level).
- Frontmatter Cursor 2.4+: `name`, `description`, `model: inherit`, `readonly`.
- NO inyecta `tools:` (subagents heredan del padre).
- Eliminada dependencia de `build_cursor_prompts` (ya no existe).
- `uninstall()` reescrito para el nuevo layout.

### `pi.py` — **NO TOCADO** (Decision 1 firmada)
Bundle estatico con contribuciones de comunidad — respetado.

### `registry.py` (metadata nueva)
- Constante nueva `VALIDATED_IDES = {claude_code, opencode, codex, cursor, pi}`.
- 3 helpers nuevos: `is_ide_validated()`, `get_validated_ides_list()`, `get_unvalidated_ides_list()`.

---

## 6. Items para handoff a Fase 5

Fase 5 (Cleanup delegate MCP) puede empezar inmediatamente. Cambios concretos esperados:

- Eliminar tools `cortex_delegate_task`, `cortex_delegate_batch`, `cortex_get_task_result` del MCP server.
- Eliminar entry `cortex_delegate_task` del Literal `CanonicalTool` en `canonical_tools.py` y de la matriz `_TOOL_NAME_BY_IDE` (los tests de `test_canonical_tools.py` que parametrizan los MCP tools fallaran limpiamente y avisaran que hay que actualizar).
- Eliminar referencia a `cortex_delegate_task` en `render_cortex_sddwork_skill()` en `cortex_workspace.py:249-250`.
- Regenerar `.cortex/skills/cortex-SDDwork.md` desde el render actualizado.
- Eliminar tests del delegate experimental en `tests/integration/mcp/test_server.py`.
- Limpieza de docs/autopilot/ que aun referencian el delegate.

---

## 7. Handoff formal

```yaml
agent: fase-4-adapters-ssot
status: completed
artifacts_produced:
  - cortex/ide/adapters/claude_code.py (modificado: inyecta tools traducido)
  - cortex/ide/adapters/opencode.py (migrado tools -> permission)
  - cortex/ide/adapters/codex.py (rediseno: AGENTS.md root + MCP TOML)
  - cortex/ide/adapters/cursor.py (rediseno: 3 subagents en .cursor/agents/)
  - cortex/ide/__init__.py (eliminada rama cursor especial)
  - cortex/ide/prompts.py (eliminado build_cursor_prompts)
  - cortex/ide/registry.py (helpers de validacion)
  - cortex/setup/cortex_workspace.py (pre-flight check en 3 renders)
  - tests/unit/ide/test_adapters_phase4.py (13 tests nuevos)
  - tests/unit/test_ide_adapters.py (19 tests actualizados, 14 obsoletos eliminados)
  - tests/integration/test_cross_ide_smoke.py (smoke codex actualizado)
  - tests/unit/test_ide_module.py (test_inject actualizado)
  - .cortex/subagents/*.md (3 archivos regenerados con pre-flight check)
artifacts_removed:
  - .cortex/skills/cortex-SDDwork-cursor.md (hibrido obsoleto)
  - cortex/ide/prompts.py:build_cursor_prompts (funcion eliminada)
verified_claims:
  - "255 tests verdes (13 nuevos + 19 actualizados + 223 preexistentes)"
  - "Linter ruff verde"
  - "5 adapters trabajados segun decisiones firmadas (claude_code, opencode, codex, cursor + pi sin tocar)"
  - "Pre-flight check inyectado en los 3 subagents canonicos"
  - "Cero referencias activas a cortex-SDDwork-cursor o build_cursor_prompts"
  - "Codex MCP migrado a TOML, validado con tomllib.loads"
  - "OpenCode usa permission moderno, NO tools legacy, NO MCP tools declarados"
unverified_claims: []
contradicted_claims: []
context_for_next:
  - "Fase 5 (cleanup delegate MCP) desbloqueada y lista"
  - "Fase 6 (setup full interactivo) sin dependencias, lista"
  - "Fase 7 (validacion E2E) bloqueada hasta Fase 5 + Fase 6 completas"
suggested_adr: false
```
