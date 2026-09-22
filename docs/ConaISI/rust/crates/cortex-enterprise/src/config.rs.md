# rust/crates/cortex-enterprise/src/config.rs

## Qué tiene adentro

Puerto de `cortex.enterprise.config`: discovery/carga/escritura de `.cortex/org.yaml`, presets por perfil y resumen de topología.  Paridad de emisión: `yaml.safe_dump(payload, sort_keys=False, allow_unicode=False)` vía `cortex_setup::yaml::dump_with(node, false)`. La carga normaliza el slug como el validator Pydantic (`slug or name`, fallback "organization") y ejecuta las validaciones cruzadas.
Archivo de 369 líneas.
Símbolos públicos observados:
- `pub const DEFAULT_ENTERPRISE_CONFIG_PATH: &str = ".cortex/org.yaml"`
- `pub fn list_enterprise_presets() -> Vec<&'static str>`
- `pub fn root_enterprise_config_path(project_root: &Path) -> PathBuf`
- `pub fn discover_enterprise_config_path(`
- `pub fn load_enterprise_config(`
- `pub fn build_enterprise_org_config(`
- `pub fn write_enterprise_config(`
- `pub fn render_enterprise_config_yaml(config: &EnterpriseOrgConfig) -> String`
- `pub fn dump_enterprise_config_yaml(config: &EnterpriseOrgConfig) -> String`
- `pub fn describe_enterprise_topology(`

## Para qué sirve

Puerto de `cortex.enterprise.config`: discovery/carga/escritura de `.cortex/org.yaml`, presets por perfil y resumen de topología.  Paridad de emisión: `yaml.safe_dump(payload, sort_keys=False, allow_unicode=False)` vía `cortex_setup::yaml::dump_with(node, false)`. La carga normaliza el slug como el validator Pydantic (`slug or name`, fallback "organization") y ejecuta las validaciones cruzadas.

## Relaciones

### Recibe de

- `use cortex_setup::yaml::{self as pyyaml, Yaml}`
- `use crate::error::EnterpriseError`
- `use crate::models::{`
- `use cortex_workspace::runtime_context::slugify`
- Contexto de crate `cortex-enterprise`: cortex-app, cortex-setup, cortex-workspace

### Envía a

- Crate `cortex-enterprise` envía hacia: cortex-cli enterprise, cortex-doctor, cortex-actions knowledge.promote, cortex-brain-app org_memory

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-enterprise/src/config.rs`.
