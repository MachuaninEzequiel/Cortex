# rust/crates/cortex-tutor — estructura interna

Visor de documentación con 7 topics estáticos + hints contextuales. Contenido `include_str!` desde `content/` (captura `export_text()` de rich, sin ANSI).

```
cortex-tutor/
├── Cargo.toml
├── content/
│   ├── menu.txt
│   └── topic_{start,commands,workflow,pipeline,vault,enterprise,ide}.txt
├── examples/tutor_check.rs
├── src/
│   ├── lib.rs
│   ├── engine.rs    # render_menu, show_topic_by_slug
│   ├── hint.rs      # ProjectState → Hint
│   └── topics.rs    # TopicMeta, get_all_topics
└── tests/tutor_core.rs
```

## Relaciones

- **Recibe de:** `cortex-workspace` (estado de proyecto para hints), archivos `content/*.txt`.
- **Envía a:** `cortex-cli tutor`. El catálogo de tópicos en `cortex-actions::catalog` (`TUTOR_TOPICS`) es una lista estática paralela (títulos/rutas de guía), no importa este crate.
