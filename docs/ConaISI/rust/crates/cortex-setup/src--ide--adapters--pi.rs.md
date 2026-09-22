# rust/crates/cortex-setup/src/ide/adapters/pi.rs

## Qué tiene adentro

`PiAdapter`. `inject_profiles` copia bundle in-tree `cortex-pi/` **verbatim** al project root (no rehidrata desde `.cortex`; sync canónico desactivado). `inject_mcp` no aplica (Pi usa bash tools). uninstall conservador (solo bloques marcados / archivos 100% Cortex).

## Para qué sirve

IDE Pi.

## Relaciones

### Recibe de

- Bundle `cortex-pi/` del monorepo.

### Envía a

- AGENTS.md/README/justfile/extensions del proyecto.

### Notas de implementación observadas en el código

Marcadores HTML iguales a Codex.
