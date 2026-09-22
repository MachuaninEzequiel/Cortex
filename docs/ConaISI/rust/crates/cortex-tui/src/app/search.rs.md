# rust/crates/cortex-tui/src/app/search.rs

## Qué tiene adentro

Búsqueda de la TUI (spec §12/§11): la pantalla orquesta el MISMO motor que `cortex search` (NativeMemory, en cortex-cli) a través de un trait — la TUI no depende de embeddings ni duplica lógica de retrieval.  El CLI inyecta el provider en `UiRequest::search` (adapter lazy: los modelos se cargan recién en la primera búsqueda, nunca en el arranque del Home). El feedback explícito ("marcar útil") espera el port nativo del FeedbackCollector — anotado.
Archivo de 42 líneas.
Símbolos públicos observados:
- `pub struct SearchHit`
- `pub struct SearchData`
- `pub trait SearchProvider: Send + Sync`

## Para qué sirve

Búsqueda de la TUI (spec §12/§11): la pantalla orquesta el MISMO motor que `cortex search` (NativeMemory, en cortex-cli) a través de un trait — la TUI no depende de embeddings ni duplica lógica de retrieval.  El CLI inyecta el provider en `UiRequest::search` (adapter lazy: los modelos se cargan recién en la primera búsqueda, nunca en el arranque del Home). El feedback explícito ("marcar útil") espera el port nativo del FeedbackCollector — anotado.

## Relaciones

### Recibe de

- Sin `use` de crates Cortex/tauri detectados en el extracto (puede ser manifiesto, JSON, CSS o binario de entrada).
- Contexto de crate `cortex-tui`: cortex-actions, cortex-app, cortex-branding

### Envía a

- Crate `cortex-tui` envía hacia: cortex-cli (TUI)

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-tui/src/app/search.rs`.
