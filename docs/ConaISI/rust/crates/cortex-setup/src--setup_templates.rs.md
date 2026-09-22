# rust/crates/cortex-setup/src/setup_templates.rs

## Qué tiene adentro

`fill` sustituye sentinelas U+E000 n U+E001. Renderers: config.yaml, enterprise vault README, CI PR/governance/feature, CD deploy, architecture/decisions/context/runbooks markdown, gitignore snippet, git vault policy, workspace.yaml, org.yaml.

## Para qué sirve

Generar archivos de `cortex setup`.

## Relaciones

### Recibe de

- `setup_templates_gen` constantes + `ProjectContext`.

### Envía a

- `setup_cmd` que escribe `.cortex/` y `.github/workflows`.

### Notas de implementación observadas en el código

Orden de interpolación = orden de evaluación de f-strings Python.
