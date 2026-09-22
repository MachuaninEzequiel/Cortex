# apps/brain-ui/src/components/Chat.tsx

## Qué tiene adentro

Layout del hilo: header con nombre/branch/sesión, botón limpiar historial, lista `ChatMessage`, `ChatInput`, auto-scroll.

Props: `project`, `messages`, `onSendMessage`, `onExecuteTool`, `onClearHistory`, `isGenerating`, `lang`.

## Para qué sirve

Superficie de conversación del proyecto seleccionado.

## Relaciones

### Recibe de

- `App.tsx` (estado)
- `ChatMessage`, `ChatInput`, `getT`

### Envía a

- callbacks hacia `App` (send, execute tool, clear)

### Notas de implementación observadas en el código

Nombre de proyecto = último segmento del path.
