---
name: implement
description: Implementar un ticket con contexto fresco, verificando con evidencia y cerrando con checkpoint. Usar cuando hay un ticket desbloqueado listo para codigo, cuando el humano pide implementar o tomar un issue, o al ejecutar un plan ticketizado.
when-to-use: Un ticket esta desbloqueado y hay que llevarlo a codigo con evidencia verificable.
---

# Implement — un ticket a la vez, con evidencia (fase: implement)

El middle COMPOSED no impone como codeas; impone como **registras**. Esta skill es el punto de entrada cuando hay un ticket listo.

## Flujo

1. **Contexto fresco**: leer solo el ticket y la spec (los paths vienen del checkpoint `plan`). Si el ticket no esta a mano, pedirlo — no asumir de memoria de conversacion.
2. **Plan chico antes de tocar**: 2-4 pasos, cada uno con su verificacion. Si el plan pasa los 6 pasos, el ticket era muy grande: volver a `/to-tickets`.
3. **Implementar el slice** respetando `files_in_scope` de la spec. Si hace falta tocar algo fuera de scope: PARAR y registrar el drift en `unverified_claims` avisando al humano (nunca expandir scope en silencio).
4. **Validar con evidencia real**: correr el `Verification` del ticket (test, comando, paso reproducible). Lo que no se corro, NO entra como `verified_claims`.
5. Disciplina segun el caso: para logica nueva, "Call the Skill tool with `tdd`" ANTES de escribir codigo de produccion; para un bug sin reproduccion estable, "Call the Skill tool with `diagnose`".
6. Cierre del slice: commit atomico del ticket (los demas archivos quedan para su propio slice).
7. Antes del checkpoint, correr la suite del crate tocado: el verde del slice no exonera al resto.

El fino del oficio (revision del diff propio, tamanos de cambio, evidencia honesta, cuando delegar) esta en `references/implement-craft.md` — cargarlo solo cuando el slice no es trivial.

## Checkpoint obligatorio (por ticket)

El gate de fases exige `artifacts_touched` no vacio + al menos un `verified_claims` con evidencia **>10 chars** para `phase: implement` — sin evidencia ⇒ **redelegate** (no "mas vago": con comando y resultado). El inputSchema congelado del server MCP no lista `phase`: pasarlo igual como argumento extra.

```json
cortex_session_checkpoint({
  "session_id": "<activa — ver cortex_session_status>",
  "source": "user-skill",
  "phase": "implement",
  "verified_claims": ["<ticket NN: que se hizo + comando corrido + resultado observado>"],
  "unverified_claims": ["<lo asumido sin probar, incl. drift de scope si lo hay>"],
  "artifacts_touched": ["<paths tocados por el slice>"],
  "note": "<handoff al siguiente ticket o a review, <=1 linea>"
})
```

Reglas: `note` <= 1 linea. 1-3 checkpoints ricos por sesion; no uno por archivo. Si el slice no dejo artefacto ni evidencia, todavia no esta implementado: no emitir checkpoint "prolijos" con campos vacios.
Los `unverified_claims` no son verguenza: son el mapa de lo que el cierre todavia no puede probar.
