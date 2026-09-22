# Índice lote 3 — crates Rust restantes + notas de cobertura

Documentación generada **solo desde código** (Cargo.toml, `src/`, tests, examples, configs). No se leyó `docs/`, README ni `apps/docs/src/content`.

Cada crate tiene `00-estructura.md` y un `.md` por archivo fuente (ruta espejo + sufijo `.md`).


## cortex-brain (16 documentos)

- Estructura: `rust/crates/cortex-brain/00-estructura.md`
- `rust/crates/cortex-brain/Cargo.toml.md`
- `rust/crates/cortex-brain/src/chat.rs.md`
- `rust/crates/cortex-brain/src/download.rs.md`
- `rust/crates/cortex-brain/src/i18n.rs.md`
- `rust/crates/cortex-brain/src/lib.rs.md`
- `rust/crates/cortex-brain/src/llama.rs.md`
- `rust/crates/cortex-brain/src/main.rs.md`
- `rust/crates/cortex-brain/src/paths.rs.md`
- `rust/crates/cortex-brain/src/router.rs.md`
- `rust/crates/cortex-brain/src/tools.rs.md`
- `rust/crates/cortex-brain/src/window.rs.md`
- `rust/crates/cortex-brain/tests/i18n.rs.md`
- `rust/crates/cortex-brain/tests/spec_behavior.rs.md`
- `rust/crates/cortex-brain/tests/tool_i18n.rs.md`
- `rust/crates/cortex-brain/tests/tool_protocol.rs.md`

## cortex-brain-app (15 documentos)

- Estructura: `rust/crates/cortex-brain-app/00-estructura.md`
- `rust/crates/cortex-brain-app/.gitignore.md`
- `rust/crates/cortex-brain-app/Cargo.toml.md`
- `rust/crates/cortex-brain-app/build.rs.md`
- `rust/crates/cortex-brain-app/capabilities/default.json.md`
- `rust/crates/cortex-brain-app/src/chat.rs.md`
- `rust/crates/cortex-brain-app/src/graph.rs.md`
- `rust/crates/cortex-brain-app/src/ipc.rs.md`
- `rust/crates/cortex-brain-app/src/lib.rs.md`
- `rust/crates/cortex-brain-app/src/main.rs.md`
- `rust/crates/cortex-brain-app/src/org_memory.rs.md`
- `rust/crates/cortex-brain-app/src/projects.rs.md`
- `rust/crates/cortex-brain-app/tauri.conf.json.md`
- `rust/crates/cortex-brain-app/tests/eval_governance_model.rs.md`
- `rust/crates/cortex-brain-app/tests/smoke.rs.md`

## cortex-branding (11 documentos)

- Estructura: `rust/crates/cortex-branding/00-estructura.md`
- `rust/crates/cortex-branding/Cargo.toml.md`
- `rust/crates/cortex-branding/examples/preview.rs.md`
- `rust/crates/cortex-branding/src/ansi.rs.md`
- `rust/crates/cortex-branding/src/gradient.rs.md`
- `rust/crates/cortex-branding/src/lib.rs.md`
- `rust/crates/cortex-branding/src/logo.rs.md`
- `rust/crates/cortex-branding/src/palette.rs.md`
- `rust/crates/cortex-branding/src/pixels.rs.md`
- `rust/crates/cortex-branding/src/wordmark.rs.md`
- `rust/crates/cortex-branding/tests/geometry.rs.md`

## cortex-tui (43 documentos)

- Estructura: `rust/crates/cortex-tui/00-estructura.md`
- `rust/crates/cortex-tui/Cargo.toml.md`
- `rust/crates/cortex-tui/examples/capture.rs.md`
- `rust/crates/cortex-tui/examples/home_preview.rs.md`
- `rust/crates/cortex-tui/examples/splash.rs.md`
- `rust/crates/cortex-tui/src/actions.rs.md`
- `rust/crates/cortex-tui/src/app/action.rs.md`
- `rust/crates/cortex-tui/src/app/effect.rs.md`
- `rust/crates/cortex-tui/src/app/mod.rs.md`
- `rust/crates/cortex-tui/src/app/runtime.rs.md`
- `rust/crates/cortex-tui/src/app/search.rs.md`
- `rust/crates/cortex-tui/src/app/state.rs.md`
- `rust/crates/cortex-tui/src/app/update.rs.md`
- `rust/crates/cortex-tui/src/clipboard.rs.md`
- `rust/crates/cortex-tui/src/components/empty_state.rs.md`
- `rust/crates/cortex-tui/src/components/feedback.rs.md`
- `rust/crates/cortex-tui/src/components/header.rs.md`
- `rust/crates/cortex-tui/src/components/help.rs.md`
- `rust/crates/cortex-tui/src/components/list.rs.md`
- `rust/crates/cortex-tui/src/components/mod.rs.md`
- `rust/crates/cortex-tui/src/components/panel.rs.md`
- `rust/crates/cortex-tui/src/components/status_bar.rs.md`
- `rust/crates/cortex-tui/src/deprecated/header_legacy.rs.md`
- `rust/crates/cortex-tui/src/deprecated/mod.rs.md`
- `rust/crates/cortex-tui/src/deprecated/renderer_legacy.rs.md`
- `rust/crates/cortex-tui/src/deprecated/splash_legacy.rs.md`
- `rust/crates/cortex-tui/src/event.rs.md`
- `rust/crates/cortex-tui/src/hit.rs.md`
- `rust/crates/cortex-tui/src/home.rs.md`
- `rust/crates/cortex-tui/src/keymap.rs.md`
- `rust/crates/cortex-tui/src/layout.rs.md`
- `rust/crates/cortex-tui/src/lib.rs.md`
- `rust/crates/cortex-tui/src/renderer.rs.md`
- `rust/crates/cortex-tui/src/search.rs.md`
- `rust/crates/cortex-tui/src/session_detail.rs.md`
- `rust/crates/cortex-tui/src/sessions.rs.md`
- `rust/crates/cortex-tui/src/splash.rs.md`
- `rust/crates/cortex-tui/src/terminal.rs.md`
- `rust/crates/cortex-tui/src/theme.rs.md`
- `rust/crates/cortex-tui/src/view.rs.md`
- `rust/crates/cortex-tui/tests/sessions_screen.rs.md`
- `rust/crates/cortex-tui/tests/snapshots.rs.md`
- `rust/crates/cortex-tui/tests/theme_hygiene.rs.md`

## cortex-companion (43 documentos)

- Estructura: `rust/crates/cortex-companion/00-estructura.md`
- `rust/crates/cortex-companion/Cargo.toml.md`
- `rust/crates/cortex-companion/examples/preview_ansi.rs.md`
- `rust/crates/cortex-companion/src/app.rs.md`
- `rust/crates/cortex-companion/src/approval.rs.md`
- `rust/crates/cortex-companion/src/bin/companion.rs.md`
- `rust/crates/cortex-companion/src/bin/copilot.rs.md`
- `rust/crates/cortex-companion/src/bin/float.rs.md`
- `rust/crates/cortex-companion/src/bin/sidecar.rs.md`
- `rust/crates/cortex-companion/src/brain_panel.rs.md`
- `rust/crates/cortex-companion/src/clipboard.rs.md`
- `rust/crates/cortex-companion/src/effects.rs.md`
- `rust/crates/cortex-companion/src/engine.rs.md`
- `rust/crates/cortex-companion/src/feedback.rs.md`
- `rust/crates/cortex-companion/src/herdr.rs.md`
- `rust/crates/cortex-companion/src/hud_brand.rs.md`
- `rust/crates/cortex-companion/src/lib.rs.md`
- `rust/crates/cortex-companion/src/menu.rs.md`
- `rust/crates/cortex-companion/src/runner.rs.md`
- `rust/crates/cortex-companion/src/screens/actions_screen.rs.md`
- `rust/crates/cortex-companion/src/screens/brain_screen.rs.md`
- `rust/crates/cortex-companion/src/screens/copilot_screen.rs.md`
- `rust/crates/cortex-companion/src/screens/home.rs.md`
- `rust/crates/cortex-companion/src/screens/hud_screen.rs.md`
- `rust/crates/cortex-companion/src/screens/menu_screen.rs.md`
- `rust/crates/cortex-companion/src/screens/mod.rs.md`
- `rust/crates/cortex-companion/src/screens/search_screen.rs.md`
- `rust/crates/cortex-companion/src/screens/sessions_screen.rs.md`
- `rust/crates/cortex-companion/src/theme.rs.md`
- `rust/crates/cortex-companion/src/widgets.rs.md`
- `rust/crates/cortex-companion/tests/app_input.rs.md`
- `rust/crates/cortex-companion/tests/approval.rs.md`
- `rust/crates/cortex-companion/tests/approval_flow_ui.rs.md`
- `rust/crates/cortex-companion/tests/brain_panel.rs.md`
- `rust/crates/cortex-companion/tests/current_branch.rs.md`
- `rust/crates/cortex-companion/tests/hud.rs.md`
- `rust/crates/cortex-companion/tests/menu_catalog.rs.md`
- `rust/crates/cortex-companion/tests/parity_cli.rs.md`
- `rust/crates/cortex-companion/tests/plugin_manifest.rs.md`
- `rust/crates/cortex-companion/tests/product_gates_v1.rs.md`
- `rust/crates/cortex-companion/tests/rss_measure.rs.md`
- `rust/crates/cortex-companion/tests/screens_snapshot.rs.md`
- `rust/crates/cortex-companion/tests/search_screen.rs.md`

## cortex-actions (14 documentos)

- Estructura: `rust/crates/cortex-actions/00-estructura.md`
- `rust/crates/cortex-actions/Cargo.toml.md`
- `rust/crates/cortex-actions/examples/actions_check.rs.md`
- `rust/crates/cortex-actions/src/catalog.rs.md`
- `rust/crates/cortex-actions/src/context.rs.md`
- `rust/crates/cortex-actions/src/learning.rs.md`
- `rust/crates/cortex-actions/src/lib.rs.md`
- `rust/crates/cortex-actions/src/metrics.rs.md`
- `rust/crates/cortex-actions/src/models.rs.md`
- `rust/crates/cortex-actions/src/registry.rs.md`
- `rust/crates/cortex-actions/src/runner.rs.md`
- `rust/crates/cortex-actions/src/scheduler.rs.md`
- `rust/crates/cortex-actions/src/signals.rs.md`
- `rust/crates/cortex-actions/src/store.rs.md`

## cortex-autopilot (15 documentos)

- Estructura: `rust/crates/cortex-autopilot/00-estructura.md`
- `rust/crates/cortex-autopilot/Cargo.toml.md`
- `rust/crates/cortex-autopilot/examples/cierre_autopilot_check.rs.md`
- `rust/crates/cortex-autopilot/src/config.rs.md`
- `rust/crates/cortex-autopilot/src/detectors/ambiguous.rs.md`
- `rust/crates/cortex-autopilot/src/detectors/default.rs.md`
- `rust/crates/cortex-autopilot/src/detectors/mod.rs.md`
- `rust/crates/cortex-autopilot/src/errors.rs.md`
- `rust/crates/cortex-autopilot/src/lib.rs.md`
- `rust/crates/cortex-autopilot/src/lifecycle.rs.md`
- `rust/crates/cortex-autopilot/src/models.rs.md`
- `rust/crates/cortex-autopilot/src/policies.rs.md`
- `rust/crates/cortex-autopilot/src/service.rs.md`
- `rust/crates/cortex-autopilot/src/session_models.rs.md`
- `rust/crates/cortex-autopilot/tests/decision_layer.rs.md`

## cortex-pipeline (18 documentos)

- Estructura: `rust/crates/cortex-pipeline/00-estructura.md`
- `rust/crates/cortex-pipeline/Cargo.toml.md`
- `rust/crates/cortex-pipeline/examples/documentation_gate.rs.md`
- `rust/crates/cortex-pipeline/examples/pipeline_check.rs.md`
- `rust/crates/cortex-pipeline/src/domain/context.rs.md`
- `rust/crates/cortex-pipeline/src/domain/mod.rs.md`
- `rust/crates/cortex-pipeline/src/domain/types.rs.md`
- `rust/crates/cortex-pipeline/src/lib.rs.md`
- `rust/crates/cortex-pipeline/src/orchestrator.rs.md`
- `rust/crates/cortex-pipeline/src/runners/github.rs.md`
- `rust/crates/cortex-pipeline/src/runners/mod.rs.md`
- `rust/crates/cortex-pipeline/src/stages/documentation.rs.md`
- `rust/crates/cortex-pipeline/src/stages/lint.rs.md`
- `rust/crates/cortex-pipeline/src/stages/mod.rs.md`
- `rust/crates/cortex-pipeline/src/stages/security.rs.md`
- `rust/crates/cortex-pipeline/src/stages/test.rs.md`
- `rust/crates/cortex-pipeline/tests/documentation_stage.rs.md`
- `rust/crates/cortex-pipeline/tests/pipeline_core.rs.md`

## cortex-enterprise (23 documentos)

- Estructura: `rust/crates/cortex-enterprise/00-estructura.md`
- `rust/crates/cortex-enterprise/Cargo.toml.md`
- `rust/crates/cortex-enterprise/examples/enterprise_check.rs.md`
- `rust/crates/cortex-enterprise/src/clock.rs.md`
- `rust/crates/cortex-enterprise/src/config.rs.md`
- `rust/crates/cortex-enterprise/src/error.rs.md`
- `rust/crates/cortex-enterprise/src/frontmatter.rs.md`
- `rust/crates/cortex-enterprise/src/governance.rs.md`
- `rust/crates/cortex-enterprise/src/knowledge_promotion.rs.md`
- `rust/crates/cortex-enterprise/src/lib.rs.md`
- `rust/crates/cortex-enterprise/src/maintenance.rs.md`
- `rust/crates/cortex-enterprise/src/models.rs.md`
- `rust/crates/cortex-enterprise/src/promotion_doctype.rs.md`
- `rust/crates/cortex-enterprise/src/promotion_models.rs.md`
- `rust/crates/cortex-enterprise/src/reporting.rs.md`
- `rust/crates/cortex-enterprise/src/retrieval.rs.md`
- `rust/crates/cortex-enterprise/src/review_knowledge.rs.md`
- `rust/crates/cortex-enterprise/src/sources.rs.md`
- `rust/crates/cortex-enterprise/tests/doctype_review_maintenance.rs.md`
- `rust/crates/cortex-enterprise/tests/knowledge_promotion.rs.md`
- `rust/crates/cortex-enterprise/tests/models_config_governance.rs.md`
- `rust/crates/cortex-enterprise/tests/reporting.rs.md`
- `rust/crates/cortex-enterprise/tests/retrieval.rs.md`

## cortex-doctor (8 documentos)

- Estructura: `rust/crates/cortex-doctor/00-estructura.md`
- `rust/crates/cortex-doctor/Cargo.toml.md`
- `rust/crates/cortex-doctor/examples/doctor_check.rs.md`
- `rust/crates/cortex-doctor/src/checks.rs.md`
- `rust/crates/cortex-doctor/src/doctor.rs.md`
- `rust/crates/cortex-doctor/src/lib.rs.md`
- `rust/crates/cortex-doctor/src/native.rs.md`
- `rust/crates/cortex-doctor/tests/doctor_core.rs.md`

## cortex-tutor (16 documentos)

- Estructura: `rust/crates/cortex-tutor/00-estructura.md`
- `rust/crates/cortex-tutor/Cargo.toml.md`
- `rust/crates/cortex-tutor/content/menu.txt.md`
- `rust/crates/cortex-tutor/content/topic_commands.txt.md`
- `rust/crates/cortex-tutor/content/topic_enterprise.txt.md`
- `rust/crates/cortex-tutor/content/topic_ide.txt.md`
- `rust/crates/cortex-tutor/content/topic_pipeline.txt.md`
- `rust/crates/cortex-tutor/content/topic_start.txt.md`
- `rust/crates/cortex-tutor/content/topic_vault.txt.md`
- `rust/crates/cortex-tutor/content/topic_workflow.txt.md`
- `rust/crates/cortex-tutor/examples/tutor_check.rs.md`
- `rust/crates/cortex-tutor/src/engine.rs.md`
- `rust/crates/cortex-tutor/src/hint.rs.md`
- `rust/crates/cortex-tutor/src/lib.rs.md`
- `rust/crates/cortex-tutor/src/topics.rs.md`
- `rust/crates/cortex-tutor/tests/tutor_core.rs.md`

## cortex-webgraph-server (16 documentos)

- Estructura: `rust/crates/cortex-webgraph-server/00-estructura.md`
- `rust/crates/cortex-webgraph-server/Cargo.toml.md`
- `rust/crates/cortex-webgraph-server/examples/webgraph_check.rs.md`
- `rust/crates/cortex-webgraph-server/src/cache.rs.md`
- `rust/crates/cortex-webgraph-server/src/config.rs.md`
- `rust/crates/cortex-webgraph-server/src/contracts.rs.md`
- `rust/crates/cortex-webgraph-server/src/federation.rs.md`
- `rust/crates/cortex-webgraph-server/src/graph_builder.rs.md`
- `rust/crates/cortex-webgraph-server/src/lib.rs.md`
- `rust/crates/cortex-webgraph-server/src/openers.rs.md`
- `rust/crates/cortex-webgraph-server/src/pyjson.rs.md`
- `rust/crates/cortex-webgraph-server/src/relation_builder.rs.md`
- `rust/crates/cortex-webgraph-server/src/server.rs.md`
- `rust/crates/cortex-webgraph-server/src/service.rs.md`
- `rust/crates/cortex-webgraph-server/src/sources.rs.md`
- `rust/crates/cortex-webgraph-server/src/style.rs.md`

## Total documentos en estos crates: 238


## Relación general (deps Cargo observadas)


```
cortex-branding ──► cortex-brain ──► cortex-brain-app ──► apps/brain-ui
                 └──────────────► cortex-companion
cortex-actions ──► cortex-cli / companion / tui
cortex-app ──► actions, autopilot, doctor, pipeline, webgraph-server, companion
cortex-enterprise ──► doctor, autopilot, actions(knowledge.promote), brain-app(org)
cortex-workspace ──► autopilot, enterprise, companion, webgraph, tutor, doctor
cortex-core ──► webgraph-server (vecinos semánticos)
```


## Prioridad de lectura para entender la versión actual

1. `cortex-brain` (router, tools, llama, download) + `cortex-brain-app` (Tauri/IPC/engine)

2. `cortex-actions` catálogo + `cortex-companion` engine/approval/herdr

3. `cortex-webgraph-server`, `cortex-enterprise`, `cortex-autopilot`

4. `cortex-tui` / `cortex-branding` (superficie CLI visual)
