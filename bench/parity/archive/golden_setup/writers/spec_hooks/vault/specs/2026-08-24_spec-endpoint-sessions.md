---
schema_version: 1
doc_type: spec
title: 'Spec: endpoint /sessions'
created_at: '2026-08-24T12:34:56.789012Z'
updated_at: '2026-08-24T12:34:56.789012Z'
tags:
- api
status: approved
links: []
vault_scope: local
fingerprint: 7ef14f1b3c87fc88cf55e16f235d2522c8d02baadb28ce805799e363180682da
verification_hooks:
- name: build
  command: cargo build --release
  required: true
  success_criteria: exit code 0
  timeout_seconds: 600
- name: lint
  command: ruff check . || true
  required: false
  success_criteria: sin errores bloqueantes
  timeout_seconds: 120
goal: Exponer /sessions con paginación.
files_in_scope:
- src/api/sessions.py
constraints:
- p95 < 200ms
acceptance_criteria:
- curl devuelve 200
- tests integración verdes
---

## Goal

Exponer /sessions con paginación.

## Requirements

- GET lista sesiones
- filtro por fecha

## Files in Scope

- `src/api/sessions.py`

## Constraints

- p95 < 200ms

## Acceptance Criteria

- [ ] curl devuelve 200
- [ ] tests integración verdes

## Verification Hooks

Commands that objectively prove the work is done. Run by
`cortex finish-session` (Pluggable Middle, Phase 01).

### build
```bash
cargo build --release
```

Success: exit code 0 · Timeout: 600s
### lint *(optional)*
```bash
ruff check . || true
```

Success: sin errores bloqueantes · Timeout: 120s
