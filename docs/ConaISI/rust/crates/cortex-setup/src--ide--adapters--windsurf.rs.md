# rust/crates/cortex-setup/src/ide/adapters/windsurf.rs

## Qué tiene adentro

`WindsurfAdapter`. Community. Inyección de perfiles/MCP según paths Windsurf.

## Para qué sirve

Windsurf IDE.

## Relaciones

### Recibe de

- IdeCtx + base helpers.

### Envía a

- Config Windsurf.

### Notas de implementación observadas en el código

Orden registry: community, después vscode.
