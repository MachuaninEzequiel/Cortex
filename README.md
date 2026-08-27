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
| **TUI** | A ratatui terminal interface: splash, home and the sessions screen. |
| **MCP server** | `cortex mcp-serve` exposes 30+ canonical tools to any MCP client. |
| **IDE integration** | 11 validated adapters install hooks, prompts and skills into your editor/agent. |
| **Brain** | The local AI assistant (read-only by design). |

### The TUI

![Splash](assets/shots/splash-full.png)

![Home](assets/shots/home-es.png)

![Sessions](assets/shots/sessions-real.png)

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

## Parts

| Part | Role |
|---|---|
| `rust/crates/cortex-app` | Core services: sessions, documenter, retrieval, quality gates. |
| `rust/crates/cortex-cli` | The native CLI — text and `--json` output for every command. |
| `rust/crates/cortex-tui` | ratatui screens (splash, home, sessions). |
| `rust/crates/cortex-mcp` | The MCP server with canonical tool payloads. |
| `rust/crates/cortex-actions` | The Action Engine (scheduler, registry, learning, signals). |
| `rust/crates/cortex-setup` | Bootstrap, templates, IDE adapters and hooks. |
| `rust/crates/cortex-brain` | The local AI assistant (llama.cpp, optional feature). |
| `rust/crates/cortex-app` | …and the rest of the workspace: embed, webgraph, pipeline, doctor, tutor, enterprise. |

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