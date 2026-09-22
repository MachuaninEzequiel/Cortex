# rust/crates/cortex-workspace/src/layout.rs

## Qué tiene adentro

- `resolve_lexical`: canonicaliza o absolutiza + normaliza `.`/`..`.
- `find_git_root`: camina hacia arriba buscando `.git/` directorio.
- `WorkspaceLayout { repo_root, workspace_root, is_legacy_layout, is_new_layout }`.
- `discover(start)` con precedencia de 4 casos.
- Constructores `from_repo_root` (nuevo) y `from_legacy_root`.
- Getters de rutas: config, org.yaml, vault, vault-enterprise, memoria episódica, skills, sessions, subagents, AGENT.md, system-prompt, workspace.yaml, webgraph, logs, scripts, workflows GitHub, promotion records, CONTEXT.md, índice del vault, `.gitignore`.
- `resolve_workspace_relative`, getters legacy y `repr()` espejo de Python.

## Para qué sirve

Fuente única de verdad de **dónde** viven los artefactos de Cortex según layout nuevo o legacy.

## Relaciones

### Recibe de

- Disco: `.cortex/workspace.yaml` (`layout_version`), `.cortex/config.yaml`, `config.yaml` raíz, `.git/`.
- `start: &Path` (cwd o `--project-root`).

### Envía a

- CLI (`paths` + todos los comandos), MCP (`backends::repo_root`/`vault_path`), git_policy, runtime_context (indirecto), skills (vía `skills_dir()` del layout en consumidores).

### Notas de implementación observadas en el código

Los directorios llamados `.cortex` se saltan al walk-up (no son raíces). YAML inválido en `workspace.yaml` cae al siguiente caso. `find_git_root` exige `.git` **directorio** (`is_dir()`).
