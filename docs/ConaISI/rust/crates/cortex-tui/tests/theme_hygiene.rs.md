# rust/crates/cortex-tui/tests/theme_hygiene.rs

## Qué tiene adentro

Archivo de 64 líneas.
Higiene del tema (spec §7.2): ningún `Color::Rgb(...)` fuera de `theme.rs` y `renderer.rs`. La paleta de marca vive en `cortex-branding`; acá se exige que las pantallas/componentes usen `Theme` o los widgets, nunca colores crudos.  El test escanea las fuentes del crate (src/), excluyendo theme.rs y renderer.rs (los dos lugares habilitados). Falla con el archivo y la línea del infractor.
Tests: `no_hay_color_rgb_fuera_de_theme_y_renderer`, `theme_expone_tokens_semanticos`

## Para qué sirve

Higiene del tema (spec §7.2): ningún `Color::Rgb(...)` fuera de `theme.rs` y `renderer.rs`. La paleta de marca vive en `cortex-branding`; acá se exige que las pantallas/componentes usen `Theme` o los widgets, nunca colores crudos.  El test escanea las fuentes del crate (src/), excluyendo theme.rs y renderer.rs (los dos lugares habilitados). Falla con el archivo y la línea del infractor.

## Relaciones

### Recibe de

- `use cortex_branding::ansi::ColorMode`

### Envía a

- Suite de tests / cargo / bundler según el tipo de archivo.
- El crate o app que lo contiene (ver `00-estructura.md`).

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-tui/tests/theme_hygiene.rs`. 64 líneas.
