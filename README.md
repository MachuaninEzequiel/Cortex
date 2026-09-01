<div align="center">
  <br />
  <a href="https://github.com/MachuaninEzequiel/Cortex" target="_blank">
    <img src="assets/logo.png" alt="Cortex Logo" width="380" />
  </a>
  <br />

  <h1>CORTEX</h1>

  <p>
    <strong>Hybrid memory, governance and a local AI brain — for your agents and your team.</strong>
  </p>

  <p>
    <a href="README.md">🇬🇧 English</a> · <a href="README.es.md">🇪🇸 Español</a>
  </p>
</div>

---

## What is Cortex

Cortex is a **memory and governance layer for AI agents**. It lives in your
repository and gives every agent you use — Claude Code, Cursor, Codex,
OpenCode, Pi, or any MCP-capable tool — the same persistent context,
disciplined workflow and verifiable closure that a well-run engineering team
has: *specs → verified work → documented sessions*.

Everything runs **on your machine**. The core experience needs no API keys,
no cloud, no telemetry: a native binary (Rust), your vault as markdown, and
— optionally — a local LLM speaking your project's language.

## Why it exists

AI agents are powerful and amnesiac. Each session starts from zero: they
forget decisions, lose context between tasks, and rarely leave behind
verifiable evidence of what was done. The more agents you use, the worse the
fragmentation.

Cortex solves the three failures that make agent work unreliable at scale:

| Failure | What Cortex does |
|---|---|
| **Amnesia** | Sessions persist every decision and outcome as hybrid memory (episodic + semantic), searchable in two languages. |
| **No discipline** | Every unit of work is a spec-driven Session with checkpoints, quality gates and a verifiable close. "Done" means *proven*, not *said*. |
| **No shared context** | The same vault, sessions and rules are read by every agent through the CLI and the MCP server — a single source of truth per project. |

## Life inside Cortex

A Session is the unit of work. It opens from a spec, records checkpoints as
you advance, and closes only when verification passes:

```text
open a session  →  cortex session current / checkpoint / task
do the work     →  your agent, your IDE, your way
close it        →  cortex finish            (verification hooks run)
next?           →  cortex next              (the Action Engine suggests)
```

The **Action Engine** is Cortex's proactive layer: it reads your project
state and suggests the next useful step — validate docs, re-index the vault,
learn a topic — each with a cost, a score and a concrete effect:

![Action Engine](assets/shots/action-engine.png)

## Three operating modes

Every session runs in one of three modes, inferred automatically. They
describe **how checkpoints reach the session**:

| Mode | How progress is recorded |
|---|---|
| **Managed** | An orchestrating skill verifies each step before advancing. |
| **Observed** | Your IDE emits checkpoints through hooks (Claude Code, Cursor, Pi, OpenCode…). |
| **BYO** | Bring your own workflow; the reconstructor synthesizes the session from git diff + checkpoints. |

## Interfaces

Cortex is not a monolithic tool — it's a family of surfaces around one
native core:

| Surface | Format |
|---|---|
| **CLI** | 25+ command families (`session`, `docs`, `ci`, `setup`, `search`, `context`, `next`, `hu`, `pr-context`, `reindex`, `ide`…). Text and `--json`. |
| **TUI** | A ratatui terminal interface: splash, home, sessions, search and the action-approval screen (`cortex`, `cortex session watch`, `cortex next --tui`). |
| **Brain App** | Native standalone desktop app (Tauri 2 + React + Rust) with global quick launcher (`Ctrl+Shift+B`), floating mode, multi-model catalog, and auto tool execution. |
| **MCP server** | `cortex mcp-serve` exposes 30+ canonical tools to any MCP client. |
| **IDE integration** | 11 validated adapters install hooks, prompts and skills into your editor/agent. |

### The Cortex Brain Desktop App

Cortex Brain is a native, standalone desktop application that acts as your local AI coding expert with zero cloud dependency.

![Cortex Brain App](docs/cortex-brain/Captura%20de%20pantalla_20260901_100855.png)

* **🧠 In-Process Local LLM Inference:** Powered by `llama.cpp` and optimized for Liquid AI's **Liquid LFM2.5 1.2B Instruct (Q4_K_M)** (~730 MB), running at lightning-fast sub-second speeds completely offline.
* **📦 Curated Multi-Model Catalog:** Hot-swap between specialized local models with 1 click:
  * *Liquid LFM2.5 1.2B* — Ultra-lightweight hybrid architecture, ideal for low-RAM / CPU machines.
  * *Qwen 2.5 Coder (1.5B / 3B)* — Multilingual coding & refactoring specialist.
  * *DeepSeek R1 Distill 1.5B* — Step-by-step reasoning (*Chain-of-Thought*).
  * *Custom GGUFs* — Paste any HuggingFace `.gguf` URL to download and run locally.
* **🚀 Floating Global Launcher (`Ctrl + Shift + B`):** Summon or hide Cortex Brain instantly from any IDE, editor, or browser. Press `Escape` to dismiss back to your code. Includes an *Always-on-Top* pin mode.
* **⚡ Autonomous Safe Tool Protocol:** Read-only tools (`memory.search`, `vault.stats`, `docs.related`, `git.status`) execute automatically to enrich responses. Mutating actions require explicit user approval via interactive modals.
* **💾 Project History Persistence:** Automatically saves conversation turns in `<project>/.cortex/brain/history.jsonl` per workspace.
* **🍃 Zero Idle RAM Overhead:** Automatically unloads the model from RAM after 90 seconds of inactivity, freeing memory completely until the next query.
* **🖥️ Cross-Platform Native Installers:** Available as `.deb` (Debian/Ubuntu Linux), `.exe` / NSIS setup (Windows), and `.dmg` (macOS Apple Silicon & Intel).

### The TUI

![Splash](assets/shots/splash-full.png)

![Home](assets/shots/home-es.png)

![Sessions](assets/shots/sessions-real.png)

**TUI keymap** (`?` opens the full help, derived from the same map):

| Key | Action |
|---|---|
| `j`/`k`, `↑`/`↓` | navigate / scroll |
| `g`/`G` | top / bottom |
| `Enter` | open: session detail, action review, search hit |
| `a` | actions screen (from home) · approve the auto-ok batch (in actions) |
| `s` | sessions screen |
| `/` | search |
| `y` | mark the selected hit as useful (persisted feedback) |
| `c` | copy the selection (OSC 52: session id or hit path) |
| `b`, `Esc` | back (overlays first, then screen stack) |
| `?` | help |
| `q`, `Ctrl+C` | quit |

### The CLI

```text
cortex session list      sessions on disk, live table
cortex next              Action Engine suggestions
cortex search "auth"     hybrid episodic + semantic retrieval
cortex context           enriched context bundle for the current task
cortex doctor            governance health check
cortex tutor             offline interactive guide
```

### The MCP server

One command exposes Cortex to any MCP-capable agent:

```text
cortex mcp-serve   →  initialize / list_tools / call_tool over stdio
```

Tools are grouped by family: **search** (`cortex_search`, `cortex_search_vector`,
`cortex_context`), **spec & docs** (`cortex_create_spec`, `cortex_write_doc`,
`cortex_emit_proposal`), **sessions** (`cortex_session_open/checkpoint/close`,
`cortex_save_session`, `cortex_finish_session`), **review** (`cortex_self_review_note`,
`cortex_review_checkpoint`, `cortex_verify_session_claims`), **work items**
(`cortex_import_hu`, `cortex_get_hu`) and **autopilot**
(`cortex_autopilot_start/preflight/checkpoint/finish/status`).

## Full tour — 12 prompts para probar Cortex entero

Acabás de incorporar Cortex a tu proyecto. Esta tanda recorre **todas** las
superficies — CLI, TUI, ActionEngine, sesiones, autopilot, docs, MCP — sin
alterar tu proyecto: lo único que escribe son artefactos de prueba **marcados**
y los borra al final (el estado de sesión queda en `.cortex/`, que es el
estado propio de Cortex, no de tu código).

**Requisitos**: `cortex-cli init` ya corrido, el binario en el `PATH` y (si tu
agente vive en pi/Claude Code/Codex con el server `cortex mcp-serve`
configurado) las tools MCP disponibles. Cada prompt da la equivalencia
CLI/MCP: el agente elige la que tenga.

Copia y pegá los prompts **en orden**, uno por turno.

### 1. Diagnóstico — ¿qué está sano?

> Corré `cortex-cli doctor` y `cortex-cli ide status`. Resumime en 5 líneas
> qué está configurado y qué marca como pendiente. No modifiques nada.

**Prueba**: `doctor` (salud del runtime) + `ide status` (11 adaptadores).
**Esperás ver**: `[OK]` en config/vault/layout y la tabla de IDEs con `✗`
hasta inyectar. `episodic_store` en FAIL es normal antes del primer reindex.

### 2. Búsqueda híbrida — la memoria

> Buscá en la memoria de Cortex la palabra "<una palabra de tu dominio>"
> (usá `cortex_search` si tenés MCP, si no `cortex-cli search "<palabra>"
> --top-k 5`). Mostrame los hits con fuente (episodic/semantic), score y
> ruta. No escribas nada.

**Prueba**: retrieval híbrido (BM25 + episódico, o embeddings si el modelo
está). **Esperás ver**: tu vault indexado con `[SEMANTIC]`/`[EPISODIC]` hits.

### 3. Contexto enriquecido

> Armá el contexto enriquecido para la tarea "entender este proyecto"
> (`cortex_context` / `cortex-cli context`). Contame qué fuentes usó y
> mostrame el bundle. No escribas nada.

**Prueba**: `context` (pre-flight de contexto del flujo de trabajo).

### 4. Gobernanza — el ticket

> Hacé el pre-flight de gobernanza con `cortex_sync_ticket` para la tarea
> "tour de prueba de Cortex": user_request "recorrer todas las capacidades
> de Cortex sin modificar el proyecto". Mostrame el contexto del ticket.

**Prueba**: la puerta de gobernanza que desbloquea todo el flujo.

### 5. Spec + apertura de sesión (única escritura real)

> Creá una spec de PRUEBA con `cortex_create_spec` (proposal_mode "skip",
> título "tour-cortex") que documente: qué partes de Cortex vamos a probar
> (CLI, TUI, ActionEngine, sesiones, autopilot, docs, MCP). Si abre una
> sesión automáticamente, usala.

**Prueba**: `SpecService` + `SessionOpener` (spec en `vault/specs/` + sesión
en `.cortex/sessions/`). **Esperás ver**: el path del spec y el
`session_id`.

### 6. Checkpoint — registrar avance

> Registrá un checkpoint manual con `cortex_session_checkpoint` (source
> "manual", note "inicio del tour") resumiendo lo probado hasta acá.
> Verificá el estado con `cortex_session_status`. (CLI equivalente:
> `cortex-cli session checkpoint --source manual --note "inicio del tour"`
> con el `--session-id` que abrió el paso 5.)

**Prueba**: el flujo de checkpoints (claims verificados, artefactos).

### 7. ActionEngine — el motor que propone

> Mostrame qué propone el ActionEngine con `cortex-cli next` (o la tool MCP
> equivalente). **NO ejecutes ninguna acción**: listalas con su score,
> costo, reversibilidad y effect.

**Prueba**: el scheduler (impacto×frescura−costo, máx 5, precondiciones).

### 8. Autopilot — preflight de decisión

> Con `cortex_autopilot_preflight` evaluá la tarea "relevar este proyecto":
> tipo de tarea, confianza y complejidad sugerida. Read-only, no abras
> ninguna sesión nueva.

**Prueba**: los detectores de la capa de decisión autopilot.

### 9. Memoria episódica + feedback

> Guardá un aprendizaje de esta sesión en la memoria episódica con
> `cortex-cli remember "Cortex: <un dato aprendido sobre este proyecto>"
> --type general`. Mostrá la confirmación. El feedback "marcar útil" vive
> en la TUI (paso manual: `/` para buscar y `y` sobre un hit) — si ya lo
> hiciste, confirmalo; desde el chat no existe un comando CLI dedicado
> (persiste `.cortex/feedback.jsonl`).

**Prueba**: escritura de memoria episódica (+ feedback opcional que alimenta
el aprendizaje del motor, ventana 14d).

### 10. Docs — writer real + limpieza

> Escribí una nota de PRUEBA con `cortex_write_doc` (doc_type "adr", title
> "TOUR-PRUEBA", summary "nota del tour de Cortex") mostrando el path
> creado. Después BORRALA (y borrá también `vault/session-notes/` del tour
> si existe). Confirmame que no quedó ningún archivo de prueba.

**Prueba**: el writer de docs en vault (write + overwrite/duplicate) y la
regla de no-dejar basura.

### 11. Cierre de sesión

> Cerrá la sesión del tour con `cortex_finish_session` (si tenés MCP; el
> CLI nativo aún no expone close — si no tenés MCP, avisámelo y la dejamos
> abierta). Verificá con `cortex_session_list` que quedó `closed` y mostrame
> el path de la nota de sesión.

**Prueba**: el cierre (estado final + nota de sesión en `vault/session-notes/`).

### 12. Evidencia final

> Resumí el recorrido: qué partes probamos (doctor, search, context,
> gobernanza, spec/sesión, checkpoints, ActionEngine, autopilot, memoria,
> docs, finish), qué archivos se crearon y cuáles se limpiaron. Corré
> `cortex-cli doctor` una última vez y decime si algo cambió respecto del
> paso 1.

**Prueba**: la trazabilidad del tour + el proyecto intacto.

### Parada manual (opcional) — la TUI

La TUI es interactiva; probala vos en una terminal:

```bash
cortex-cli            # Home TUI (isotipo + panel + atajos a/s//q)
cortex-cli session watch    # sesiones en vivo (Enter abre el detalle)
cortex-cli next --tui       # acciones con revisión previa modular
```

### Resumen de la ruta

| # | Superficie | Lee/escribe | Destruye algo? |
|---|---|---|---|
| 1 | doctor + IDE status | lee | no |
| 2 | search (híbrido) | lee | no |
| 3 | context | lee | no |
| 4 | sync_ticket (gobernanza) | lee | no |
| 5 | spec + sesión | escribe `vault/specs/tour-cortex.md` + session | sí, se borra en 11 |
| 6 | checkpoint | escribe `.cortex/sessions/` (estado de Cortex) | no (estado propio) |
| 7 | ActionEngine (next) | lee | no |
| 8 | autopilot preflight | lee | no |
| 9 | memoria + feedback | escribe `.cortex/feedback.jsonl` / memoria | no (estado de Cortex) |
| 10 | write_doc | escribe nota y LA BORRA | sí, se auto-limpia |
| 11 | finish session | escribe nota de sesión | se borra en 10 si aplica |
| 12 | doctor + resumen | lee | no |

Al terminar, tu proyecto queda con un único artefacto nuevo sí-mismo: la
sesión cerrada en `.cortex/sessions/` (y la nota de cierre, borrable), el
spec de prueba borrado y el vault sin residuos — el estado que Cortex
administra por diseño.

## Parts

| Part | Role |
|---|---|
| `rust/crates/cortex-brain-app` | Native standalone desktop app (Tauri 2 + IPC server) with global quick launcher. |
| `apps/brain-ui` | Cortex Brain frontend (React 18 + Vite + Tailwind + Catppuccin Mocha). |
| `rust/crates/cortex-brain` | Local LLM inference engine (Liquid LFM2.5 GGUF + llama.cpp) & tool execution loop. |
| `rust/crates/cortex-app` | Core services: sessions, documenter, retrieval, quality gates. |
| `rust/crates/cortex-cli` | The native CLI — text and `--json` output for every command. |
| `rust/crates/cortex-tui` | ratatui screens (splash, home, sessions, actions approval). |
| `rust/crates/cortex-mcp` | The MCP server with canonical tool payloads. |
| `rust/crates/cortex-actions` | The Action Engine (scheduler, registry, learning, signals). |
| `rust/crates/cortex-setup` | Bootstrap, templates, IDE adapters and hooks. |
| `rust/crates/cortex-companion` | Real-time companion HUD & visual approval engine. |

## Local AIs

Cortex ships one local assistant and one optional model-backed layer:

- **cortex-brain** — a native (Rust + llama.cpp) assistant that knows *this*
  project. It answers read-only questions and proposes exact commands for
  anything else. Mutations are impossible by design: it proposes, you run.

```text
🧠 cortex-brain — backend: llama.cpp (GGUF)

You: how many notes are in the vault?
🔧 model suggestion [read]: vault.stats
Run 'vault.stats' ? [y/N]: y
Vault: 128 .md notes
```

- Without a model it degrades to a deterministic router (zero tokens).
- Embedders are **per language**: Spanish (`multilingual-e5-large`,
  MRR@10 0.96) and English (`MiniLM-L6-v2`, MRR@10 1.0), chosen by
  frontmatter or heuristic.

## Addons & integrations

Cortex adapts to the stacks you already use:

| Addon | What it installs |
|---|---|
| **11 IDE/agent adapters** | Claude Code, Codex, OpenCode, Pi, Cursor, Windsurf, VS Code, Claude Desktop, Hermes, Antigravity… — each gets validated hooks, prompts and agent skills. |
| **Skills** | Agent skill templates for the orchestrating workflow (the *Managed* mode). |
| **CI plugin** | `cortex ci validate-pr` and review-session commands for PR pipelines. |
| **Pipeline** | A native pipeline with security/lint/test/documentation stages. |

## Language

UI and output are bilingual — Spanish by default, English on demand
(`ui.language` in config, or `LANG=en`). The retrieval quality is measured
per language and deliberately high in both.

## Status

Cortex is **100% native Rust** since the 2026-08 transformation: the CLI no
longer delegates to Python, every command the oracle exposes is wired, and
the Python package survives only as the frozen CI parity oracle. Version:
**0.7.0**.

> Installation and usage guides live outside this README — see
> `docs/` (coming next). Core: `LICENSE` MIT.