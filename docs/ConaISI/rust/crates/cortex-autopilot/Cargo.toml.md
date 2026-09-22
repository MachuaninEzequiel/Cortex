# rust/crates/cortex-autopilot/Cargo.toml

## Qué tiene adentro

Archivo de 23 líneas.
ADR chico (Cierre T3): solo para el checker de gate — normalizaciones {{TS}}/{{MIN}} y edición del timestamp del fixture A08. `regex 1.x` ya está en Cargo.lock (cortex-app/cortex-mcp) — cero paquetes nuevos.
Manifiesto Cargo. Líneas de deps Cortex observadas:
- `cortex-app = { path = "../cortex-app" }`
- `cortex-enterprise = { path = "../cortex-enterprise" }`
- `cortex-workspace = { path = "../cortex-workspace" }`
- `cortex-mcp = { path = "../cortex-mcp" }`
Nombres de package/bin: cortex-autopilot

## Para qué sirve

ADR chico (Cierre T3): solo para el checker de gate — normalizaciones {{TS}}/{{MIN}} y edición del timestamp del fixture A08. `regex 1.x` ya está en Cargo.lock (cortex-app/cortex-mcp) — cero paquetes nuevos.

## Relaciones

### Recibe de

- Sin imports Cortex en el extracto (manifiesto, lock, html, gitignore o JSON).

### Envía a

- Suite de tests / cargo / bundler según el tipo de archivo.
- El crate o app que lo contiene (ver `00-estructura.md`).

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-autopilot/Cargo.toml`. 23 líneas.
