# src/semantic/parser.rs

## Qué tiene adentro

Puerto de `markdown_parser.py`.

`ParsedDoc { title, content, tags, links }`.

Frontmatter: bloque `^---\s*\n...\n---\s*\n` no-greedy DOTALL anclado al inicio (`frontmatter_span`). YAML → `serde_yaml::Mapping` o vacío.

Título: `fm.title` no vacío, si no `stem.replace('_',' ').title()` con `py_title` (mayúscula tras no-cased).

Tags: frontmatter lista o escalar + hashtags inline `(?<!\w)#([A-Za-z][A-Za-z0-9_-]*)` por escaneo; dedup ordenado.

Wiki-links: regex `\[\[([^\]|#]+)(?:[|#][^\]]*)?\]\]` (captura destino, ignora alias/heading).

`content` = cuerpo sin frontmatter + strip.

## Para qué sirve

Convertir un `.md` crudo en campos de índice.

## Relaciones

### Recibe de

- Texto del archivo y `Path` (stem).

### Envía a

- `SemanticIndex::build` / `index_file`.

### Notas de implementación observadas en el código

Hashtags solo ASCII letter inicial. Frontmatter inválido → mapping vacío, no error.
