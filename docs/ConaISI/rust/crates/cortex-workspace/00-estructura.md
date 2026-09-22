# Estructura interna — `rust/crates/cortex-workspace`

Crate de dominio de **workspace**: descubrimiento de layout (nuevo vs legacy), rutas canónicas, handoff YAML entre agentes, política de `.gitignore`, instalación del bundle de skills Obsidian, contexto runtime (git/namespace episódico) y emisor YAML byte-compatible con PyYAML.

Dependencias (`Cargo.toml`): `serde`, `serde_json`, `serde_yaml`. Dev: `tempfile`, `sha2`. **No** depende de otros crates Cortex. Quien necesite resolución segura de paths consume `cortex_app::security` (no se duplica aquí).

```
cortex-workspace/
├── Cargo.toml
├── examples/
│   └── workspace_check.rs
├── src/
│   ├── lib.rs
│   ├── layout.rs
│   ├── handoff.rs
│   ├── git_policy.rs
│   ├── skills.rs
│   ├── runtime_context.rs
│   └── pyyaml.rs
└── tests/
    └── spec_parity.rs
```

## Relación con el resto del lote 2

- `cortex-cli` y `cortex-mcp` descubren el proyecto con `WorkspaceLayout::discover`.
- `cortex-setup` instala skills COMPOSED aparte; este crate instala el bundle **Obsidian** (`obsidian-markdown`, `json-canvas`, `obsidian-bases`, `obsidian-cli`, `defuddle`).
- `cortex-services` no depende de este crate; el CLI sí, para resolver vault/sessions.

## Layouts

- **Nuevo** (`layout_version >= 2` o `.cortex/config.yaml` sin `config.yaml` en raíz): `workspace_root = repo/.cortex`.
- **Legacy**: `workspace_root == repo_root`. Config en `config.yaml` de la raíz.
