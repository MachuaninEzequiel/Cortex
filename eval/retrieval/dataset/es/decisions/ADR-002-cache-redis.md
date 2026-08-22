---
title: ADR-002: Cache de sesiones con Redis
tags: [redis]
---

## Context
Las sesiones de usuario crecen y Postgres no soporta el volumen de lecturas.
## Decision
Usamos Redis como cache distribuido para sesiones con TTL de 24 horas.
## Consequences
La invalidación de cache requiere pub/sub; el failover de Redis debe ser supervisado.
