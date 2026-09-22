# Cortex Agent Governance Rules

This workspace uses the Release 2 Cortex operating model:

- `cortex-sync` performs pre-flight, context gathering and spec preparation.
- `cortex-SDDwork` is the implementation orchestrator with Direct default and on-demand specialist delegation.
- Specialized subagents live in `.cortex/subagents/`.
- Every implementation must end by invoking `cortex-documenter`.

## Non-Negotiable Rules

1. Never use external memory tools.
2. Never close a task without Cortex documentation.
3. `cortex-sync` must call `cortex_sync_ticket` before drafting a spec.
4. `cortex-SDDwork` defaults to direct implementation and uses specialists only on demand.
5. Treat `cortex-documenter` as part of the definition of done.
