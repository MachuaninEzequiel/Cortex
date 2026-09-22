# rust/crates/cortex-cli/tests/t_lea_b_ide.rs

## Qué tiene adentro

`ide` list/setup/remove/status sobre adapters + HookInstaller. Servicios reales + tmp.

## Para qué sirve

MITAD B IDE.

## Relaciones

### Recibe de

- ide_cmd + cortex-setup.

### Envía a

- cargo test.

### Notas de implementación observadas en el código

TDD: RED cuando run devolvía false.
