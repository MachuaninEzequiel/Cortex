---
title: Runbook: Cache de sesión inválido
tags: [ops]
---

## Síntomas
Usuarios deslogueados aleatoriamente o viendo datos de otros.
## Diagnóstico
Revisar evictions de Redis y desincronización de pub/sub.
## Mitigación
Flush selectivo por namespace de sesión y reinicio gradual de pods.
