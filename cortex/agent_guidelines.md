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
   - `cortex_create_spec`
4. Hand execution off to `cortex-SDDwork`.

## Ecosystem Isolation

External memory tools are forbidden in a Cortex-governed repository.
Never use:
- `engram_*`
- `mem_*`
- `save_memory`
- `session_summary`

If a memory tool does not start with `cortex_`, it does not belong to this workspace.

## Release 2 Execution Model

- `cortex-sync` prepares context and the spec.
- `cortex-SDDwork` orchestrates implementation through specialized subagents using `cortex_delegate_batch` / `cortex_delegate_task`.
- `cortex-documenter` is the mandatory final step.

## Definition of Done

A task is not complete until Cortex documentation has been written and synced.
