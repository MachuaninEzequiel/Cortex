# apps/brain-ui/src/hooks/useTauri.ts

## Qué tiene adentro

- `tauriInvoke<T>(cmd, args?)`: si `isTauri()` llama `invoke` de `@tauri-apps/api/core`; si no, warn + throw
- `tauriListen<T>(event, handler)`: `listen` y extrae `e.payload`; fuera de Tauri no-op unlisten

## Para qué sirve

Única puerta JS→Rust. Permite fallar limpio en preview web/tests.

## Relaciones

### Recibe de

- `@tauri-apps/api/core` y `/event`

### Envía a

- commands/eventos del backend `cortex-brain-app`

### Notas de implementación observadas en el código

No hay mocks de retorno: sin runtime Tauri siempre error.
