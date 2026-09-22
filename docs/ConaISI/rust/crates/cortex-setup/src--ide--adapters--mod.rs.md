# rust/crates/cortex-setup/src/ide/adapters/mod.rs

## Qué tiene adentro

11 `pub mod`. `all_adapters()` en orden Python (target → community → experimental). `mcp_command(ctx)` → JSON command cortex-cli mcp-server --stdio + PYTHONPATH=project_root, PYTHONWARNINGS=ignore.

## Para qué sirve

Registry de adapters.

## Relaciones

### Recibe de

- Cada adapter struct.

### Envía a

- CLI ide/setup.

### Notas de implementación observadas en el código

PYTHONPATH se mantiene por compat legacy aunque el binario es nativo.
