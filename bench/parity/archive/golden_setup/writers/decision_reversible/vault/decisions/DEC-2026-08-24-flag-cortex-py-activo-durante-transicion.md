---
schema_version: 1
doc_type: decision
title: Flag CORTEX_PY activo durante transición
created_at: '2026-08-24T12:34:56.789012Z'
updated_at: '2026-08-24T12:34:56.789012Z'
tags: []
status: active
links: []
vault_scope: local
fingerprint: 09cee65a35effb8514da2066ede5fae61bd292212c5edaa0c19d204c5b3536a6
reversible_within_days: 14
---

## Context

Doble vía CLI.

## Decision

Env var fuerza CLI viejo.

## Alternative Rejected

Feature flags por comando

## Reason

Simplicidad operativa.

## Reversibility

This decision can be reverted within 14 days without significant cost.
