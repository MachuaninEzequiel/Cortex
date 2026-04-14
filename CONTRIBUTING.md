# Contributing to Cortex

Thank you for your interest in contributing! This document explains how to get started.

## Development Setup

```bash
git clone https://github.com/yourusername/cortex
cd cortex
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pre-commit install
```

## Running Tests

```bash
pytest                          # run all tests
pytest tests/episodic/          # specific module
pytest -k "test_search"         # by name
pytest --cov=cortex             # with coverage
```

## Code Style

We use **ruff** for linting and formatting:

```bash
ruff check .
ruff format .
```

## Project Structure

| Path | Purpose |
|------|---------|
| `cortex/core.py` | Main `AgentMemory` public API |
| `cortex/episodic/` | Vector DB memory layer |
| `cortex/semantic/` | Markdown vault layer |
| `cortex/retrieval/` | Hybrid search / RRF fusion |
| `cortex/hooks/` | Agent framework integrations |
| `cortex/cli/` | Typer CLI commands |
| `tests/` | Pytest test suite |
| `vault/` | Example markdown notes |

## Submitting a PR

1. Fork the repo and create a feature branch: `git checkout -b feat/my-feature`
2. Make your changes with tests
3. Ensure `pytest` and `ruff check .` pass
4. Open a pull request describing what you changed and why

## Areas for Contribution

- [ ] Qdrant backend for `EpisodicMemoryStore`
- [ ] BM25 + vector hybrid for `VaultReader`
- [ ] Knowledge graph builder (auto-link extraction)
- [ ] CrewAI hook
- [ ] OpenAI Agents SDK hook
- [ ] Web UI for browsing memories
