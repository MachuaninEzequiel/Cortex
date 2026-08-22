---
title: Runbook: Checkout outage
tags: [checkout]
---

## Symptoms
Slow checkout or 502 errors when confirming an order.
## Diagnosis
Check payment gateway latency and the Postgres connection pool.
## Mitigation
If Stripe is down, enable deferred queue mode and notify support.
