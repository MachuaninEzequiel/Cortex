---
schema_version: 1
doc_type: incident
title: MCP server colgado 14 minutos
created_at: '2026-08-24T12:34:56.789012Z'
updated_at: '2026-08-24T12:34:56.789012Z'
tags: []
status: mitigated
links: []
vault_scope: local
fingerprint: 700a4bfa3e68c7463857242ad47e7297233c1129bb33989326024c1a165e6b6f
incident_number: 3
severity: high
opened_at: '2026-05-15T09:30:00Z'
closed_at: null
affected_services:
- mcp-server
- opencode
root_cause_postmortem: null
---

## Short Description

stderr sin drenar bloqueó el event loop

## Severity

**HIGH**

## Affected Services

- mcp-server
- opencode

## Impact

subagente bloqueado, contexto perdido

## Timeline

- 09:30 primer reporte
- 10:12 mitigado reiniciando pipe stderr

## Root Cause

Pending postmortem.
