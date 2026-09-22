# rust/crates/cortex-cli/src/commands/setup_cmd.rs

## Qué tiene adentro

Perfiles: `agent`, `pipeline`, `full`, `composed`, `webgraph`, `enterprise`. `init` = alias `setup agent` (exige `--non-interactive` o dry-run; nativo no tiene TUI interactivo). `composed` instala familia COMPOSED + tríada y upsert `## Agent skills` en CLAUDE.md/AGENTS.md con marcadores COMPOSED_*. Escribe workspace.yaml, config.yaml, org.yaml, vault seed, memory dir, adapters IDE si `--ide`.

## Para qué sirve

Inicializar un repo Cortex.

## Relaciones

### Recibe de

- `cortex_setup::{detector, setup_templates, skills_bundle, ide}`.

### Envía a

- Árbol `.cortex/` + workflows + skills + markdowns de agente.

### Notas de implementación observadas en el código

Sin `--non-interactive` y sin `--dry-run` → error `"Interactive setup is not available in the native CLI"`.
