# rust/crates/cortex-pipeline/Cargo.toml

## Qué tiene adentro

Archivo de 21 líneas.
T4: Documentation real — DocVerifier/Session/documenter (P5/P12A-5) + NoteService (write de la nota de sesión fallback). Ambos ya están en el lock vía cortex-enterprise/cortex-cli ⇒ cero paquetes nuevos.
Manifiesto Cargo. Líneas de deps Cortex observadas:
- `cortex-enterprise = { path = "../cortex-enterprise" }`
- `cortex-app = { path = "../cortex-app" }`
- `cortex-services = { path = "../cortex-services" }`
- `cortex-workspace = { path = "../cortex-workspace" }`
Nombres de package/bin: cortex-pipeline

## Para qué sirve

T4: Documentation real — DocVerifier/Session/documenter (P5/P12A-5) + NoteService (write de la nota de sesión fallback). Ambos ya están en el lock vía cortex-enterprise/cortex-cli ⇒ cero paquetes nuevos.

## Relaciones

### Recibe de

- Sin imports Cortex en el extracto (manifiesto, lock, html, gitignore o JSON).

### Envía a

- Suite de tests / cargo / bundler según el tipo de archivo.
- El crate o app que lo contiene (ver `00-estructura.md`).

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-pipeline/Cargo.toml`. 21 líneas.
