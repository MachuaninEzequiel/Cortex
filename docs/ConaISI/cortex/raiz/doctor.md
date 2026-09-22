# cortex/doctor.py

## Qué tiene adentro

- **925 líneas.** Diagnóstico de un proyecto Cortex.
- Tipos: `DoctorSeverity` (`fail|warn|info`), `DoctorScope` (`project|enterprise|all`), `DoctorCheck`, `DoctorReport` (`has_failures`, `has_warnings`).
- `run_doctor(project_root, scope="project")` arma una lista de checks.

Checks observados al inicio del archivo: existencia de `project_root`, `layout_mode` (new/legacy), `config_yaml` + validación `CortexConfig`, `vault_dir`, `episodic_store` (en CI `GITHUB_ACTIONS=true` baja a warn), `cortex_workspace`, `agent_guidelines`. El resto del archivo continúa con gitignore, git, webgraph deps, enterprise (`load_enterprise_config`), validación de docs (`DocValidator`), autopilot, etc.

## Para qué sirve

Health-check de runtime/layout. Lo consume `cortex doctor` (CLI) y reportes enterprise.

## Relaciones

### Recibe de

- `WorkspaceLayout`, YAML config, `CortexConfig`.
- `DocValidator`, `git_policy` (patrones gitignore), `runtime_context`.
- `load_enterprise_config` / `describe_enterprise_topology`.
- `webgraph.setup.get_missing_webgraph_dependencies`.
- Filesystem del repo.

### Envía a

- CLI `doctor` y `memory-report` (vía enterprise reporting que puede envolver doctor).
- No persiste: devuelve `DoctorReport`.

### Notas de implementación observadas en el código

- Primer check fatal si el root no existe: retorna inmediatamente.
- Store episódico ausente es `fail` salvo GitHub Actions (`warn`).

---
Fuente: lectura de `cortex/doctor.py` (inicio + estructura de checks). No se usó documentación previa.
