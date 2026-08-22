---
title: ADR-004: Stock en tiempo real con WebSockets
tags: [realtime]
---

## Context
Los usuarios ven stock desactualizado en la ficha de producto.
## Decision
Publicamos cambios de stock vía WebSockets desde el servicio de inventario.
## Consequences
Requiere conexiones persistentes y un balanceador compatible con sticky sessions.
