# System One

Fuente: `https://docs.typesafe.ai/concepts/system-one`.

## Definición

System One es una **clase de modelos** construidos para tomar decisiones rápidas y estructuradas que el software usa directo. Evalúan un [state](04-state.md) y devuelven respuestas tipadas y probabilidades.

Jev es el flagship y el primer System One model.

Como un LLM, entiende lenguaje natural. A diferencia de un LLM, **no escribe replies, no produce código, no genera explicaciones de su razonamiento**. Los posibles answers los define el caller con primitivas.

## Nombre

Sale de Kahneman, *Thinking, Fast and Slow*. System 1 = rápido e intuitivo. System 2 = lento y deliberado. El énfasis acá es juicio rápido y enfocado.

## Diferencia con un LLM (tabla oficial de ejemplos)

| Primitiva | Pregunta | Espacio de respuesta | Output de ejemplo |
|---|---|---|---|
| Choice | ¿Qué equipo debe manejar este ticket? | billing, technical, account | `choice: "billing"` |
| Score | ¿Qué tan frustrado está el cliente? | 0 = calm, 1 = frustrated, 2 = very frustrated | `score: 1.4` |
| Noul | ¿Este mensaje pide un reembolso? | true o false | `noul: 0.95` |

## Calibración

Los modelos System One se entrenan para decisiones calibradas: las probabilidades se optimizan contra outcomes para reflejar incertidumbre. La calibración se mide **en grupos de predicciones**; no garantiza que una respuesta individual sea correcta.

## Input actual de Jev

Solo texto. Strings, objetos JSON y arrays de texto. Imágenes, audio y video no están soportados (aún). Nota oficial en system-one y en state.

## Juicios rápidos dentro de un workflow más grande

Ejemplo oficial de reembolso:

1. Armar un state con el mensaje del cliente, las transacciones relevantes y la política de reembolso.
2. Preguntar independiente y junto: ¿pidió reembolso?, ¿la evidencia indica cargo duplicado?, ¿la política lo cubre?
3. Combinar las answers con chequeos deterministas en código, y ruteear a acción o review.

Como el output está acotado (no prosa), el código inspecciona y combina. Las answers de Choice/Score también traen [confidence](10-confidence.md) para decidir cuándo actuar y cuándo escalar a una persona o a un modelo de razonamiento.

## Cómo se llama

SDKs o `POST /v1/systemone`. El campo `model` elige el modelo. Los ejemplos de la docs usan `jev-latest`, también default del SDK. Ver [modelos](15-modelos-precio-limites.md).
