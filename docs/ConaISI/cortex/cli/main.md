# cortex/cli/main.py

## Qué tiene adentro

- **1931 líneas.** Aplicación Typer `app` (`name="cortex"`). Entrypoint de consola.
- Sin subcomando: abre Home TUI (`cortex.tui.core.run_home`).
- `--version` / `-V` imprime `cortex {__version__}`.
- Windows: reconfigura stdout/stderr a UTF-8. `warnings.filterwarnings("ignore")`.
- Monta sub-Typer (varios `hidden=True`): `webgraph`, `autopilot`, `session`, `ide`, `pr-context`, `hu`, `ci`, `docs`, `setup`, `review-knowledge`.
- Registro diferido: `brain.cli.register`, `cli.next.register` (ActionEngine), `cli.documenting.register`, `cli.embedding.register`, `cli.mcp_cmd.register`.
- `_DEFAULT_CONFIG`: YAML mínimo episódico/semántico/retrieval/llm para init/setup.

Comandos top-level observados en el archivo: `init`, `doctor`, `org-config`, `context`, `verify-docs`, `validate-docs`, `index-docs`, `agent-guidelines`, `tutor`, `hint`, `install-skills`, `remember`, `search`, `promote-knowledge`, `sync-enterprise-vault`, `install-ide`, `uninstall-ide`, `inject`, `sync-ide`, `stats`, `memory-report`, `forget`.

Subcomandos `setup`: `agent`, `pipeline`, `full`, `webgraph`, `enterprise`.
Subcomandos `pr-context`: `capture`, `store`, `search`, `generate`, `full`.

El docstring del módulo lista la superficie canónica de adopter (search, context, remember, create-spec, save-session, doctor, MCP, etc.).

## Para qué sirve

Única puerta CLI Python. Orquesta; no reimplementa stores. Varios comandos están `hidden=True` (siguen existiendo para scripts/tests).

## Relaciones

### Recibe de

- `WorkspaceLayout`, YAML de proyecto.
- Submódulos `cortex.cli.*`, `cortex.webgraph.cli`, `cortex.autopilot.cli`, `cortex.brain.cli`.
- `AgentMemory` (vía `cli.common` u otros helpers en el resto del archivo).
- `typer`, `yaml`.

### Envía a

- Proceso usuario / CI (stdout).
- `cortex.cli.__init__` reexporta `app`.
- `pyproject.toml` `[project.scripts] cortex = "cortex.cli.main:app"`.
- TUI, MCP stdio, Flask webgraph, setup writers, vault, chroma.

### Notas de implementación observadas en el código

- Compat: `_parse_verification_hooks` se reexporta desde `documenting` porque tests lo importaban de `main`.
- `init` es alias de setup agent (docstring del módulo).
- `install-ide` es alias deprecado de `inject`.

---
Fuente: lectura de `cortex/cli/main.py` (cabecera + inventario de `@app.command` / `add_typer`). No se usó documentación previa.
