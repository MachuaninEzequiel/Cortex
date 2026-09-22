# rust/crates/cortex-setup/src/routing.rs

## Qué tiene adentro

`RouteSpec { subfolder, filename_template, template_name, promotable, enterprise_subfolder }`. Tabla por DocType (sessions, specs, decisions ADR-/DEC-, incidents INC-, etc.). `FilenameCtx`, `resolve_target_path`.

## Para qué sirve

Decidir carpeta y nombre de archivo de una nota.

## Relaciones

### Recibe de

- DocType + ctx (date, slug, numbers, session_id, ...).

### Envía a

- writers `build_note`.

### Notas de implementación observadas en el código

HU no promotable. Design filename `{session_id}.md` en `designs/`. Glossary enterprise_subfolder `"glossary"` sin project_id.
