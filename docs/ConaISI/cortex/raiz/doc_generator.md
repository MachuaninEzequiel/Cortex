# cortex/doc_generator.py

## Qué tiene adentro

- `DocGenerator`: fallback de documentación cuando un PR **no** trae notas de agente.
- Solo genera tipo `session` → `vault/sessions/` con template `_TEMPLATE_SESSION` (frontmatter + warning callout + summary + diff + pipeline table).
- API: `generate_all(ctx: PRContext)`, `write_docs(docs)`.

## Para qué sirve

Red de seguridad DevSecDocOps: que el día de trabajo no se pierda si el agente no escribió vault.

## Relaciones

### Recibe de

- `PRContext`, `GeneratedDoc` (`cortex.models`).
- Captura típica: `pr_capture`.

### Envía a

- Archivos Markdown en el vault.
- `PRService.generate_pr_docs` / pipeline `DocumentationStage` (según imports de services/pipeline).

---
Fuente: lectura de `cortex/doc_generator.py`. No se usó documentación previa.
