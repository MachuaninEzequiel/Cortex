# Índice — documentación TypeSafe (fuente oficial)

Carpeta extraída de `https://docs.typesafe.ai` el 2026-09-17. Índice canónico de TypeSafe: `https://docs.typesafe.ai/llms.txt`. Sitemap: `https://docs.typesafe.ai/sitemap.xml`.

No se usó marketing de `typesafe.ai` salvo el manifiesto citado por la propia docs (`https://typesafe.ai/manifesto` en el AI primer). No se inventaron campos de API.

## Orden de lectura

| # | Archivo | Página(s) origen |
|---|---------|------------------|
| 01 | [Qué es y propósito](01-que-es-y-proposito.md) | `/introduction`, `/introduction/quickstart` |
| 02 | [System One](02-system-one.md) | `/concepts/system-one` |
| 03 | [Entrenamiento RLCD](03-entrenamiento-rlcd.md) | `/introduction/machine-learning-primer` |
| 04 | [State](04-state.md) | `/concepts/state` |
| 05 | [Primitivas](05-primitivas.md) | `/primitives` |
| 06 | [Choice](06-choice.md) | `/primitives/choice` |
| 07 | [Score](07-score.md) | `/primitives/score` |
| 08 | [Noul](08-noul.md) | `/primitives/noul` |
| 09 | [Estructura avanzada](09-estructura-avanzada.md) | `/primitives/advanced` |
| 10 | [Confidence](10-confidence.md) | `/confidence` |
| 11 | [Cómo construir](11-como-construir.md) | `/concepts/how-to-build-with-system-one` |
| 12 | [Patrones](12-patrones.md) | `/patterns`, fan-out, confidence-routing, composite-scoring, intent-routing |
| 13 | [API HTTP](13-api-http.md) | `/api` |
| 14 | [SDKs](14-sdks.md) | `/sdk`, `/sdk/python`, `/sdk/python/usage`, `/sdk/javascript` |
| 15 | [Modelos, precio, límites](15-modelos-precio-limites.md) | `/models` + nota de contexto en jaggedness |
| 16 | [Jaggedness Jev 1.13](16-jaggedness-jev-1.13.md) | `/model-jaggedness/jev-1.13` |
| 17 | [Cookbooks](17-cookbooks.md) | `/cookbooks/*` (18 recetas) |
| 18 | [Casos de uso y demos](18-casos-de-uso-y-demos.md) | `/concepts/use-case-map`, `/demos`, `/demos/smart-home` |
| 19 | [Agent skill](19-agent-skill.md) | `/agent-skill` |

## Hechos que se repiten en toda la docs (SSoT)

- Modelo flagship: **Jev**. Versión leída: `jev-1.13.0`. Alias: `jev-latest` (default SDK) y `jev-preview` (hoy apunta al mismo).
- Endpoint: `POST https://api.typesafe.ai/v1/systemone`.
- Tres preguntas: `choice`, `score`, `noul`.
- Input: `state` + `model` + `questions`. Output: `answers` + `usage`.
- Preguntas de un mismo request: mismo state, independientes, en paralelo.
- Jev no genera texto, código ni explicaciones.
- Input actual: solo texto (string / objeto JSON / array de texto). Sin imagen, audio ni video.
- Playground: `https://console.typesafe.ai/playground`. Keys: `https://console.typesafe.ai/settings/keys`.
