# Estructura interna — `rust/crates/cortex-setup`

Capa de **setup + writers canónicos + 11 adapters IDE + session hooks + skills COMPOSED**. Paridad-como-contrato contra Python (P8).

Dependencias: chrono, minijinja, serde, serde_json preserve_order, sha2, unicode-normalization. **No** depende de otros crates Cortex (lib.rs).

Plantillas reales de notas: `cortex/documentation/templates/*.md.j2` embebidas (`PY_TEMPLATES_DIR`). Familia COMPOSED: `templates/composed/`. Tríada thin+craft: `cortex/setup/workspace_files/` via include_str.

```
cortex-setup/
├── Cargo.toml
├── examples/{note_dump,yaml_dump}.rs
├── src/
│   ├── lib.rs
│   ├── detector.rs          # stack/CI/env
│   ├── doc_type.rs          # 13 DocType + valid_statuses
│   ├── fingerprint.rs
│   ├── slug.rs
│   ├── yaml.rs              # dumper PyYAML
│   ├── jinja.rs             # 13 templates md.j2
│   ├── routing.rs           # carpetas/filenames
│   ├── writers.rs           # build_note
│   ├── setup_templates.rs
│   ├── setup_templates_gen.rs  # NO EDITAR (AST Python)
│   ├── skills_bundle.rs
│   ├── ide/
│   │   ├── mod.rs           # IdeCtx, IdeAdapter
│   │   ├── base.rs
│   │   ├── canonical_tools.rs
│   │   ├── prompts.rs
│   │   └── adapters/        # 11 IDEs + mcp_command
│   └── session_hooks/       # claude_code, cursor, opencode, pi
├── templates/composed/      # grill, to-spec, to-tickets, implement, tdd,
│                            # diagnose, review, glossary + INSTALL
└── tests/                   # writers/ide/hooks/setup parity + composed
```

## DocTypes (`doc_type.rs`)

session, handoff, spec, adr, decision, incident, postmortem, runbook, architecture, changelog, hu, glossary, design.

## Adapters IDE (`all_adapters` orden Python)

1. ClaudeCode 2. OpenCode 3. Pi 4. Codex 5. Cursor 6. ClaudeDesktop 7. VSCode 8. Windsurf 9. Zed 10. Antigravity 11. Hermes

MCP command común: `cortex-cli mcp-server --stdio` + env PYTHONPATH/PYTHONWARNINGS.

## Relación lote 2

- CLI `setup`/`ide`/`session hooks` / `docs` writers.
- Services `persist_note` → `build_note`.
- MCP docs/spec usan writers/routing.
