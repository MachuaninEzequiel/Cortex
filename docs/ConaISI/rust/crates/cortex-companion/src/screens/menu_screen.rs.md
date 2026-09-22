# rust/crates/cortex-companion/src/screens/menu_screen.rs

## Qué tiene adentro

Pantalla Menu del Companion (G-B2c): el catálogo anti-olvido.  Render puro sobre `flat_rows()` (menu.rs): secciones por dominio + una fila por capacidad. Click en una entrada la ejecuta (lecturas directas; mutantes piden aprobación en el runtime). El panel de salida muestra el resultado (`--json` para las familias integradas, error P6/P9 honesto con el comando exacto para las que aún no lo están).  Geometría COMPARTIDA con `hit_test` (app.rs): las consts de filas/botón son las mismas por estructura, no pueden divergir.
Archivo de 206 líneas.
Símbolos públicos observados:
- `pub struct MenuAreas`
- `pub fn menu_areas(area: Rect) -> MenuAreas`
- `pub fn render_menu(`
- `pub struct AppRenderInfo`

## Para qué sirve

Pantalla Menu del Companion (G-B2c): el catálogo anti-olvido.  Render puro sobre `flat_rows()` (menu.rs): secciones por dominio + una fila por capacidad. Click en una entrada la ejecuta (lecturas directas; mutantes piden aprobación en el runtime). El panel de salida muestra el resultado (`--json` para las familias integradas, error P6/P9 honesto con el comando exacto para las que aún no lo están).  Geometría COMPARTIDA con `hit_test` (app.rs): las consts de filas/botón son las mismas por estructura, no pueden divergir.

## Relaciones

### Recibe de

- `use crate::app::{`
- `use crate::menu::{flat_rows, FlatRow, MenuOutput}`
- `use crate::widgets::{button, Button}`
- Contexto de crate `cortex-companion`: cortex-cli, cortex-actions, cortex-app, cortex-config, cortex-workspace, cortex-branding, cortex-brain, herdr CLI

### Envía a

- Crate `cortex-companion` envía hacia: TUI ratatui, action_log.jsonl, panes herdr

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-companion/src/screens/menu_screen.rs`.
