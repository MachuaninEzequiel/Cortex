# Cortex Git and Vault Policy

## Recommended Tracking Matrix

- Track `vault/specs/`
- Track `vault/decisions/`
- Track `vault/runbooks/`
- Track `vault/hu/`
- Track `vault/incidents/`
- Ignore `vault/sessions/` by default unless the team explicitly audits session history in Git
- Ignore `.memory/` and any Chroma persistence artifacts

## Recommended `.gitignore`

```gitignore
# Cortex local state
.memory/
*.chroma/

# Cortex vault policy
# Track: vault/specs, vault/decisions, vault/runbooks, vault/hu, vault/incidents
# Ignore session churn by default unless your team explicitly audits sessions in Git
vault/sessions/
```

## Notes

- `vault/sessions/` is useful operational history, but it can create high churn in client repositories.
- Durable knowledge should usually be reviewed like code.
- Imported work items in `vault/hu/` are shared context and should usually remain versioned.
