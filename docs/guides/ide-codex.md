---
title: Cortex + Codex CLI — guía para adopters
date: 2026-05-13
status: target IDE (oficialmente soportado a partir de Ola 1 / 2026-05-13)
---

# Cortex con Codex CLI

[Codex CLI](https://github.com/openai/codex) (OpenAI) es uno de los **4 IDEs target** oficialmente soportados por Cortex. El adapter IDE fue agregado en Ola 1 (2026-05-13) — antes solo existía el adapter de autopilot.

## Prerrequisitos

- Python 3.10 o superior.
- Codex CLI instalado (`codex --version` responde). Si no lo tenés: consultá las instrucciones en https://github.com/openai/codex.
- API key de OpenAI configurada según la doc de Codex.
- Cortex instalado: `pipx install --editable C:\ruta\al\repo\Cortex` (o equivalente).

## Setup en tu repo

```bash
cd /ruta/a/tu/repo
cortex setup full --ide codex --git-depth 5
cortex doctor --scope all
```

Resultado esperado:

- `.cortex/` con el workspace cognitivo completo (igual que los otros IDEs target).
- `.codex/AGENTS.md` en el proyecto — gobernanza tripartita (sync → SDDwork → documenter) específica para Codex.
- `.codex/skills/cortex-sync.md` y `cortex-sddwork.md`.
- `.codex/agents/cortex-code-explorer.md`, `cortex-code-implementer.md`, `cortex-documenter.md`.
- `.codex/mcp.json` con el server `cortex` apuntando a `cortex mcp-server --stdio --project-root <ruta-absoluta>`.

**Nota sobre `.codex/AGENTS.md`:** se escribe **dentro** de `.codex/`, no en el root del proyecto. Eso es deliberado para no colisionar con repos que ya tienen un `AGENTS.md` propio (por ejemplo, `cortex-pi/AGENTS.md`). Si tu proyecto necesita las directivas Cortex a nivel root, copiá manualmente el contenido o usá `cortex inject --ide pi` (que sí escribe a nivel root).

## Verificación

1. Abrí Codex en el repo.
2. El agente debería detectar `.codex/mcp.json` y registrar el server `cortex`.
3. Pedile que invoque `cortex_sync_ticket` (paso 1 obligatorio).
4. Luego `cortex_create_spec` — el server **rechaza** si saltea `sync_ticket` con un mensaje de "VIOLACIÓN DE GOBERNANZA" (test cubierto en `tests/unit/test_mcp_server.py::TestGovernanceGuard`).
5. Tras implementación, `cortex_save_session` persiste e indexa la sesión.

### Modo autonomo (Autopilot)

```bash
cortex autopilot install --ide codex
cortex autopilot start --mode assist
```

Crea `.codex/autopilot.md` con marker `<!-- AUTOPILOT-CODEX -->`. El doctor de autopilot verifica esa presencia y reporta `hooks: installed for codex`.

## Troubleshooting

**Codex no detecta el server MCP.** Confirmá que `.codex/mcp.json` tiene `cortex` bajo `mcpServers` con `command: "cortex"`. Si Codex usa otro path para su MCP registry, ajustá `cortex/ide/adapters/codex.py:get_config_paths()` y abrí issue.

**`cortex create-spec` desde dentro de Codex retorna "VIOLACIÓN DE GOBERNANZA".** Es lo esperado si no se llamó `cortex_sync_ticket` antes. Pedile al agente que ejecute primero `cortex_sync_ticket`. **No es una falla**, es gobernanza forzada.

**`detect_installation()` retorna False pero Codex sí está instalado.** El adapter chequea `shutil.which("codex")`. Si tu Codex está bajo un nombre distinto (ej. `openai-codex`), considera crear un alias en PATH o abrir un issue para extender el chequeo.

**`.codex/agents/` no se regenera tras `cortex inject`.** El adapter sobrescribe con `_backup_file` (timestamp). Verificá que no tengas un `.cortex/subagents/` vacío — si lo está, no hay nada que inyectar. `cortex setup agent --ide codex` regenera todo el workspace.

## Desinstalar Cortex de Codex

```bash
# Opción 1: dejar solo los archivos no-Cortex en .codex/.
# Opción 2: borrar completo (perdés autopilot.md si lo tenés).
rm -rf .codex
```

El método `CodexAdapter.uninstall()` elimina solamente los archivos Cortex-managed (preserva contenido user-authored si lo hay).

## Tripartita Refinada (0.5.0)

A partir de Cortex **0.5.0**, los skills y agents inyectados en Codex obedecen los contratos verificables de *Tripartita Refinada*. Lo que vas a notar como adopter:

### 1. `.codex/AGENTS.md` tiene una sección nueva

Después de `cortex setup full --ide codex` (o `cortex inject --ide codex`), `.codex/AGENTS.md` incluye una sección `## Tripartita Refinada — verifiable contracts` con 4 reglas:

- **Verification Gate.** El `cortex-documenter` no puede invocar `cortex_save_session` sin antes pasar por `cortex_verify_session_claims`, que cruza los claims contra el `git diff` real y devuelve un label `verified` / `asserted` / `contradicted`.
- **Handoff schema.** Cada handoff entre agents debe ser un YAML validado por `cortex_validate_handoff` contra el schema `AgentHandoff`. **Particularidad de Codex:** como Codex no tiene `Task` tool nativo (a diferencia de Claude Code o el `Task` enabled en OpenCode), la "delegación" se logra por convención — el handoff es el último mensaje del agent saliente; el siguiente agent (sea otro turno del usuario en un nuevo rol, o el mismo agent re-prompteado) lo consume como input.
- **Status `handoff` first-class.** Si una verificación falla o el trabajo es parcial, cerrar con `status: handoff` (no `completed`). El próximo agent verá la marca y sabe que hay trabajo abierto que verificar.
- **CONTEXT.md awareness.** Si encontrás un término de dominio que no reconocés, mirá `CONTEXT.md` antes de inventar uno. El documenter actualiza `CONTEXT.md` cuando un término pasa a ser canonical.

### 2. Tools MCP nuevas en el server `cortex`

Codex descubre automáticamente los 2 tools nuevos del MCP server vía MCP discovery (no requiere configuración por tool en `.codex/mcp.json`):

- **`cortex_validate_handoff`** — valida un YAML handoff contra el schema `AgentHandoff`.
- **`cortex_verify_session_claims`** — cruza claims del implementador contra el `git diff` y devuelve buckets `verified` / `asserted`.

### 3. Sesiones marcadas como handoff

`cortex_save_session` ahora acepta 5 parámetros opcionales (`handoff`, `blockers`, `verified_state`, `unverified_claims`, `suggested_skills`). Cuando `handoff=True`, el archivo en `.cortex/vault/sessions/` lleva `status: handoff` en frontmatter, el tag `handoff` se agrega para búsqueda, y aparecen 4 secciones nuevas en el cuerpo cuando las listas correspondientes son no-vacías.

### 4. Confidence labels en respuestas de búsqueda

`cortex_search` y `cortex_context` emiten labels `[verified]`, `[asserted]` o `[contradicted]` junto al `memory_type` de cada hit que tenga `confidence` definida (memorias post-0.5.0). Codex puede ponderar esos labels al construir contexto: las verificadas pesan más que las asertadas.

### Nota sobre delegación en Codex

Codex no tiene un tool nativo equivalente al `Task` de Claude Code. Eso significa que la "cadena tripartita" (sync → SDDwork → explorer/implementer → documenter) se ejecuta por turnos del usuario, no por delegación automática:

1. Vos pedís al agente que actúe como `cortex-sync` → emite SPEC + handoff YAML.
2. Vos cambiás de rol (`cortex-sddwork`) y le pasás el handoff YAML como input.
3. SDDwork implementa o delega a explorer/implementer (otro turno) y emite handoff.
4. Documenter consume el último handoff y persiste con Verification Gate.

El AGENTS.md describe exactamente este flujo. Si tu workflow se siente burocrático con tantos turnos, considerá Claude Code u OpenCode (que sí tienen `Task` nativo).

## Próximos pasos

- `cortex webgraph serve` para visualizar la memoria del proyecto.
- Integración con el pipeline CI: los 5 workflows de `.github/workflows/` ya están configurados por `cortex setup pipeline`.
- Para entornos enterprise: `cortex setup enterprise --preset multi-project-team` (ver `docs/guides/enterprise-vault.md`).

## Estado del adapter Codex en Cortex

El adapter fue creado en **Ola 1 (2026-05-13)**. Cobertura de tests:

- `tests/unit/test_ide_adapters.py::test_target_ides_are_registered`
- `tests/unit/test_ide_adapters.py::test_codex_adapter_inject_profiles`
- `tests/unit/test_ide_adapters.py::test_codex_adapter_inject_mcp_uses_absolute_path`
- `tests/unit/test_ide_adapters.py::test_get_ide_tier_classifies_each_adapter` (Codex como `target`)

Reportar regresiones referenciando esos tests + el commit que las introdujo.
