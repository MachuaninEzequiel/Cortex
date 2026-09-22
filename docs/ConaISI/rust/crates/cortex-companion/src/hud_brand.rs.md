# rust/crates/cortex-companion/src/hud_brand.rs

## Qué tiene adentro

Mosaicos voxel del HUD (doc 17).  Muestreados desde `assets/hud-v1/logo-mark.png` (isotipo) y un wordmark de 26×6 legible a 3 filas de half-block. El papel del PNG no se pinta: `0` = transparente. Distinto de 0 = `0xRRGGBB` bosque/menta (GRID). Las caras superiores del voxel van en menta-pálido / texto, nunca placa.
Archivo de 257 líneas.
Símbolos públicos observados:
- `pub const FOREST: u32 = 0x03522E`
- `pub const FOREST_DEEP: u32 = 0x06331C`
- `pub const MINT: u32 = 0x8FDCB0`
- `pub const MINT_SOFT: u32 = 0xAEE8C6`
- `pub const MINT_PALE: u32 = 0xC8F0DC`
- `pub const TOP: u32 = 0xE4EDE7`
- `pub const MARK_W: usize = 26`
- `pub const MARK_H: usize = 18`
- `pub const WORD_W: usize = 29`
- `pub const WORD_H: usize = 5`
- `pub const CELL_BG: Color = Color::Rgb(0x1E, 0x1E, 0x2E)`
- `pub enum MarkRam`
- `pub fn tone(v: u32, ram: MarkRam) -> u32`
- `pub fn blit(buf: &mut Buffer, area: Rect, data: &[u32], w: usize, h: usize)`
- `pub fn blit_mark(buf: &mut Buffer, area: Rect, ram: MarkRam)`
- `pub fn blit_word(buf: &mut Buffer, area: Rect)`
Tests en el mismo archivo: `dims`, `mark_tiene_tinta`, `sin_neon`, `ram_tones_darken_idle`

## Para qué sirve

Mosaicos voxel del HUD (doc 17).  Muestreados desde `assets/hud-v1/logo-mark.png` (isotipo) y un wordmark de 26×6 legible a 3 filas de half-block. El papel del PNG no se pinta: `0` = transparente. Distinto de 0 = `0xRRGGBB` bosque/menta (GRID). Las caras superiores del voxel van en menta-pálido / texto, nunca placa.

## Relaciones

### Recibe de

- Sin `use` de crates Cortex/tauri detectados en el extracto (puede ser manifiesto, JSON, CSS o binario de entrada).
- Contexto de crate `cortex-companion`: cortex-cli, cortex-actions, cortex-app, cortex-config, cortex-workspace, cortex-branding, cortex-brain, herdr CLI

### Envía a

- Crate `cortex-companion` envía hacia: TUI ratatui, action_log.jsonl, panes herdr

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-companion/src/hud_brand.rs`.
