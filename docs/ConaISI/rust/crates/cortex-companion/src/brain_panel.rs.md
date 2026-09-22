# rust/crates/cortex-companion/src/brain_panel.rs

## Qué tiene adentro

Panel Brain híbrido in-process (no subprocess):

- `BrainMode::{Deterministic, Llm}`
- `BrainMsg::{User, Brain, Proposal{command, audit_key}}`
- `BrainPanel { messages, mode, input, outcome }`
- `tokenize` (comillas simples/dobles)
- `route_brain_tool(name, args, be)`: mapa 1:1 a `Backend` (search, doctor, stats, session, actions.propose). Tool sin mapping → error explícito. `webgraph.serve` → Err con comando exacto (no replica spawn)
- `run_turn`: router/`LlmBackend` + `extraer_tool`; Read se ejecuta; mutaciones → `Proposal` para `run_guarded`
- `/quit` no cierra el Companion (pista de `q`/Ctrl+C)

## Para qué sirve

Mismo catálogo/router del crate `cortex-brain` pero despachando al engine del Companion.

## Relaciones

### Recibe de

- `cortex_brain::{chat, i18n, router, tools}`
- `crate::engine::Backend`, `crate::menu` (`command_is_guarded`)

### Envía a

- `screens/brain_screen.rs` (render)
- `approval::run_guarded` vía propuestas

### Notas de implementación observadas en el código

El binario `cortex-brain` standalone sigue usando subprocess CLI; este módulo es el equivalente in-process.
