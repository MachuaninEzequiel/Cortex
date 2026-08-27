---
title: Cortex Git and Vault Policy
tags: [runbook, governance, git]
created: 2026-04-26
---

# Cortex Git and Vault Policy

## Recommended Tracking Matrix

- Track `vault/specs/`
- Track `vault/decisions/`
- Track `vault/runbooks/`
- Track `vault/hu/`
- Track `vault/incidents/`
- Ignore `vault/sessions/` by default unless your team explicitly audits session history in Git
- Ignore `.memory/` and any Chroma persistence artifacts

## Recommended `.gitignore` Snippet

```gitignore
# Cortex local state
.memory/
*.chroma/

# Cortex vault policy
# Track: vault/specs, vault/decisions, vault/runbooks, vault/hu, vault/incidents
# Ignore session churn by default unless your team explicitly audits sessions in Git
vault/sessions/
```

## Policy Notes

- `vault/sessions/` is operational history, so it can create high churn. Teams may choose to track it, but the default recommendation is to keep it local.
- `vault/specs/`, `vault/decisions/` and `vault/runbooks/` are durable knowledge and should usually be reviewed like code.
- Imported work items in `vault/hu/` are useful shared context and should normally be versioned.
