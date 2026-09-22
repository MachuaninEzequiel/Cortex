# rust/crates/cortex-enterprise — estructura interna

Puerto de `cortex/enterprise/`: org YAML, gobernanza, promoción, retención, retrieval, reporting.

```
cortex-enterprise/
├── Cargo.toml
├── examples/enterprise_check.rs
├── src/
│   ├── lib.rs
│   ├── clock.rs / error.rs / models.rs / config.rs
│   ├── frontmatter.rs / governance.rs
│   ├── knowledge_promotion.rs / promotion_models.rs / promotion_doctype.rs
│   ├── review_knowledge.rs / maintenance.rs
│   ├── sources.rs / retrieval.rs / reporting.rs
└── tests/
    ├── models_config_governance.rs
    ├── knowledge_promotion.rs
    ├── doctype_review_maintenance.rs
    ├── retrieval.rs
    └── reporting.rs
```

Config default: `.cortex/org.yaml`. Gobernanza: teams, `ADMIN_TEAM`, `assert_can_promote` / `assert_can_review`, visibilidad por classification.

## Relaciones

- **Recibe de:** `cortex-app`, `cortex-setup`, `cortex-workspace`, vault local + enterprise.
- **Envía a:** CLI (`promote`, `review`, `memory-report`), doctor (backend), actions `knowledge.promote`, brain-app `org_memory`.
