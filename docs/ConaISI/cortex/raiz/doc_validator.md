# cortex/doc_validator.py

## Qué tiene adentro

- `DocValidationIssue`, `DocValidationResult`.
- `DocValidator(vault_path)`: frontmatter YAML (`title` + `tags` o `date`), wikilinks `[[note]]`, embeds `![[note]]` resolubles en el vault.
- Regex: `_FRONTMATTER_RE`, `_EMBED_RE`, `_WIKILINK_RE`.

## Para qué sirve

Validar docs de agente ya escritos (no generarlos).

## Relaciones

### Recibe de

- Markdown en disco + PyYAML.

### Envía a

- `doctor.py`, CLI `validate-docs`.

---
Fuente: lectura de `cortex/doc_validator.py`. No se usó documentación previa.
