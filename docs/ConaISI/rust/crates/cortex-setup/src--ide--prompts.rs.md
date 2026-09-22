# rust/crates/cortex-setup/src/ide/prompts.rs

## Qué tiene adentro

`split/strip_markdown_frontmatter`. `get_skill_prompt` (`.cortex/skills/<name>.md` o fallback). `get_subagent_prompt`. `build_all_prompts`: cortex-sync, cortex-SDDwork, cortex-documenter.

## Para qué sirve

SSoT de prompts desde el workspace instalado.

## Relaciones

### Recibe de

- Disco skills/subagents.

### Envía a

- `inject_profiles` de adapters.

### Notas de implementación observadas en el código

Fallback mínimo si falta el archivo (pide `cortex setup agent`).
