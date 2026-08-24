---
schema_version: 1
doc_type: adr
title: Migrar colas a Redis Streams
created_at: '2026-08-24T12:34:56.789012Z'
updated_at: '2026-08-24T12:34:56.789012Z'
tags: []
status: proposed
links: []
vault_scope: local
fingerprint: 0eea3fc7260aafa79192c6ce990ed4df8d815024280a627c70f6e90900ecdd4c
adr_number: 2
supersedes: []
superseded_by: null
alternatives_considered: []
acceptance_criteria_met: false
---

## Context

La cola actual pierde mensajes.

## Decision

Redis Streams con consumer groups.

## Alternatives Considered

(none)

## Consequences

Requiere redis >= 6.2.

