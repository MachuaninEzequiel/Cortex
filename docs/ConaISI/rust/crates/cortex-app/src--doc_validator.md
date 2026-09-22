# src/doc_validator.rs

## Qué tiene adentro

`DocValidationIssue`, `Severity`, `DocValidationResult`, `DocValidator`.

Checks: frontmatter YAML `---`, title, date/created, wikilinks `[[nota]]`, embeds `![[nota]]` rotos.

El mensaje de YAML inválido incluye texto de serde_yaml (≠ PyYAML) ⇒ los gates lo normalizan a `{{YAML_ERR}}`.

## Para qué sirve

Validar docs generadas/escritas antes de persistirlas.

## Relaciones

### Recibe de

- Contenido markdown / `GeneratedDoc`.

### Envía a

- `PRService` / example `p12a4_check`.

### Notas de implementación observadas en el código

El detalle del parser YAML no es contrato.
