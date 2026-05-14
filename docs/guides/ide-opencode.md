---
title: Cortex + OpenCode — guía para adopters
date: 2026-05-13
status: target IDE (oficialmente soportado)
---

# Cortex con OpenCode

[OpenCode](https://opencode.ai/) es uno de los **4 IDEs target** oficialmente soportados por Cortex.

## Prerrequisitos

- Python 3.10 o superior.
- OpenCode instalado y operativo (`opencode --version` responde).
- Cortex instalado vía `pipx install --editable C:\ruta\al\repo\Cortex` (o equivalente).

## Setup en tu repo

```bash
cd /ruta/a/tu/repo
cortex setup full --ide opencode --git-depth 5
cortex doctor --scope all
```

Resultado esperado:

- `.cortex/` con todo el workspace (igual que Claude Code).
- `~/.config/opencode/opencode.json` con bloque `agent.cortex-sync`, `agent.cortex-SDDwork` y bloque `mcp.cortex` (server stdio con `--project-root` absoluto).
- `~/.config/opencode/skills/cortex-sync.md` y `cortex-SDDwork.md` (skills compartidas globalmente — no por proyecto — porque OpenCode lo espera así por XDG).
- `~/.config/opencode/subagents/cortex-code-explorer.md`, `cortex-code-implementer.md`, `cortex-documenter.md`.

**Importante:** OpenCode guarda sus skills/subagents en `~/.config/opencode/`, **no** en el proyecto. Esto es por diseño (XDG). El MCP sí queda apuntado al `--project-root` específico, por lo que cambiar de proyecto activa el contexto correcto automáticamente.

## Verificación

1. Abrí el repo en OpenCode.
2. El agente debería listar las herramientas `cortex_*` disponibles.
3. Pedile que ejecute `cortex_sync_ticket` con tu pedido inicial.
4. Luego `cortex_create_spec` (el server bloquea si no llamó sync_ticket antes — esto es **gobernanza forzada**, ver `cortex/mcp/server.py:_GOVERNANCE_VIOLATION_MESSAGE`).
5. Tras la implementación, `cortex_save_session` persiste + indexa la sesión.

### WSL (Windows Subsystem for Linux)

OpenCode bajo WSL necesita un "shielded wrapper" para evitar contaminación del stream JSON-RPC con mensajes de stderr. El adapter lo detecta automáticamente: si corre bajo WSL, crea `~/.cortex/bin/cortex-mcp-wrapper` y lo usa en lugar del `cortex` directo. No hace falta acción manual.

### Modo autonomo (Autopilot)

```bash
cortex autopilot install --ide opencode
cortex autopilot start --mode assist
```

Esto crea `.opencode/hooks.md` con el marker `AUTOPILOT-OPENCODE`. El doctor de autopilot verifica esa presencia al diagnosticar.

## Troubleshooting

**Cortex tools no aparecen en OpenCode.** Verificá `~/.config/opencode/opencode.json`: debe tener un bloque `mcp.cortex` con `enabled: true`. Si no, re-corré `cortex inject --ide opencode`.

**Errores de UnicodeDecodeError o JSON malformado al iniciar el server.** Probable contaminación de stderr. Si estás bajo WSL, eliminá `~/.cortex/bin/cortex-mcp-wrapper` para forzar su regeneración: `rm ~/.cortex/bin/cortex-mcp-wrapper && cortex inject --ide opencode`.

**OpenCode usa skills viejas tras una actualización de Cortex.** Las skills están bajo `~/.config/opencode/skills/`, no por proyecto. Re-correr `cortex inject --ide opencode` sobrescribe con la versión actual.

**El bloque `mcp.cortex` se pisó con configuración de otro server.** El adapter hace deep-merge, no reemplazo. Si ves problemas, abrí el JSON y verificá que tu `mcp.cortex` no tenga merge accidental con otros servers.

## Desinstalar Cortex de OpenCode

```bash
# El bloque cortex queda en el JSON; lo borrás manualmente.
# Opcional: rm -rf ~/.config/opencode/skills/cortex-* ~/.config/opencode/subagents/cortex-*
```

## Tripartita Refinada (0.5.0)

A partir de Cortex **0.5.0**, los agents y subagents inyectados en OpenCode obedecen los contratos verificables de *Tripartita Refinada*. Lo que vas a notar como adopter:

### 1. Tools nuevas habilitadas en los agents primary

`cortex inject --ide opencode` ahora habilita 2 tools MCP nuevas en el bloque `tools` de **`agent.cortex-sync`** y **`agent.cortex-SDDwork`** dentro de `~/.config/opencode/opencode.json`:

- **`cortex_validate_handoff`** — valida un YAML handoff contra el schema `AgentHandoff`. `cortex-sync` la usa para chequear el handoff que recibe de SDDwork antes de cerrar su turno; `cortex-SDDwork` la usa para validar handoffs de los subagents que delega vía `Task`.
- **`cortex_verify_session_claims`** — cruza una lista de claims contra el `git diff` actual y devuelve buckets `verified` / `asserted`. El orquestador SDDwork la invoca antes de pasarle la información al `cortex-documenter`, que rellena el campo `confidence` de cada memoria con el resultado.

Si actualizás Cortex de 0.4.x a 0.5.0 y ya tenés setup previo, **re-corré `cortex inject --ide opencode`** para que las tools nuevas aparezcan en el JSON. El deep-merge preserva todo lo demás (otros servers MCP, otros agents tuyos).

### 2. Subagents canonical actualizados

Los archivos en `~/.config/opencode/subagents/cortex-{code-explorer,code-implementer,documenter}.md` se regeneran desde el canonical de `.cortex/subagents/` cada vez que corrés `cortex inject --ide opencode`. Después del bump a 0.5.0, esos archivos contienen las secciones nuevas:

- **HIGH-SIGNAL DOCUMENTATION MODE** (documenter).
- **VERIFICATION GATE** con checklist (documenter).
- **Modo Handoff** con frontmatter (documenter).
- **3 criterios para crear ADR** (documenter).
- **Anti-rationalization** y **Contrato de Salida YAML** (los 3 subagents).

Como los subagents viven bajo `~/.config/opencode/` (XDG global, no por proyecto), cualquier proyecto donde corrás OpenCode después de re-injectar va a heredar los nuevos contratos sin re-correr setup.

### 3. Sesiones marcadas como handoff

Cuando `cortex-SDDwork` cierra un turno con trabajo parcial, ahora puede invocar `cortex_save_session` con `handoff=True` y los nuevos parámetros opcionales (`blockers`, `verified_state`, `unverified_claims`, `suggested_skills`). El archivo en `.cortex/vault/sessions/` lleva `status: handoff` en frontmatter y el tag `handoff` para búsquedas rápidas. Esto le permite al siguiente agente (incluso en otra sesión de OpenCode) retomar exactamente donde quedó la anterior sin re-investigar.

### 4. Confidence labels en respuestas de búsqueda

`cortex_search` y `cortex_context` ahora emiten un label `[verified]` / `[asserted]` / `[contradicted]` junto al `memory_type` de cada hit que tenga `confidence` definida (memorias post-0.5.0 producidas con el Verification Gate). OpenCode pondera esos labels al construir contexto: las memorias verificadas pesan más que las asertadas, y las contradichas se filtran o muestran con warning.

## Próximos pasos

Mismos que cualquier IDE target: `cortex webgraph serve`, `cortex memory-report`, integración con CI Enterprise.
