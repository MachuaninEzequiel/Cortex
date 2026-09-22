# rust/crates/cortex-brain/src/chat.rs

## Qué tiene adentro

- Trait `LlmBackend`: `name`, `generate`, `generate_streaming` (default: una pieza).
- `ScriptedBackend`: cola de respuestas; error ruidoso si se agota. Público para CI sin GGUF.
- `DeterministicBackend`: `route_intent` + slash (`help/quit/doctor/stats/...`) o `dispatch` de tool; si no hay match, razón + `help_text()`.
- Protocolo TOOL:
  - `extraer_tool`: primera línea `TOOL: nombre args`
  - `respuesta_sin_tool`
  - `confirma`: `s|si|sí|y|yes`
  - `procesar_respuesta_modelo`: si tool no está en catálogo no llega a aprobar ni despachar
- Banner: `banner` / `banner_ansi` / `banner_plain` combinando `LogoVariant::Mark` + wordmark de `cortex-branding` (gap 2).
- `help_text()`: i18n + catálogo de tools.

Reexporta `route_intent`, `Intent`, `build_tools`, `dispatch`, `Tier`, `ToolSpec`.

## Para qué sirve

Núcleo del loop de chat independiente de IO: backends, confirmación y render del chrome. El binario, Tauri y Companion reutilizan este contrato.

## Relaciones

### Recibe de

- `router::route_intent`
- `tools::{build_tools, dispatch}`
- `i18n`
- `cortex_branding::{ansi, logo, wordmark, pixels}`

### Envía a

- `tools::dispatch` cuando hay aprobación
- Callers: `main.rs`, `cortex-brain-app::chat`, tests de protocolo

### Notas de implementación observadas en el código

`generate_streaming` usa `&mut dyn FnMut` para que el trait sea dyn-compatible (`Box<dyn LlmBackend>`).
