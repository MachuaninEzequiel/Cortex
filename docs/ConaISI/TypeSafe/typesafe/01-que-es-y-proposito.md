# Qué es TypeSafe y para qué existe

Fuente: `https://docs.typesafe.ai/introduction` y `https://docs.typesafe.ai/introduction/quickstart`.

## El mismatch que TypeSafe declara

Los LLM están diseñados para producir texto que un humano lee. Cuando el código necesita un juicio (clasificar, ruteear, puntuar, decidir sí/no), hay un desajuste: se fuerza a un generador de texto a emitir decisiones estructuradas y después se parsea el resultado.

Jev es el modelo flagship de TypeSafe y el primer **System One model**. Evalúa preguntas tipadas contra un **state** y devuelve resultados estructurados. Sin generación de texto, sin parsing. Valores tipados y distribuciones de probabilidad que el código puede ramificar, ordenar y ruteear.

## Las tres primitivas (tabla oficial)

| Tipo de pregunta | Objetivo | Devuelve |
|---|---|---|
| Choice | Elegir una opción de una lista | `choice`, `probabilities`, `confidence` |
| Score | Puntuar el state en una rúbrica | `score`, `probabilities`, `confidence` |
| Noul | ¿Es verdadera esta afirmación? | `noul` (0–1) |

Las tres se mezclan en una sola llamada. Cada pregunta se evalúa en paralelo y en aislamiento contra el mismo state. Añadir preguntas casi no cambia el tiempo de respuesta. Como son independientes, añadir más no crea context-rot entre ellas.

## Preguntas atómicas, composición en código

System One funciona mejor cuando cada pregunta pide **una sola cosa**, bien acotada. Analogía de la docs: el juicio que una persona muy informada haría en unos segundos con el contexto correcto.

Si la pregunta exigiría razonamiento extendido o mezcla factores independientes, hay que descomponer: un factor por pregunta, combinar en código. Ejemplo oficial: no “rate this startup pitch”; sí market size, technical feasibility y differentiation por separado, y una fórmula propia. Si cambian las prioridades, se cambia un coeficiente, no un prompt.

## Quick start (cuatro caminos oficiales)

1. **Playground.** `https://console.typesafe.ai/playground`. Pegar texto como state, agregar preguntas.
2. **HTTP.** `POST https://api.typesafe.ai/v1/systemone` con `Authorization: Bearer <API_KEY>`.
3. **Python SDK.** `pip install typesafe-sdk` o `uv add typesafe-sdk`. Python ≥ 3.10. Cliente lee `TYPESAFE_API_KEY`. Default `jev-latest`.
4. **Agent skill.** Plugin Claude Code `typesafe@typesafe-ai` o `npx skills add typesafe-ai/skills --skill typesafe-ai`.

## Ejemplo canónico de la docs (ticket Stripe)

State:

```text
Hi, I've been trying to connect my Stripe account for 3 days and it keeps failing. I'm losing sales. Please help ASAP.
```

Tres preguntas en un request:

- Choice `department`: billing / technical / sales.
- Score `frustration`: calm → frustrated → very angry.
- Noul `is_urgent`: el mensaje transmite urgencia.

Respuesta ilustrativa de la docs:

```json
{
  "model": "jev-latest",
  "answers": {
    "department": {
      "type": "choice",
      "choice": "technical",
      "probabilities": { "billing": 0.159, "technical": 0.84, "sales": 0.001 },
      "confidence": 0.596
    },
    "frustration": {
      "type": "score",
      "score": 1.035,
      "legend": {
        "0": "Calm, just stating facts",
        "1": "Frustrated but civil",
        "2": "Very angry, strong language"
      },
      "confidence": 0.842
    },
    "is_urgent": { "type": "noul", "noul": 0.999 }
  },
  "usage": { "input_tokens": 312, "output_tokens": 48 }
}
```

El código lee `.choice`, `.score`, `.noul`. No parsea prosa.

## SDK Python (forma oficial)

```python
from typesafe_sdk import Choice, Noul, Score, TypeSafeClient

client = TypeSafeClient()
response = client.system_one(state=ticket, questions={...})
response.answers["department"].choice
response.answers["frustration"].score
response.answers["is_urgent"].noul
```

También se puede indexar por tipo: `response.nouls`, `response.choices`, `response.scores`.
