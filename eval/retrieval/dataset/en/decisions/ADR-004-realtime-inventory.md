---
title: ADR-004: Real-time inventory with WebSockets
tags: [doc]
---

## Context
Customers see stale stock levels on product pages.
## Decision
Inventory changes are broadcast via WebSockets from the inventory service.
## Consequences
Requires persistent connections and a load balancer with sticky sessions.
