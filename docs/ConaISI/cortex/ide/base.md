# cortex/ide/base.py

## Qué tiene adentro

- **Ruta de código:** `cortex/ide/base.py` (417 líneas).
- **Módulo Python:** `cortex.ide.base`.
- **Docstring del módulo:** cortex.ide.base --------------- Abstract base class for IDE adapters.
- **Clases definidas:**
  - `IDEAdapter` (ABC)
    - Contract for all IDE adapters.
    - Métodos públicos/especiales: `name`, `display_name`, `get_config_paths`, `inject_profiles`, `inject_mcp`, `detect_installation`, `validate`, `uninstall`, `needs_wsl_shielding`, `inject_all`
    - Métodos internos: `_get_mcp_command`
- **Funciones de módulo:**
  - `_generate_autogen_header(sources, ide_name)` — Generate the autogeneration header for IDE config files.
  - `_is_wsl()` — Detect if we are running under WSL.
  - `_backup_file(file_path)` — Create a timestamped backup of a file before modification.
  - `_deep_merge_dict(base, update)` — Recursively merge two dictionaries.
  - `_append_to_markdown(file_path, content, separator)` — Append content to a markdown file with a separator.
  - `_marker_block_pattern(open_marker, close_marker)` — Compiled regex matching one full marker block (markers included).
  - `has_marker_block(content, open_marker, close_marker)` — True if ``content`` contains at least one Cortex marker block.
  - `extract_marker_blocks(content, open_marker, close_marker)` — Return every Cortex block found in ``content``, markers included.
  - `strip_marker_blocks(content, open_marker, close_marker)` — Remove every Cortex block from ``content``, preserving everything else.
  - `upsert_marker_block(content, block, open_marker, close_marker)` — Insert or replace the Cortex block in ``content`` (codex semantics).
  - `is_cortex_owned_file(content, open_marker, close_marker)` — True if Cortex created this file entirely.
  - `is_content_identical_to_bundle(content, bundle)` — True if ``content`` matches what Cortex would write (``bundle``).
  - `_create_shielded_wrapper(project_root)` — Create a shielded bash wrapper to filter WSL and Python noise.
- **Constantes / símbolos de módulo:** `CORTEX_MARKER_OPEN`, `CORTEX_MARKER_CLOSE`, `_TIMESTAMP_LINE_RE`

## Para qué sirve

cortex.ide.base
---------------
Abstract base class for IDE adapters.

Every IDE adapter must implement this contract to provide
consistent profile injection, MCP configuration, and validation.

## Relaciones

### Recibe de

- Dependencias externas/stdlib: `platform`, `re`, `shutil`, `__future__`, `abc`, `datetime`, `pathlib`, `typing`

### Envía a

- `cortex.cli.ide`
- `cortex.ide.adapters.antigravity`
- `cortex.ide.adapters.claude_code`
- `cortex.ide.adapters.claude_desktop`
- `cortex.ide.adapters.codex`
- `cortex.ide.adapters.cursor`
- `cortex.ide.adapters.hermes`
- `cortex.ide.adapters.opencode`
- `cortex.ide.adapters.pi`
- `cortex.ide.adapters.vscode`
- `cortex.ide.adapters.windsurf`
- `cortex.ide.adapters.zed`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 417.
Docstrings de símbolos públicos:
- `IDEAdapter.name`: Machine-readable identifier (e.g. 'opencode', 'cursor').
- `IDEAdapter.display_name`: Human-readable name (e.g. 'OpenCode', 'Cursor').
- `IDEAdapter.get_config_paths`: Return a dict of config path names to actual Paths.
- `IDEAdapter.inject_profiles`: Inject Cortex agent profiles in the IDE's native format.
- `IDEAdapter.inject_mcp`: Inject MCP server configuration for the IDE.
- `IDEAdapter.detect_installation`: Detect if the IDE is installed on the system.
- `IDEAdapter.validate`: Validate that Cortex is correctly configured in this IDE.
- `IDEAdapter.uninstall`: Remove Cortex configuration from this IDE.
- `IDEAdapter.needs_wsl_shielding`: Whether this adapter requires WSL stderr shielding.
- `IDEAdapter.inject_all`: Convenience: inject both profiles and MCP in one call.
- `has_marker_block`: True if ``content`` contains at least one Cortex marker block.
- `extract_marker_blocks`: Return every Cortex block found in ``content``, markers included.

---
Fuente: código de `cortex/ide/base.py` (AST + grafo de imports internos). No se usó documentación previa.
