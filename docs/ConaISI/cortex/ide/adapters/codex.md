# cortex/ide/adapters/codex.py

## Qué tiene adentro

- **Ruta de código:** `cortex/ide/adapters/codex.py` (624 líneas).
- **Módulo Python:** `cortex.ide.adapters.codex`.
- **Docstring del módulo:** cortex.ide.adapters.codex — Codex CLI adapter.
- **Clases definidas:**
  - `CodexAdapter` (IDEAdapter)
    - Adapter for the OpenAI Codex CLI.
    - Métodos públicos/especiales: `name`, `display_name`, `get_config_paths`, `inject_profiles`, `inject_mcp`, `detect_installation`, `uninstall`
    - Métodos internos: `_print_trust_notice`
- **Funciones de módulo:**
  - `_build_cortex_agents_section(autogen_header)` — Build the Cortex block injected into AGENTS.md at the project root.
  - `_replace_or_append_cortex_section(existing, cortex_block)` — Reemplaza el bloque Cortex en ``existing`` o lo appendea al final.
  - `_resolve_cortex_command()` — Ruta absoluta al ejecutable ``cortex``, o el nombre pelado como fallback.
  - `_build_cortex_toml_block(project_root)` — Devuelve el bloque TOML de configuracion del MCP server Cortex.
  - `_replace_or_append_cortex_toml_block(existing, cortex_toml)` — Reemplaza el bloque Cortex en ``existing`` config.toml o lo appendea.
  - `_codex_global_config_path()` — Resuelve el ``config.toml`` GLOBAL de Codex (respeta ``CODEX_HOME``).
  - `_trust_markers(project_root)` — Marcadores BEGIN/END especificos del path para la entrada de trust.
  - `_build_cortex_trust_block(project_root)` — Entrada de trust para el config global, envuelta en marcadores del path.
  - `_global_has_foreign_trust(content, project_root)` — ¿Existe ya un ``[projects."<este path>"]`` FUERA de nuestros marcadores?
  - `_merge_trust_into_global(existing, project_root)` — Merge no-destructivo del trust de ESTE proyecto en el config global.
- **Constantes / símbolos de módulo:** `_CORTEX_AGENTS_MD_MARKER_OPEN`, `_CORTEX_AGENTS_MD_MARKER_CLOSE`, `_CORTEX_TOML_MARKER_OPEN`, `_CORTEX_TOML_MARKER_CLOSE`, `_CORTEX_TRUST_MARKER_OPEN_TPL`, `_CORTEX_TRUST_MARKER_CLOSE_TPL`

## Para qué sirve

cortex.ide.adapters.codex — Codex CLI adapter.

Codex (the OpenAI ``codex`` CLI, https://github.com/openai/codex) is one of
the four IDE targets officially supported by Cortex.

Rediseno completo en Fase 4 del plan multi-IDE & MCP hardening (2026-05-15)
basado en validacion contra documentacion oficial:

- https://developers.openai.com/codex/guides/agents-md
- https://developers.openai.com/codex/mcp

Diferencias clave vs version anterior:

1. **AGENTS.md va al project root**, NO ``.codex/AGENTS.md``. Codex lee
   ``AGENTS.md`` en project root (con merge layered desde ``~/.codex/AGENTS.md``
   global y directorios padre). El path anterior ``.codex/AGENTS.md`` era
   ignorado por Codex.

2. **Codex NO soporta subagents personalizados.** Decision 2 del creador
   firmada en `MATRIZ-NATIVA-IDES.md`: el agente unico ejecuta las 3 fases
   tripartitas (explorer + implementer + documenter) **secuencialmente**
   dentro de la misma sesion, guiado por instrucciones explicitas en
   ``AGENTS.md``.

3. **MCP config en TOML**, no JSON. Sintaxis: ``[mcp_servers.<name>]`` con
   seccion separada ``[mcp_servers.<name>.env]`` para variables de entorno.

4. ``.codex/agents/`` y ``.codex/skills/`` no se generan (Codex los ignora).

Layout escrito por este adapter:

    AGENTS.md             ← project root, instrucciones del flujo tripartito
                            secuencial
    .codex/
      config.toml         ← MCP server registration en TOML

## Relaciones

### Recibe de

- `cortex.ide.base` (IDEAdapter, _backup_file, _generate_autogen_header)
- Dependencias externas/stdlib: `os`, `re`, `shutil`, `__future__`, `pathlib`

### Envía a

- Ningún otro módulo `cortex.*` lo importa por nombre de módulo en el AST de `cortex/` (puede ser entrypoint CLI, script, o import dinámico).

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 624.
Docstrings de símbolos públicos:
- `CodexAdapter.inject_profiles`: Inyectar AGENTS.md en project root con instrucciones del flujo Cortex.
- `CodexAdapter.inject_mcp`: Inyectar el MCP server Cortex para Codex (modelo mono-repo).
- `CodexAdapter.detect_installation`: Detect whether the Codex CLI binary is available on PATH.
- `CodexAdapter.uninstall`: Remove Cortex sections from AGENTS.md and config.toml. Idempotent.

---
Fuente: código de `cortex/ide/adapters/codex.py` (AST + grafo de imports internos). No se usó documentación previa.
