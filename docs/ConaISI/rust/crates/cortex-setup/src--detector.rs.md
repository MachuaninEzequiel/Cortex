# rust/crates/cortex-setup/src/detector.rs

## Qué tiene adentro

`StackInfo` (language, package_manager, project_name, frameworks, test/lint/build commands). `CIInfo`, `EnvInfo` (OPENAI/ANTHROPIC/OLLAMA). `Layout { New, Legacy }`. `ProjectContext::detect` / `detect_with`.

## Para qué sirve

Alimentar templates de setup (config.yaml, CI, runbooks).

## Relaciones

### Recibe de

- Archivos del repo (package.json, Cargo.toml, pyproject, etc. vía detect_stack).
- Env vars de API keys.

### Envía a

- `setup_templates::render_*` y `setup_cmd`.

### Notas de implementación observadas en el código

Layout por `.cortex/workspace.yaml` layout_version>=2; discovery completo de workspace vive en cortex-workspace, no aquí.
