---
title: Runbook: Caída del checkout
tags: [checkout]
---

## Síntomas
Checkout lento o errores 502 al confirmar pedido.
## Diagnóstico
Verificar latencia de la pasarela de pagos y pool de conexiones a Postgres.
## Mitigación
Si Mercado Pago está caído, activar el modo de cola diferida y avisar a soporte.
