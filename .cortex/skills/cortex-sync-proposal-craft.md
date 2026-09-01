---
name: cortex-sync-proposal-craft
description: Craft on-demand para plantear alternativas honestas (cargar desde cortex-sync antes de cortex_emit_proposal).
---

# Proposal Craft — alternativas como un experto

Cargá este archivo SOLO antes de `cortex_emit_proposal` (PASO 3.5 de
`cortex-sync`).

## Cuándo ofrecer alternativas

- **Siempre que haya más de una forma razonable** de resolver el problema.
- **Nunca** fabriques alternativas para llenar la estructura: si solo hay
  una vía correcta, decila en el resumen y marcá las otras como descartadas
  con su razón.
- Si el ticket ya fija la solución, la propuesta igual vale: el resumen
  documenta POR QUÉ esa y no otra (protege la decisión para el futuro).

## rejected_reason honesto (evidencia, no gusto)

| MALO (gusto) | BUENO (evidencia) |
|---|---|
| "Es más complejo" | "Añade un crate nuevo con 3 deps; la alternativa B reusa el BM25 existente" |
| "No me gusta" | "El timestamp viaja en la query y rompe el cache por sha256 (ver ADR-X)" |
| "Podríamos arrepentirnos" | "Cambia el wire-format congelado del MCP; requeriría recaptura de goldens" |

Si la razón real es costo/esfuerzo/riesgo, decila así, con el dato:
"fuerza de trabajo ~3x la opción C, mismo resultado funcional".

## Estructura de la propuesta

1. **summary**: resumen ejecutivo de 2-3 líneas (problema + dirección
   recomendada).
2. **alternatives**: 2-3 opciones (A, B, C) con descripción corta y
   `rejected_reason` — la recomendada puede llevar `rejected_reason: ""`.
3. **recommendation_id**: la elegida.
4. **risks**: los 1-3 riesgos que si salen mal, importan (no relleno).

## Regla de oro

El usuario decide con la card; tu honestidad en los descartes es lo que hace
la decisión defendible en el futuro. Un `rejected_reason` vago es lo primero
que un reviewer va a impugnar.