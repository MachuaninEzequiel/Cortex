# API HTTP

Fuente: `https://docs.typesafe.ai/api`.

## Endpoint de evaluación

```http
POST https://api.typesafe.ai/v1/systemone
Authorization: Bearer <API_KEY>
Content-Type: application/json
```

También existe `GET https://api.typesafe.ai/v1/models` (listado de nombres que la cuenta puede mandar en `model`; hoy lista aliases).

## Request body

| Campo | Tipo | Required | Qué es |
|---|---|---|---|
| `state` | string \| object \| array | sí | Contenido a evaluar |
| `model` | string | sí | Modelo. Docs: usar `"jev-latest"` |
| `questions` | map<string, Question> | sí | Mapa de questions. El caller elige cada key; las answers vuelven bajo las mismas keys. **La key no se manda al modelo y no se usa en inference.** |

### Noul

`type: "noul"`, `instructions` (string|object|array), `criteria?` con `true` / `false`.

### Choice

`type: "choice"`, `instructions`, `criteria` map<option, string|null>. Null cuando la opción no necesita detalle extra.

### Score

`type: "score"`, `instructions`, `criteria` array. Mínimo dos niveles.

## Response body

| Campo | Tipo | Qué es |
|---|---|---|
| `model` | string | Modelo que evaluó. Con alias, reporta el ID versionado que contestó |
| `answers` | map<string, Answer> | Una answer por question, mismas keys |
| `usage.input_tokens` | integer | Tokens de input (se cobran) |
| `usage.output_tokens` | integer | Tokens de output (**gratis** según `/models`) |

### Noul answer

`type: "noul"`, `noul: number` (0 = no, 1 = yes).

### Choice answer

`type: "choice"`, `choice: string`, `probabilities: map<string, number>` (suman 1), `confidence: number`.

### Score answer

`type: "score"`, `score: number` (media ponderada; puede caer entre niveles), `legend: map<string, string>`, `probabilities: map<string, number>` (keys = índices de nivel como string), `confidence: number`.

## Errores

| Status | Significado |
|---|---|
| `401 Unauthorized` | API key missing o inválida |
| `422 Unprocessable Entity` | Body falló validación (campo missing, question malformada). El body detalla el campo |
| `429 Too Many Requests` | Rate limit. Back off |
| `529 Overloaded` | TypeSafe temporalmente overloaded. Retry |

Los SDKs reintentan con backoff y honran `retry-after` si viene. Quien llama HTTP directo debe hacer exponential backoff en 429 y 529.

## Listado de modelos

`GET /v1/models` con Bearer. Cada entry: `name`, `description`, `release_date`. Los IDs versionados (`jev-1.13.0`) se aceptan en `model` aunque no aparezcan en la lista.
