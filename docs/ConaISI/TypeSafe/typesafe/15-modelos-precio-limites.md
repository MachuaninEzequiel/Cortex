# Modelos, precio y límites

Fuente: `https://docs.typesafe.ai/models`. Contexto extra de `/model-jaggedness/jev-1.13` y `/primitives`.

## Modelo actual

Jev es el flagship y el primer System One. Todo modelo de esta página se sirve por el mismo endpoint `POST /v1/systemone`. El campo `model` elige cuál.

| | `jev-1.13.0` |
|---|---|
| Precio | **$42 / Btok** = **$0.042 / Mtok** de **input** |
| Output | **Gratis** |
| Rate limits | 250,000 tokens/segundo · 1,200 requests/minuto |

Un request que pase cualquiera de los dos límites → `429`. SDKs reintentan con backoff y honran `retry-after`.

Warning oficial: los rate limits se están ajustando dinámicamente por demanda. Pueden cambiar without notice. Límites más altos en planes custom/enterprise: `sales@typesafe.ai`.

## Aliases

| Alias | Apunta a | Significado |
|---|---|---|
| `jev-latest` | `jev-1.13.0` | Release estable más reciente. Default SDK. Nombre de los ejemplos |
| `jev-preview` | `jev-1.13.0` | Release más reciente, oficial o no. Se adelanta a `jev-latest` cuando hay preview. **Hoy no hay preview distinto.** |

Un alias se mueve cuando sale un release, así que las answers detrás pueden cambiar sin cambio del caller. El campo `model` de la **response** reporta el ID versionado que contestó: loguearlo. Si hay thresholds de confidence tuneados contra una versión, **pinnear el ID** (`jev-1.13.0`) y migrar a mano.

## Contexto / token budget

Tensión entre páginas oficiales. Se citan las dos:

1. `/primitives`: el presupuesto lo comparten state y questions; “around **32,000 tokens**, roughly 150,000 characters of English text”.
2. `/model-jaggedness/jev-1.13` (más específico, last reviewed 2026-09-16):
   - **64k tokens juntos** para todo `state` + `questions`
   - **32k tokens** para el `state` + la `question` más larga
   - Jev ingesta el state y después procesa todas las questions en paralelo, así que el “context length” no es el de un LLM chat

La forma eficiente: empacar muchas questions por query (fan-out).

## Latencia

How-to-build: la mayoría de queries ~**100 ms**. Use-case map: “frontier intelligence at real-time speeds (**150 ms**)”. Smart-home: la call TypeSafe es tan rápida vs un LLM que el overhead es negligible.

## Qué no hay (hoy)

- Un solo modelo de decisión (Jev). No hay familia mini/large en `/models`.
- Multimodal: no.
- Generación de texto: no.
