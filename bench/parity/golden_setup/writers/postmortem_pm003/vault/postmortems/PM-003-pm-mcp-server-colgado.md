---
schema_version: 1
doc_type: postmortem
title: 'PM: MCP server colgado'
created_at: '2026-08-24T12:34:56.789012Z'
updated_at: '2026-08-24T12:34:56.789012Z'
tags: []
status: published
links: []
vault_scope: local
fingerprint: 17c5ca56f64e1120112d4029b06283820a148c913ec2d83054f2147dcb96d3db
incident_number: 3
incident_path: INC-003-2026-05-15-mcp-colgado.md
severity: high
---

## Incident Reference

See [[INC-003-2026-05-15-mcp-colgado.md]].

## Severity

**HIGH**

## Root Cause

contrapresión del pipe stderr

## Contributing Factors

- logging a stderr
- cliente lento

## Timeline

- 2026-05-15 incidente
- 2026-05-16 fix

## What Went Well

- diagnóstico rápido

## What Went Wrong

- alerta tardía

## Action Items

- [ ] logs sólo a archivo
- [ ] drain background
