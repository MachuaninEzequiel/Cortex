# cortex/enterprise/config.py

## Qué tiene adentro

- **Ruta de código:** `cortex/enterprise/config.py` (290 líneas).
- **Módulo Python:** `cortex.enterprise.config`.
- **Funciones de módulo:**
  - `list_enterprise_presets()`
  - `discover_enterprise_config_path(project_root)` — Discover the enterprise config file.
  - `load_enterprise_config(project_root)` — Load enterprise organisational config.
  - `root_enterprise_config_path(project_root)` — Return the legacy path for org.yaml (repo_root / .cortex / org.yaml).
  - `build_enterprise_org_config()`
  - `write_enterprise_config(project_root, config)` — Write enterprise config to disk.
  - `render_enterprise_config_yaml(config)`
  - `describe_enterprise_topology(config, project_root)`
- **Constantes / símbolos de módulo:** `DEFAULT_ENTERPRISE_CONFIG_PATH`, `_PRESET_PROFILES`

## Para qué sirve

Expone las funciones list_enterprise_presets, discover_enterprise_config_path, load_enterprise_config, root_enterprise_config_path, build_enterprise_org_config, write_enterprise_config, render_enterprise_config_yaml, describe_enterprise_topology. No hay docstring de módulo.

## Relaciones

### Recibe de

- `cortex.enterprise.models` (EnterpriseOrgConfig, OrgProfile)
- `cortex.runtime_context` (slugify)
- Dependencias externas/stdlib: `yaml`, `__future__`, `pathlib`, `typing`

### Envía a

- `cortex.core`
- `cortex.doctor`
- `cortex.enterprise`
- `cortex.enterprise.knowledge_promotion`
- `cortex.enterprise.reporting`
- `cortex.setup.enterprise_presets`
- `cortex.setup.enterprise_wizard`
- `cortex.setup.orchestrator`
- `cortex.setup.templates`
- `cortex.webgraph.service`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 290.
Docstrings de símbolos públicos:
- `discover_enterprise_config_path`: Discover the enterprise config file.
- `load_enterprise_config`: Load enterprise organisational config.
- `root_enterprise_config_path`: Return the legacy path for org.yaml (repo_root / .cortex / org.yaml).
- `write_enterprise_config`: Write enterprise config to disk.

---
Fuente: código de `cortex/enterprise/config.py` (AST + grafo de imports internos). No se usó documentación previa.
