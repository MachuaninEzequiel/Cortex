---
name: to-spec
description: Convertir requisitos aclarados en una spec con criterios de aceptacion verificables, scope declarado y verification hooks.
when-to-use: El requisito esta afilado (grill o conversacion) y hay que materializarlo como spec antes de ticketizar o implementar.
disable-model-invocation: true
---

# To Spec — la spec es un contrato verificable (fase: spec)

Una spec buena no describe la solucion: define el problema, el "terminado" observable y los bordes. El middle trabaja contra ella; el documenter la usa al cierre.

## Flujo

1. Reunir el material: conversacion aclarada (idealmente desde `/grill`), ticket/HU si existe, y `CONTEXT.md` si esta en el repo (terminos canonicos obligatorios, sin sinonimos prohibidos).
2. Escribir la spec con las secciones obligatorias:
   - `## Goal` — objetivo medible en 2-3 lineas (verbo + resultado observable).
   - `## Non-goals` — que NO entra (anti-objetivos explicitos).
   - `## Acceptance criteria` — cada criterio responde SI/NO mirando el artefacto, no la intencion. Mal: "el login es rapido". Bien: "login con credenciales validas crea sesion; p95 < 200 ms medido con <comando>".
   - `files_in_scope` — paths que la sesion puede tocar; el gate de scope los usa para medir drift.
   - `## Verification hooks` — comandos `sh -c` ejecutables que prueban el cierre (`exit 0` = paso). Sin hooks, "done" no puede ser "probado".
   - `## Constraints` — rendimiento, compatibilidad, plataformas, prohibiciones.
3. Persistir: con sesion abierta, `cortex_write_doc` (doc_type `spec` → `vault/specs/`). Si hay que abrir spec+sesion desde cero, eso es trabajo de `/cortex-sync` (pre-flight `cortex_sync_ticket` por gobernanza); no lo fuerces desde aca.
4. Quiz de dos preguntas al humano: este criterio se verifica mirando que artefacto exactamente? algo del trabajo futuro queda fuera del scope declarado? Corregir antes de cerrar.

## Checkpoint obligatorio

El gate de fases de Cortex exige al menos un `verified_claims` con evidencia **>10 chars** para `phase: spec` (sin evidencia ⇒ warn). El inputSchema congelado del server MCP no lista `phase`: pasarlo igual como argumento extra.

```json
cortex_session_checkpoint({
  "session_id": "<activa — ver cortex_session_status>",
  "source": "user-skill",
  "phase": "spec",
  "verified_claims": ["<spec escrita y persistida en vault/specs/<path>; criterios verificables confirmados por el humano>"],
  "unverified_claims": ["<lo que quedo asumido sin confirmar>"],
  "artifacts_touched": ["<path de la spec>"],
  "note": "<handoff a to-tickets, <=1 linea>"
})
```

Reglas: `note` <= 1 linea. Nunca dejar la spec solo en el chat: si no queda en disco, no existe para el cierre ni para los gates.
