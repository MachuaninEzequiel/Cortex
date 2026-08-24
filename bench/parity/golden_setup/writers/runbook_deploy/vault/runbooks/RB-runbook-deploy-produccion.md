---
schema_version: 1
doc_type: runbook
title: Runbook deploy producción
created_at: '2026-08-24T12:34:56.789012Z'
updated_at: '2026-08-24T12:34:56.789012Z'
tags:
- ops
status: verified
links: []
vault_scope: local
fingerprint: e6d2e763c3fc79d5114dc64adbb74838e3b9557fd57c701d5d53e2a7bc81f202
runbook_kind: deploy
applies_to:
- producción
estimated_duration_minutes: 45
last_verified_at: '2026-08-01T00:00:00Z'
---

## Description

Pasos para desplegar cortex-memory.

## Kind

**deploy**

## Applies To

- producción

## Prerequisites

- [ ] green CI
- [ ] backup store

## Procedure

### Step 1

taggear release
### Step 2

correr wheels workflow
### Step 3

actualizar pipx

## Rollback Procedure

### Rollback Step 1

reinstalar versión previa
### Rollback Step 2

restaurar store

## Verification

- [ ] cortex doctor --strict

## Estimated Duration

45 minutes

## Last Verified

2026-08-01T00:00:00.000000Z
