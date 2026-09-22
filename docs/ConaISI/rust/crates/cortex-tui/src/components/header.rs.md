# rust/crates/cortex-tui/src/components/header.rs

## Qué tiene adentro

Cabecera de pantallas operativas (spec §10 Header): marca mínima + nombre de vista + estado global a la derecha. Máximo dos filas.  El isotipo gráfico (Mark, 5 filas) solo se dibuja cuando el área lo permite (spec §8: Compact/Mark según modo; bajo el ancho mínimo se muestra "CORTEX" como texto). En headers de una línea la marca es SIEMPRE texto: el logo no roba espacio operativo.
Archivo de 171 líneas.
Símbolos públicos observados:
- `pub struct AppHeader<'a>`
Tests en el mismo archivo: `header_angosto_usa_texto_cortex`, `header_con_altura_usa_isotipo_mark`, `header_angosto_sin_altura_no_roba_espacio`

## Para qué sirve

Cabecera de pantallas operativas (spec §10 Header): marca mínima + nombre de vista + estado global a la derecha. Máximo dos filas.  El isotipo gráfico (Mark, 5 filas) solo se dibuja cuando el área lo permite (spec §8: Compact/Mark según modo; bajo el ancho mínimo se muestra "CORTEX" como texto). En headers de una línea la marca es SIEMPRE texto: el logo no roba espacio operativo.

## Relaciones

### Recibe de

- `use crate::layout::{logo_for, LayoutMode}`
- `use crate::renderer::CortexLogo`
- `use crate::theme::{self, StatusKind, Theme}`
- `use cortex_branding::logo::LogoVariant`
- Contexto de crate `cortex-tui`: cortex-actions, cortex-app, cortex-branding

### Envía a

- Crate `cortex-tui` envía hacia: cortex-cli (TUI)

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-tui/src/components/header.rs`.
