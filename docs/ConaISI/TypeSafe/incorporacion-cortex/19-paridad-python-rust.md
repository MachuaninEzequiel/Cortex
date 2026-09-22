# Paridad Python / Rust

Hechos ConaISI (`contexto/03`): el repo está lleno de `*_parity.rs`, `cli_self_golden`, `mcp_golden_contract`. Se clonan nombres de tools, orden de keys JSON, textos de error Typer-like, números BM25 (substring + idf snapshot), bits de cosine (Neumaier), dump YAML estilo PyYAML.

El CLI nativo **no** lanza Python. `CORTEX_PY=1` avisa y sigue nativo. Brain nativo lanza el **binario CLI** para tools READ, no un import.

## Qué no se puede romper

- 32 tools, nombres, orden de keys (`tools_catalog.rs`).
- Textos de error del CLI.
- Números BM25 y cosine. TypeSafe **no entra** a `cortex-core`.
- Layout `WorkspaceLayout`.
- Golden MCP.

## Qué paridad **no** aplica

Las answers de Jev no son deterministas al bit (son un modelo). No hay que golden-filear `noul == 0.93`. La paridad es:

1. **Mismo request JSON** al API (state + questions ids + criteria) desde Python y desde Rust. Un test de serialización, no de red.
2. **Mismo mapeo** answer → tipo Cortex (tablas de `16-contrato-de-datos.md`).
3. **Mismo fail-open** (429 → lexicon/NoOp).
4. **Mismos thresholds default** (un `questions.yaml`, no dos copias).

Si Python llama `typesafe-sdk` y Rust llama `ureq`, el body HTTP tiene que ser el mismo canónico. Fixture: payload del experimento 1.

## Oráculo

Hoy Python es oráculo de BM25/cosine. Para judgement, el oráculo es **la API TypeSafe**, no Python. Los tests `*_parity.rs` de core no se tocan. Tests nuevos: `judgement_payload_parity`.

## Brain DEPRECATED

`cortex.brain` Python es oráculo del router regex. Si el router pasa a TypeSafe, el oráculo Python o se actualiza al mismo adapter o se deja de usar como paridad de intent. No mantener un regex “oficial” y un Choice “oficial” que divergen. Un solo `JudgementBackend`.

## FFI

`cortex-py` / `cortex_core._native` es batch cosine/store. No pasar Jev por PyO3. Coste FFI + no aplica.

## Feature flags

Rust: feature `judgement` opcional, como `llama` y `onnx`. Compile sin red, sin SDK, sin key. Python: extra opcional `typesafe-sdk` en `pyproject.toml` optional-dependencies, paralelo a `openai` / `webgraph`.

## CI de Cortex

Pipeline stages security/lint/test/documentation. No fallar CI si TypeSafe está down. Tests de judgement: skip sin key (`TYPESAFE_API_KEY`), o usar replay de HTTP. Nunca flaky contra producción TypeSafe en el golden de MCP.
