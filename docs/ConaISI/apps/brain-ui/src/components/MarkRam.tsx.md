# apps/brain-ui/src/components/MarkRam.tsx

## Qué tiene adentro

Isotipo voxel del mark con tres estados `MarkRamState`: `idle` (grises mocha, “0 MB RAM”), `weak_awake` (mint pálido, modelo en RAM), `awake` (forest/mint, generando). Tamaños sm/md/lg. Click opcional.

## Para qué sirve

Widget de RAM viva en TopBar/StatusBar (ticker `loaded_projects` / generación).

## Relaciones

### Recibe de

- `MarkRamState` (`types.ts`)
- estado calculado en `App.tsx`

### Envía a

- `onClick` opcional

### Notas de implementación observadas en el código

Colores alineados a `tailwind.config.js` (`cortex.forest/mint`) y a `cortex-companion` hud_brand.
