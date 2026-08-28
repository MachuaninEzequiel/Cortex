---
name: to-tickets
description: Descomponer la spec en tickets como vertical slices (tracer bullets), cada uno con su verificacion y sus blocking edges declarados.
when-to-use: La spec esta escrita y persistida; hay que partir el trabajo en unidades que quepan cada una en una ventana de contexto fresca.
disable-model-invocation: true
---

# To Tickets — un ticket = una ventana de contexto (fase: plan)

El ticket es la unidad de contexto descartable: lo que cierra con una ventana fresca teniendo la spec como ancla. No son "tareas de 10 minutos": son slices que entregan algo verificable.

## Flujo

1. Leer la spec persistida (path de la sesion o `vault/specs/`), especialmente Goal, Non-goals y Acceptance criteria.
2. Ticketizar en **vertical slices (tracer bullets)**: cada ticket atraviesa las capas necesarias para un resultado observable — no "hacer el modelo", "hacer la UI". Cada ticket lleva:
   - `What` — el corte observable que entrega.
   - `Blocked by` — edges explicitos entre tickets (numeros). Sin edges declarados, el orden es improvisacion.
   - `Verification` — el paso que lo prueba (comando o criterio de la spec). Sin verificacion, no es ticket.
   - `Done when` — condicion binaria mirando el artefacto.
3. Presupuesto de contexto: si para cerrar el slice hace falta recordar cosas que ya no estan en pantalla, el slice es muy grande — partirlo.
4. Persistir los tickets en `.scratch/<feature>/issues/NN-<slug>.md`, numerados, con sus edges.
5. Ordenar: el primer ticket debe ser un tracer bullet que atraviese todas las capas — enderezar el camino antes de ensancharlo.
6. Chequeo final antes de checkpoint: cada ticket se puede cerrar sin abrir el contexto de los demas? Si no, el corte esta mal hecho.

## Checkpoint obligatorio

El gate de fases exige al menos un `artifacts_touched` para `phase: plan` — los tickets en disco SON el artifact (plan sin archivo ⇒ warn). El inputSchema congelado del server MCP no lista `phase`: pasarlo igual como argumento extra.

```json
cortex_session_checkpoint({
  "session_id": "<activa — ver cortex_session_status>",
  "source": "user-skill",
  "phase": "plan",
  "verified_claims": ["<N tickets escritos, cada uno con Verification y Done-when; edges declarados entre ellos>"],
  "unverified_claims": ["<supuestos sobre orden o bloqueos que el humano no confirmo>"],
  "artifacts_touched": [".scratch/<feature>/issues/01-<slug>.md", ".scratch/<feature>/issues/02-<slug>.md"],
  "note": "<handoff a implement: por que ticket empezar y por que, <=1 linea>"
})
```

Reglas: `note` <= 1 linea. UN checkpoint por ticketizacion completa (no uno por ticket): el plan es una decision, no una lista de tareas. Si durante la ticketizacion aparece que la spec tiene un criterio no verificable, volver a `/to-spec` antes de seguir.
