# rust/crates/cortex-enterprise/src/frontmatter.rs

## Qué tiene adentro

Puerto de los helpers de frontmatter de `cortex.enterprise.knowledge_promotion` (`_FRONTMATTER_RE`, `_split_frontmatter`, `_upsert_frontmatter`, `_normalized_markdown_fingerprint`, `_doc_type_from_rel_path`).  El splitter replica manualmente el regex `^---\s*\n(.*?)\n---\s*\n` (DOTALL, lazy) sin dependencia nueva: mismo backtracking de `\s*` greedy ante el `\n` literal (consume todo el whitespace y retrocede un paso si el último carácter consumido es el `\n` que exige el patrón).
Archivo de 186 líneas.
Símbolos públicos observados:
- `pub struct SplitFrontmatter`
- `pub fn split_frontmatter(raw: &str) -> Option<SplitFrontmatter>`
- `pub fn yaml_value_to_node(value: &serde_yaml::Value) -> Yaml`
- `pub fn upsert_frontmatter(raw: &str, updates: Vec<(String, Option<serde_yaml::Value>)>) -> String`
- `pub fn normalized_markdown_fingerprint(raw: &str) -> String`
- `pub fn doc_type_from_rel_path(rel_path: &str) -> Option<&'static str>`

## Para qué sirve

Puerto de los helpers de frontmatter de `cortex.enterprise.knowledge_promotion` (`_FRONTMATTER_RE`, `_split_frontmatter`, `_upsert_frontmatter`, `_normalized_markdown_fingerprint`, `_doc_type_from_rel_path`).  El splitter replica manualmente el regex `^---\s*\n(.*?)\n---\s*\n` (DOTALL, lazy) sin dependencia nueva: mismo backtracking de `\s*` greedy ante el `\n` literal (consume todo el whitespace y retrocede un paso si el último carácter consumido es el `\n` que exige el patrón).

## Relaciones

### Recibe de

- `use cortex_setup::yaml::Yaml`
- Contexto de crate `cortex-enterprise`: cortex-app, cortex-setup, cortex-workspace

### Envía a

- Crate `cortex-enterprise` envía hacia: cortex-cli enterprise, cortex-doctor, cortex-actions knowledge.promote, cortex-brain-app org_memory

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-enterprise/src/frontmatter.rs`.
