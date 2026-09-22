# Cortex — documento madre (estado actual, extraído del código)

Este archivo es el índice de `ConaISI/`. Todo lo que afirma sale de código bajo `cortex/`, `apps/` y `rust/`. No se usó documentación previa del repo (`docs/`, README, CHANGELOG, handoffs, prosa de `apps/docs/src/content`) como fuente.

Fecha del inventario: sesión de lectura del árbol actual. Versiones leídas en código: **Python `cortex-memory` 0.7.0** (`cortex/__init__.py`, `pyproject.toml`); **workspace Rust 0.1.0** (`rust/Cargo.toml`); **CLI nativo `cortex-cli` 0.1.0**; **MCP nativo `SERVER_VERSION = "2.2"`**.

---

## 1. Qué es Cortex

Cortex es un **sistema de memoria cognitiva híbrida para agentes de IA**.

Un agente (Claude Code, Cursor, Pi, Codex, un LLM local, un humano en la TUI) no “recuerda” el repo por sí solo. Cortex guarda dos capas y las fusiona al consultar:

1. **Memoria episódica** — lo que pasó: sesiones, bugs, PRs, conversaciones. En Python vive en Chroma (`EpisodicMemoryStore`). En Rust, en el módulo episódico de `cortex-app` (JSONL). Cada ítem es un `MemoryEntry` con tags, files, tipo y `confidence` (verified / asserted / contradicted).
2. **Memoria semántica** — lo que el proyecto *es*: markdown en un vault compatible con Obsidian (wiki-links, tags, frontmatter, tipos spec/adr/hu/session/runbook/…). `VaultReader` / `cortex-app::semantic` indexan y buscan (BM25 substring + embeddings).
3. **Fusión** — Reciprocal Rank Fusion con `k=60`, pesos adaptativos según intent de la query (`HybridSearch` / `cortex-app::context::hybrid`). El resultado se serializa a prompt (`RetrievalResult.to_prompt`).

Alrededor de eso el código monta un **ciclo de trabajo**: spec → sesión (open/checkpoint/close) → implementación con quality gates → documenter al finish → promoción enterprise opcional. Y varias **superficies**: CLI, MCP (32 tools), TUI, Companion/HERDR, Brain local (llama.cpp + Tauri), webgraph HTTP, adapters de IDE, ActionEngine, autopilot, pipeline CI, tutor, doctor.

La frase del `pyproject.toml` («Hybrid cognitive memory system for AI agents — episodic + semantic») coincide con el about del CLI nativo y con la descripción de Starlight en `apps/docs/astro.config.mjs`.

---

## 2. Estado actual: dos stacks, un producto

El repo contiene **el paquete Python original y la migración nativa Rust, ya wireada como CLI 100% nativo**.

| Hecho en el código | Dónde |
|---|---|
| CLI nativo no pasa a Python; `CORTEX_PY=1` solo avisa | `rust/crates/cortex-cli/src/main.rs` |
| `cortex.brain` DEPRECATED; dueño = `cortex-brain` Rust | `cortex/brain/__init__.py` |
| Núcleo vectorial/BM25/webgraph en Rust puro | `cortex-core` (sin PyO3) |
| Fachada PyO3 batch `cortex_core._native` | `cortex-py` |
| MCP nativo rmcp, 32 tools, golden de contrato | `cortex-mcp` |
| Brain + Tauri + UI React | `cortex-brain`, `cortex-brain-app`, `apps/brain-ui` |
| Paquete pip `cortex` → Typer sigue existiendo | `pyproject.toml` `[project.scripts]` |
| Tests pytest cubren el paquete `cortex` | `tool.pytest.ini_options` |

Punto de partida honesto para un paper/pitch: **Cortex ya corre nativo (CLI, MCP, TUI, brain, webgraph, enterprise) con paridad buscada contra el oráculo Python; el paquete 0.7.0 sigue en el árbol como librería, tests y referencia semántica.**

---

## 3. Cómo está armado este inventario

```
ConaISI/
  00-MADRE.md                          ← este archivo
  rust/
    00-estructura.md                   ← árbol + grafo de crates
    Cargo.toml.md
    examples--dbg_ap.rs.md
    crates/<crate>/00-estructura.md
    crates/<crate>/<archivo>.md        ← una ficha por archivo fuente
    crates/_lote1-indice.md            ← core, embed, py, config, app
    crates/_lote2-indice.md            ← cli, mcp, setup, workspace, services
    crates/_lote3-indice.md            ← resto de crates
  cortex/
    00-estructura.md
    _indice.md
    raiz/                              ← core.py, models.py, doctor.py, …
    <subpaquete>/00-estructura.md
    <subpaquete>/<modulo>.md           ← una ficha por .py (262)
  apps/
    00-estructura.md
    _brain-ui-indice.md
    brain-ui/                          ← fichas ts/tsx/css/config
    docs/                              ← config del sitio (no la prosa)
  contexto/
    01-arquitectura-general.md
    02-memoria-hibrida-y-datos.md
    03-python-y-rust.md
    04-superficies.md
    05-relaciones-entre-carpetas.md
    06-sesion-documenter-autopilot.md
    07-enterprise-governance.md
  ciclo-desarrollo/                    ← ciclo molecular, red conceptual y diagramas de arquitectura
    00-indice.md
    01-ciclo-desarrollo-software-molecular.md
    02-red-neuronal-conceptual.md
    03-diagramas-arquitectura-y-secuencia.md
  TypeSafe/                            ← addendum 2026-09-17 (NO sale del código Cortex)
    00-MADRE.md
    typesafe/                          ← docs oficiales de TypeSafe AI / Jev
    incorporacion-cortex/              ← diseño de encaje, sin PR
    implementacion/                    ← especificación e implementación canónica en Rust
```

Cada ficha de archivo tiene: **Qué tiene adentro / Para qué sirve / Recibe de / Envía a / Notas de implementación**.

No se documentó `rust/target/`, `__pycache__`, `node_modules/`, `apps/docs/dist/`, binarios `.so`, GGUF, iconos binarios (solo se mencionan en estructuras).

---

## 4. Índice — `rust/` (versión nativa, 22 crates)

Entrada: [`rust/00-estructura.md`](rust/00-estructura.md)

| Crate | Fichas | Rol |
|---|---|---|
| [cortex-core](rust/crates/cortex-core/00-estructura.md) | scoring, store v3, BM25, webgraph | dominio puro |
| [cortex-embed](rust/crates/cortex-embed/00-estructura.md) | ONNX mean-pool L2 | embeddings |
| [cortex-py](rust/crates/cortex-py/00-estructura.md) | PyO3 `_native` | FFI batch |
| [cortex-config](rust/crates/cortex-config/00-estructura.md) | YAML→JSON canónico | config |
| [cortex-app](rust/crates/cortex-app/00-estructura.md) | semantic, episodic, context, session, documenter, ci, pr | aplicación |
| [cortex-services](rust/crates/cortex-services/00-estructura.md) | SpecService, NoteService, migrate/validate | servicios |
| [cortex-setup](rust/crates/cortex-setup/00-estructura.md) | 11 IDE adapters, hooks, writers, templates | bootstrap |
| [cortex-workspace](rust/crates/cortex-workspace/00-estructura.md) | WorkspaceLayout, handoff, skills | paths |
| [cortex-cli](rust/crates/cortex-cli/00-estructura.md) | binario clap, todos los comandos | CLI |
| [cortex-mcp](rust/crates/cortex-mcp/00-estructura.md) | 32 tools, backends nativos | MCP |
| [cortex-actions](rust/crates/cortex-actions/00-estructura.md) | catálogo + scheduler + runner | next |
| [cortex-tui](rust/crates/cortex-tui/00-estructura.md) | Home/sessions/search | TUI |
| [cortex-branding](rust/crates/cortex-branding/00-estructura.md) | paleta, logo, wordmark | marca |
| [cortex-brain](rust/crates/cortex-brain/00-estructura.md) | router, tools, llama, download | asistente |
| [cortex-brain-app](rust/crates/cortex-brain-app/00-estructura.md) | Tauri, IPC, org_memory, graph | shell desktop |
| [cortex-companion](rust/crates/cortex-companion/00-estructura.md) | HUD, HERDR, approval | companion |
| [cortex-enterprise](rust/crates/cortex-enterprise/00-estructura.md) | org, promote, retrieve | enterprise |
| [cortex-doctor](rust/crates/cortex-doctor/00-estructura.md) | checks | doctor |
| [cortex-autopilot](rust/crates/cortex-autopilot/00-estructura.md) | detectores + lifecycle | autopilot |
| [cortex-pipeline](rust/crates/cortex-pipeline/00-estructura.md) | stages + GitHub runner | CI |
| [cortex-tutor](rust/crates/cortex-tutor/00-estructura.md) | topics + hint | tutor |
| [cortex-webgraph-server](rust/crates/cortex-webgraph-server/00-estructura.md) | axum graph | webgraph |

Grafo de path-deps: ver `rust/00-estructura.md`. El hub de comandos es `cortex-cli`; el hub de dominio es `cortex-app`; el hub de disco es `cortex-workspace`.

Comandos nativos (primer token): doctor, tutor, hint, org-config, promote-knowledge, review-knowledge, memory-report, webgraph, autopilot, search, context, stats, session, next, hu, ide, remember, forget, docs, ci, setup, pr-context, mcp-server, reindex, init, finish, agent-guidelines, install-skills.

---

## 5. Índice — `cortex/` (paquete Python 0.7.0)

Entrada: [`cortex/00-estructura.md`](cortex/00-estructura.md) · índice completo: [`cortex/_indice.md`](cortex/_indice.md)

Subpaquetes (cada uno con `00-estructura.md` + ficha por `.py`):

| Subpaquete | Qué hace en el código |
|---|---|
| `raiz/` (`core.py`, `models.py`, `doctor.py`, `handoff.py`, `runtime_context.py`, `git_policy.py`, `feedback_*`, `memory_decay.py`, `pr_capture.py`, `doc_*`) | Fachada `AgentMemory`, modelos Pydantic, utilidades |
| `episodic/` | Chroma store, embedder, summarizer |
| `semantic/` | vault reader, chunker, parser, vector cache (+ nativo) |
| `retrieval/` | HybridSearch RRF + intent |
| `embedders/` | factory onnx/local/openai/fastembed + language |
| `context_enricher/` | estrategias, budget, presenter, telemetry |
| `services/` | Spec, Note, PR, Session alias |
| `session/` | lifecycle, storage, gates, verification, hooks IDE |
| `documenter/` | reconstrucción, contradicciones, ADR, persistencia |
| `documentation/` | schemas de doc types, writers jinja, migration, validation |
| `cli/` | Typer (script `cortex`) |
| `mcp/` | server 1.x + tools search/sessions/documenter/workspace |
| `setup/` | orchestrator, detector, templates, enterprise wizard |
| `ide/` | mismos adapters que rust-setup |
| `workspace/` | WorkspaceLayout Python |
| `action_engine/` | catálogo/scheduler/runner (espejo de cortex-actions) |
| `autopilot/` | service + detectors + policies |
| `pipeline/` | orchestrator + stages + GitHub runner |
| `enterprise/` | org, governance, promotion, reporting |
| `webgraph/` | Flask + graph builder + static UI |
| `workitems/` | Jira read-only |
| `tui/` | TUI Python |
| `tutor/` | topics + hint |
| `brain/` | **DEPRECATED** |
| `ci/` | validate-pr |
| `security/` | paths |
| `hooks/` | agent_hooks |
| `skills/` | skills embebidas (listadas, no usadas como arquitectura) |

API pública reexportada en `cortex/__init__.py`: `AgentMemory`, `EpisodicMemoryStore`, `VaultReader`, `HybridSearch`, `SpecService`, `NoteService`, `SessionService`, `PRService`, `EmbedderFactory`, `EmbeddingConfig`, pipeline types, modelos `UnifiedHit`/`PRContext`/`GeneratedDoc`/`WorkContext`/`EnrichedItem`/`EnrichedContext`.

Métodos de `AgentMemory` (fachada): `remember`/`store_memory`, `retrieve`, `forget`, `stats`, `create_note`, `sync_vault`, `create_spec_note`, `save_session_note`, open/checkpoint/close/get/list session, tasks, `store_pr_context`/`generate_pr_docs`/`write_pr_docs`/`get_pr_context`, work items, `enrich`.

---

## 6. Índice — `apps/`

Entrada: [`apps/00-estructura.md`](apps/00-estructura.md)

- **brain-ui** — React 18 + Vite 5 + Tailwind 3 + Tauri API 2. Componentes de chat, gobernanza, org memory, webgraph, doctor, aprobación de tools. Puente: `src/hooks/useTauri.ts`. Índice: [`apps/_brain-ui-indice.md`](apps/_brain-ui-indice.md).
- **docs** — Astro 5 Starlight, `site = https://docs.cortex.dev`, i18n es/en, sidebar alineado a CLI nativo y 32 tools MCP. En este inventario solo se leyó el *empaquetado* (`astro.config.mjs`, `package.json`, `content/config.ts`), no la prosa.

---

## 7. Índice — documentos de contexto

Leer en este orden:

1. [Arquitectura general](contexto/01-arquitectura-general.md) — capas, invariantes, qué se persiste
2. [Memoria híbrida y datos](contexto/02-memoria-hibrida-y-datos.md) — RRF, embeddings, enricher, webgraph
3. [Python y Rust](contexto/03-python-y-rust.md) — tabla de porteo, paridad, cómo se elige runtime
4. [Superficies](contexto/04-superficies.md) — CLI, MCP, TUI, companion, brain, IDE, next
5. [Relaciones entre carpetas](contexto/05-relaciones-entre-carpetas.md) — quién habla con quién
6. [Sesión / documenter / autopilot](contexto/06-sesion-documenter-autopilot.md) — ciclo de trabajo
7. [Enterprise](contexto/07-enterprise-governance.md) — org.yaml, promote, doctor

---

## 8. Mapa mental para el congreso (hechos, no claims de marketing)

Lo que el código **hace**:

- Recuerda trabajo (episódica) y conocimiento (vault).
- Recupera con RRF adaptativo e inyecta contexto con presupuesto.
- Enseña el grafo (webgraph) y federación multi-proyecto.
- Amarra el trabajo a una sesión con checkpoints y claims verificables.
- Cierra con documenter (notas + confidence).
- Expone 32 tools MCP para que el agente no reinvente el flujo.
- Se inyecta en 11 IDEs con bloques auto-generados.
- Corre un LLM local (GGUF/llama.cpp) que **consulta** Cortex y **no muta** (propone el comando).
- Capa enterprise: equipos, clasificación, promoción, retención, reportes.
- Doctor y tutor offline (zero tokens).

Lo que el código **no afirma por sí solo** (no inventar en el paper): número de usuarios, benchmarks de producción no medidos aquí, “reemplazo total de Python en todos los tests” — pytest sigue apuntando a `cortex`. La migración nativa está en el workspace y en el dispatch del CLI; la librería Python 0.7.0 no fue borrada.

---

## 9. Dependencias externas relevantes (manifiestos)

Python (`pyproject.toml`): pydantic 2, pyyaml, typer, chromadb, mcp 1.x, jinja2. Opcionales: sentence-transformers, fastembed, openai, anthropic, httpx, flask.

Rust workspace: serde, chrono, minijinja, sha2, rmcp 0.8, tokio, ureq 3. Crates individuales añaden ort/tokenizers (embed), axum (webgraph), clap (cli), ratatui (tui/companion), pyo3/numpy (cortex-py), tauri (brain-app), llama-cpp (feature).

Requires-python: `>=3.11`.

---

## 10. Cómo navegar si se busca una pregunta concreta

| Pregunta | Ir a |
|---|---|
| ¿Qué es Cortex en una página? | este archivo §1–2 |
| ¿Cómo fluyen los datos? | contexto/02 y 05 |
| ¿Qué hace cada crate Rust? | rust/00-estructura.md + 00-estructura del crate |
| ¿Qué hace `core.py`? | cortex/raiz/core.md |
| ¿Cuáles son las 32 tools? | contexto/04 + rust/crates/cortex-mcp/src--tools_catalog.rs.md (o `src/tools_catalog.rs.md`) |
| ¿Cómo busca? | cortex/retrieval/hybrid_search.md + rust cortex-app context/hybrid |
| ¿Cómo es el brain? | rust/crates/cortex-brain/src/lib.rs.md + apps/brain-ui |
| ¿Python vs Rust? | contexto/03 |
| ¿Ciclo spec-sesión-finish? | contexto/06 |
| ¿Enterprise? | contexto/07 |
| ¿Qué es TypeSafe / Jev? | TypeSafe/typesafe/ |
| ¿Cómo encajaría TypeSafe en Cortex? | TypeSafe/incorporacion-cortex/ |

---

## 11. Addendum — TypeSafe (no es inventario de código)

El 2026-09-17 se agregó `ConaISI/TypeSafe/`. **No sale del código de Cortex.** Es documentación extraída de `https://docs.typesafe.ai` más un diseño de incorporación. No se modificó `cortex/`, `rust/` ni `apps/`.

Entrada: [`TypeSafe/00-MADRE.md`](TypeSafe/00-MADRE.md).

Fin del documento madre.
