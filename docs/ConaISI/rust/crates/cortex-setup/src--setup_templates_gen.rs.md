# rust/crates/cortex-setup/src/setup_templates_gen.rs

## Qué tiene adentro

Archivo **GENERADO** por `bench/parity/p8_gen_setup_templates.py`. Constante `DEVSECDOCSOPS_SCRIPT` (bash que llama `cortex pr-context *` y `cortex sync-vault`). Plantillas RENDER* con sentinelas.

## Para qué sirve

SSoT de texto de templates Python sin editar a mano.

## Relaciones

### Recibe de

- AST de `cortex/setup/templates.py` (generador externo).

### Envía a

- setup_templates.rs.

### Notas de implementación observadas en el código

`#![allow(non_upper_case_globals)]` porque nombres vienen de funciones Python.
