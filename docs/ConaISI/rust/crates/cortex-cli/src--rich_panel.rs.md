# rust/crates/cortex-cli/src/rich_panel.rs

## Qué tiene adentro

Réplica de `rich.panel.Panel` width=80, box ROUNDED, padding (1,2), sin ANSI. `PANEL_WIDTH=80`. `render(title, content)`. Wrap greedy por palabras, unicode-width.

## Para qué sirve

`cortex hint` byte-parity cuando stdout está pipeado.

## Relaciones

### Recibe de

- `commands::tutor::run_hint` + `cortex_tutor::hint`.

### Envía a

- stdout.

### Notas de implementación observadas en el código

Título centrado en el borde superior con guiones floor izquierda / resto derecha.
