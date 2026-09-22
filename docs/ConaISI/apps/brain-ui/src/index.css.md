# apps/brain-ui/src/index.css

## Qué tiene adentro

Directivas Tailwind (`base/components/utilities`). `html, body, #root { height:100%; margin:0 }`. `body { overflow:hidden }` (WebView Tauri sin scroll de página).

## Para qué sirve

Reset de layout de la ventana desktop.

## Relaciones

### Recibe de

- importado por `main.tsx`

### Envía a

- estilos globales + utilidades Tailwind generadas

### Notas de implementación observadas en el código

El overflow hidden asume que el scroll vive dentro de paneles (Chat), no en body.
