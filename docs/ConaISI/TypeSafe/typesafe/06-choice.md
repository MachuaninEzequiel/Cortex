# Choice

Fuente: `https://docs.typesafe.ai/primitives/choice`.

## Cuándo usarlo

Cuando la answer es una de un conjunto fijo de opciones. Ejemplos oficiales: qué equipo maneja un ticket, categoría de producto, lenguaje de un snippet. Si es posición en un espectro → Score. Si es sí/no → Noul.

## Request

Top-level: `state`, `model`, `questions` (mapa id → question).

Campos de una Choice:

- `type`: siempre `"choice"`.
- `instructions`: la pregunta.
- `criteria`: mapa. Key = nombre de opción; value = descripción (string, objeto, array o `null`).

Hasta **255 opciones**. Agregar opciones cuesta pocos tokens; dar la lista completa (equipos, categorías, productos) en vez de un shortlist. Agregar `other` / `none of the above` cuando la lista puede no cubrir todo input.

El ID de la question no se manda al modelo. Los **nombres de opción y sus descripciones sí**. Escribir descripciones que separen las opciones entre sí.

`instructions` y cada entry de `criteria` pueden ser string, object o array. Empezar con string. Usar object cuando hace falta several kinds of guidance (qué cubre, qué no, ejemplos).

## Response

Bajo el mismo id:

- `type`: `"choice"`
- `choice`: la opción de mayor probabilidad
- `probabilities`: distribución completa. Suman 1
- `confidence`: 0–1, derivado de qué tan spread está `probabilities`. Plana → baja. Pico único → alta

Ejemplo fácil de la docs (zapatos talle incorrecto → `returns` con confidence 1.0, probabilidad 1.0 en returns).

Ejemplo ambiguo (talle + dos cargos + “what are you going to do”):

- `department`: `returns` 0.60, `billing` 0.38, `shipping` 0.02, **confidence 0.39**. El top es accionable; el segundo no es ruido.
- `return_reason`: `wrong_size` confidence 1.0.
- `shipping_issue`: split `delayed` 0.63 / `other` 0.37, confidence 0.53 — pregunta especulativa; si department no es shipping, el código la ignora.
- `requested_resolution`: confidence **0.16**, distribución chata: el cliente no dijo qué quiere.
- `tone`: `frustrated` 0.92, confidence 0.88.

Patrón de código oficial: si `department.confidence < 0.3` → triage humano. Si una segunda opción tiene probabilidad > 0.25, notificar a ese equipo también. Si `requested_resolution.confidence < 0.5` → preguntar al cliente, no adivinar.

## Buenas prácticas

- Más de una Choice por call. Las especulativas se ignoran si no aplican.
- Para taxonomías profundas: encadenar Choice nivel por nivel. Cookbook Hierarchical Classification: beam search sobre las probabilities, guardar las mejores K paths, no un greedy path único.
- `criteria` con `null` cuando el nombre de la opción ya es claro (`calm`, `frustrated`, `angry`).
- Si dos opciones se confunden, estructurar cada una con `what` / `not_for` / `examples` (ver [estructura avanzada](09-estructura-avanzada.md)). Ejemplo oficial: `return_policy` vs `return_status` — ambas mencionan returns; el `not_for` las separa y la answer sale `return_status` con confidence 1.0.
