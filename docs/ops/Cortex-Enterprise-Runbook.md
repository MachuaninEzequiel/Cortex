# Cortex Enterprise Runbook

## Purpose

This runbook defines the shared operating model for teams using Cortex across local development, CI and multi-project analysis.

## Roles

### DevOps

- Run `cortex setup pipeline` in governed repositories.
- Validate baseline health with `cortex doctor`.
- Keep `.memory/` local-only and out of Git.
- Wire CI to run `cortex verify-docs` and `cortex validate-docs`.

### Developers

- Start with `cortex-sync` before implementation work.
- Persist specs in `vault/specs/`.
- Persist working outcomes in `vault/sessions/`.
- Use `cortex search` and `cortex context` before repeating prior work.

### Analysts

- Use `cortex webgraph serve --project-root <repo>` for one repository.
- Use `cortex webgraph serve --workspace-file .cortex/webgraph/workspace.yaml` for a federated view.
- Filter the WebGraph by project, node type and recent activity to reduce noise.

### Staff / Tech Leads

- Review `vault/decisions/` for architectural drift.
- Keep `vault/runbooks/` current when delivery or support flows change.
- Decide explicitly whether session notes are Git-tracked in your environment.

## Daily Checks

```bash
cortex doctor
cortex validate-docs --vault vault
```

## Release Readiness

- Confirm `vault/specs/`, `vault/decisions/`, `vault/runbooks/` and `vault/hu/` are current.
- Confirm local-only state remains outside Git.
- Re-run `cortex doctor --strict` before publishing Cortex tooling changes.
