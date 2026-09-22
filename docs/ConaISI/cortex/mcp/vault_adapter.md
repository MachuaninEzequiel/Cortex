# cortex/mcp/vault_adapter.py

## Qué tiene adentro

- **Ruta de código:** `cortex/mcp/vault_adapter.py` (29 líneas).
- **Módulo Python:** `cortex.mcp.vault_adapter`.
- **Docstring del módulo:** Adaptador ``VaultLike`` mínimo sobre un path del workspace.
- **Clases definidas:**
  - `PathVault`
    - Implementación mínima de :class:`VaultLike` sobre un directorio.
    - Métodos públicos/especiales: `__init__`, `path`, `index_file`

## Para qué sirve

Adaptador ``VaultLike`` mínimo sobre un path del workspace.

Fuente única del adaptador que antes estaba duplicado inline dentro de
``_write_design_note_text`` y ``_write_doc_text`` (deuda V6 del plan de
transformación, docs/transformacion/01-PODA-Y-LIMPIEZA.md).

Los writers canónicos solo necesitan ``path`` e ``index_file``; la
indexación semántica real la hace el caller vía ``memory.sync_vault()``,
por eso ``index_file`` es un no-op explícito.

## Relaciones

### Recibe de

- Dependencias externas/stdlib: `__future__`, `pathlib`

### Envía a

- `cortex.mcp.tools.workspace`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 29.

---
Fuente: código de `cortex/mcp/vault_adapter.py` (AST + grafo de imports internos). No se usó documentación previa.
