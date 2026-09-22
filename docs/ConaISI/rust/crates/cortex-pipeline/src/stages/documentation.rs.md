# rust/crates/cortex-pipeline/src/stages/documentation.rs

## Qué tiene adentro

Puerto de `stages/documentation.py` — verificación de docs de agente y nota de sesión fallback wireada al persister/reconstructor nativos (P5).  Sustituye el stub contractual (P6/P9) por una implementación real: - paso 1 `_store_pr_with_results` → `cortex_app::pr::PRService::store_pr_context` sobre la memoria episódica nativa (`NativeEpisodicStore` JSONL). - paso 2 `_verify_docs` → `cortex_app::doc_verifier::DocVerifier`. - paso 3 `_index_docs`  → `cortex_app::semantic::SemanticIndex::build` (equiv. nativo de `AgentMemory.sync_vault()` → nº de documentos). - paso 4 `_generate_fallback` → documenter nativo: `reconstruct_gitless`/`reconstruct_git` → `persister::build_create_args` → `cortex_services::note::NoteService::create` (write de la nota).
Archivo de 471 líneas.
Símbolos públicos observados:
- `pub struct DocumentationStage`

## Para qué sirve

Puerto de `stages/documentation.py` — verificación de docs de agente y nota de sesión fallback wireada al persister/reconstructor nativos (P5).  Sustituye el stub contractual (P6/P9) por una implementación real: - paso 1 `_store_pr_with_results` → `cortex_app::pr::PRService::store_pr_context` sobre la memoria episódica nativa (`NativeEpisodicStore` JSONL). - paso 2 `_verify_docs` → `cortex_app::doc_verifier::DocVerifier`. - paso 3 `_index_docs`  → `cortex_app::semantic::SemanticIndex::build` (equiv. nativo de `AgentMemory.sync_vault()` → nº de documentos). - paso 4 `_generate_fallback` → documenter nativo: `reconstruct_gitless`/`reconstruct_git` → `persister::build_create_args` → `cortex_services::note::NoteService::create` (write de la nota).

## Relaciones

### Recibe de

- `use cortex_app::doc_verifier::DocVerifier`
- `use cortex_app::documenter::persister::{self, CreateArgs}`
- `use cortex_app::documenter::spec_loader::load_spec`
- `use cortex_app::documenter::{reconstruct_git, reconstruct_gitless}`
- `use cortex_app::episodic::{AppendParams, MemoryEntry, NativeEpisodicStore}`
- `use cortex_app::pr::{PRContext, PRService}`
- `use cortex_app::session::service::SessionService`
- `use cortex_app::session::VerificationHookResult`
- `use cortex_app::workitems::EpisodicMemoryRequest`
- `use cortex_services::note::{NoteCreate, NoteService}`
- `use cortex_services::{EpisodicPort, EpisodicRequest, SemanticPort}`
- `use crate::domain::context::PipelineContext`
- `use crate::domain::types::{StageResult, StageStatus, StageType}`
- Contexto de crate `cortex-pipeline`: cortex-enterprise, cortex-app, cortex-services, cortex-workspace

### Envía a

- Crate `cortex-pipeline` envía hacia: StageResult/PipelineReport, GitHub Actions YAML

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-pipeline/src/stages/documentation.rs`.
