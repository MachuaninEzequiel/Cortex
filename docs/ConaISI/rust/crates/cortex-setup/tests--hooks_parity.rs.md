# rust/crates/cortex-setup/tests/hooks_parity.rs

## Qué tiene adentro

P8e: installer/uninstaller vs goldens hooks/. JSON inválido fuera del gate (mensaje serde ≠ json.JSONDecodeError).

## Para qué sirve

Paridad de session hooks.

## Relaciones

### Recibe de

- HookInstaller + goldens.

### Envía a

- cargo test.

### Notas de implementación observadas en el código

Payload `{{TARGET}}` normalizado.
