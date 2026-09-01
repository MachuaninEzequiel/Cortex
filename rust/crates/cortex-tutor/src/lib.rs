//! Puerto de `cortex.tutor` (P12B-7, porte fiel aprobado — opción A):
//! visor interactivo de documentación con 7 topics estáticos + HintEngine
//! contextual. Render simplificado: el contenido se porta byte-exacto vía
//! `include_str!` desde la captura `export_text()` de rich (divergencia
//! cosmética documentada: sin colores/estilos ANSI).

pub mod engine;
pub mod hint;
pub mod topics;
