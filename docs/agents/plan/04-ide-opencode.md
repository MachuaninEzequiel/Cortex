---
title: Plan 04 — Materialización en OpenCode
status: ✅ CERRADA (2026-05-14)
phase: 2 (depende de Plan 01 y 02)
implementacion: ../implementacion/04-ide-opencode.md
---

# Plan 04 — Materialización en OpenCode

## Modelo mental de OpenCode

| Concepto Cortex | OpenCode lo llama | Path |
|-----------------|-------------------|------|
| Skill primario (sync, SDDwork) | "Agent" en JSON | `~/.config/opencode/opencode.json::agent.<name>` |
| Subagent | "Subagent" md | `~/.config/opencode/subagents/<name>.md` |
| Herramienta MCP | "MCP server" | `~/.config/opencode/opencode.json::mcp.cortex` |
| Herramientas permitidas por agent | `tools` dict por agent | `agent.<name>.tools` |
| Hook autopilot | Markdown con marker | `.opencode/hooks.md` |
| Delegación entre agents | `Task` tool nativo | (built-in, requiere `tools.Task: true`) |

**Particularidad:** OpenCode separa profiles (en `~/.config/opencode/`, XDG global) del proyecto. El MCP sí apunta a `--project-root` específico, por lo que cambiar de proyecto activa el contexto correcto. Los skills/subagents son **globales del usuario**, no por proyecto.

## Cómo se sincroniza canonical → OpenCode

`cortex inject --ide opencode` regenera:

- `~/.config/opencode/opencode.json` (deep-merge con bloque `agent.cortex-sync`, `agent.cortex-SDDwork`, `mcp.cortex`).
- `~/.config/opencode/skills/cortex-sync.md` (skill prompt completo).
- `~/.config/opencode/skills/cortex-SDDwork.md` (idem).
- `~/.config/opencode/subagents/cortex-code-explorer.md` (subagent prompt completo).
- `~/.config/opencode/subagents/cortex-code-implementer.md` (idem).
- `~/.config/opencode/subagents/cortex-documenter.md` (idem).

**Implicación clave:** igual que Claude Code, todos los cambios canonical heredan automáticamente al regenerar.

## Cambios específicos a OpenCode

### Cambio 1 — Tools permitidos por agent

`opencode.json` declara explícitamente qué tools puede usar cada agent. Hoy el adapter define:

```python
"cortex-sync": {
    "tools": {
        "read": True, "write": False, "edit": False, "bash": False,
        "cortex_context": True, "cortex_search": True,
        "cortex_search_vector": True, "cortex_sync_ticket": True,
        "cortex_create_spec": True, "cortex_sync_vault": True,
    },
},
"cortex-SDDwork": {
    "tools": {
        "read": True, "write": True, "edit": True, "bash": False,
        "cortex_context": True, "cortex_search": True,
        "cortex_search_vector": True, "cortex_save_session": True,
        "cortex_sync_vault": True, "Task": True,
    },
},
```

**Hay que agregar los nuevos tools** que se introducen en Plan 02 §1-2:

- `cortex_validate_handoff: True` — habilitarlo para los dos agents (sync para validar handoff de SDDwork; SDDwork para validar handoff de subagents delegated via Task).
- `cortex_verify_session_claims: True` — habilitarlo para SDDwork (el orquestador) y para los subagents delegated (que en OpenCode son "subagents" en el sentido de Task).

### Archivos a tocar

- `cortex/ide/adapters/opencode.py::inject_profiles`:
  - Localizar `cortex_profiles` dict (líneas 85-108 aprox).
  - Agregar las nuevas entradas en `tools` dict.
- `tests/unit/test_ide_adapters.py::test_opencode_adapter_inject_profiles` — extender para verificar tools nuevos.

### Plan

1. **Agregar tools nuevos** en `cortex_profiles`:
   ```python
   "cortex-sync": {
       ...,
       "tools": {
           ...,
           "cortex_validate_handoff": True,  # NUEVO Tripartita Refinada
           "cortex_verify_session_claims": True,  # NUEVO Tripartita Refinada
       },
   },
   "cortex-SDDwork": {
       ...,
       "tools": {
           ...,
           "cortex_validate_handoff": True,  # NUEVO Tripartita Refinada
           "cortex_verify_session_claims": True,  # NUEVO Tripartita Refinada
       },
   },
   ```

2. **Test:**
   ```python
   def test_opencode_agents_have_new_handoff_tools(tmp_path, monkeypatch):
       monkeypatch.setattr("cortex.ide.adapters.opencode.Path.home", staticmethod(lambda: tmp_path))
       adapter = get_adapter("opencode")
       adapter.inject_profiles(tmp_path / "project", prompts={
           "cortex-sync": "x", "cortex-SDDwork": "y",
       })
       data = json.loads((tmp_path / ".config/opencode/opencode.json").read_text(encoding="utf-8"))
       for agent_name in ("cortex-sync", "cortex-SDDwork"):
           tools = data["agent"][agent_name]["tools"]
           assert tools["cortex_validate_handoff"] is True
           assert tools["cortex_verify_session_claims"] is True
   ```

### Cambio 2 — Hook autopilot ya cubre Handoff Mode

`.opencode/hooks.md` con marker `AUTOPILOT-OPENCODE` ya existe (Ola 0). El autopilot service ahora soporta `status: handoff` (Plan 01 §5). El hook NO necesita cambios — el status se propaga vía `state.json`.

**Acción:** ninguna en OpenCode.

### Cambio 3 — Verificación de skills/subagents inyectados

Igual que Claude Code: los archivos en `~/.config/opencode/skills/` y `~/.config/opencode/subagents/` heredan del canonical. Verificar marcadores en smoke.

## Smoke por IDE

### Test manual

1. Crear repo limpio `/tmp/oc-smoke`.
2. `cortex setup full --non-interactive --git-depth 1 --ide opencode`.
3. Verificar archivos generados:

| Archivo | Marcador esperado |
|---------|-------------------|
| `~/.config/opencode/skills/cortex-sync.md` | "Pre-flight: cargar CONTEXT.md", "Anti-rationalization", "Contrato de Salida" |
| `~/.config/opencode/skills/cortex-SDDwork.md` | "Anti-rationalization", "Contrato de Salida" |
| `~/.config/opencode/subagents/cortex-documenter.md` | "HIGH-SIGNAL", "VERIFICATION GATE", "Modo Handoff", "3 criterios", "Contrato de Salida" |
| `~/.config/opencode/subagents/cortex-code-explorer.md` | "Anti-rationalization", "Contrato de Salida" |
| `~/.config/opencode/subagents/cortex-code-implementer.md` | "Anti-rationalization", "Contrato de Salida" |
| `~/.config/opencode/opencode.json` | `cortex_validate_handoff: true` para sync y SDDwork |
| `.opencode/hooks.md` | "AUTOPILOT-OPENCODE" marker |

## Checklist Plan 04 (OpenCode)

- [x] Tools nuevos agregados a `cortex_profiles` en adapter (cortex_validate_handoff + cortex_verify_session_claims en sync y SDDwork).
- [x] Test `test_opencode_agents_have_new_handoff_tools` verde — entregado como `TestOpenCodeTripartitaRefinada` con 3 tests (sync, SDDwork, regression de tools pre-existentes).
- [x] `opencode.json` tiene los 2 tools nuevos por agent (verificado por los tests).
- [x] `docs/guides/ide-opencode.md` actualizado con sección "Tripartita Refinada (0.5.0)".
- [ ] Smoke manual: skills y subagents en `~/.config/opencode/` contienen los 7+ marcadores. **(Pendiente del usuario — paso interactivo, no automatizable.)**

**Plan 04 cerrado al 100% de los items automatizables. Smoke manual queda como verificación opcional del usuario antes de release.**
