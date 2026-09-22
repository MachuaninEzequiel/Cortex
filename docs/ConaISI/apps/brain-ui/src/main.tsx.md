# apps/brain-ui/src/main.tsx

## Qué tiene adentro

Bootstrap React: monta `App` en `#root` con `StrictMode`.

Si `isTauri()`, parchea `console.log/warn/error` y listeners `error`/`unhandledrejection` para `invoke("log_to_terminal")`.

`RootErrorBoundary`: muestra stack y botón reintentar; crash → `REACT_CRASH` al terminal Rust.

## Para qué sirve

Entrada del bundle Vite y puente de logs JS→stderr de la app nativa.

## Relaciones

### Recibe de

- `App`, `index.css`, `@tauri-apps/api/core`

### Envía a

- DOM `#root`; command `log_to_terminal`

### Notas de implementación observadas en el código

Sin `#root` lanza Error. Colores del fallback de crash coinciden con mocha (`#181825`, `#f38ba8`).
