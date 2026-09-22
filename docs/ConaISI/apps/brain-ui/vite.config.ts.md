# apps/brain-ui/vite.config.ts

## Qué tiene adentro

Vite + `@vitejs/plugin-react`. `server.port=1420`, `strictPort: true`, `clearScreen: false`. `envPrefix`: `VITE_`, `TAURI_`. Build `es2022`, minify esbuild, sin sourcemap.

## Para qué sirve

Dev server y bundle que Tauri carga (`frontendDist` = `apps/brain-ui/dist`).

## Relaciones

### Recibe de

- fuentes `src/`

### Envía a

- `dist/` consumido por `cortex-brain-app`

### Notas de implementación observadas en el código

Puerto fijo requerido por Tauri; HMR de red deshabilitado por comentario de seguridad.
