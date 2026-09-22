# Noul

Fuente: `https://docs.typesafe.ai/primitives/noul`.

## Cuándo usarlo

Cuando la answer es sí o no. Ejemplos oficiales: ¿el mensaje pide reembolso?, ¿el resume menciona distributed systems?, ¿el comentario contiene PII?, ¿el cuarto tiene minibar?

Conjunto de opciones → Choice. Espectro → Score.

## Request

| Campo | Required | Descripción |
|---|---|---|
| `type` | sí | `"noul"` |
| `instructions` | sí | La pregunta o statement sí/no |
| `criteria` | no | `{ true, false }` describiendo qué significa yes y no |

Buen practice: phrasing tal que **alta probabilidad = “yes”**, para que la answer no sea ambigua.

Probar con y sin `criteria` en el use-case propio. El instruction alcanza para la mayoría; `criteria` ayuda cuando el borde sí/no es sutil.

## Response

Un solo número: `noul` ∈ [0, 1] = probabilidad de que la answer sea **yes**. Cerca de 1 = sí fuerte. Cerca de 0 = no fuerte. Cerca de 0.5 = yes y no con probabilidad similar.

Lo más habitual: thresholdar a boolean cuando el código necesita una decisión dura.

Ejemplo oficial:

State: `"I have asked three times now. Can I please just talk to a real person?"`

- `is_human_escalation` → noul 0.99
- `is_repeat_contact` (con criteria true/false) → noul 0.93

## Noul no devuelve confidence aparte

La propia probabilidad *es* la incertidumbre. No hay segundo eje.

Recordatorio: 0.5 **no** es “nivel medio”. “Is the candidate strong in Python?” mal definido hace la probabilidad ininterpretable. Para skill, usar Score.

## Tips oficiales

- Además de pregunta, se puede phrasing como **statement** a evaluar por truthfulness. Para “the customer is requesting a refund”, un valor cerca de 1 significa que el statement es true. Probar ambos phrasings con datos propios.
- `criteria` opcional con descripciones `true`/`false` para clavar el borde.
- Alinear instructions y criteria. Un Noul donde `true` mapea a “no” y `false` a “yes” rinde peor (jaggedness: contradictory instructions).
