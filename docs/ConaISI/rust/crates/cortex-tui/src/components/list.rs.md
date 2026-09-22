# rust/crates/cortex-tui/src/components/list.rs

## Qué tiene adentro

Lista seleccionable (spec §13 SelectableList): ventana + barra lateral de selección + conteo de posición. El CALLER estiliza las filas (incluida la seleccionada con `theme.selected()`); este widget solo hace el windowing determinístico y la marca de foco (`▌`, spec §7.4).
Archivo de 128 líneas.
Símbolos públicos observados:
- `pub struct SelectableList<'a>`
Tests en el mismo archivo: `muestra_ventana_y_marca_seleccion`, `ventana_respeta_offset`, `posicion_visible_en_overflow`

## Para qué sirve

Lista seleccionable (spec §13 SelectableList): ventana + barra lateral de selección + conteo de posición. El CALLER estiliza las filas (incluida la seleccionada con `theme.selected()`); este widget solo hace el windowing determinístico y la marca de foco (`▌`, spec §7.4).

## Relaciones

### Recibe de

- `use crate::theme::Theme`
- `use cortex_branding::ansi::ColorMode`
- Contexto de crate `cortex-tui`: cortex-actions, cortex-app, cortex-branding

### Envía a

- Crate `cortex-tui` envía hacia: cortex-cli (TUI)

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-tui/src/components/list.rs`.
