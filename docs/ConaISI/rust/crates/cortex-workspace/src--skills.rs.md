# rust/crates/cortex-workspace/src/skills.rs

## Qué tiene adentro

Bundles embebidos con `include_str!` desde `cortex/skills/` del monorepo:

- `obsidian-markdown` (+ CALLOUTS, EMBEDS, PROPERTIES)
- `json-canvas` (+ EXAMPLES)
- `obsidian-bases` (+ FUNCTIONS_REFERENCE)
- `obsidian-cli`
- `defuddle`

`SKILL_NAMES` (ese orden) e `install_skills(target_dir)`: crea destino, salta existentes (`"<name> (already exists)"`), warning stderr si falla un skill y continúa.

## Para qué sirve

Instalar skills Obsidian en `.cortex/skills/` sin dependencias de runtime. Lo usa `cortex install-skills`.

## Relaciones

### Recibe de

- Archivos fuente Python/markdown en `cortex/skills/**` (compile-time).
- `target_dir` (CLI `--dest`, default `.cortex/skills`).

### Envía a

- Disco: árbol de skills.
- `cortex-cli::commands::misc::install_skills`.

### Notas de implementación observadas en el código

Si no se puede crear `target_dir`, warning y `Vec` vacío. Destinos existentes **nunca** se pisan.
