# Tesis

Fuentes Cortex: `ConaISI/00-MADRE.md` §1, §8; `contexto/01`, `04`, `06`. Fuentes TypeSafe: `typesafe/02`, `03`, `11`.

## Lo que Cortex ya es

Un sistema de memoria cognitiva híbrida para agentes. Dos stores (episódica + semántica), fusión RRF, ciclo spec → sesión → gates → documenter → promoción, 32 tools MCP, CLI nativo, Brain que **consulta y no muta**.

La frase de `pyproject.toml` y del CLI nativo coinciden: *hybrid cognitive memory for AI agents*. El paper/pitch honesto de MADRE §8: recuerda trabajo y conocimiento, recupera, enseña el grafo, amarra trabajo a sesión, cierra con documenter, se inyecta en 11 IDEs, corre un LLM local que propone comandos.

El Brain Python (DEPRECATED) y el Rust (`cortex-brain`) documentan el mismo invariante: router determinista primero (0 tokens); LLM encima, no en lugar.

Eso **ya es** la arquitectura que TypeSafe llama “AI-powered software”: código dueño del control flow; el modelo solo donde hace falta sentido común sobre texto no estructurado.

## Lo que Cortex todavía no es

Un sistema que **juzgue** texto con incertidumbre honesta.

Hoy, entre “el path contiene `auth`” y “llamá a Claude/llama.cpp”, no hay nada. Los detectores, intents, ADR candidates, quality gates y el ContradictionDetector son lexicon, keywords, placeholders o **NoOp**. El `confidence` de `MemoryEntry` es un enum de tres valores nacido del Verification Gate contra el git diff, no una probabilidad calibrada.

Eso produce un loop:

```
intent lexicon → retrieval sesgado a keywords
  → enricher inyecta 4000 chars mediocres
    → el agente trabaja con contexto sucio
      → checkpoints flojos (gates de TBD/FIXME)
        → documenter no detecta contradicciones
          → vault que se pudre
            → el próximo retrieval empeora
```

El techo del producto no es el store nativo, ni la paridad BM25, ni las 32 tools. Es la calidad del juicio semántico en cada seam.

## Por qué TypeSafe es la capa que cierra el loop

Jev existe para exactamente esos seams:

- Input = state que Cortex **ya tiene** (query, hits, spec, diff, checkpoints, ADRs, org notes).
- Output = números que Cortex **ya ramifica** (`if`, top-N, accept/warn/redelegate, promote/draft, READ vs LLM).
- Latencia ~100–150 ms, questions en paralelo, output gratis, $0.042/MTok input.
- Calibración: un 0.2 ocurre ~20% de las veces (en grupos). El sistema puede decir “no sé” y Cortex ya tiene paths de humano / review / `uncertain`.
- No genera texto → no pelea con Jinja writers, summarizer, ni llama.cpp.
- No elige el siguiente paso → no pelea con SessionService, Autopilot policies, ni “Brain no muta”.

TypeSafe no es un competidor de Cortex. Es el **System One** que Cortex describe en arquitectura y todavía implementa con regex.

## Por qué “exponencial” no es marketing acá

Tres efectos se multiplican, no se suman:

1. **Mejor contexto × cada tool MCP.** `cortex_search` y `cortex_context` son el alimento de todos los agentes. Un rerank calibrado mejora finish, autopilot, brain, promote y al humano en la TUI a la vez.
2. **Incertidumbre honesta × mutaciones.** Finish, promote, autopilot start y quality gates son los únicos momentos en que Cortex escribe conocimiento. Gating por confidence corta basura en el vault. Vault más limpio → retrieval mejor → loop positivo.
3. **Mismo control flow.** No hay que reescribir el producto. Los Protocols ya existen (`ContradictionDetector`, detector protocol, `QueryIntentDetector`, `PromotionRulesEngine`). TypeSafe es un backend de esos Protocols.

El ratio que TypeSafe declara (>100× intelligence-to-speed-and-cost vs reasoning models) se aplica al **volumen** de Cortex: cada search, cada checkpoint, cada finish, cada `cortex next`. Un reasoning model por hit es inviable. Un Noul por hit, 20 en paralelo, 100 ms, es el punto de operación del sistema.

## Lo que esta tesis no afirma

- Que Jev reemplace embeddings, BM25 o RRF.
- Que Jev reemplace el Brain LLM para chat.
- Que Jev escriba ADRs, session notes o handoffs.
- Que haya que borrar Python o romper paridad.
- Números de usuarios, benchmarks de producción de Cortex, ni calidad medida de Jev *sobre el vault de Cortex* — eso es el experimento 1 de `17-orden-de-experimentos.md`.
