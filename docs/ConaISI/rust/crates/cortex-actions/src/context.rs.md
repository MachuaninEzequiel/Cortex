# rust/crates/cortex-actions/src/context.rs

## Qué tiene adentro

Puerto de `cortex/action_engine/context.py` (Obra 05 Fase B).  Regla dura #1 del contrato: toda acción delega en su servicio. El `ActionContext` agrupa las dependencias del catálogo. La carga perezosa de servicios pesados (ChromaDB/ONNX) no existe acá: las ejecuciones que los requieren devuelven fallo explícito hasta su fase nativa (P11/P12); precondiciones y dry-runs —que es lo que gatea la paridad de `next`— son 100% nativos y deterministas.
Archivo de 161 líneas.
Símbolos públicos observados:
- `pub struct ActionContext`
Tests en el mismo archivo: `legacy_fixture_layout`, `new_layout_ws_es_dot_cortex`

## Para qué sirve

Puerto de `cortex/action_engine/context.py` (Obra 05 Fase B).  Regla dura #1 del contrato: toda acción delega en su servicio. El `ActionContext` agrupa las dependencias del catálogo. La carga perezosa de servicios pesados (ChromaDB/ONNX) no existe acá: las ejecuciones que los requieren devuelven fallo explícito hasta su fase nativa (P11/P12); precondiciones y dry-runs —que es lo que gatea la paridad de `next`— son 100% nativos y deterministas.

## Relaciones

### Recibe de

- Sin `use` de crates Cortex/tauri detectados en el extracto (puede ser manifiesto, JSON, CSS o binario de entrada).
- Contexto de crate `cortex-actions`: cortex-app, cortex-enterprise, cortex-setup

### Envía a

- Crate `cortex-actions` envía hacia: cortex-cli next, cortex-companion, cortex-tui, .cortex/action_log.jsonl

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-actions/src/context.rs`.
