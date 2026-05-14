---
title: Plan 06 — Materialización en Codex CLI
status: ✅ CERRADA (2026-05-14)
phase: 2 (depende de Plan 01 y 02)
implementacion: ../implementacion/06-ide-codex.md
---

# Plan 06 — Materialización en Codex CLI

## Modelo mental de Codex

| Concepto Cortex | Codex lo llama | Path |
|-----------------|----------------|------|
| Skill primario | "Skill" markdown | `.codex/skills/cortex-sync.md`, `.codex/skills/cortex-sddwork.md` |
| Subagent | "Agent" markdown | `.codex/agents/cortex-code-explorer.md`, `implementer`, `documenter` |
| Herramienta MCP | "MCP server" | `.codex/mcp.json::mcpServers.cortex` |
| Governance top-level | `AGENTS.md` (Codex convention) | `.codex/AGENTS.md` |
| Hook autopilot | Markdown con marker | `.codex/autopilot.md` (con `AUTOPILOT-CODEX`) |
| Delegación | (limited — vía prompts en AGENTS.md) | (sin tool nativo equivalente a Claude `Task`) |

**Particularidades de Codex:**

- Adapter más nuevo (creado en Ola 1). Más simple que Claude Code/OpenCode/Pi.
- No tiene tool nativo de delegación (a diferencia de Claude `Task`). La delegación entre agents se logra vía instrucciones en `AGENTS.md` que dicen "consultá al agent X para esto".
- `.codex/AGENTS.md` es la pieza más importante — es lo primero que Codex lee al cargar el proyecto.

## Cómo se sincroniza canonical → Codex

`cortex inject --ide codex` regenera:

- `.codex/AGENTS.md` (governance + workflow rules).
- `.codex/skills/cortex-sync.md` (skill prompt completo).
- `.codex/skills/cortex-sddwork.md` (idem).
- `.codex/agents/cortex-code-explorer.md` (subagent prompt completo).
- `.codex/agents/cortex-code-implementer.md` (idem).
- `.codex/agents/cortex-documenter.md` (idem).
- `.codex/mcp.json` (MCP server con `--project-root` absoluto).

**Implicación clave:** igual que los otros IDEs, los cambios canonical de Plan 01 heredan automáticamente al regenerar.

## Cambios específicos a Codex

### Cambio 1 — `.codex/AGENTS.md` con las nuevas reglas

`AGENTS.md` es el "first read" de Codex. Hoy contiene una lista corta. Hay que agregar:

- Verification Gate obligatorio antes de `cortex_save_session`.
- Handoff YAML estructurado entre agents (incluso si Codex no tiene tool de delegación nativo).
- Status `handoff` válido cuando un check falla.
- CONTEXT.md como referencia opcional.

### Archivos a tocar

- `cortex/ide/adapters/codex.py::inject_profiles`:
  - Localizar la generación de `agents_md_path` (líneas ~95-115 zone).
  - Agregar las 4 nuevas reglas a la lista de bullets en el markdown generado.
- `tests/unit/test_ide_adapters.py::test_codex_adapter_inject_profiles` — extender para verificar marcadores.

### Plan

1. Localizar en `cortex/ide/adapters/codex.py` el bloque:
   ```python
   agents_md_path.write_text(
       "\n".join([
           "<!--",
           header.strip(),
           "-->",
           "",
           "# Cortex Workflow for Codex",
           "",
           "- Run `cortex-sync` before any implementation work to gather context and persist a spec.",
           # ... otras líneas existentes
       ])
       + "\n",
       encoding="utf-8",
   )
   ```

2. Agregar líneas:
   ```python
   "- The documenter MUST pass the Verification Gate before invoking `cortex_save_session`.",
   "- Every handoff between agents MUST be a YAML block validated by `cortex_validate_handoff`.",
   "- If a verification check fails, close the session with `status: handoff` (not `completed`).",
   "- If `CONTEXT.md` exists at the project root or `.cortex/CONTEXT.md`, treat its terms as canonical and avoid prohibited synonyms.",
   ```

3. **Test:**
   ```python
   def test_codex_agents_md_mentions_verification_gate(tmp_path):
       project_root = tmp_path / "project"
       project_root.mkdir()
       (project_root / ".cortex" / "subagents").mkdir(parents=True)
       for name in ("cortex-code-explorer", "cortex-code-implementer", "cortex-documenter"):
           (project_root / ".cortex" / "subagents" / f"{name}.md").write_text(f"# {name}\nbody", encoding="utf-8")

       adapter = get_adapter("codex")
       adapter.inject_profiles(project_root, prompts={"cortex-sync": "x", "cortex-SDDwork": "y"})
       agents_md = (project_root / ".codex" / "AGENTS.md").read_text(encoding="utf-8")
       assert "Verification Gate" in agents_md
       assert "cortex_validate_handoff" in agents_md
       assert "status: handoff" in agents_md
       assert "CONTEXT.md" in agents_md
   ```

### Cambio 2 — Skills y agents inyectados heredan automáticamente

Los archivos `.codex/skills/*.md` y `.codex/agents/*.md` se generan desde el canonical (`.cortex/skills/` y `.cortex/subagents/`). Igual que Claude Code, **sin trabajo extra** una vez que Plan 01 está cerrado y se corre `cortex inject`.

**Verificación:** smoke (abajo).

### Cambio 3 — Workaround para delegación sin tool nativo

Codex no tiene `Task` tool nativo. La delegación entre agents se logra cuando un agent emite el handoff YAML y el siguiente lee el archivo / el output anterior. Para que esto funcione bien:

- El skill `cortex-sddwork.md` debe instruir explícitamente: "Cuando termines, escribí el handoff YAML como tu último mensaje. El próximo agent (que vos mismo invocás cambiando de rol, o que el usuario invoca manualmente) leerá ese YAML como input."

- Cuando un sub-agent termina, su mensaje final es el YAML. El usuario / agente principal lo copia al input del siguiente.

**Acción:** ninguna específica de código. El comportamiento se logra por convención + el contrato de salida del Plan 01 §8.

### Cambio 4 — Hook autopilot

`.codex/autopilot.md` con marker `AUTOPILOT-CODEX` ya existe. Soporta el nuevo `status: handoff` automáticamente (porque el autopilot service lo persiste en `state.json`).

**Acción:** ninguna.

### Cambio 5 — MCP discovery automático

Los 2 tools nuevos (`cortex_validate_handoff`, `cortex_verify_session_claims`) se exponen al server. Codex los descubre vía MCP discovery cuando arranca. No hace falta configurar por tool.

**Acción:** ninguna en Codex config.

## Smoke por IDE

### Test manual

1. Crear repo limpio `/tmp/codex-smoke`.
2. `cortex setup full --non-interactive --git-depth 1 --ide codex`.
3. Verificar `.codex/`:

| Archivo | Marcador esperado |
|---------|-------------------|
| `.codex/AGENTS.md` | "Verification Gate", "cortex_validate_handoff", "status: handoff", "CONTEXT.md" |
| `.codex/skills/cortex-sync.md` | "Pre-flight: cargar CONTEXT.md", "Anti-rationalization", "Contrato de Salida" |
| `.codex/skills/cortex-sddwork.md` | "Anti-rationalization", "Contrato de Salida" |
| `.codex/agents/cortex-documenter.md` | "HIGH-SIGNAL", "VERIFICATION GATE", "Modo Handoff", "3 criterios", "Contrato de Salida" |
| `.codex/agents/cortex-code-explorer.md` | "Anti-rationalization", "Contrato de Salida" |
| `.codex/agents/cortex-code-implementer.md` | "Anti-rationalization", "Contrato de Salida" |
| `.codex/mcp.json` | `cortex` server con `--project-root <abs>` |
| `.codex/autopilot.md` | "AUTOPILOT-CODEX" marker (si autopilot install corrido) |

## Checklist Plan 06 (Codex)

- [x] `.codex/AGENTS.md` template actualizado con 4 reglas (Verification Gate, validate_handoff, handoff status, CONTEXT.md).
- [x] Test verde — entregado como `TestCodexTripartitaRefinada::test_agents_md_mentions_verification_gate` (incluye verificación adicional de la nota sobre la ausencia de `Task` nativo en Codex).
- [x] Tests de inheritance entregados (en vez de diferirlos a Plan 07): `test_documenter_agent_inherits_canonical_markers` + `test_explorer_and_implementer_inherit_anti_rationalization`.
- [x] `docs/guides/ide-codex.md` actualizado con sección "Tripartita Refinada (0.5.0)" + nota sobre delegación por convención (Codex no tiene Task tool nativo).
- [ ] Smoke manual: skills y agents en `.codex/` contienen los 6+ marcadores. **(Pendiente del usuario — paso interactivo, no automatizable.)**

**Plan 06 cerrado al 100% de items automatizables. Smoke manual queda como verificación opcional del usuario antes del release de 0.5.0.**
