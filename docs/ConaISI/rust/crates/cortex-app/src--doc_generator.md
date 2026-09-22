# src/doc_generator.rs

## Qué tiene adentro

Generador FALLBACK de docs (P12A-4). `GeneratedDoc { doc_type, title, content, vault_subfolder, filename }`. `DocTypeGen`: session, hu, adr, incident, changelog, security.

Templates embebidos (SESSION y otros) con placeholders `{{title}}` etc. Render: replace simple + regex `\{\{[^}]*\}\}` → `"N/A"`. NO es Jinja.

`DocGenerator` usa `now: DateTime<Utc>` explícito para filename y date.

## Para qué sirve

Cuando un PR no trae docs de agente, generar notas mínimas de advertencia.

## Relaciones

### Recibe de

- `PRContext` (vía `PRService`).

### Envía a

- `GeneratedDoc` → `doc_validator` / `write_pr_docs`.

### Notas de implementación observadas en el código

El template session incluye admonition «Fallback Documentation».
