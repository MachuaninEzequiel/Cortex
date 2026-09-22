# cortex/setup/enterprise_presets.py

## Qué tiene adentro

- **Ruta de código:** `cortex/setup/enterprise_presets.py` (77 líneas).
- **Módulo Python:** `cortex.setup.enterprise_presets`.
- **Clases definidas:**
  - `EnterpriseSetupInput`
- **Funciones de módulo:**
  - `validate_enterprise_preset(profile)`
  - `load_org_config_overrides(path)`
  - `resolve_enterprise_setup()` — Resolve the enterprise setup, adjusting relative paths for
  - `_deep_merge(base, incoming)`

## Para qué sirve

Define EnterpriseSetupInput. No hay docstring de módulo; el propósito se infiere de las clases y métodos listados.

## Relaciones

### Recibe de

- `cortex.enterprise.config` (build_enterprise_org_config, list_enterprise_presets)
- Dependencias externas/stdlib: `yaml`, `__future__`, `dataclasses`, `pathlib`, `typing`

### Envía a

- `cortex.setup.orchestrator`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 77.
Docstrings de símbolos públicos:
- `resolve_enterprise_setup`: Resolve the enterprise setup, adjusting relative paths for

---
Fuente: código de `cortex/setup/enterprise_presets.py` (AST + grafo de imports internos). No se usó documentación previa.
