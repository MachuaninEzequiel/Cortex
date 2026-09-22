# TypeSafe × Cortex — documento madre

Este árbol **no sale del código de Cortex**. Es un inventario de la documentación pública de TypeSafe AI (leída el 2026-09-17 desde `https://docs.typesafe.ai` y `https://docs.typesafe.ai/llms.txt`) más un diseño de incorporación a Cortex, anclado en el inventario de `ConaISI/` (Python `cortex-memory` 0.7.0 / workspace Rust 0.1.0).

No se modificó ningún archivo bajo `cortex/`, `rust/`, `apps/` ni tests. Solo se escribió documentación aquí.

Fecha: 2026-09-17.
Fuentes TypeSafe: introduction, quickstart, system-one, state, primitives (choice/score/noul/advanced), confidence, how-to-build, patterns, API, models, SDKs, machine-learning-primer, jaggedness jev-1.13, cookbooks, demos, agent-skill, use-case-map.
Fuentes Cortex: `ConaISI/00-MADRE.md` y `ConaISI/contexto/01`–`07`, más fichas de retrieval, enricher, documenter, autopilot, brain, action_engine, enterprise, session.

---

## 1. Qué hay acá

```
ConaISI/TypeSafe/
  00-MADRE.md                         ← este archivo
  typesafe/                           ← el producto TypeSafe, fiel a su docs
    00-indice.md
    01-que-es-y-proposito.md
    02-system-one.md
    03-entrenamiento-rlcd.md
    04-state.md
    05-primitivas.md
    06-choice.md
    07-score.md
    08-noul.md
    09-estructura-avanzada.md
    10-confidence.md
    11-como-construir.md
    12-patrones.md
    13-api-http.md
    14-sdks.md
    15-modelos-precio-limites.md
    16-jaggedness-jev-1.13.md
    17-cookbooks.md
    18-casos-de-uso-y-demos.md
    19-agent-skill.md
  incorporacion-cortex/               ← cómo encaja en Cortex (síntesis)
    00-indice.md
    01-tesis.md
    02-huecos-en-cortex.md
    03-principio-de-encaje.md
    04-lo-que-typesafe-no-debe-hacer.md
    05-retrieval-rerank-intent.md
    06-context-enricher.md
    07-documenter-contradicciones-adr.md
    08-session-quality-gates.md
    09-autopilot.md
    10-brain-mcp-tools.md
    11-enterprise-promotion.md
    12-action-engine.md
    13-escritura-memoria.md
    14-guardrails-ci.md
    15-arquitectura-de-insercion.md
    16-contrato-de-datos.md
    17-orden-de-experimentos.md
    18-metricas-y-eval.md
    19-paridad-python-rust.md
    20-riesgos.md
  implementacion/                     ← cómo se ancla, dual-mode, UX, costo
    00-indice.md
    01-dos-modos.md
    02-arquitectura-modular.md
    03-archivos-a-crear.md
    04-experiencia-de-usuario.md
    05-modelo-de-costo.md
    06-flujos-runtime.md
```

## 2. Cómo leer

1. Si no sabés qué es TypeSafe: `typesafe/01` → `02` → `05` → `10` → `16`.
2. Si ya lo sabés y querés el encaje: `incorporacion-cortex/01` → `02` → `03` → `05` (el experimento que más vale) → `15` → `17`.
3. Si querés implementación práctica (dual-mode, archivos, UX, $): `implementacion/`.
3. Cada ficha de `typesafe/` declara de qué página oficial sale. Si hay tensión entre dos páginas (p. ej. presupuesto de tokens), se citan las dos.
4. Cada ficha de `incorporacion-cortex/` declara qué módulo de Cortex toca (nombre ConaISI) y qué primitiva TypeSafe usa. No prescribe un PR.

## 3. Una frase por lado

**TypeSafe / Jev:** modelo System One. Recibe `state` + preguntas tipadas (Choice, Score, Noul). Devuelve valores, distribuciones de probabilidad y confianza. No genera texto. ~100–150 ms. Entrenado con RLCD (calibración, no preferencia humana).

**Cortex:** memoria cognitiva híbrida para agentes (episódica + semántica + RRF). Código dueño del ciclo spec → sesión → gates → documenter → promoción. Superficies CLI/MCP/TUI/Brain. Los juicios semánticos de hoy son lexicon, regex o fórmula; el LLM solo aparece en summarizer y en el chat del Brain.

**Tesis de este árbol:** Cortex ya es “AI-powered software” en arquitectura. Le falta la capa de juicio calibrado entre regex y LLM. TypeSafe es esa capa. No reemplaza retrieval, vault, sesión ni paridad nativa.

## 4. Invariantes que este inventario no viola

- No se toca código de Cortex.
- TypeSafe no genera notas, handoffs ni respuestas de chat.
- TypeSafe no elige el siguiente paso del agente.
- TypeSafe no hace BM25, cosine, RRF, embeddings, git, YAML ni aritmética.
- Cualquier inserción futura es un Protocol/trait detrás de seams que ConaISI ya documenta (`ContradictionDetector`, detectors, intent, promotion).
