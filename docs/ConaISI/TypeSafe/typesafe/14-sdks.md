# Client SDKs

Fuentes: `/sdk`, `/sdk/python`, `/sdk/python/usage`, `/sdk/javascript`.

Los SDKs dan questions y answers tipadas y manejan retries con la policy default.

## Python (`typesafe-sdk`)

Requiere Python ≥ 3.10.

```sh
pip install typesafe-sdk
# o
uv add typesafe-sdk
```

Clientes: `TypeSafeClient` (sync) y `AsyncTypeSafeClient` (async). Context managers.

```python
from typesafe_sdk import Choice, Noul, Score, TypeSafeClient

with TypeSafeClient() as client:
    response = client.system_one(
        state={"document": "..."},
        questions={
            "billing": Noul(instructions="Is this ticket about billing?"),
            "tone": Choice(
                instructions="What is the customer's tone?",
                criteria={"calm": None, "frustrated": None, "angry": None},
            ),
            "urgency": Score(
                instructions="How urgent is this ticket?",
                criteria=["can wait", "this week", "today"],
            ),
        },
    )

print(response.nouls["billing"].noul)
print(response.choices["tone"].choice)
print(response.scores["urgency"].score)
# también: response.answers["billing"].noul
```

`system_one` acepta `state` posicional o keyword, y `questions` posicional o keyword.

### Modelo

```python
print(TypeSafeClient().models.list())
client = TypeSafeClient(model="jev")  # o "jev-latest", "jev-1.13.0"
```

### Retries

`RetryPolicy(max_retries=..., backoff_max=..., timeout=...)` en el client o per-call.

### Errores

`TypeSafeAPIError` con `status` y `request_id`.

### Logging

Logger `typesafe_sdk`. `TYPESAFE_LOG_LEVEL` = debug|info|warning|error|off, aplicado una vez al import. `info`: una línea por request. `debug`: headers y bodies. Headers secretos (authorization, API keys, cookies, nombres con `token` o `secret`) se redactan. **Bodies no se redactan.**

### Environment

| Variable | Qué configura | Default |
|---|---|---|
| `TYPESAFE_API_KEY` | API key (required) | — |
| `TYPESAFE_BASE_URL` | API root | `https://api.typesafe.ai` |
| `TYPESAFE_DEFAULT_MODEL` | Modelo default | `jev-latest` |
| `TYPESAFE_LOG_LEVEL` | Nivel del logger | unset |

### Forward compatibility

- `extra_body={...}` para campos que el SDK todavía no modela.
- Questions como dict crudo (`{"type": "noul", "instructions": "...", "weight": 2}`).
- Answer kinds desconocidos: warning y skip. Inspeccionar `result.raw_http_response.json()["answers"]`.
- Extra fields desconocidos en responses reconocidas: se ignoran.

## JavaScript / TypeScript (`@typesafe-ai/sdk`)

Node.js 20+. ESM, CJS y declarations.

```sh
npm install @typesafe-ai/sdk
```

```ts
import { choice, TypeSafeClient } from "@typesafe-ai/sdk";

const client = new TypeSafeClient();
const response = await client.systemOne({
  state: { document: "I was charged twice. Please fix this ASAP." },
  questions: {
    category: choice("What is this ticket about?", {
      billing: null,
      technical: null,
      other: null,
    }),
  },
});
console.log(response.answers.category.choice);
```

Helpers: `choice()`, `noul()`, `score()`. Los tipos de answer se infieren de las questions.

También se puede llamar la HTTP API desde cualquier lenguaje.
