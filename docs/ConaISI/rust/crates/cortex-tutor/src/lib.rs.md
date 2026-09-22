# rust/crates/cortex-tutor/src/lib.rs

## Qué tiene adentro

Puerto de `cortex.tutor` (P12B-7, porte fiel aprobado — opción A): visor interactivo de documentación con 7 topics estáticos + HintEngine contextual. Render simplificado: el contenido se porta byte-exacto vía `include_str!` desde la captura `export_text()` de rich (divergencia cosmética documentada: sin colores/estilos ANSI).
Archivo de 9 líneas.
Símbolos públicos observados:
- `pub mod engine`
- `pub mod hint`
- `pub mod topics`

## Para qué sirve

Puerto de `cortex.tutor` (P12B-7, porte fiel aprobado — opción A): visor interactivo de documentación con 7 topics estáticos + HintEngine contextual. Render simplificado: el contenido se porta byte-exacto vía `include_str!` desde la captura `export_text()` de rich (divergencia cosmética documentada: sin colores/estilos ANSI).

## Relaciones

### Recibe de

- Sin `use` de crates Cortex/tauri detectados en el extracto (puede ser manifiesto, JSON, CSS o binario de entrada).
- Contexto de crate `cortex-tutor`: cortex-workspace, content/*.txt

### Envía a

- Crate `cortex-tutor` envía hacia: cortex-cli tutor, cortex-actions learn.topic (tópicos estáticos)

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-tutor/src/lib.rs`.
