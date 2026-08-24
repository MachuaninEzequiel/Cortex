<div align="center">
  <br />
    <a href="https://github.com/MachuaninEzequiel/Cortex" target="_blank">
      <img src="assets/logo.png" alt="Cortex Logo" width="420">
    </a>
  <br />

  <h1>CORTEX</h1>

  <p>
    <strong>Hybrid cognitive memory, governance and a local AI brain — for your agents and your team.</strong>
  </p>

  <p>
    <a href="README.md">🇬🇧 English</a> · <a href="README.es.md">🇪🇸 Español</a>
  </p>

  <p>
    <a href="https://github.com/MachuaninEzequiel/Cortex"><img src="https://img.shields.io/badge/Python-3.11+-blue.svg" alt="Python 3.11+" /></a>
    <a href="https://github.com/MachuaninEzequiel/Cortex"><img src="https://img.shields.io/badge/Rust-native%20layer%20(opt--in)-orange.svg" alt="Rust native layer" /></a>
    <a href="https://github.com/MachuaninEzequiel/Cortex"><img src="https://img.shields.io/badge/tests-2400%2B%20green-brightgreen.svg" alt="tests" /></a>
    <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License: MIT" /></a>
  </p>
</div>

---

Cortex gives your AI agents **persistent memory** (episodic + semantic), a
**disciplined engineering lifecycle** (specs → verified work → documented
sessions) and — uniquely — a **local assistant with a real LLM** that can
query your project without ever mutating it. Everything runs on your machine:
no API keys required for the core experience.

## 🧠 Meet `cortex-brain`

A native (Rust + llama.cpp) assistant that knows **this** project. It answers
questions, runs read-only tools, and — when it wants to execute something —
it must ask you first:

```text
🧠 cortex-brain — backend: llama.cpp (GGUF)

You: how many notes are in the vault?
🔧 model suggestion [read]: vault.stats
Run 'vault.stats' ? [y/N]: y
Vault: 128 .md notes

You: clean up the temp files
The brain NEVER executes mutations: it proposes the exact command.
  → cortex vault.reindex --dry-run   (review it, then run it yourself)
```

| | |
|---|---|
| **Fully local** | GGUF via llama.cpp (`LFM2.5-1.2B-Instruct`, ~730 MB). No cloud, no keys. |
| **Proposes, never mutates** | Mutations are impossible by design — the tool registry has no destructive tools; actions come back as exact CLI commands for *you* to run. |
| **Deterministic fallback** | Without a model, the router still works (`cortex-brain` with zero tokens). |
| **Bilingual** | UI in English or Spanish (`ui.language`). |
| **Dedicated window** | `cortex-brain --window` opens its own terminal. |

## Why Cortex

- **Session amnesia is expensive.** Agents forget decisions, incidents and
  context between tasks. Cortex persists them as queryable memory.
- **Retrieval quality in Spanish matters.** Per-language embeddings measured
  with our own eval suite: Spanish MRR@10 **0.88 → 0.96** vs an English-only
  default; English stays at **1.0** on our dataset.
- **Trust needs verification.** Work closes through checkpoints and
  executable verification hooks — "done" means *proven*, not *claimed*.
- **Your laptop is enough.** The full CLI runs in ~100 MB of RAM; heavy
  pieces are opt-in and measured (see [Hardware](#hardware-honest-numbers)).

## Installation

Requirements: Python **3.11+** · ~500 MB disk for core · Linux/macOS/Windows.

```bash
# Core (memory, sessions, governance)
pip install -e .

# Recommended extras
pip install -e ".[webgraph]"     # graph visualizer
pip install -e ".[fastembed]"    # multilingual embeddings (Spanish e5-large)

# Optional backends
pip install -e ".[local]"        # sentence-transformers (PyTorch)
pip install -e ".[openai]"       # OpenAI embeddings/LLM
```

Bootstrap a project (creates config, vault, skills, IDE adapters):

```bash
cortex init          # alias of `cortex setup agent` — new-user flow
cortex doctor        # validate prerequisites & governance state
cortex tutor         # offline interactive guide, zero tokens
```

### Enabling the brain 🧠 (optional)

```bash
# Build the Rust workspace with the llama.cpp feature (requires Rust toolchain)
cd rust && cargo build --release -p cortex-brain --features llama

# One-time: place a GGUF model (default path shown by the binary)
mkdir -p ~/.cache/cortex/models
# … drop LFM2.5-1.2B-Instruct-Q4_K_M.gguf there (~730 MB)

./rust/target/release/cortex-brain --model        # chat with the real LLM
./rust/target/release/cortex-brain                # deterministic mode, no model
```

Hardware-wise the brain peaks at **~1.3 GB RAM** — fine on an 8 GB laptop.

## Quickstart — 60 seconds

```bash
cortex init                      # bootstrap this project
cortex start                     # open a working session (spec-driven)
# … do the work with your agent/IDE …
cortex finish                    # verify hooks run, session gets documented
cortex next                      # what should I do next? (suggested actions)
cortex search "auth refactor"    # hybrid search over episodic + semantic memory
cortex context                   # enriched context bundle for the current task
```

## The 8 level-0 commands

| Command | What it does |
|---|---|
| `brain` | Local expert assistant (read-only + safe-actions). |
| `start` | Persist an implementation spec into the vault. |
| `finish` | Close a Session: reconstruct, run verification hooks, persist. |
| `init` | Bootstrap Cortex in a project (new-user flow). |
| `doctor` | Validate runtime prerequisites and governance state. |
| `context` | Get enriched context for current work. |
| `tutor` | Offline interactive guide (zero tokens). |
| `search` | Query both memory layers and print results. |

Under the hood there are 35+ more commands (`reindex`, `embedding-status`,
`session`, `ci`, `ide`, `stats`, `next`…) — discovered progressively via
`tutor` and `doctor`.

## Hybrid memory, bilingual retrieval

Two layers fused with Reciprocal Rank Fusion:

| Layer | Store | Strength |
|---|---|---|
| **Episodic** | ChromaDB (`.memory/chroma`) | events, decisions, entities — *what happened* |
| **Semantic** | Markdown vault (Obsidian-friendly) | curated knowledge — *what we know* |

Embeddings are configured **per language**, selected by frontmatter
(`lang: es`) or heuristic detection:

| Language | Model | Backend | Measured quality |
|---|---|---|---|
| 🇪🇸 ES | `intfloat/multilingual-e5-large` | fastembed (ONNX) | MRR@10 **0.9615** |
| 🇬🇧 EN | `all-MiniLM-L6-v2` | ONNX (chromadb) | MRR@10 **1.0** |

Model migrations are safe: caches fingerprint the active model, and
`cortex reindex --prune-old-caches` rebuilds with backup + rollback.

## IDE & agent integration

```bash
cortex ide list                  # 11 supported IDEs/agents
cortex ide setup --ide claude-code   # or cursor, codex, opencode, pi…
cortex ide status
```

Agents get structured access through the **MCP server** (`cortex mcp-server`):
canonical tools for sessions, specs, notes, design docs and review gates —
with a golden contract test suite pinning the tool surface byte-for-byte.

## Sessions & operating modes

Every unit of work becomes a **Session** with checkpoints. Three modes,
inferred automatically:

| Mode | How checkpoints arrive |
|---|---|
| `managed` | The orchestrator skill verifies each step before moving on. |
| `observed` | Your IDE emits checkpoints via hooks (Claude Code, Cursor, Pi, OpenCode…). |
| `byo` | Bring any workflow; the reconstructor synthesizes from git diff + hooks. |

Quality gates ship built-in: transactional note indexing, two-stage review
(`accept / redelegate / warn`), self-review of drafts, and budget-aware
context injection.

## Performance (measured, not promised)

An opt-in native layer written in Rust — activated per environment with
`CORTEX_NATIVE=1`, bit-for-bit parity verified gate by gate:

| Hot path | Python baseline | Native | Speed-up |
|---|---|---|---|
| Batch cosine scoring | 51.1 ms | 1.85 ms | **27.6×** |
| Vector store cold load (5k) | 31.6 ms | 5.0 ms | **6.4×** |
| Vector ingestion (5k) | 50 s | 13.6 ms | **3684×** |
| BM25 p99 | 10.1 ms | 1.85 ms | **5.5×** (≤2 ms gate met) |
| Webgraph n=1000 | 3.16 s | 345 ms | **9.2×** |
| First query after boot (cold embedder) | 457 ms | 22 ms | **20.8×** |

Full methodology: `bench/results/COMPARE.md` and the ADRs under
`docs/transformacion/`.

## Hardware: honest numbers

Measured peaks on a mid-range laptop (ASUS S5402ZA, 11 GB RAM):

| Operation | Peak RAM |
|---|---|
| `cortex search` (full CLI pipeline) | ~106 MB |
| Semantic embedder (MiniLM batch) | ~465 MB |
| Multilingual e5-large loaded (ES) | ~2.2 GB |
| `cortex-brain --model` (LFM2.5, ctx 4096) | ~1.3 GB |

Rule of thumb: **one resident model at a time**. An 8 GB machine runs
everything comfortably if you don't hold the LLM and the big embedder open
simultaneously. (We quantized MiniLM to int8 to save RAM and the quality gate
rejected it — parity 0.947 < 0.99 — so we didn't ship it.)

## Architecture

```text
┌────────────────────────── Python application layer ──────────────────────┐
│  CLI (Typer, 8 visible cmds)   MCP server   TUI Home   ActionEngine      │
│  Session primitive · quality gates · documenter · hybrid retrieval (RRF) │
└───────┬────────────────────────┬──────────────────────┬─────────────────┘
        │ pyo3 (_native, opt-in) │ subprocess           │ chromadb / vault
┌───────▼──────────┐   ┌─────────▼─────────┐   ┌────────▼─────────┐
│ cortex-core (RS) │   │ cortex-brain (RS) │   │ storage           │
│ scoring·BM25·    │   │ llama.cpp + GGUF  │   │ .memory/chroma    │
│ store·webgraph   │   │ LFM2.5 local LLM  │   │ vault/*.md        │
└──────────────────┘   └───────────────────┘   └───────────────────┘
```

## Configuration reference

Everything lives in `config.yaml` (per project) — validated by Pydantic at
startup:

| Block | Purpose |
|---|---|
| `episodic` | ChromaDB persistence, collection, legacy embedding fields |
| `embedding` | **Per-language models**: `per_language.es/en` + `language_detection: heuristic\|off` |
| `semantic` | Vault path (Obsidian-compatible markdown) |
| `retrieval` | `top_k`, RRF weights per source |
| `llm` / `integrations` | Optional cloud providers |
| `documenter` | `default_mode: auto \| interactive` |
| `ui.language` | `es` \| `en` (TUI + brain chrome) |

## Troubleshooting

- `cortex doctor` — validates everything and tells you the fix command.
- `cortex embedding-status` — which embedder is active per language, cache state.
- Model downloads land in `~/.cache/cortex/fastembed` (persistent, never `/tmp`).
- Running tools/scripts? Override the CLI binary with `CORTEX_BIN=/path/to/cortex`.
- On machines where long HTTP downloads stall: re-running resumes partial
  blobs; nothing is lost mid-model.

## Project status

The 2026-08 Transformation Program is **complete**: pruning & structure (01),
IDE standard (02), Rust native layer (03), bilingual embeddings (04),
UX/ActionEngine/TUI (05), local brain (06) — plus a reality audit with every
finding resolved. Current version: **0.7.0**. See
[`CHANGELOG.md`](CHANGELOG.md) and `docs/transformacion/`.

On the roadmap: GPU path for the last mile of end-to-end latency, native CLI
subcommands (when services migrate in Obra E), and the `pct_motor` usage
window.

## Contributing & license

PRs welcome — please keep commits atomic and the gates green
(`pytest tests/unit tests/integration`, `ruff`, `vulture`,
`cargo clippy && cargo test`).

MIT — see [LICENSE](LICENSE).
