# rust/crates/cortex-setup/src/skills_bundle.rs

## Qué tiene adentro

`COMPOSED_FAMILY` (8 skills directorio + INSTALL-COMPOSED.md). `TRIAD_SKILLS` (cortex-sync + crafts, cortex-SDDwork + craft, cortex-documenter + craft). `install_composed_family`, `install_triad_skills`. Marcadores `COMPOSED_MARKER_OPEN/CLOSE` distintos de los canónicos IDE. `agent_skills_block()`.

## Para qué sirve

`cortex setup composed`.

## Relaciones

### Recibe de

- `templates/composed/**` y `cortex/setup/workspace_files/*.md`.

### Envía a

- `.cortex/skills/composed/` y `.cortex/skills/`.
- CLAUDE.md/AGENTS.md vía CLI upsert.

### Notas de implementación observadas en el código

No pisa destinos existentes. Unidades reportadas `(already exists)` si todos los archivos de la unidad ya estaban. R12: marcadores dedicados para no pisar sección Codex.
