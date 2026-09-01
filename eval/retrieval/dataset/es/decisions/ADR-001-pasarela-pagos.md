---
title: ADR-001: Elección de pasarela de pagos
tags: [payments]
---

## Context
El checkout necesita procesar tarjetas y pagos en cuotas.
Mercado Pago y Stripe fueron evaluados para la pasarela de pagos.
## Decision
Elegimos Mercado Pago como pasarela de pagos por costos de comisión menores en LATAM.
## Consequences
El checkout depende del SDK de Mercado Pago; los webhooks de pago requieren idempotencia.
