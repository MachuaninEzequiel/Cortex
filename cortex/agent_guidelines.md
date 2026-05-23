# Cortex Agent - Governance Rules

## Mandatory Pre-flight

Use `cortex-sync` first.

1. Run `git fetch` silently.
2. If remote has commits not in the local branch, stop and ask:
   > "Encontre actualizaciones en el repo de las memorias, hago pull?"
3. Use Cortex tools only to gather context:
   - `cortex_sync_ticket`
   - `cortex_search`
   - `cortex_context`
   - `cortex_create_spec` (con `verification_hooks` recomendados)
4. Sync abre la Session automaticamente al persistir el spec.

## Ecosystem Isolation

External memory tools are forbidden in a Cortex-governed repository.
Never use:

- `engram_*`
- `mem_*`
- `save_memory`
- `session_summary`

If a memory tool does not start with `cortex_`, it does not belong to this workspace.

## Execution Model (Pluggable Middle, Fase 02+)

Cortex envuelve el workflow en tres puntos: **sync** (antes), **middle**
(durante) y **documenter** (despues). El "middle" es **pluggable** — admite
tres modos:

| Modo | Middle | Cuando usarlo |
|---|---|---|
| **Managed** | `cortex-SDDwork` + subagents | Default cuando el usuario no trae tooling propio. |
| **Observed** | Agente del usuario + IDE hooks | El usuario tiene skills/agentes propios pero quiere que Cortex observe. |
| **BYO** | Lo que sea (manual, otro agente) | Maxima libertad; Cortex reconstruye desde diff. |

- `cortex-sync` prepara contexto y persiste la spec con verification hooks. **Abre la Session.**
- **Middle (uno de los tres):**
  - **Managed**: `cortex-SDDwork` orquesta. Cada paso significativo emite un `cortex_session_checkpoint`. Subagent delegation es nativa del IDE (Task tool en Claude Code, `mode: subagent` en opencode, secuencial single-agent en Codex). El MCP server NO expone tool de delegate — ver `docs/multi-ide-mcp-hardening/MATRIZ-NATIVA-IDES.md` seccion 5.
  - **Observed**: el agente externo del usuario hace el trabajo; opcionalmente IDE hooks (Fase 03) emiten checkpoints.
  - **BYO**: el usuario codea sin emitir checkpoints. La reconstruccion se basa 100% en el diff.
- `cortex-documenter` cierra la Session via `cortex finish-session` (CLI) o `cortex_finish_session` (MCP). NO emite YAML; lee la Session y reconstruye.

## Contrato compartido entre agentes Cortex

A partir de Fase 02, el contrato entre `cortex-sync`, `cortex-SDDwork`,
`cortex-code-explorer`, `cortex-code-implementer` y `cortex-documenter`
es la **Session**. NO se usan handoffs YAML inline.

- Emite checkpoints con `cortex_session_checkpoint(source=<agent-id>, ...)`.
- `cortex_validate_handoff` esta **deprecated** desde Fase 02 (queda para
  modo Legacy YAML del documenter, usado solo por Codex y compat).
- El schema `cortex.handoff.AgentHandoff` sigue siendo valido pero ya no
  es el contrato principal.

## Definition of Done

A task is not complete until:

1. `cortex finish-session` se ejecuto (o `cortex_finish_session` via MCP).
2. La Session esta en status `CLOSED` (o `HANDOFF` si el trabajo es parcial).
3. El session note esta persistido en el Vault.
4. La memoria episodica + semantica esta indexada con la nueva nota.
