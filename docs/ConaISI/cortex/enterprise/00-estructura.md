# Estructura — `cortex/enterprise`

## Para qué existe esta carpeta

(sin docstring de paquete; reexportes)

## Árbol interno (código, sin `__pycache__`)

```
enterprise/
├── __init__.py
├── config.py
├── governance.py
├── knowledge_promotion.py
├── maintenance.py
├── models.py
├── promotion_doctype.py
├── promotion_models.py
├── reporting.py
├── retrieval_service.py
└── sources.py
```

## Archivos Python cubiertos aquí

| Archivo | Líneas | Síntesis observada |
|---|---:|---|
| `cortex/enterprise/__init__.py` | 22 | reexportes / marcador de paquete |
| `cortex/enterprise/config.py` | 290 | list_enterprise_presets, discover_enterprise_config_path, load_enterprise_config, root_enterprise_config_path, build_enterprise_org_config, write_enterprise_config, render_enterprise_config_yaml, describe_enterprise_topology |
| `cortex/enterprise/governance.py` | 153 | cortex.enterprise.governance - Multi-tenant permissions and visibility. |
| `cortex/enterprise/knowledge_promotion.py` | 339 | PromotionPaths, PromotionRepository, PromotionRulesEngine, KnowledgePromotionService, _utc_now, _split_frontmatter, _upsert_frontmatter, _normalized_markdown_fingerprint, _doc_type_from_rel_path |
| `cortex/enterprise/maintenance.py` | 169 | cortex.enterprise.maintenance - Retention scan and archival. |
| `cortex/enterprise/models.py` | 184 | OrganizationConfig, MemoryConfig, PromotionConfig, GovernanceConfig, IntegrationConfig, TeamConfig, RetentionPolicy, EnterprisePolicies, EnterpriseOrgConfig |
| `cortex/enterprise/promotion_doctype.py` | 449 | cortex.enterprise.promotion_doctype - DocType-aware promotion (Fase 10). |
| `cortex/enterprise/promotion_models.py` | 75 | PromotionIssue, PromotionCandidate, PromotionDecision, PromotionRecordEvent, PromotionRecord |
| `cortex/enterprise/reporting.py` | 219 | PromotionEventSummary, PromotionReport, MemorySourceReport, MemoryReportPayload, EnterpriseReportingService, _utc_now, _doctor_to_payload, _extract_check_count, _count_markdown_files, _summarize_latest_events |
| `cortex/enterprise/retrieval_service.py` | 222 | RetrievalSourceConfig, EnterpriseRetrievalService |
| `cortex/enterprise/sources.py` | 115 | VaultSource, EpisodicSource, MultiVaultReader, MultiEpisodicReader |

## Relaciones de la carpeta

### Recibe de (unión de imports `cortex.*` de los módulos de este nivel)

- `cortex.doc_validator`
- `cortex.doctor`
- `cortex.documentation.common`
- `cortex.documentation.doc_type`
- `cortex.documentation.errors`
- `cortex.documentation.routing`
- `cortex.enterprise.config`
- `cortex.enterprise.governance`
- `cortex.enterprise.knowledge_promotion`
- `cortex.enterprise.models`
- `cortex.enterprise.promotion_models`
- `cortex.enterprise.sources`
- `cortex.episodic.memory_store`
- `cortex.models`
- `cortex.runtime_context`
- `cortex.semantic.vault_reader`
- `cortex.workspace.layout`

### Envía a (módulos `cortex.*` que importan a este nivel)

- `cortex.cli.review_knowledge`
- `cortex.core`
- `cortex.doctor`
- `cortex.enterprise`
- `cortex.enterprise.config`
- `cortex.enterprise.governance`
- `cortex.enterprise.knowledge_promotion`
- `cortex.enterprise.maintenance`
- `cortex.enterprise.promotion_doctype`
- `cortex.enterprise.reporting`
- `cortex.enterprise.retrieval_service`
- `cortex.setup.enterprise_presets`
- `cortex.setup.enterprise_wizard`
- `cortex.setup.orchestrator`
- `cortex.setup.templates`
- `cortex.webgraph.service`

---
Fuente: árbol de `cortex/` + AST de imports. No se usó documentación previa.
