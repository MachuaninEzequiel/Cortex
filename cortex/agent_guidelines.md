# Cortex Agent - Governance Rules

## MANDATORY: Pre-flight (execute on FIRST user message only)

1. Run `git fetch` silently.
2. If remote has commits not in local branch → **STOP everything** and ask literally:
   > "Encontré actualizaciones en el repo de las memorias, ¿hago pull?"
3. Only on approval → run `git pull`.
4. Run `cortex context --files <files_you_will_touch>` to inject memory context.
5. Notify: **"✅ Pre-flight completo. Puedes cambiar a cortex-work (Tab) para continuar con menor consumo de tokens."**

Never skip this. Never start coding before completing steps 1–5.

---

## Documentation (end of session)

Trigger: user says "done", "wrap up", "terminé", "vamos a commitear", or similar.

Steps:
1. Run `git diff --stat` + `git status`
2. Write `vault/sessions/YYYY-MM-DD_topic.md` with this structure:

```markdown
---
title: "Brief title of what was done"
date: YYYY-MM-DD
tags: [relevant, tags]
status: generated
---

# Session: <title>

## Summary
One paragraph of what was accomplished.

## Changes Made
- file.ext -- what changed and why

## Decisions Taken
- Decision: context -> chosen option -> reason

## Next Steps
- [ ] Pending task
```

3. Run: `git add . && git commit -m "feat/fix: description" && cortex sync-vault`

---

## Rules Summary

| Rule | Action |
|------|--------|
| First message | Always run pre-flight |
| Before touching files | Run `cortex context --files <files>` |
| Architectural decision | Create `vault/decisions/ADR-NNN.md` |
| End of session | Write session note + sync vault |
| No docs generated | Cortex creates a fallback warning note |

## Vault Structure
```
vault/sessions/   <- write here every session
vault/decisions/  <- ADRs
vault/hu/         <- user stories
vault/incidents/  <- bugs found & fixed
vault/security/   <- security changes
```
