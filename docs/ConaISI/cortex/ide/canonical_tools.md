# cortex/ide/canonical_tools.py

## Qué tiene adentro

- **Ruta de código:** `cortex/ide/canonical_tools.py` (325 líneas).
- **Módulo Python:** `cortex.ide.canonical_tools`.
- **Docstring del módulo:** cortex.ide.canonical_tools -------------------------- Vocabulario canonico de tools de Cortex y matriz de traduccion por IDE.
- **Clases definidas:**
  - `UnknownCanonicalToolError` (KeyError)
    - Raised cuando se pide traducir un tool canonico que no existe.
  - `UnvalidatedIDEError` (KeyError)
    - Raised cuando se pide traducir para un IDE no validado en este plan.
- **Funciones de módulo:**
  - `translate(canonical, ide)` — Traducir un tool canonico al nombre que el IDE espera.
  - `translate_list(canonical_tools, ide)` — Traducir una lista de tools canonicos al formato del IDE.
  - `get_validated_ides()` — Devuelve la lista de IDEs validados contra docs oficiales 2026.
  - `get_canonical_tools()` — Devuelve la lista completa de tools canonicos.
- **Constantes / símbolos de módulo:** `_TOOL_NAME_BY_IDE`

## Para qué sirve

cortex.ide.canonical_tools
--------------------------
Vocabulario canonico de tools de Cortex y matriz de traduccion por IDE.

Los prompts canonicos (renders en ``cortex/setup/cortex_workspace.py`` que
producen ``.cortex/subagents/*.md`` y ``.cortex/skills/*.md``) referencian
tools por su NOMBRE CANONICO de Cortex (ej. ``read_file``, ``cortex_save_session``).

Cada adapter de IDE traduce esos nombres al formato que el IDE entiende
cuando inyecta el frontmatter ``tools:`` del archivo especifico del IDE.

Coherencia con principio rector #1 ("Cortex se comporta igual en todos los IDEs"):
NUNCA se reescribe el cuerpo del prompt. La traduccion solo aplica al
frontmatter ``tools:`` que el adapter inyecta.

Decisiones del creador (firmadas 2026-05-15, `MATRIZ-NATIVA-IDES.md` seccion 4):

- **claude_code**: usa nombres PascalCase nativos (``Read``, ``Write``) +
  prefijo ``mcp__cortex__`` para tools MCP.
- **opencode**: usa nombres lowercase nativos (``read``, ``write``) +
  los tools MCP se descubren dinamicamente (no se declaran en frontmatter).
- **codex**: NO usa frontmatter ``tools:`` — AGENTS.md es markdown plano.
  Este modulo NO traduce para codex (no aplica).
- **pi**: NO se toca el adapter (bundle estatico con contribuciones de
  comunidad). No usa MCP. Este modulo NO traduce para pi.
- **community/experimental** (vscode, cursor, claude_desktop, windsurf,
  antigravity, hermes, zed): NO validados contra docs oficiales 2026 en
  este plan. Quedan fuera de la matriz hasta plan futuro.

Si un adapter community necesita escribir archivos en formato compatible con
claude_code (ej. vscode escribe a ``.claude/agents/``), puede usar
``translate(canonical, "claude_code")`` directamente.

## Relaciones

### Recibe de

- Dependencias externas/stdlib: `__future__`, `typing`

### Envía a

- `cortex.ide.adapters.claude_code`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 325.
Docstrings de símbolos públicos:
- `translate`: Traducir un tool canonico al nombre que el IDE espera.
- `translate_list`: Traducir una lista de tools canonicos al formato del IDE.
- `get_validated_ides`: Devuelve la lista de IDEs validados contra docs oficiales 2026.
- `get_canonical_tools`: Devuelve la lista completa de tools canonicos.

---
Fuente: código de `cortex/ide/canonical_tools.py` (AST + grafo de imports internos). No se usó documentación previa.
