# rust/crates/cortex-branding/src/pixels.rs

## Qué tiene adentro

Representación lógica de píxeles del branding (prompt §8-9).  Separa GEOMETRÍA (máscaras en `logo.rs`) de COLOR (`gradient.rs`): la máscara dice qué clase de píxel hay en cada celda; el gradiente decide el color según posición y clase. El render (`ansi.rs` o el widget de `cortex-tui`) convierte eso a terminal.
Archivo de 246 líneas.
Símbolos públicos observados:
- `pub enum PixelKind`
- `pub struct PixelMap`
Tests en el mismo archivo: `parse_roundtrip`, `shadow_solo_exterior`, `filas_cortas_se_paddean`, `blit_copia_solo_lo_opaco`

## Para qué sirve

Representación lógica de píxeles del branding (prompt §8-9).  Separa GEOMETRÍA (máscaras en `logo.rs`) de COLOR (`gradient.rs`): la máscara dice qué clase de píxel hay en cada celda; el gradiente decide el color según posición y clase. El render (`ansi.rs` o el widget de `cortex-tui`) convierte eso a terminal.

## Relaciones

### Recibe de

- Sin `use` de crates Cortex/tauri detectados en el extracto (puede ser manifiesto, JSON, CSS o binario de entrada).
- Contexto de crate `cortex-branding`: nada de otros crates Cortex

### Envía a

- Crate `cortex-branding` envía hacia: cortex-brain (banner), cortex-tui, cortex-companion

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-branding/src/pixels.rs`.
