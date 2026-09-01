---
name: tdd
description: Test-Driven Development como ley — cero codigo de produccion sin un test que haya fallado primero. Usar cuando se escribe logica nueva con comportamiento asegurable, cuando un fix necesita garantia antes del cambio, o cuando el humano pide TDD o test-first.
when-to-use: Hay logica que escribir o un bug con reproduccion establecida; el test rojo va primero.
---

# TDD — Iron Law (fase: implement)

**No se escribe codigo de produccion sin un test que haya fallado primero.** Ni una linea. Un test escrito despues no prueba que el codigo lo necesite: prueba que el codigo existe.

## Ciclo

1. **RED**: escribir el test mas chico que avanza el slice. El nombre describe el comportamiento observable, no el implemento. Correrlo. Verlo fallar **por la razon esperada** (assert fallido, no error de infra).
2. **GREEN**: el minimo codigo que pasa el rojo — sin features extra "mientras estoy". Correr: verde.
3. **REFACTOR**: con verde, limpiar duplicacion y nombres. Correr de nuevo. Siguiente slice, vertical.

Cada slice termina con la suite del crate verde (`cargo test -p <crate>`), no solo el test nuevo.
Si un verde llega sin rojo previo, el test no conto: borrarlo y rehacer el ciclo desde el paso 1.

Los anti-patrones que rompen el ciclo (test que pasa primero, mock de lo que se quiere probar, testeos al implemento, verde "deberia pasar", flaky tolerado) y como salir estan en `references/tdd-craft.md` — cargarlo cuando aparezca la tentacion o un ciclo raro.

## Checkpoint obligatorio

El gate de fases exige `artifacts_touched` no vacio + `verified_claims` con evidencia **>10 chars** para `phase: implement` (sin evidencia ⇒ redelegate). En TDD la evidencia son los estados del ciclo, literales: rojo y verde con sus comandos. El inputSchema congelado del server MCP no lista `phase`: pasarlo igual como argumento extra.

```json
cortex_session_checkpoint({
  "session_id": "<activa — ver cortex_session_status>",
  "source": "user-skill",
  "phase": "implement",
  "verified_claims": ["<test <nombre> RED: cargo test <filtro> → FAILED (assert esperado); GREEN: minimo fix → ok; suite crate → N passed>"],
  "unverified_claims": ["<caminos no cubiertos por tests>"],
  "artifacts_touched": ["<archivo bajo test>", "<archivo de produccion>"],
  "note": "<handoff al siguiente slice o a review, <=1 linea>"
})
```

Reglas: `note` <= 1 linea. Un checkpoint por slice cerrado (con el ciclo completo dentro), no por cada rojo/verde suelto.
El rojo y el verde son dos estados del MISMO test: si cambio el test entre ellos, cambie la pregunta, no el codigo.
La garantia del crate se mide con la suite completa, no con el test recien escrito.
