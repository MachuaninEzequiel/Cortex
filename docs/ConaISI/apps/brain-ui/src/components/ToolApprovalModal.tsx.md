# apps/brain-ui/src/components/ToolApprovalModal.tsx

## Qué tiene adentro

Modal de aprobación: muestra tool/args y equivalente CLI ``cortex ${tool} ${args}``. Escape cancela. Botones confirmar/cancelar i18n.

## Para qué sirve

Confirmar SafeAction / tools pendientes (`pendingToolCall` en App) antes de `execute_cortex_tool`.

## Relaciones

### Recibe de

- `App.tsx` (`isOpen`, `toolCall`, lang)
- `getT(lang).toolModal`

### Envía a

- `onConfirm` / `onCancel` → App

### Notas de implementación observadas en el código

El comando mostrado asume subcomandos CLI separados por espacio, no necesariamente el dotted name de tools del brain (`session.current`).
