# rust/crates/cortex-tui/src/keymap.rs

## Qué tiene adentro

Mapa de teclas → acciones semánticas (spec §12): un solo lugar decide qué gesto hace qué, según contexto (overlay abierto, input activo). La ayuda se genera desde acá — nunca se duplica como texto hardcodeado.
Archivo de 298 líneas.
Símbolos públicos observados:
- `pub struct KeyContext`
- `pub fn key_to_action(key: KeyEvent, ctx: KeyContext) -> Option<Action>`
- `pub fn global_hints(lang: &'static str) -> Vec<(&'static str, &'static str)>`
- `pub fn full_help(lang: &'static str) -> Vec<(&'static str, &'static str)>`
Tests en el mismo archivo: `j_k_y_flechas_producen_lo_mismo`, `release_es_ignorado`, `q_no_sale_con_overlay`, `enter_arma_confirmacion_dentro_del_modal`, `en_input_las_letras_escriben`, `ayuda_se_deriva_del_mapa`, `accesos_directos_por_pantalla`

## Para qué sirve

Mapa de teclas → acciones semánticas (spec §12): un solo lugar decide qué gesto hace qué, según contexto (overlay abierto, input activo). La ayuda se genera desde acá — nunca se duplica como texto hardcodeado.

## Relaciones

### Recibe de

- `use crate::app::{Action, Overlay, Screen}`
- Contexto de crate `cortex-tui`: cortex-actions, cortex-app, cortex-branding

### Envía a

- Crate `cortex-tui` envía hacia: cortex-cli (TUI)

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-tui/src/keymap.rs`.
