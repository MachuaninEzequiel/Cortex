---
title: ADR-001: Payment gateway selection
tags: [doc]
---

## Context
The checkout must process cards and installment payments. Mercado Pago and Stripe were evaluated.
## Decision
We chose Stripe as the payment gateway for its developer experience and webhook reliability.
## Consequences
Checkout depends on Stripe SDK; payment webhooks require idempotency keys.
