---
title: ADR-002: Session caching with Redis
tags: [doc]
---

## Context
User sessions grow and Postgres cannot sustain the read volume.
## Decision
We use Redis as the distributed session cache with a 24h TTL.
## Consequences
Cache invalidation requires pub/sub; Redis failover must be supervised.
