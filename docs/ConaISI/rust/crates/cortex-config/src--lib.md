# src/lib.rs

## Qué tiene adentro

`#![forbid(unsafe_code)]`. Espejo de bloques Pydantic de `cortex/core.py`.

Enums (serde lowercase): `EmbeddingBackend` {onnx, local, openai, fastembed}, `NamespaceMode` {project, branch, custom}, `LanguageDetection` {off, heuristic}, `LlmProvider` {none, openai, anthropic, ollama}, `DocumenterMode` {auto, interactive}.

Structs con defaults Python:
- `EpisodicConfig`: persist_dir=`memory`, collection=`cortex_episodic`, model=`all-MiniLM-L6-v2`, backend onnx, namespace project, namespace_value `""`.
- `SemanticConfig`: vault_path=`vault`.
- `EmbeddingLanguageConfig` {model, backend Option}.
- `EmbeddingConfig`: model/backend Option, language_detection, `per_language: BTreeMap` (sorted).
- `RetrievalConfig`: top_k∈[1,100] default 5; pesos f64 >0 default 1.0.
- `LlmConfig`, `JiraIntegrationConfig` (email_env `JIRA_EMAIL`, token_env `JIRA_API_TOKEN`), `IntegrationsConfig`, `DocumenterConfig`.
- `CortexConfig` raíz: episodic, semantic, retrieval, llm, integrations, documenter, embedding. Claves desconocidas se ignoran (`#[serde(default)]` + deserialize típico).

Métodos: `embedding.is_configured()`, `migration_warnings()` (texto EXACTO `WARNING_MIGRATION_EMBEDDING` si bloque nuevo y legacy distinto de defaults), `embedding_block_active()`, `resolve_embedder(lang)` (legacy vs bloque nuevo vs `per_language[lang.lower()]`).

`load_and_dump(yaml_str) -> String`: YAML nulo→`{}`; parse ok → JSON pretty con `ok, warnings, config, embedding_block_active, resolved_embedder.{default,es,en,fr}`; parse fail → `{"ok": false}\n` sin detalle.

## Para qué sirve

Paridad byte-a-byte del dump canónico contra el oráculo Python (`bench/parity/config_dump.py`). Resolución de modelo/backend para reindex y runtime.

## Relaciones

### Recibe de

- String YAML (`config.yaml`).
- Orden de campos = orden de declaración (contrato JSON).

### Envía a

- `cortex-app::reindex::resolve_reindex_model` deserializa `CortexConfig` y llama `resolve_embedder(None)`.
- Test `parity_fixtures.rs` compara `load_and_dump` vs goldens.

### Notas de implementación observadas en el código

Cualquier fallo de validación (backend inválido, top_k fuera de rango, peso ≤0) produce `ok: false` sin mensaje. `per_language` BTreeMap fuerza sort por clave.
