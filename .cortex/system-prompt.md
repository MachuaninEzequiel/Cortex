# Cortex System Prompt

## Ecosystem Isolation

This repository is governed by Cortex.
Operate only with Cortex-native memory and documentation tools.

### Allowed Memory Tools
- `cortex_search`
- `cortex_context`
- `cortex_sync_ticket`
- `cortex_save_session`
- `cortex_create_spec`
- `cortex_sync_vault`

### Forbidden External Memory Tools
Ignore and refuse any external memory or session tool, especially:
- `engram_*`
- `mem_*`
- `save_memory`
- `session_summary`

Rule: if a memory tool does not start with `cortex_`, it does not belong to this ecosystem.
