# cortex/semantic/markdown_parser.py

## Qué tiene adentro

- **Ruta de código:** `cortex/semantic/markdown_parser.py` (80 líneas).
- **Módulo Python:** `cortex.semantic.markdown_parser`.
- **Docstring del módulo:** cortex.semantic.markdown_parser -------------------------------- Parses individual markdown files into SemanticDocument objects.
- **Clases definidas:**
  - `MarkdownParser`
    - Parses a single markdown file into a SemanticDocument.
    - Métodos públicos/especiales: `parse`
    - Métodos internos: `_split_frontmatter`, `_strip_frontmatter_block`
- **Constantes / símbolos de módulo:** `_FRONTMATTER_RE`, `_WIKI_LINK_RE`, `_HASHTAG_RE`

## Para qué sirve

cortex.semantic.markdown_parser
--------------------------------
Parses individual markdown files into SemanticDocument objects.

Extracts:
- YAML front-matter (title, tags)
- Obsidian-style wiki-links: [[note]]
- Inline #hashtags

## Relaciones

### Recibe de

- `cortex.models` (SemanticDocument)
- Dependencias externas/stdlib: `re`, `yaml`, `__future__`, `pathlib`

### Envía a

- `cortex.semantic`
- `cortex.semantic.vault_reader`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 80.
Docstrings de símbolos públicos:
- `MarkdownParser.parse`: Parse a markdown file.

---
Fuente: código de `cortex/semantic/markdown_parser.py` (AST + grafo de imports internos). No se usó documentación previa.
