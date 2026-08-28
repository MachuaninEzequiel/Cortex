---
name: review
description: Revision de codigo en dos ejes paralelos — Standards y Spec — con reportes separados y hallazgos accionables con file:line.
when-to-use: El trabajo esta implementado y, antes de cerrar la sesion o abrir PR, hay que revisarlo con criterio propio.
disable-model-invocation: true
---

# Review — dos ejes, un veredicto (fase: review)

Revisar solo "que compile y ande" es medio. Los dos ejes corren **en paralelo y se reportan separado**: uno mira la calidad del codigo, el otro la fidelidad a la spec.

## Flujo

1. **Eje Standards (calidad)**: diff contra `files_in_scope`; profundidad de modulos, duplicacion, nombres, errores tragados, tests que verifican comportamiento (no mocks). Checklist y formato de hallazgos en `references/review-craft.md` — cargarlo recien al empezar el eje.
2. **Eje Spec (fidelidad)**: cada Acceptance criterion de la spec, verificado contra el artefacto (comando corrido, no lectura de intencion); drift de scope; `unverified_claims` abiertos de los checkpoints `implement`.
3. **Hallazgos accionables**: file:line + que esta mal + por que importa + fix sugerido. Sin file:line no es hallazgo, es opinion. Severidades: Critical (bloquea) / Important (fix antes de close) / Minor (defer).
4. **Gate entre pasos** (opcional): `cortex_review_checkpoint` sobre el ultimo checkpoint `implement` — su `redelegate` pesa mas que tu opinion.
5. Veredicto: `approve` (sin Critical/Important), `request-changes` (con Important), `block` (con Critical).
6. Los Critical/Important se fixean ANTES de emitir el checkpoint review; los Minor se registran en `unverified_claims` o salen como ticket nuevo — nunca se negocian a bajo para poder cerrar.
7. Re-check: lo fixado se verifica contra el MISMO criterio del hallazgo, no contra la palabra del autor.

## Checkpoint obligatorio

El gate de fases exige al menos un `verified_claims` con evidencia **>10 chars** para `phase: review` (sin evidencia ⇒ warn). La evidencia: que se corrio y que se encontro, por eje. El inputSchema congelado del server MCP no lista `phase`: pasarlo igual como argumento extra.

```json
cortex_session_checkpoint({
  "session_id": "<activa — ver cortex_session_status>",
  "source": "user-skill",
  "phase": "review",
  "verified_claims": ["<Standards: <hallazgos o 'limpio', con los archivos revisados> · Spec: <criterios verificados + comando corrido> ⇒ veredicto <approve/request-changes/block>>"],
  "unverified_claims": ["<lo que no se pudo verificar y por que>"],
  "artifacts_touched": [],
  "note": "<handoff al cierre, <=1 linea>"
})
```

Reglas: `note` <= 1 linea. La revision no se salta aunque el cambio sea "obvio": los cambios obvios son los que se arreglan dos veces.
Un `approve` sin evidencia corrida es un no-evento: el gate de review lo marca igual (warn) que un claim vacio.
Si el autor responde un hallazgo con "funciona", el hallazgo sube de severidad: no se discutio el porque.
