---
schema_version: 1
doc_type: adr
title: Usar tokens vs sesiones para auth
created_at: '2026-08-24T12:34:56.789012Z'
updated_at: '2026-08-24T12:34:56.789012Z'
tags:
- auth
- latencia
status: accepted
links:
- spec-2026-08-01
vault_scope: local
fingerprint: d48f34e1f0402cbb63158a962bd8228f90e845b31b7ed623b1f55de825a70675
adr_number: 7
supersedes: []
superseded_by: null
alternatives_considered:
- sesiones httpOnly con store compartido
- JWT stateless con revocación vía blacklist
acceptance_criteria_met: true
---

## Context

El servicio necesita recordar al usuario entre despliegues: la sesión en memoria no sobrevive restarts y la latencia p99 de regenerar sesión es inaceptable para el SLA acordado.

## Decision

Emitimos tokens opacos firmados con rotación cada 24h.

## Alternatives Considered

- sesiones httpOnly con store compartido
- JWT stateless con revocación vía blacklist

## Consequences

Requiere cache Redis; simplifica el escalamiento horizontal.

