# 🧠 cortex

> **Hybrid cognitive memory for AI agents.**  
> Combines episodic memory (vector DB) and semantic memory (markdown knowledge base) into a unified retrieval layer — so your agents remember *what they did* and *what they know*.

[![PyPI version](https://img.shields.io/pypi/v/cortex-memory.svg)](https://pypi.org/project/cortex-memory/)
[![Python](https://img.shields.io/pypi/pyversions/cortex-memory.svg)](https://pypi.org/project/cortex-memory/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tests](https://github.com/yourusername/cortex/actions/workflows/ci.yml/badge.svg)](https://github.com/yourusername/cortex/actions)
[![Coverage](https://img.shields.io/codecov/c/github/yourusername/cortex)](https://codecov.io/gh/yourusername/cortex)

---

## The Problem

Most AI agents have no persistent memory. They start fresh on every call, re-discovering context that already existed. Some solutions add a vector store, but ignore structured knowledge. Others use a knowledge base, but miss the agent's lived experience.

**Cortex solves this with two complementary memory types** — modelling how human cognition actually works.

---

## Cognitive Model

```
                     LLM Agent
                         │
          ┌──────────────┴──────────────┐
          │                             │
   Episodic Memory               Semantic Memory
   (what the agent did)          (what the agent knows)
          │                             │
    Vector DB (Chroma)           Markdown Vault
    + embeddings                 (Obsidian-compatible)
    + LLM summarizer             + wiki-links [[note]]
          │                             │
          └──────────────┬──────────────┘
                         │
                  Hybrid Retrieval
                (Reciprocal Rank Fusion)
                         │
                  Context → LLM
```

### Episodic Memory
Captures *what the agent did*. Agent actions, bug fixes, tool calls, conversations — all stored as dense vector embeddings, searchable by semantic similarity.

```python
memory.remember(
    "Fixed login refresh token bug. Middleware was not invalidating old token after rotation.",
    memory_type="bugfix",
    tags=["auth", "login"],
    files=["auth.ts"],
)
```

### Semantic Memory
Integrates with your **markdown knowledge base** — Obsidian vaults, project docs, architecture notes. The agent can read, create and edit notes, and follow `[[wiki-links]]`.

```
vault/
  auth.md          ← describes the auth system
  architecture.md  ← system design decisions
  api.md           ← API reference
```

### Hybrid Retrieval
A single query searches both memory types and fuses results using **Reciprocal Rank Fusion (RRF)** — returning a ranked, deduplicated context ready to inject into any LLM prompt.

```python
result = memory.retrieve("login bug")
# → episodic: bug fix from last week
# → semantic: auth.md docs
print(result.to_prompt())  # ready-to-use LLM context string
```

---

## Installation

```bash
pip install cortex-memory
```

With optional backends:

```bash
pip install "cortex-memory[openai]"       # OpenAI embeddings + summarizer
pip install "cortex-memory[anthropic]"    # Anthropic summarizer
pip install "cortex-memory[ollama]"       # local LLM via Ollama
pip install "cortex-memory[all]"          # everything
```

---

## Quick Setup (One Command)

Once you have Cortex installed, set up your entire project with a single command:

```bash
cortex setup
```

This auto-detects your project's stack (language, package manager, frameworks, CI/CD) and automatically:

- **Generates `config.yaml`** with smart defaults for your stack
- **Creates `vault/`** with starter docs (architecture, decisions, runbooks)
- **Initializes `.memory/`** with ChromaDB vector store
- **Adds GitHub Actions workflows** with Cortex integration (if they don't already exist):
  - `ci-pull-request.yml` — PR validation with lint/audit/test gates + Cortex memory
  - `ci-feature.yml` — Feature branch CI
  - `cd-deploy.yml` — Deployment pipeline with Cortex tracking
- **Installs `scripts/devsecdocops.sh`** — orchestration script for the full PR pipeline
- **Runs initial vault sync** and stores a setup memory

Want to preview what would happen without making changes?

```bash
cortex setup --dry-run
```

### What the developer gets

After running `cortex setup`, every PR automatically:

1. **Captures PR context** (title, author, branch, files changed)
2. **Stores CI results** (lint, audit, tests) as searchable episodic memories
3. **Searches for similar past PRs** using hybrid RRF search
4. **Generates documentation** into the markdown vault
5. **Syncs the vault** so all docs are indexed and searchable

No configuration needed — it adapts to your project's stack automatically.

---

## Manual Setup

### 1. Initialize

```bash
cortex init
```

Creates:
```
.memory/       ← ChromaDB vector store
vault/         ← markdown knowledge base
config.yaml    ← configuration
```

### 2. Store memories

```python
from cortex import AgentMemory

memory = AgentMemory()

# Store an episodic memory
memory.remember(
    "Deployed new payment service using BullMQ for async processing.",
    memory_type="deployment",
    tags=["payments", "queue"],
    files=["payment_service.ts"],
)

# Create a semantic note
memory.semantic.create_note(
    title="Payment Architecture",
    content="## Overview\n\nWe use BullMQ for async payment processing...",
    tags=["payments", "architecture"],
)
```

### 3. Retrieve context

```python
result = memory.retrieve("how does payment processing work?")

# Inject into your LLM
prompt = result.to_prompt()
response = llm.ask(prompt + "\n\nUser question: " + user_input)
```

---

## CLI

```bash
# Full project setup with auto-detection (recommended)
cortex setup
cortex setup --dry-run     # Preview without making changes

# Initialize the memory system (manual setup)
cortex init

# Store a memory from the terminal
cortex remember "Fixed OAuth2 callback URL bug" --type bugfix --tag auth --file oauth.py

# Search both memory layers
cortex search "oauth login"

# Sync the markdown vault after external edits
cortex sync-vault

# Print stats
cortex stats

# Delete a specific memory
cortex forget mem_abc123
```

---

## Python API

### `AgentMemory`

The main entry point. Accepts a `config.yaml` path.

```python
from cortex import AgentMemory

memory = AgentMemory(config_path="config.yaml")
```

| Method | Description |
|--------|-------------|
| `memory.remember(content, ...)` | Store an episodic memory |
| `memory.retrieve(query, top_k=5)` | Hybrid search → `RetrievalResult` |
| `memory.sync_vault()` | Re-index the markdown vault |
| `memory.forget(memory_id)` | Delete an episodic memory |
| `memory.stats()` | Stats dict with counts and paths |

### `RetrievalResult`

```python
result = memory.retrieve("auth bug")

result.episodic_hits    # list[EpisodicHit]
result.semantic_hits    # list[SemanticDocument]
result.to_prompt()      # str  ← ready to inject into LLM
```

---

## Agent Integrations

### Generic (any agent)

```python
from cortex import AgentMemory
from cortex.hooks import CortexHook

memory = AgentMemory()
hook = CortexHook(memory)

@hook.capture(memory_type="task", tags=["prod"])
def run_agent(prompt: str) -> str:
    return llm.run(prompt)
```

### LangChain

```python
from cortex.hooks import CortexLangChainCallback

callback = CortexLangChainCallback(memory)

agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    callbacks=[callback],  # ← attach cortex
)
```

### OpenAI Agents SDK / CrewAI / Claude Code

See [`examples/`](examples/) for integration patterns with other frameworks.

---

## Configuration

`config.yaml` controls all cortex behaviour:

```yaml
episodic:
  persist_dir: .memory/chroma          # ChromaDB storage path
  collection_name: cortex_episodic
  embedding_model: all-MiniLM-L6-v2    # local, no API key needed
  embedding_backend: local             # local | openai

semantic:
  vault_path: vault                    # your markdown notes folder

retrieval:
  top_k: 5                             # results per source
  episodic_weight: 1.0                 # RRF weight
  semantic_weight: 1.0                 # RRF weight

llm:
  provider: none                       # none | openai | anthropic | ollama
  model: ""                            # e.g. gpt-4o-mini
```

---

## Embedding Backends

| Backend | Model | Requires |
|---------|-------|---------|
| `local` (default) | `all-MiniLM-L6-v2` | `sentence-transformers` |
| `local` | `all-mpnet-base-v2` | `sentence-transformers` |
| `openai` | `text-embedding-3-small` | `OPENAI_API_KEY` |

---

## Repository Structure

```
cortex/
│
├── cortex/                     ← Python package
│   ├── core.py                 ← AgentMemory (main public API)
│   ├── models.py               ← Pydantic data models
│   │
│   ├── episodic/               ← Episodic memory layer
│   │   ├── memory_store.py     ← ChromaDB store + CRUD
│   │   ├── embedder.py         ← local / OpenAI embeddings
│   │   └── summarizer.py       ← LLM memory compression
│   │
│   ├── semantic/               ← Semantic memory layer
│   │   ├── vault_reader.py     ← Vault index + search + write
│   │   └── markdown_parser.py  ← Frontmatter, wiki-links, tags
│   │
│   ├── retrieval/              ← Hybrid retrieval engine
│   │   └── hybrid_search.py    ← RRF fusion
│   │
│   ├── hooks/                  ← Agent framework integrations
│   │   └── agent_hooks.py      ← LangChain, generic decorator
│   │
│   └── cli/                    ← Command-line interface
│       └── main.py             ← Typer CLI commands
│
├── vault/                      ← Example markdown knowledge base
├── tests/                      ← Pytest test suite
├── examples/                   ← Usage examples
├── config.yaml                 ← Default configuration
├── pyproject.toml
└── README.md
```

---

## Roadmap

- [x] ChromaDB episodic memory
- [x] Markdown vault (Obsidian-compatible)
- [x] Reciprocal Rank Fusion retrieval
- [x] LangChain callback hook
- [x] Typer CLI
- [ ] Qdrant backend
- [ ] BM25 hybrid for semantic search
- [ ] Auto knowledge graph (entity extraction + link inference)
- [ ] Web UI for browsing memories
- [ ] CrewAI + OpenAI Agents SDK hooks
- [ ] Memory decay / forgetting strategies
- [ ] Multi-agent shared memory

---

## Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for setup instructions, code style guide and areas where help is needed.

---

## License

MIT © cortex contributors
