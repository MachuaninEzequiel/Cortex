# rust/crates/cortex-cli/src/commands/org_config.rs

## Qué tiene adentro

Muestra `.cortex/org.yaml` resuelto. Flags `--json`, `--required` (rc 1 si falta).

## Para qué sirve

`cortex org-config`.

## Relaciones

### Recibe de

- `cortex_enterprise::config::{discover, load, dump}`.

### Envía a

- stdout JSON o YAML/texto.

### Notas de implementación observadas en el código

Mensaje `"Enterprise config not found under ..."` si no hay archivo.
