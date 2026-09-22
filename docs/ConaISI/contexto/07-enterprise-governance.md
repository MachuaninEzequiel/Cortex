# Contexto: enterprise, governance, promoción

Código: `cortex/enterprise/*` y `rust/crates/cortex-enterprise/`.

## Config

Path default: `.cortex/org.yaml` (`DEFAULT_ENTERPRISE_CONFIG_PATH`). Discovery: `discover_enterprise_config_path` / `load_enterprise_config`. Presets: `list_enterprise_presets()`. Wizard Python: `cortex/setup/enterprise_wizard.py`. CLI: `org-config`, `setup enterprise`.

Modelo `EnterpriseOrgConfig`: organization, memory, promotion, governance, integrations, teams, policies (retention).

## Governance

`ADMIN_TEAM = "admin"`. Funciones: `user_team`, `team_can_promote`, `team_can_review`, `classification_visible_to`, `allowed_classifications_for`, `assert_can_promote`, `assert_can_review`.

La retrieval unificada (`EnterpriseRetrievalService`) filtra hits por clasificación visible al actor. Scope: `local | enterprise | all` (`RetrievalScope`).

## Promoción de conocimiento

Flujo en código: candidato (`PromotionCandidate`) → reglas (`PromotionRulesEngine`) → decisión (`PromotionDecision`) → record (`PromotionRecord`) persistido por `PromotionRepository`.

Doc-type aware: `promote_note_doctype_aware`, `mark_as_accepted`, `mark_as_rejected`, `list_pending_drafts`. Review queue: `review_knowledge.rs` / CLI `review-knowledge pending|approve|reject|candidate`. CLI `promote-knowledge`. MCP no tiene tools de promote (no aparecen en `tools_catalog.rs`); eso queda en CLI/enterprise.

Brain-app UI: `org_memory.rs` lista items y approve/reject. Frontend: `OrgMemoryModal.tsx` + `GovernanceBar.tsx`.

## Mantenimiento

`scan_retention_violations` / `archive_violations` según `RetentionPolicy`.

## Reporting / doctor

`EnterpriseReportingService`: promotion report + memory source report. `DoctorBackend` trait; `cortex-doctor` implementa checks nativos (layout, gitignore, config, governance). CLI `doctor --scope`, `memory-report`.

## Fuentes

`VaultSource`, `EpisodicSource`, `SemanticHit`, `EpisodicHit`, trait `SearchBackend`. El doctor y el retrieval enterprise no reimplementan BM25: piden un backend (en nativo, el de `cortex-app`).
