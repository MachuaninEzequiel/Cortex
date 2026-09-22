# cortex/enterprise/__init__.py

## Qué tiene adentro

- **Ruta de código:** `cortex/enterprise/__init__.py` (22 líneas).
- **Módulo Python:** `cortex.enterprise`.
- **Constantes / símbolos de módulo:** `__all__`
- Archivo sin clases/funciones de módulo ni docstring (típicamente reexportes o marcador de paquete).

## Para qué sirve

Marcador de paquete o reexportes. Ver lista de imports y de quién lo importa.

## Relaciones

### Recibe de

- `cortex.enterprise.config` (DEFAULT_ENTERPRISE_CONFIG_PATH, build_enterprise_org_config, describe_enterprise_topology, discover_enterprise_config_path, list_enterprise_presets, load_enterprise_config, write_enterprise_config)
- `cortex.enterprise.models` (EnterpriseOrgConfig)

### Envía a

- Ningún otro módulo `cortex.*` lo importa por nombre de módulo en el AST de `cortex/` (puede ser entrypoint CLI, script, o import dinámico).

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 22.
Reexportes observados:
- cortex.enterprise.config: DEFAULT_ENTERPRISE_CONFIG_PATH, build_enterprise_org_config, describe_enterprise_topology, discover_enterprise_config_path, list_enterprise_presets, load_enterprise_config, write_enterprise_config
- cortex.enterprise.models: EnterpriseOrgConfig

---
Fuente: código de `cortex/enterprise/__init__.py` (AST + grafo de imports internos). No se usó documentación previa.
