# cortex/workspace/layout.py

## Qué tiene adentro

- Dataclass `WorkspaceLayout`: `repo_root`, `workspace_root`, flags `is_legacy_layout` / `is_new_layout`.
- `discover(start)` recorre padres. Precedencia:
  1. `.cortex/workspace.yaml` con `layout_version >= 2` → new.
  2. `.cortex/config.yaml` sin `config.yaml` en la raíz → new.
  3. `config.yaml` en raíz o `.cortex/` + `.git` → legacy.
  4. Bootstrap: git root o `start`, forzado new.
- Salta directorios llamados `.cortex` (son workspace, no repo root).
- `from_repo_root` construye new layout (`workspace_root = repo/.cortex`).
- Propiedades de path (resto del archivo, 564 líneas): `config_path`, `vault_path`, `sessions_dir`, memoria episódica, enterprise vault, skills, logs, agent guidelines, etc.
- `resolve_workspace_relative` para paths del YAML.

**New layout:** todo bajo `repo/.cortex/` (config, vault, memory, org.yaml, skills, webgraph, logs).

**Legacy:** `config.yaml`, `vault/`, `.memory/` en la raíz; `.cortex/` guarda skills/subagents/org.

## Para qué sirve

Única fuente de paths del runtime Python. El comentario del módulo dice que ningún otro módulo debería hardcodear layout.

## Relaciones

### Recibe de

- Filesystem + `yaml.safe_load` de `workspace.yaml`.
- Sin imports `cortex.*`.

### Envía a

Grafo AST muy amplio: `core` (vía discover en AgentMemory), CLI (main, session, ide, ci, docs, review), MCP server, doctor, autopilot, enterprise, git_policy, ide, setup.orchestrator, tutor.hint, webgraph.*, action_engine.context, workspace.__init__.

### Notas de implementación observadas en el código

- Paths relativos de `config.yaml`/`org.yaml` se resuelven contra `workspace_root` (en new = `.cortex`, en legacy = repo root).

---
Fuente: lectura de `cortex/workspace/layout.py`. No se usó documentación previa.
