# rust/crates/cortex-companion/src/menu.rs

## Qué tiene adentro

Catálogo de capacidades del Companion (G-B2c): las 27 familias reales del CLI agrupadas por dominio — la pieza anti-olvido.  v1 = lista canónica FIJA (NO un shell). Cada entrada es un `CatalogEntry` con la familia, args canónicos de lectura (dry-run donde existe) y su dominio. `command_effect` clasifica la entrada en `Direct` (se ejecuta sin aprobación) o `Guarded` (mutante ⇒ `run_guarded`, B2).  El catálogo se deriva del dispatch real del CLI (`cortex-cli/src/main.rs::dispatch_native`, 27 subárboles: los 26 del doc 14 §0 + `init`).
Archivo de 505 líneas.
Símbolos públicos observados:
- `pub enum Domain`
- `pub struct CatalogEntry`
- `pub enum CommandEffect`
- `pub fn command_effect(e: &CatalogEntry) -> CommandEffect`
- `pub fn command_is_guarded(family: &str, args: &[String]) -> bool`
- `pub fn catalog() -> Vec<CatalogEntry>`
- `pub enum FlatRow`
- `pub fn flat_rows() -> Vec<FlatRow>`
- `pub fn row_at(flat: usize) -> Option<FlatRow>`
- `pub fn entry_for(family: &str, args: &[String]) -> Option<CatalogEntry>`
- `pub struct MenuOutput`
Tests en el mismo archivo: `catalog_has_all_27_families_grouped`, `menu_entry_mutation_requires_approval_flow`, `classification_table_sane`, `entry_for_matches_catalog`

## Para qué sirve

Catálogo de capacidades del Companion (G-B2c): las 27 familias reales del CLI agrupadas por dominio — la pieza anti-olvido.  v1 = lista canónica FIJA (NO un shell). Cada entrada es un `CatalogEntry` con la familia, args canónicos de lectura (dry-run donde existe) y su dominio. `command_effect` clasifica la entrada en `Direct` (se ejecuta sin aprobación) o `Guarded` (mutante ⇒ `run_guarded`, B2).  El catálogo se deriva del dispatch real del CLI (`cortex-cli/src/main.rs::dispatch_native`, 27 subárboles: los 26 del doc 14 §0 + `init`).

## Relaciones

### Recibe de

- Sin `use` de crates Cortex/tauri detectados en el extracto (puede ser manifiesto, JSON, CSS o binario de entrada).
- Contexto de crate `cortex-companion`: cortex-cli, cortex-actions, cortex-app, cortex-config, cortex-workspace, cortex-branding, cortex-brain, herdr CLI

### Envía a

- Crate `cortex-companion` envía hacia: TUI ratatui, action_log.jsonl, panes herdr

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-companion/src/menu.rs`.
