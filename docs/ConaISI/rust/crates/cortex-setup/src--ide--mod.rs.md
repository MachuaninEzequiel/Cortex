# rust/crates/cortex-setup/src/ide/mod.rs

## Qué tiene adentro

`IdeCtx { project_root, home, now }`. `skills_dir` / `subagents_dir` siempre `project_root/.cortex/skills|subagents`. Trait `IdeAdapter` (name, display_name, config_paths, inject_profiles, inject_mcp, uninstall default no-op, needs_wsl_shielding). Type `Prompts`.

## Para qué sirve

Contrato de inyección IDE.

## Relaciones

### Recibe de

- CLI ide/setup (home y reloj congelable en tests).

### Envía a

- adapters/*.

### Notas de implementación observadas en el código

En ambos layouts skills efectivas = `repo/.cortex/skills`.
