---
title: Cortex + Claude Code — guía para adopters
date: 2026-05-13
status: target IDE (oficialmente soportado)
---

# Cortex con Claude Code

[Claude Code](https://www.anthropic.com/news/claude-code) es uno de los **4 IDEs target** oficialmente soportados por Cortex. Esta guía te lleva de cero a un setup operativo en pocos minutos.

## Prerrequisitos

- Python 3.10 o superior.
- Git 2.30+.
- Claude Code instalado y autenticado (`claude --version` retorna una versión).
- Cortex instalado via `pipx install --editable C:\ruta\al\repo\Cortex` (o ruta equivalente).

## Setup en tu repo

```bash
cd /ruta/a/tu/repo
cortex setup full --ide claude-code --git-depth 5
cortex doctor --scope all
```

Resultado esperado:

- `.cortex/` con `config.yaml`, `vault/`, `memory/`, `skills/`, `subagents/`, `AGENT.md`, `system-prompt.md`, `workspace.yaml`, `webgraph/`.
- `.github/workflows/` con los 5 workflows DevSecDocOps.
- `.claude/agents/{cortex-code-explorer,cortex-code-implementer,cortex-documenter}.md` con los subagentes Cortex.
- `.claude/skills/{cortex-sync,cortex-sddwork}/SKILL.md` con los flujos tripartitos.
- `.claude/settings.json` con `cortex` en `enabledMcpjsonServers`.
- `.mcp.json` con el server `cortex` apuntando al binario via `cortex mcp-server --stdio --project-root <ruta-absoluta>`.
- `CLAUDE.md` en el root del repo con el resumen del flujo tripartito.

## Verificación

1. Abrí el repo en Claude Code.
2. En la interfaz, ejecutá `/cortex-sync` o pedile al agente que lo invoque.
3. Claude Code va a llamar `cortex_sync_ticket` (paso 1 obligatorio).
4. Luego `cortex_create_spec` (si no se llama `sync_ticket` primero, el server **rechaza** con "VIOLACIÓN DE GOBERNANZA" — es el guard de gobernanza activo).
5. Tras la implementación, `cortex_save_session` persiste la sesión en `.cortex/vault/sessions/` Y la indexa inmediatamente en memoria episódica y semántica.

### Modo autonomo (Autopilot)

Para activar Autopilot dentro de Claude Code:

```bash
cortex autopilot install --ide claude-code
cortex autopilot start --mode assist --request "Tu pedido inicial"
```

Esto agrega `.claude/autopilot-hook.md` y deja la sesión lista para `preflight → checkpoint → finish --auto`. La nota generada por `finish --auto` queda persistida e indexada (contrato transaccional — si la indexing falla, no queda archivo huérfano).

## Troubleshooting

**El IDE no detecta el server `cortex`.** Verificá que `cortex` esté en tu PATH (`which cortex` o `where cortex`). Si lo instalaste con pipx, debería estar disponible globalmente. Si no, agregá la ruta del binario manualmente al `command` en `.mcp.json`.

**`/cortex-sync` retorna "VIOLACIÓN DE GOBERNANZA" para create-spec.** El agente está saltándose el paso 1. Asegurate de que `cortex_sync_ticket` se llame antes que `cortex_create_spec`. La política está en `cortex/mcp/server.py:_GOVERNANCE_VIOLATION_MESSAGE` y es **rechazo total**, no advertencia.

**`cortex search` no encuentra notas recién guardadas.** Indexing automático es transaccional desde Ola 0 (2026-05-13). Si una nota no aparece, verificá los logs en `.cortex/logs/mcp_calls_*.log` para errores de indexing. Como fallback puro: `cortex sync-vault`.

**Las skills no aparecen en Claude Code.** Ejecutá `cortex inject --ide claude-code` de nuevo. Re-genera `.claude/skills/` y `.claude/agents/` desde el canonical en `.cortex/skills/` y `.cortex/subagents/`.

## Desinstalar Cortex de Claude Code

```bash
cortex inject --ide claude-code  # reinstala (idempotente)
# O para borrar:
rm -rf .claude .mcp.json CLAUDE.md
```

`cortex setup` no elimina el repo de Cortex de tu sistema; solo opera sobre el proyecto actual.

## Tripartita Refinada (0.5.0)

A partir de Cortex **0.5.0**, los subagents y skills inyectados en Claude Code obedecen un conjunto de **contratos verificables** llamado *Tripartita Refinada*. Lo que vas a notar como adopter:

### 1. CLAUDE.md tiene una sección nueva

Después de `cortex setup full --ide claude-code` (o `cortex inject --ide claude-code`), el `CLAUDE.md` materializado en el root del proyecto incluye una sección `## Tripartita Refinada — verifiable contracts` con 4 reglas:

- **Verification Gate.** El `cortex-documenter` no puede invocar `cortex_save_session` sin antes haber pasado por `cortex_verify_session_claims`, que cruza los claims del agente contra el `git diff` real y devuelve un label `verified` / `asserted` / `contradicted`.
- **Handoff schema.** Cada handoff entre subagents (sync → SDDwork → explorer/implementer → documenter) tiene que ser un bloque YAML validado por `cortex_validate_handoff` contra el schema `AgentHandoff`. Prosa libre ya no es aceptable — el siguiente agente consume los campos estructurados.
- **Status `handoff` first-class.** Si una verificación falla o el trabajo es parcial, la sesión se cierra con `status: handoff` (no `completed`). Eso le avisa al siguiente agente que hay trabajo abierto que verificar.
- **CONTEXT.md awareness.** Si encontrás un término de dominio que no reconocés, mirá `CONTEXT.md` antes de inventar uno. El documenter actualiza `CONTEXT.md` cuando un término pasa a ser canonical.

### 2. Tools MCP nuevas en el server `cortex`

El MCP server expone 2 tools nuevas que Claude Code descubre automáticamente:

- **`cortex_validate_handoff`** — valida un YAML handoff contra el schema `AgentHandoff`. Devuelve OK con counts (verified_claims, unverified_claims, artifacts) o un mensaje de error con los campos que violaron el schema.
- **`cortex_verify_session_claims`** — recibe una lista de claims del implementador y los cruza contra el diff actual. Devuelve buckets `verified` (≥2 tokens del claim aparecen en el diff) y `asserted` (sin evidencia en el diff). El documenter usa el resultado para llenar el campo `confidence` de cada memoria que persiste.

Ninguna acción manual: si tu `.mcp.json` ya apunta al server `cortex`, las tools nuevas aparecen sin re-configuración.

### 3. Sesiones marcadas como handoff

`cortex_save_session` ahora acepta 5 parámetros opcionales: `handoff` (boolean), `blockers`, `verified_state`, `unverified_claims`, `suggested_skills`. Cuando `handoff=True`, el archivo en `.cortex/vault/sessions/` lleva `status: handoff` en frontmatter, el tag `handoff` se agrega para búsqueda, y aparecen secciones nuevas en el cuerpo (Verified State / Unverified Claims / Blockers / Suggested Skills) cuando las listas correspondientes son no-vacías.

### 4. Confidence labels en respuestas de búsqueda

Cuando el agente llama `cortex_search` o `cortex_context`, los hits que tienen `confidence` definida (memorias post-0.5.0 producidas con el Verification Gate activo) muestran un label `[verified]`, `[asserted]` o `[contradicted]` junto al `memory_type`. Esto le permite a Claude Code ponderar las memorias verificadas por encima de las asertadas al construir prompts de contexto.

## Próximos pasos

- `cortex webgraph serve` para visualizar el grafo de memoria del proyecto.
- `cortex memory-report` para ver salud y promotions hacia el vault enterprise.
- Reuníte con tu equipo para definir `governance.ci_profile` en `.cortex/org.yaml` (observability / advisory / enforced).
