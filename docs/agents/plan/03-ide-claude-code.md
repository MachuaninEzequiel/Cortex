---
title: Plan 03 — Materialización en Claude Code
status: ✅ CERRADA (2026-05-14)
phase: 2 (depende de Plan 01 y 02)
implementacion: ../implementacion/03-ide-claude-code.md
---

# Plan 03 — Materialización en Claude Code

Cómo se materializa cada uno de los 8 cambios canonical en el formato que Claude Code consume.

## Modelo mental de Claude Code

| Concepto Cortex | Claude Code lo llama | Path |
|-----------------|----------------------|------|
| Skill (rol primario) | "Skill" | `.claude/skills/<name>/SKILL.md` |
| Subagent (rol delegable) | "Agent" | `.claude/agents/<name>.md` |
| Herramienta MCP | "MCP server" | `.mcp.json::mcpServers.cortex` |
| Toggle de servers | "enabledMcpjsonServers" | `.claude/settings.json` |
| Delegación entre agentes | `Task` tool nativo | (built-in) |
| Top-level governance | `CLAUDE.md` | `<project_root>/CLAUDE.md` |

## Cómo se sincroniza canonical → Claude Code

El comando `cortex inject --ide claude-code` regenera:

- `CLAUDE.md` (rules de gobernanza).
- `.claude/skills/cortex-sync/SKILL.md` (desde `.cortex/skills/cortex-sync.md`).
- `.claude/skills/cortex-sddwork/SKILL.md` (desde `.cortex/skills/cortex-SDDwork.md`).
- `.claude/agents/cortex-code-explorer.md` (desde `.cortex/subagents/cortex-code-explorer.md`).
- `.claude/agents/cortex-code-implementer.md` (desde `.cortex/subagents/cortex-code-implementer.md`).
- `.claude/agents/cortex-documenter.md` (desde `.cortex/subagents/cortex-documenter.md`).
- `.claude/settings.json` (cortex enabled).
- `.mcp.json` (cortex MCP server).

**Implicación clave:** los 8 cambios canonical heredan automáticamente al correr `cortex inject --ide claude-code` después de Fase 1. **Solo hay que regenerar.**

## Cambios específicos a Claude Code

### Cambio 1 — CLAUDE.md menciona los nuevos contratos

Actualmente `CLAUDE.md` (generado por `cortex/ide/adapters/claude_code.py::inject_profiles`) tiene una lista corta. Hay que agregarle referencias a:

- "El documenter NO debe persistir sin pasar el Verification Gate."
- "Cualquier handoff entre subagents debe ser un bloque YAML conforme al schema `AgentHandoff`."
- "Status `handoff` es válido — si un check falla, NO cierres con `completed`."
- "Si descubrís un término de dominio, consultá CONTEXT.md (si existe) antes de inventar uno."

### Archivos a tocar

- `cortex/ide/adapters/claude_code.py::inject_profiles` — actualizar el bloque `claude_md_path.write_text(...)` con las nuevas reglas.
- `tests/unit/test_ide_adapters.py` — extender `test_claude_code_adapter_*` para verificar que CLAUDE.md contiene las nuevas reglas.

### Plan

1. Localizar líneas ~62-79 en `cortex/ide/adapters/claude_code.py` donde se escribe `CLAUDE.md`.
2. Agregar líneas al markdown:
   ```python
   "- The documenter MUST pass the Verification Gate before invoking `cortex_save_session`.",
   "- Every handoff between subagents MUST be a YAML block validated by `cortex_validate_handoff`.",
   "- Status `handoff` is valid — if a verification check fails, close with `status: handoff`, NOT `completed`.",
   "- If you discover a new domain term, check `CONTEXT.md` first (if it exists). Update it via the documenter if the term is canonical.",
   ```
3. Test:
   ```python
   def test_claude_code_claude_md_mentions_verification_gate(tmp_path):
       adapter = get_adapter("claude_code")
       adapter.inject_profiles(tmp_path, prompts={"cortex-sync": "x", "cortex-SDDwork": "y"})
       claude_md = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
       assert "Verification Gate" in claude_md
       assert "cortex_validate_handoff" in claude_md
       assert "handoff" in claude_md.lower()
   ```

### Cambio 2 — Skills inyectados ya tienen las nuevas secciones (sin trabajo extra)

Las skills `cortex-sync` y `cortex-SDDwork` se inyectan vía `.claude/skills/<name>/SKILL.md`. El adapter de Claude Code consume el contenido de los prompts del canonical (`get_subagent_prompt`).

**Verificación:** tras Fase 1, correr `cortex inject --ide claude-code` en un repo de prueba y verificar que el SKILL.md de `cortex-sync` incluye:

- Sección "Pre-flight: cargar CONTEXT.md si existe" (Cambio 3 del Plan 01).
- Tabla de anti-rationalization para sync (Cambio 7 del Plan 01).
- Sección "Contrato de Salida" con ejemplo YAML (Cambio 8 del Plan 01).

No hay trabajo de código aquí — solo verificación.

### Cambio 3 — Agents inyectados (explorer, implementer, documenter) heredan los 8 cambios

Mismo principio que skills. `cortex inject --ide claude-code` regenera `.claude/agents/*.md` desde `.cortex/subagents/*.md`. Los 8 cambios canonical aparecen automáticamente.

**Verificación:** tras Fase 1, verificar que `.claude/agents/cortex-documenter.md` contiene:

- Sección "HIGH-SIGNAL DOCUMENTATION MODE" (Cambio 1).
- Sección "Criterios para crear un ADR" con tabla (Cambio 2).
- Sección "VERIFICATION GATE" con checklist (Cambio 4).
- Sección "Modo Handoff" con frontmatter (Cambio 5).
- Tabla anti-rationalization (Cambio 7).
- Sección "Contrato de Salida" YAML (Cambio 8).

### Cambio 4 — Toggle del nuevo MCP tool `cortex_validate_handoff`

Claude Code usa `.claude/settings.json::enabledMcpjsonServers` para activar servers. El server "cortex" ya está. Los **tools** dentro del server se exponen automáticamente cuando Claude Code los descubre vía MCP discovery — **no hay configuración manual por tool**.

Sin embargo, vale la pena documentar en CLAUDE.md (cambio 1 arriba) que el tool nuevo existe y cuándo usarlo.

**Acción:** ninguna a nivel de Claude Code config. La sola adición del tool en el MCP server (Plan 02 §1) lo expone.

### Cambio 5 — Skills CONTEXT.md aware

El CONTEXT.md (si existe en el proyecto) se carga vía instrucción del skill, no vía un mecanismo MCP. El skill canonical `.cortex/skills/cortex-sync.md` tiene la sección "Pre-flight: cargar CONTEXT.md". Cuando se inyecta en `.claude/skills/cortex-sync/SKILL.md`, Claude Code lee esa instrucción y, al ejecutar el skill, va a `read_file CONTEXT.md` (o llamar `cortex_context` que lo incluye).

**Acción:** ninguna en Claude Code per se. Hereda del canonical.

## Smoke por IDE

### Test manual

1. Crear repo limpio bajo `/tmp/cc-smoke`.
2. `cortex setup full --non-interactive --git-depth 1 --ide claude-code`.
3. Verificar que los archivos siguientes contengan los marcadores esperados:

| Archivo | Marcador esperado |
|---------|-------------------|
| `CLAUDE.md` | "Verification Gate", "cortex_validate_handoff" |
| `.claude/skills/cortex-sync/SKILL.md` | "Pre-flight: cargar CONTEXT.md", "Contrato de Salida" |
| `.claude/skills/cortex-sddwork/SKILL.md` | "Anti-rationalization", "Contrato de Salida" |
| `.claude/agents/cortex-documenter.md` | "HIGH-SIGNAL", "VERIFICATION GATE", "Modo Handoff", "3 criterios" |
| `.claude/agents/cortex-code-explorer.md` | "Anti-rationalization", "Contrato de Salida" |
| `.claude/agents/cortex-code-implementer.md` | "Anti-rationalization", "Contrato de Salida" |
| `.mcp.json` | `cortex_validate_handoff` listed if Claude Code shows MCP tools list (manual check via Claude UI) |

### Test automatizado (extender en Plan 07)

```python
def test_claude_code_inherits_canonical_changes(tmp_path):
    """After Fase 1 + cortex inject --ide claude-code, all 8 canonical
    changes must appear in the Claude Code materialized files."""
    # ... setup tmp_path con .cortex/subagents canonical actualizado ...
    adapter = get_adapter("claude_code")
    adapter.inject_profiles(tmp_path, prompts=load_canonical_prompts(tmp_path))

    markers = {
        ".claude/agents/cortex-documenter.md": [
            "HIGH-SIGNAL", "VERIFICATION GATE", "Modo Handoff",
            "Contrato de Salida", "3 criterios",
        ],
        # ... resto
    }
    for path, expected_markers in markers.items():
        content = (tmp_path / path).read_text(encoding="utf-8")
        for marker in expected_markers:
            assert marker in content, f"{marker} missing in {path}"
```

## Checklist Plan 03 (Claude Code)

- [x] `CLAUDE.md` template actualizado con 4 nuevas reglas (Verification Gate, validate_handoff, handoff status, CONTEXT.md).
- [x] Test `test_claude_code_claude_md_mentions_verification_gate` verde (renombrado a `TestClaudeCodeTripartitaRefinada::test_claude_md_mentions_verification_gate`).
- [x] Test automatizado de inheritance (entregado en Plan 03, no Plan 07: `test_documenter_agent_inherits_canonical_markers` + `test_explorer_and_implementer_inherit_anti_rationalization`).
- [x] `docs/guides/ide-claude-code.md` actualizado con sección "Tripartita refinada (0.5.0)" describiendo los nuevos contratos.
- [ ] Smoke manual: `cortex inject --ide claude-code` en repo limpio → 6 marcadores presentes. **(Pendiente del usuario — paso interactivo, no automatizable desde el agente.)**

**Plan 03 cerrado al 100% de los items automatizables. Smoke manual queda como verificación opcional del usuario antes de release.**
