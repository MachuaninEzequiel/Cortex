---
schema_version: 1
doc_type: adr
title: Política de retención de datos personales
created_at: '2026-08-24T12:34:56.789012Z'
updated_at: '2026-08-24T12:34:56.789012Z'
tags:
- governance
status: accepted
links: []
vault_scope: enterprise
fingerprint: 0a16cbf7b16cf18b1ba8f8f1b62c396f0b39c70c4f7de9d40e5cbcc093a88f01
owner: dpo@empresa.co
team: platform
classification: confidential
retention_days: 365
audit_trail:
- actor: lead@empresa.co
  action: created
  timestamp: '2026-08-24T12:34:56.789012Z'
  reason: null
adr_number: 12
supersedes: []
superseded_by: null
alternatives_considered: []
acceptance_criteria_met: false
---

## Context

Cumplimiento normativo.

## Decision

Borrado automático a los 365 días.

## Alternatives Considered

(none)

## Consequences

Jobs nocturnos de purga.

