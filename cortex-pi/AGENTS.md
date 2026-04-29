# Cortex Agent - Governance Rules (Release 2.5)

## Mandatory Pre-flight

Use `cortex-sync` first.

1. **⚠️ Mandatory Ticket Sync**: Run `cortex_sync_ticket` BEFORE any analysis. Skip this and the MCP server will block your Spec creation.
2. Run `git fetch` silently.
3. If remote has commits not in the local branch, stop and ask:
   > "Encontre actualizaciones en el repo de las memorias, hago pull?"
4. Use Cortex tools only to gather context:
   - `cortex_sync_ticket`
   - `cortex_search`
   - `cortex_context`
   - `cortex_create_spec`

## Ecosystem Isolation

External memory tools are strictly forbidden. Use of any of the following is a governance violation:

- `engram_*`
- `mem_*`
- `save_memory`
- `session_summary`

Rule: **If it doesn't start with `cortex_`, it doesn't belong here.**

## Release 2.5 Execution Model (Full Pipeline)

1. **`cortex-sync`**: Analyzes historical context and prepares the Technical Spec.
2. **`cortex-SDDwork`**: Orchestrator. Evaluates **Intelligent Routing**:
   - 🟢 **Fast Track**: Direct implementation for simple tasks.
   - 🔴 **Deep Track**: Delegation to `cortex-code-explorer` and `cortex-code-implementer`.
3. **`cortex-security-auditor`**: Mandatory security audit (Secrets, OWASP, Static Analysis).
4. **`cortex-test-verifier`**: Mandatory quality gate (>85% coverage, stable types).
5. **`cortex-documenter`**: Mandatory final step. Knowledge persistence.

## Definition of Done

A task is not complete until:
- [ ] Code passes security audit.
- [ ] Code passes test verification (>85% coverage).
- [ ] Documentation has been written and synced to the Vault.
