# rust/crates/cortex-brain-app/tests/smoke.rs

## Qué tiene adentro

Smoke test del crate. La verificación real (ventana abre) es manual; este test garantiza que el binario al menos parsea argv sin panic.
Archivo de 28 líneas.
Tests en el mismo archivo: `argv_vacio_resuelve_app`, `argv_con_query_resuelve_query_client`, `argv_con_app_resuelve_app`

## Para qué sirve

Smoke test del crate. La verificación real (ventana abre) es manual; este test garantiza que el binario al menos parsea argv sin panic.

## Relaciones

### Recibe de

- `use cortex_brain_app::Role`
- Contexto de crate `cortex-brain-app`: cortex-brain, cortex-enterprise, cortex-workspace, tauri, apps/brain-ui dist

### Envía a

- Crate `cortex-brain-app` envía hacia: IPC unix socket, eventos Tauri, webview React

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-brain-app/tests/smoke.rs`.
