# rust/crates/cortex-brain/tests/tool_i18n.rs

## Qué tiene adentro

i18n de las salidas de tools del brain (dispatch/propose/run_cli).  Las tools son la capa que renderiza respuestas al usuario; con `ui.language: en` deben salir en inglés. Los tests tocan el idioma global bajo lock y restauran Es al final.
Archivo de 77 líneas.
Tests en el mismo archivo: `falta_query_en_ingles`, `related_pide_precision_en_ambos_idiomas`, `vault_stats_cuenta_en_idioma_vigente`, `propose_en_no_menciona_comandos_espanoles`

## Para qué sirve

i18n de las salidas de tools del brain (dispatch/propose/run_cli).  Las tools son la capa que renderiza respuestas al usuario; con `ui.language: en` deben salir en inglés. Los tests tocan el idioma global bajo lock y restauran Es al final.

## Relaciones

### Recibe de

- `use cortex_brain::i18n::{self, Lang}`
- `use cortex_brain::tools::dispatch`
- Contexto de crate `cortex-brain`: cortex-branding, ureq, llama-cpp-2 (feature), CLI cortex via Command

### Envía a

- Crate `cortex-brain` envía hacia: stdout, cortex-brain-app, cortex-companion

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-brain/tests/tool_i18n.rs`.
