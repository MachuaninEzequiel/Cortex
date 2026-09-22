# rust/crates/cortex-pipeline/tests/documentation_stage.rs

## Qué tiene adentro

Archivo de 265 líneas.
Tests de integración del `DocumentationStage` REAL (T4).  Contrato (espejo del oráculo `cortex/pipeline/stages/documentation.py`): - docs de agente presentes → PASSED + `has_agent_docs=true` (+ indexed N). - sin docs → nota de sesión fallback vía persister nativo; PASSED por defecto (`block_on_failure=false`), FAILED si `block_on_failure=true`. - sesión malformada / persister roto → ERROR "Documentation stage error:". - PR context en memoria episódica nativa (paso 1, glue documentado).  TDD: RED contra el stub (status Skipped), GREEN contra la implementación real. Fixtures reales (vault + sesión gitless + spec en disco), nunca mocks ni grep de source.
Tests: `docs_present_passed_con_has_agent_docs`, `no_docs_genera_fallback_passed`, `no_docs_con_block_on_failure_failed`, `sin_pr_ctx_fallback_skipped`, `sesion_malformada_error`, `store_pr_context_escribe_memoria_episodica`

## Para qué sirve

Tests de integración del `DocumentationStage` REAL (T4).  Contrato (espejo del oráculo `cortex/pipeline/stages/documentation.py`): - docs de agente presentes → PASSED + `has_agent_docs=true` (+ indexed N). - sin docs → nota de sesión fallback vía persister nativo; PASSED por defecto (`block_on_failure=false`), FAILED si `block_on_failure=true`. - sesión malformada / persister roto → ERROR "Documentation stage error:". - PR context en memoria episódica nativa (paso 1, glue documentado).  TDD: RED contra el stub (status Skipped), GREEN contra la implementación real. Fixtures reales (vault + sesión gitless + spec en disco), nunca mocks ni grep de source.

## Relaciones

### Recibe de

- `use cortex_app::pr::PRContext`
- `use cortex_app::session::service::SessionService`
- `use cortex_app::session::{`
- `use cortex_pipeline::domain::context::PipelineContext`
- `use cortex_pipeline::domain::types::StageStatus`
- `use cortex_pipeline::orchestrator::PipelineStage`
- `use cortex_pipeline::stages::documentation::DocumentationStage`
- `use cortex_workspace::WorkspaceLayout`

### Envía a

- Suite de tests / cargo / bundler según el tipo de archivo.
- El crate o app que lo contiene (ver `00-estructura.md`).

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-pipeline/tests/documentation_stage.rs`. 265 líneas.
