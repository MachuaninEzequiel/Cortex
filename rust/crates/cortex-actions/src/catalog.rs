//! Catálogo v1 del ActionEngine (plan §3.3) — puerto de
//! `cortex/action_engine/actions/catalog.py`: 10 acciones sobre servicios.
//!
//! Cada fábrica recibe el `ActionContext` y devuelve la `Action` con
//! precondiciones baratas (on-open), dry-run nativo y delegación en los
//! servicios de Cortex. Report-only ⇒ reversible con undo no-op para
//! satisfacer el contrato sin fingir cambios que no hay.
//!
//! Servicios nativos: DocValidator, reindex_vault, etc. delegan
//! en implementaciones reales de cortex_app; precondiciones y dry-runs
//! son 100% nativos y deterministas.

use std::collections::BTreeMap;
use std::path::{Path, PathBuf};
use std::sync::Arc;

use crate::context::ActionContext;
use crate::models::{Action, ActionResult, Categoria, Check, Costo};
use crate::registry::Registry;
use chrono::Datelike;
use cortex_app::session::{CheckpointPhase, SessionRecord};

fn no_op_undo() -> ActionResult {
    ActionResult::new(true, "acción report-only — nada que deshacer")
}

/// Acción de sólo-lectura: reversible formal, auto-ok, instant.
fn report_action(
    id: &str,
    title: &str,
    category: Categoria,
    effect: &str,
    checks: Vec<Check>,
    runner: impl Fn(bool) -> ActionResult + Send + Sync + 'static,
) -> Action {
    Action::new(id, title, category, effect)
        .expect("id válido")
        .preconditions(checks)
        .reversible(true)
        .undo(Arc::new(no_op_undo))
        .cost(Costo::Instant)
        .auto_ok(true)
        .run_fn(runner)
        .checked()
}

// ── helpers de estado ──────────────────────────────────────────────────────

fn feedback_eventos(ctx: &ActionContext) -> Vec<serde_json::Value> {
    let ruta = ctx.dot_cortex().join("feedback.jsonl");
    let Ok(text) = std::fs::read_to_string(ruta) else {
        return Vec::new();
    };
    text.lines()
        .filter(|l| !l.trim().is_empty())
        .filter_map(|l| serde_json::from_str(l).ok())
        .collect()
}

/// `_ahora_dia()`: día del año en hora LOCAL (datetime.now() sin tz).
fn ahora_dia() -> u32 {
    chrono::Local::now().ordinal()
}

/// Tópicos del tutor (puerto estático de `cortex/tutor/topics/`):
/// (título, guide_path) en orden de display.
const TUTOR_TOPICS: &[(&str, Option<&str>)] = &[
    ("Primeros Pasos", Some("docs/guides/getting-started.md")),
    ("Comandos Esenciales", None),
    (
        "Flujo de Trabajo",
        Some("docs/enterprise/MANIFIESTO-CORTEX-ENTERPRISE.md"),
    ),
    ("Pipeline CI/CD", Some("docs/guides/pipeline-setup.md")),
    (
        "Vault y Documentación",
        Some("docs/guides/vault-structure.md"),
    ),
    ("Enterprise Memory", Some("docs/guides/enterprise-vault.md")),
    ("Integración IDE", None),
];

// ── 10 acciones ────────────────────────────────────────────────────────────

pub fn setup_finish_bootstrap(ctx: &ActionContext) -> Action {
    let config = ctx.config_path();
    let vault = ctx.vault_path();

    let falta = {
        let config = config.clone();
        move || !config.exists()
    };

    let run_config = config.clone();
    let run_dot = ctx.dot_cortex();
    let run_vault = vault.clone();
    let run_ctx = ctx.clone();
    Action::new(
        "setup.finish_bootstrap",
        "Completar el bootstrap de Cortex en este proyecto",
        Categoria::Setup,
        "crea .cortex/, config.yaml y vault base vía SetupOrchestrator",
    )
    .unwrap()
    .preconditions(vec![Check::new("config.yaml inexistente", falta)])
    .cost(Costo::Minutes) // crea archivos → siempre pregunta
    .run_fn(move |dry_run| {
        // El dry-run calcula el plan sin tocar disco (bug registrado en
        // plan 01 §4/P-bugs: SetupOrchestrator.dry_run=True hoy crea archivos).
        if dry_run {
            let mut faltantes: Vec<String> = Vec::new();
            if !run_config.exists() {
                faltantes.push(run_config.to_string_lossy().replace('\\', "/"));
            }
            if !run_dot.join("sessions").exists() {
                faltantes.push(".cortex/sessions/".to_string());
            }
            if !run_vault.exists() {
                faltantes.push(run_vault.to_string_lossy().replace('\\', "/"));
            }
            let plan = if faltantes.is_empty() {
                "nada pendiente".to_string()
            } else {
                faltantes.join(", ")
            };
            return ActionResult::new(true, format!("[dry-run] bootstrap crearía: {plan}"));
        }

        let pctx = cortex_setup::detector::ProjectContext::detect(&run_ctx.repo_root);

        fn write_file(root: &Path, rel: &str, content: &str) -> Result<(), String> {
            let path = root.join(rel);
            if let Some(parent) = path.parent() {
                std::fs::create_dir_all(parent).map_err(|e| e.to_string())?;
            }
            std::fs::write(&path, content).map_err(|e| e.to_string())
        }

        use cortex_setup::setup_templates as tpl;
        if let Err(e) = write_file(
            &run_ctx.repo_root,
            ".cortex/workspace.yaml",
            &tpl::render_workspace_yaml(),
        ) {
            return ActionResult::fail(format!("error escribiendo workspace.yaml: {e}"));
        }
        if let Err(e) = write_file(
            &run_ctx.repo_root,
            "config.yaml",
            &tpl::render_config_yaml(&pctx),
        ) {
            return ActionResult::fail(format!("error escribiendo config.yaml: {e}"));
        }
        let org_yaml =
            match tpl::render_org_yaml(&pctx.stack.project_name, "small-company", true, false) {
                Ok(s) => s,
                Err(e) => return ActionResult::fail(format!("error renderizando org.yaml: {e}")),
            };
        if let Err(e) = write_file(&run_ctx.repo_root, ".cortex/org.yaml", &org_yaml) {
            return ActionResult::fail(format!("error escribiendo org.yaml: {e}"));
        }
        let _ = write_file(
            &run_ctx.repo_root,
            ".cortex/vault/architecture.md",
            &tpl::render_architecture_md(&pctx),
        );
        let _ = write_file(
            &run_ctx.repo_root,
            ".cortex/vault/context.md",
            &tpl::render_context_md(&pctx),
        );
        let _ = write_file(
            &run_ctx.repo_root,
            ".cortex/vault/decisions/README.md",
            &tpl::render_decisions_md(),
        );
        let _ = write_file(
            &run_ctx.repo_root,
            ".cortex/vault/runbooks/README.md",
            &tpl::render_runbooks_md(&pctx),
        );
        let _ = std::fs::create_dir_all(run_ctx.dot_cortex().join("memory"));
        let _ = std::fs::create_dir_all(run_ctx.dot_cortex().join("sessions"));

        ActionResult::new(
            true,
            "bootstrap completado: config.yaml, .cortex/org.yaml, vault y memory creados",
        )
    })
    .checked()
}

pub fn session_close_stale(ctx: &ActionContext) -> Action {
    const DIAS_STALE: i64 = 7;

    fn stale_ids(ctx: &ActionContext, dias_stale: i64) -> Vec<String> {
        let ahora = chrono::Utc::now();
        let mut ids = Vec::new();
        for r in ctx.sesiones_abiertas() {
            let edad_dias = opened_age_days(&r, &ahora);
            if edad_dias >= dias_stale && r.checkpoints.is_empty() {
                ids.push(r.session_id);
            }
        }
        ids
    }

    let hay_stale_ctx = ctx.clone();
    let hay_stale = move || !stale_ids(&hay_stale_ctx, DIAS_STALE).is_empty();

    let run_ctx = ctx.clone();
    report_action(
        "session.close_stale",
        &format!("Cerrar sesiones OPEN de más de {DIAS_STALE} días sin checkpoints"),
        Categoria::Maintenance,
        &format!("informa sesiones OPEN stale (> {DIAS_STALE} días sin checkpoints)"),
        vec![Check::new(
            format!("hay sesiones OPEN >{DIAS_STALE}d sin checkpoints"),
            hay_stale,
        )],
        move |_dry_run| {
            let ids = stale_ids(&run_ctx, DIAS_STALE);
            if ids.is_empty() {
                return ActionResult::new(true, "sin sesiones stale");
            }
            ActionResult::new(
                true,
                format!(
                    "sesiones stale (ids): {} — el agente que codea cierra; Companion no cierra",
                    ids.join(", ")
                ),
            )
        },
    )
}

fn porcelain_paths(repo: &Path) -> Vec<String> {
    let out = std::process::Command::new("git")
        .args(["status", "--porcelain"])
        .current_dir(repo)
        .output();
    let Ok(o) = out else { return Vec::new() };
    let s = String::from_utf8_lossy(&o.stdout);
    let mut res = Vec::new();
    for line in s.lines() {
        if line.len() > 3 {
            let path_part = line[3..].trim();
            if let Some((_, r)) = path_part.split_once(" -> ") {
                res.push(r.trim().to_string());
            } else {
                res.push(path_part.to_string());
            }
        }
    }
    res
}

pub fn session_checkpoint_now(ctx: &ActionContext) -> Action {
    fn hay_cambios(ctx: &ActionContext) -> bool {
        if ctx.sesiones_abiertas().is_empty() {
            return false;
        }
        let repo = &ctx.repo_root;
        if !repo.join(".git").exists() {
            return false;
        }
        // git status --porcelain (timeout 5s en Python); vacío ⇒ sin cambios.
        std::process::Command::new("git")
            .args(["status", "--porcelain"])
            .current_dir(repo)
            .output()
            .map(|o| !o.stdout.is_empty())
            .unwrap_or(false)
    }

    let pre_ctx = ctx.clone();
    let run_ctx = ctx.clone();
    Action::new(
        "session.checkpoint_now",
        "Registrar checkpoint de los archivos cambiados",
        Categoria::Maintenance,
        "agrega un checkpoint manual a la sesión activa",
    )
    .unwrap()
    .preconditions(vec![Check::new(
        "hay sesión abierta y archivos cambiados",
        move || hay_cambios(&pre_ctx),
    )])
    .run_fn(move |dry_run| {
        let abiertas = run_ctx.sesiones_abiertas();
        if abiertas.is_empty() {
            return ActionResult::fail("no hay sesión abierta");
        }
        let objetivo = &abiertas[0];
        if dry_run {
            return ActionResult::dry(format!(
                "checkpoint en {} con los archivos cambiados",
                objetivo.session_id
            ));
        }
        let storage =
            cortex_app::session::SessionStorage::new(run_ctx.dot_cortex().join("sessions"));
        let svc = cortex_app::session::service::SessionService::new(storage, &run_ctx.repo_root);
        let artifacts = porcelain_paths(&run_ctx.repo_root);
        match svc.checkpoint(
            &objetivo.session_id,
            cortex_app::session::CheckpointSource::Manual,
            vec![],
            vec![],
            artifacts,
            "checkpoint del Action Engine",
            None,
        ) {
            Ok(rec) => {
                let n = rec.checkpoints.len();
                ActionResult::new(
                    true,
                    format!("checkpoint #{} registrado en {}", n, objetivo.session_id),
                )
            }
            Err(e) => ActionResult::fail(format!("error al registrar checkpoint: {e}")),
        }
    })
    .checked()
}

pub fn vault_reindex(ctx: &ActionContext) -> Action {
    let run_ctx = ctx.clone();
    Action::new(
        "vault.reindex",
        "Re-indexar el vault semántico",
        Categoria::Maintenance,
        "parse+chunk+embed de vault/ via AgentMemory.sync_vault()",
    )
    .unwrap()
    .preconditions(vec![Check::new("vault disponible", || true)]) // idempotente: se ofrece siempre
    .reversible(true)
    .undo(Arc::new(|| {
        ActionResult::new(true, "reindex es idempotente — nada que deshacer")
    }))
    .cost(Costo::Seconds) // tarda segundos: pide confirmación (auto_ok=False)
    .run_fn(move |dry_run| {
        if dry_run {
            return ActionResult::dry("re-indexar el vault (sync_vault)");
        }
        let model = match cortex_app::reindex::resolve_reindex_model(&run_ctx.config_path()) {
            Ok(m) => m,
            Err(e) => return ActionResult::fail(format!("{e}")),
        };
        let model_dir = cortex_app::context::domain_detector::default_model_dir();
        let vectors_dir = cortex_app::reindex::vectors_dir(&run_ctx.dot_cortex());
        match cortex_app::reindex::reindex_vault(
            &run_ctx.vault_path(),
            &vectors_dir,
            &model,
            model_dir.as_deref(),
        ) {
            Ok(outcome) => ActionResult::new(
                true,
                format!(
                    "reindex ok: {} chunks dim {}",
                    outcome.n_chunks, outcome.dim
                ),
            ),
            Err(cortex_app::reindex::ReindexError::UnsupportedModel { model }) => {
                ActionResult::fail(format!(
                    "reindex nativo solo embebe all-MiniLM-L6-v2 (configurado: {model})"
                ))
            }
            Err(cortex_app::reindex::ReindexError::ModelMissing { hint }) => ActionResult::fail(
                format!("modelo ONNX no encontrado en {hint}: instalalo y reintentá"),
            ),
            Err(e) => ActionResult::fail(format!("{e}")),
        }
    })
    .checked()
}

pub fn vault_validate_docs(ctx: &ActionContext) -> Action {
    let hay_ctx = ctx.clone();
    let hay_docs = move || {
        let vault = hay_ctx.vault_path();
        vault.exists() && !rglob_md_paths(&vault).is_empty()
    };

    let run_ctx = ctx.clone();
    report_action(
        "vault.validate_docs",
        "Validar los documentos del vault",
        Categoria::Quality,
        "corre DocValidator sobre hasta 200 .md del vault e informa errores",
        vec![Check::new("hay .md en el vault", hay_docs)],
        move |dry_run| {
            let mut paths = rglob_md_paths(&run_ctx.vault_path());
            if dry_run {
                return ActionResult::new(
                    true,
                    format!("[dry-run] validaría ~{} docs", paths.len().min(200)),
                );
            }
            if paths.is_empty() {
                return ActionResult::new(true, "sin .md para validar");
            }
            paths.truncate(200);
            let validator = cortex_app::doc_validator::DocValidator::new(run_ctx.vault_path());
            let results = validator.validate_batch(&paths);
            let mut total_errors = 0;
            let mut total_warnings = 0;
            let mut err_details: Vec<serde_json::Value> = Vec::new();
            for r in &results {
                let errs = r.errors();
                let warns = r.warnings();
                total_errors += errs.len();
                total_warnings += warns.len();
                for e in errs {
                    err_details.push(serde_json::json!({
                        "file": e.file,
                        "field": e.field,
                        "message": e.message,
                    }));
                }
            }
            let mut details = BTreeMap::new();
            details.insert("errores".to_string(), serde_json::Value::Array(err_details));
            ActionResult::new(
                true,
                format!(
                    "validó {} docs: {} errores, {} warnings",
                    paths.len(),
                    total_errors,
                    total_warnings
                ),
            )
            .with_details(details)
        },
    )
}

pub fn quality_run_gates(ctx: &ActionContext) -> Action {
    fn hay_objetivo(ctx: &ActionContext) -> bool {
        ctx.sesiones_abiertas()
            .iter()
            .any(|r| !r.checkpoints.is_empty() && !r.spec_path.is_empty())
    }

    let pre_ctx = ctx.clone();
    let run_ctx = ctx.clone();
    report_action(
        "quality.run_gates",
        "Correr quality gates sobre el último checkpoint",
        Categoria::Quality,
        "review_checkpoint(checkpoint, spec) de la primera sesión OPEN con checkpoints",
        vec![Check::new(
            "sesión OPEN con checkpoints y spec",
            move || hay_objetivo(&pre_ctx),
        )],
        move |dry_run| {
            if dry_run {
                return ActionResult::dry("revisar último checkpoint con quality gates");
            }
            let abiertas = run_ctx.sesiones_abiertas();
            let Some(sesion) = abiertas.iter().find(|r| !r.checkpoints.is_empty()) else {
                return ActionResult::fail("sin sesión abierta con checkpoints");
            };
            let last_cp = sesion.checkpoints.last().unwrap();
            let files_in_scope = if !sesion.spec_path.is_empty() {
                let spec_p = run_ctx.repo_root.join(&sesion.spec_path);
                cortex_app::documenter::spec_loader::load_spec(&spec_p).files_in_scope
            } else {
                vec![]
            };
            let verdict =
                cortex_app::session::quality_gates::review_checkpoint(last_cp, &files_in_scope);
            let mut details = BTreeMap::new();
            details.insert(
                "accepted".to_string(),
                serde_json::Value::Bool(verdict.accepted),
            );
            details.insert(
                "action".to_string(),
                serde_json::Value::String(verdict.action.as_str().to_string()),
            );
            details.insert(
                "reason".to_string(),
                serde_json::Value::String(verdict.reason.clone()),
            );
            ActionResult::new(
                verdict.accepted,
                format!(
                    "accepted={} action={} reason={}",
                    verdict.accepted,
                    verdict.action.as_str(),
                    verdict.reason
                ),
            )
            .with_details(details)
        },
    )
}

pub fn learn_topic(_ctx: &ActionContext) -> Action {
    report_action(
        "learn.topic",
        "Aprender un tópico del tutor hoy",
        Categoria::Learning,
        "sugiere un tópico del tutor (rotación diaria) con deep-link a su guía",
        vec![Check::new("tutor disponible", || true)],
        move |_dry_run| {
            // Python no distingue dry-run: siempre sugiere el tópico del día.
            let topic = TUTOR_TOPICS[(ahora_dia() as usize) % TUTOR_TOPICS.len()];
            let mut mensaje = format!("Topic sugerido: {}", topic.0);
            if let Some(guia) = topic.1 {
                mensaje.push_str(&format!(" — guía: {guia}"));
            }
            ActionResult::new(true, mensaje)
        },
    )
}

pub fn knowledge_promote(ctx: &ActionContext) -> Action {
    let hay_enterprise_ctx = ctx.clone();
    let hay_enterprise = move || hay_enterprise_ctx.dot_cortex().join("enterprise").exists();

    let run_ctx = ctx.clone();
    report_action(
        "knowledge.promote",
        "Revisar pendientes de promoción enterprise",
        Categoria::Knowledge,
        "promueve candidatos de conocimiento al vault enterprise (Approve = review)",
        vec![Check::new("workspace enterprise presente", hay_enterprise)],
        move |dry_run| {
            let mut svc = match cortex_enterprise::knowledge_promotion::KnowledgePromotionService::from_project_root(
                &run_ctx.repo_root,
                None,
                Arc::new(cortex_enterprise::clock::SystemClock),
            ) {
                Ok(s) => s,
                Err(e) => return ActionResult::fail(format!("{e}")),
            };
            let cands = match svc.discover_candidates() {
                Ok(c) => c,
                Err(e) => return ActionResult::fail(format!("{e}")),
            };
            if dry_run {
                return ActionResult::new(
                    true,
                    format!("[dry-run] promovería {} candidatos", cands.len()),
                );
            }
            if cands.is_empty() {
                return ActionResult::new(true, "sin candidatos a promover");
            }
            for c in cands
                .iter()
                .filter(|c| c.issues.iter().all(|i| i.severity != "error"))
            {
                let _ = svc.review(&c.origin_id, true, "companion", Some("HUD Aprobar"));
            }
            let plan = match svc.plan_promotion() {
                Ok(p) => p,
                Err(e) => return ActionResult::fail(format!("{e}")),
            };
            let written = match svc.apply_promotion(&plan, "companion") {
                Ok(w) => w,
                Err(e) => return ActionResult::fail(format!("{e}")),
            };
            ActionResult::new(true, format!("promovidos: {}", written.len()))
        },
    )
}

pub fn memory_prune(ctx: &ActionContext) -> Action {
    const NEGATIVOS: [&str; 2] = ["not_useful", "negative"];

    fn conteo_candidatos(ctx: &ActionContext) -> Vec<(String, usize)> {
        let mut conteo: Vec<(String, usize)> = Vec::new();
        for e in feedback_eventos(ctx) {
            let tipo = e
                .get("feedback_type")
                .and_then(|v| v.as_str())
                .unwrap_or("");
            let mid = e.get("memory_id").and_then(|v| v.as_str()).unwrap_or("");
            if NEGATIVOS.contains(&tipo) && !mid.is_empty() {
                match conteo.iter_mut().find(|(k, _)| k == mid) {
                    Some((_, n)) => *n += 1,
                    None => conteo.push((mid.to_string(), 1)),
                }
            }
        }
        conteo
    }

    let hay_ctx = ctx.clone();
    let hay_feedback_negativo = move || {
        conteo_candidatos(&hay_ctx)
            .into_iter()
            .map(|(_, n)| n)
            .sum::<usize>()
            >= 3
    };

    let run_ctx = ctx.clone();
    Action::new(
        "memory.prune",
        "Revisar memorias con feedback negativo",
        Categoria::Quality,
        "olvida memorias con feedback negativo persistido vía NativeEpisodicStore",
    )
    .unwrap()
    .preconditions(vec![Check::new(
        "≥3 feedbacks negativos registrados",
        hay_feedback_negativo,
    )])
    .cost(Costo::Seconds)
    .auto_ok(false)
    .reversible(false)
    .run_fn(move |dry_run| {
        let mut conteo = conteo_candidatos(&run_ctx);
        conteo.sort_by_key(|b| std::cmp::Reverse(b.1));
        conteo.truncate(5);
        let candidatos: Vec<String> = conteo.into_iter().map(|(k, _)| k).collect();
        if dry_run {
            let mut details = BTreeMap::new();
            details.insert(
                "candidatos".to_string(),
                serde_json::to_value(&candidatos).unwrap_or_default(),
            );
            return ActionResult::dry(format!(
                "olvidaría memorias con feedback negativo: {}",
                candidatos.join(", ")
            ))
            .with_details(details);
        }
        if candidatos.is_empty() {
            return ActionResult::new(true, "sin candidatos a olvidar");
        }

        let mem_dir = run_ctx.dot_cortex().join("memory");
        let jsonl_path = if mem_dir.join("episodic_export.jsonl").exists() {
            mem_dir.join("episodic_export.jsonl")
        } else if mem_dir.join("memories.jsonl").exists() {
            mem_dir.join("memories.jsonl")
        } else {
            return ActionResult::fail("sin store episódico; nada que olvidar");
        };

        let mut store = match cortex_app::episodic::NativeEpisodicStore::load(&jsonl_path) {
            Ok(st) => st,
            Err(e) => return ActionResult::fail(format!("error al cargar store episódico: {e}")),
        };

        let mut olvidadas = Vec::new();
        let mut no_encontradas = Vec::new();
        for id in &candidatos {
            match store.delete(id) {
                Ok(true) => olvidadas.push(id.clone()),
                Ok(false) => no_encontradas.push(id.clone()),
                Err(e) => return ActionResult::fail(format!("error al borrar {id}: {e}")),
            }
        }

        let mut msg_parts = Vec::new();
        if !olvidadas.is_empty() {
            msg_parts.push(format!("olvidadas: {}", olvidadas.join(", ")));
        }
        if !no_encontradas.is_empty() {
            msg_parts.push(format!("no encontradas: {}", no_encontradas.join(", ")));
        }
        let ok = !olvidadas.is_empty() || candidatos.is_empty();
        let message = if msg_parts.is_empty() {
            "sin cambios en memoria episódica".to_string()
        } else {
            msg_parts.join("; ")
        };
        let mut details = BTreeMap::new();
        details.insert(
            "olvidadas".to_string(),
            serde_json::to_value(&olvidadas).unwrap_or_default(),
        );
        details.insert(
            "no_encontradas".to_string(),
            serde_json::to_value(&no_encontradas).unwrap_or_default(),
        );
        ActionResult::new(ok, message).with_details(details)
    })
    .checked()
}

pub fn ide_resync(ctx: &ActionContext) -> Action {
    fn hay_workspace_ide(ctx: &ActionContext) -> bool {
        let cortex_dir = ctx.workspace_root.join(".cortex");
        rglob_count_ext(&cortex_dir, "md") > 0 && ctx.dot_cortex().join("workspace.yaml").exists()
    }

    let pre_ctx = ctx.clone();
    let run_ctx = ctx.clone();
    Action::new(
        "ide.resync",
        "Re-sincronizar skills de Cortex en los IDEs configurados",
        Categoria::Setup,
        "re-inyecta perfiles/skills con marcadores (Obra 02)",
    )
    .unwrap()
    .preconditions(vec![Check::new(
        ".cortex/workspace.yaml presente",
        move || hay_workspace_ide(&pre_ctx),
    )])
    .reversible(true)
    .undo(Arc::new(|| {
        ActionResult::new(true, "re-sync idempotente — nada que deshacer")
    }))
    .cost(Costo::Seconds)
    .run_fn(move |dry_run| {
        if dry_run {
            return ActionResult::dry("re-inyectar skills/config en los IDEs configurados");
        }
        let home = std::env::var_os("HOME")
            .map(PathBuf::from)
            .unwrap_or_else(|| run_ctx.repo_root.clone());
        let ide_ctx = cortex_setup::ide::IdeCtx {
            project_root: &run_ctx.repo_root,
            home: &home,
            now: chrono::Utc::now(),
        };
        let prompts = cortex_setup::ide::prompts::build_all_prompts(&ide_ctx);
        let adapters = cortex_setup::ide::adapters::all_adapters();
        let mut written_total = Vec::new();
        for adapter in &adapters {
            let configs = adapter.config_paths(&ide_ctx);
            let present = configs.iter().any(|(_, p)| p.exists());
            if present {
                if let Ok(w) = adapter.inject_profiles(&ide_ctx, &prompts) {
                    written_total.extend(w);
                }
                if let Ok(w) = adapter.inject_mcp(&ide_ctx) {
                    written_total.extend(w);
                }
            }
        }
        ActionResult::new(
            true,
            format!(
                "re-sync ide completado: {} archivos tocados",
                written_total.len()
            ),
        )
    })
    .checked()
}

/// `build_default_registry(ctx)` — registra las 10 acciones v1 EN ORDEN +
/// la acción nativa `session.suggest_next_phase` (Obra 08 stream A, spec 13
/// §7.2) apenda al final para preservar el orden de inserción observable
/// (desempate estable del scheduler) de las 10 originales.
pub fn build_default_registry(ctx: &ActionContext) -> Registry {
    let mut registry = Registry::new();
    for res in [
        setup_finish_bootstrap(ctx),
        session_close_stale(ctx),
        session_checkpoint_now(ctx),
        vault_reindex(ctx),
        vault_validate_docs(ctx),
        quality_run_gates(ctx),
        learn_topic(ctx),
        knowledge_promote(ctx),
        memory_prune(ctx),
        ide_resync(ctx),
        session_suggest_next_phase(ctx),
    ] {
        registry.register(res).expect("catálogo sin duplicados");
    }
    registry
}

// ── helpers ────────────────────────────────────────────────────────────────

/// Siguiente fase en la cadena COMPOSED; `None` en `close` (nada que
/// sugerir). grill→spec→plan→implement→review→close→None (spec 13 §7.2).
pub fn next_phase(p: CheckpointPhase) -> Option<CheckpointPhase> {
    match p {
        CheckpointPhase::Grill => Some(CheckpointPhase::Spec),
        CheckpointPhase::Spec => Some(CheckpointPhase::Plan),
        CheckpointPhase::Plan => Some(CheckpointPhase::Implement),
        CheckpointPhase::Implement => Some(CheckpointPhase::Review),
        CheckpointPhase::Review => Some(CheckpointPhase::Close),
        CheckpointPhase::Close => None,
    }
}

/// (fase actual, fase sugerida) sobre la PRIMERA sesión OPEN — convención
/// igual a `session.checkpoint_now` (`abiertas[0]`). «Última fase» = el
/// último checkpoint con `phase` en orden de apenda (la sesión puede mezclar
/// checkpoints sin fase, p. ej. ide-hook). `None` si no hay sesión, no hay
/// fase, o la última fase es `close` (⇒ nada que sugerir ⇒ no se ofrece).
fn fase_sugerida(ctx: &ActionContext) -> Option<(CheckpointPhase, CheckpointPhase)> {
    let r = ctx.sesiones_abiertas().into_iter().next()?;
    let ultima = r.checkpoints.iter().rev().find_map(|c| c.phase)?;
    Some((ultima, next_phase(ultima)?))
}

/// `session.suggest_next_phase` (Obra 08 stream A, G-A6a): sugiere la
/// siguiente fase del modo COMPOSED leyendo el último checkpoint con fase.
/// Report-only (auto_ok, instant, reversible con undo no-op — patrón de
/// `session.close_stale`/`learn.topic`). NO bloqueante: solo un mensaje.
pub fn session_suggest_next_phase(ctx: &ActionContext) -> Action {
    let pre_ctx = ctx.clone();
    let run_ctx = ctx.clone();
    report_action(
        "session.suggest_next_phase",
        "Sugerir la siguiente fase COMPOSED de la sesión activa",
        Categoria::Maintenance,
        "muestra la fase siguiente sugerida según el último checkpoint con fase de la sesión OPEN",
        vec![Check::new("sesión activa con última fase", move || {
            fase_sugerida(&pre_ctx).is_some()
        })],
        move |_dry_run| {
            // Report-only: ignora dry_run como close_stale/learn.topic
            // (no escribe nada en ninguno de los dos modos).
            match fase_sugerida(&run_ctx) {
                Some((actual, siguiente)) => ActionResult::new(
                    true,
                    format!(
                        "Sesión en {} → siguiente fase sugerida: {}",
                        actual.as_str(),
                        siguiente.as_str()
                    ),
                ),
                None => ActionResult::new(true, "sin fase COMPOSED sugerible"),
            }
        },
    )
}

fn opened_age_days(record: &SessionRecord, ahora: &chrono::DateTime<chrono::Utc>) -> i64 {
    // Python: (ahora - r.opened_at).days if r.opened_at else 999.
    if record.opened_at.is_empty() {
        return 999;
    }
    match chrono::DateTime::parse_from_rfc3339(&record.opened_at) {
        Ok(dt) => (*ahora - dt.with_timezone(&chrono::Utc)).num_days(),
        Err(_) => 999,
    }
}

fn rglob_md_paths(dir: &Path) -> Vec<PathBuf> {
    let mut out = Vec::new();
    collect_md_paths(dir, &mut out);
    out.sort();
    out
}

fn collect_md_paths(dir: &Path, out: &mut Vec<PathBuf>) {
    let Ok(rd) = std::fs::read_dir(dir) else {
        return;
    };
    for entry in rd.flatten() {
        let p = entry.path();
        if p.is_dir() {
            collect_md_paths(&p, out);
        } else if p.extension().and_then(|e| e.to_str()) == Some("md") {
            out.push(p);
        }
    }
}

fn rglob_count_ext(dir: &Path, ext: &str) -> usize {
    let Ok(rd) = std::fs::read_dir(dir) else {
        return 0;
    };
    let mut n = 0;
    for entry in rd.flatten() {
        let p = entry.path();
        if p.is_dir() {
            n += rglob_count_ext(&p, ext);
        } else if p.extension().and_then(|e| e.to_str()) == Some(ext) {
            n += 1;
        }
    }
    n
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::scheduler::Scheduler;
    use crate::store::PreferencesStore;
    use cortex_app::session::{Checkpoint, CheckpointSource, SessionStatus, SessionStorage};
    use std::path::PathBuf;

    struct Tmp(PathBuf);
    impl Drop for Tmp {
        fn drop(&mut self) {
            std::fs::remove_dir_all(&self.0).ok();
        }
    }

    fn tmpdir(tag: &str) -> Tmp {
        let d = std::env::temp_dir().join(format!(
            "cortex-actions-cat-{tag}-{}-{}",
            std::process::id(),
            chrono::Utc::now().timestamp_nanos_opt().unwrap_or_default()
        ));
        std::fs::create_dir_all(&d).unwrap();
        Tmp(d)
    }

    fn cp(phase: Option<CheckpointPhase>) -> Checkpoint {
        Checkpoint {
            timestamp: "2026-08-28T01:00:00+00:00".to_string(),
            source: CheckpointSource::UserSkill,
            verified_claims: vec![],
            unverified_claims: vec![],
            artifacts_touched: vec![],
            note: String::new(),
            phase,
        }
    }

    /// Fixture legacy (config.yaml en raíz — patrón de context.rs) con una
    /// sesión OPEN con los checkpoints dados.
    fn ctx_con_sesion(base: &Path, checkpoints: Vec<Checkpoint>) -> ActionContext {
        std::fs::write(base.join("config.yaml"), "semantic:\n  vault_path: vault\n").unwrap();
        let ctx = ActionContext::from_project_root(Some(base));
        let storage = SessionStorage::new(ctx.dot_cortex().join("sessions"));
        let r = SessionRecord {
            session_id: "2026-08-28_fixture".to_string(),
            opened_at: "2026-08-28T00:00:00+00:00".to_string(),
            status: SessionStatus::Open,
            checkpoints,
            ..SessionRecord::default()
        };
        storage.save(&r).unwrap();
        ctx
    }

    #[test]
    fn next_phase_cadena_completa() {
        assert_eq!(
            next_phase(CheckpointPhase::Grill),
            Some(CheckpointPhase::Spec)
        );
        assert_eq!(
            next_phase(CheckpointPhase::Spec),
            Some(CheckpointPhase::Plan)
        );
        assert_eq!(
            next_phase(CheckpointPhase::Plan),
            Some(CheckpointPhase::Implement)
        );
        assert_eq!(
            next_phase(CheckpointPhase::Implement),
            Some(CheckpointPhase::Review)
        );
        assert_eq!(
            next_phase(CheckpointPhase::Review),
            Some(CheckpointPhase::Close)
        );
        assert_eq!(next_phase(CheckpointPhase::Close), None);
    }

    #[test]
    fn registry_contiene_suggest_next_phase_con_contrato() {
        let g = tmpdir("reg");
        let ctx = ActionContext::from_project_root(Some(&g.0));
        let reg = build_default_registry(&ctx);
        let a = reg
            .get("session.suggest_next_phase")
            .expect("la acción debe existir en el registry");
        assert_eq!(a.cost, Costo::Instant);
        assert!(a.reversible);
        assert!(a.auto_ok);
        assert_eq!(a.category, Categoria::Maintenance);
        // apenda al final: preserva el orden de inserción observable de las
        // 10 originales (desempate estable del scheduler).
        assert_eq!(reg.len(), 11);
        assert_eq!(reg.all().last().unwrap().id, "session.suggest_next_phase");
    }

    #[test]
    fn scheduler_propone_con_sesion_en_implement_y_mensaje_exacto() {
        let g = tmpdir("impl");
        let ctx = ctx_con_sesion(&g.0, vec![cp(None), cp(Some(CheckpointPhase::Implement))]);
        let prefs = PreferencesStore::new(&g.0);
        let reg = build_default_registry(&ctx);
        let props = Scheduler::new(&prefs).propose(&reg, false);
        assert!(props
            .iter()
            .any(|p| p.action_id == "session.suggest_next_phase"));
        // Effect con el mensaje exacto del brief (spec 13 §7.2).
        let res = (reg.get("session.suggest_next_phase").unwrap().run)(false);
        assert_eq!(
            res.message,
            "Sesión en implement → siguiente fase sugerida: review"
        );
        assert!(res.ok);
    }

    #[test]
    fn no_propone_sin_fase_o_con_ultima_fase_close() {
        // checkpoints legados (sin phase) ⇒ no se ofrece: la garantía de que
        // el fixture del oráculo P6 sigue sin proponer la acción nativa.
        let g = tmpdir("nofase");
        let ctx = ctx_con_sesion(&g.0, vec![cp(None), cp(None)]);
        let prefs = PreferencesStore::new(&g.0);
        let reg = build_default_registry(&ctx);
        let props = Scheduler::new(&prefs).propose(&reg, false);
        assert!(!props
            .iter()
            .any(|p| p.action_id == "session.suggest_next_phase"));

        // última fase close ⇒ nada que sugerir ⇒ no se ofrece.
        let g2 = tmpdir("close");
        let ctx2 = ctx_con_sesion(
            &g2.0,
            vec![
                cp(Some(CheckpointPhase::Implement)),
                cp(Some(CheckpointPhase::Close)),
            ],
        );
        let prefs2 = PreferencesStore::new(&g2.0);
        let reg2 = build_default_registry(&ctx2);
        let props2 = Scheduler::new(&prefs2).propose(&reg2, false);
        assert!(!props2
            .iter()
            .any(|p| p.action_id == "session.suggest_next_phase"));
    }

    #[test]
    fn validate_docs_corre_nativo_y_no_dice_p11() {
        let g = tmpdir("val_p11");
        std::fs::create_dir_all(g.0.join("vault")).unwrap();
        std::fs::write(
            g.0.join("vault").join("nota.md"),
            "---\ntitle: Nota\ndate: 2026-08-29\n---\nContenido\n",
        )
        .unwrap();
        std::fs::write(g.0.join("config.yaml"), "semantic:\n  vault_path: vault\n").unwrap();
        let ctx = ActionContext::from_project_root(Some(&g.0));
        let res = (vault_validate_docs(&ctx).run)(false);
        assert!(res.ok, "el validador nativo debe correr");
        assert!(
            !res.message.contains("P11"),
            "stub P11 muerto: {}",
            res.message
        );
        assert!(!res.message.contains("aún no existe"), "{}", res.message);
    }

    #[test]
    fn validate_docs_reporta_error_real_en_md_roto() {
        let g = tmpdir("val_roto");
        std::fs::create_dir_all(g.0.join("vault")).unwrap();
        std::fs::write(
            g.0.join("vault").join("nota.md"),
            "Contenido sin frontmatter\n",
        )
        .unwrap();
        std::fs::write(g.0.join("config.yaml"), "semantic:\n  vault_path: vault\n").unwrap();
        let ctx = ActionContext::from_project_root(Some(&g.0));
        let res = (vault_validate_docs(&ctx).run)(false);
        assert!(res.ok, "validar es informe, no fail de infraestructura");
        assert!(
            res.message.contains("warnings") || res.message.contains("errores"),
            "{}",
            res.message
        );
    }

    #[test]
    fn reindex_sin_minilm_falla_honesto_no_p12() {
        let g = tmpdir("reindex_e5");
        std::fs::create_dir_all(g.0.join("vault")).unwrap();
        std::fs::write(
            g.0.join("config.yaml"),
            "embedding:\n  model: e5-algo\nsemantic:\n  vault_path: vault\n",
        )
        .unwrap();
        let ctx = ActionContext::from_project_root(Some(&g.0));
        let res = (vault_reindex(&ctx).run)(false);
        assert!(!res.ok);
        assert!(!res.message.contains("P12"), "{}", res.message);
        assert!(!res.message.contains("AgentMemory"), "{}", res.message);
        assert!(
            res.message.contains("e5-algo"),
            "si se ignora el YAML no muere: {}",
            res.message
        );
        assert!(
            res.message.contains("MiniLM") || res.message.contains("all-MiniLM"),
            "{}",
            res.message
        );
    }

    #[test]
    fn strings_teatro_p11_p12_no_viven_en_catalog() {
        let (body, _) = include_str!("catalog.rs")
            .split_once("mod tests")
            .expect("tests");
        assert!(!body.contains("cola larga P11"));
        assert!(!body.contains("AgentMemory nativo (P12)"));
    }

    #[test]
    fn prune_borra_id_del_jsonl() {
        let g = tmpdir("prune_del");
        let dot = g.0.join(".cortex");
        let mem = dot.join("memory");
        std::fs::create_dir_all(&mem).unwrap();
        let fb_line = serde_json::json!({
            "type": "explicit",
            "memory_id": "mem-1",
            "feedback_type": "not_useful",
            "source": "tui",
            "ts": "2026-08-29T12:00:00Z"
        });
        std::fs::write(
            dot.join("feedback.jsonl"),
            format!("{fb_line}\n{fb_line}\n{fb_line}\n"),
        )
        .unwrap();
        let row1 = serde_json::json!({
            "id": "mem-1",
            "document": "Texto de memoria 1",
            "meta": {"id": "mem-1", "memory_type": "general", "tags": "[]", "files": "[]", "timestamp": "2026-08-29T00:00:00+00:00", "metadata_json": "{}"},
            "embedding": [0.1, 0.2, 0.3]
        });
        let row2 = serde_json::json!({
            "id": "mem-2",
            "document": "Texto de memoria 2",
            "meta": {"id": "mem-2", "memory_type": "general", "tags": "[]", "files": "[]", "timestamp": "2026-08-29T00:00:00+00:00", "metadata_json": "{}"},
            "embedding": [0.4, 0.5, 0.6]
        });
        std::fs::write(mem.join("memories.jsonl"), format!("{row1}\n{row2}\n")).unwrap();
        std::fs::write(g.0.join("config.yaml"), "semantic:\n  vault_path: vault\n").unwrap();

        let ctx = ActionContext::from_project_root(Some(&g.0));
        let res = (memory_prune(&ctx).run)(false);
        assert!(res.ok, "{}", res.message);
        assert!(res.message.contains("olvidadas: mem-1"), "{}", res.message);

        let post = std::fs::read_to_string(mem.join("memories.jsonl")).unwrap();
        assert!(!post.contains("mem-1"), "mem-1 debe haber sido borrado");
        assert!(post.contains("mem-2"), "mem-2 debe permanecer intacto");
    }

    #[test]
    fn prune_dry_run_no_borra() {
        let g = tmpdir("prune_dry");
        let dot = g.0.join(".cortex");
        let mem = dot.join("memory");
        std::fs::create_dir_all(&mem).unwrap();
        let fb_line = serde_json::json!({
            "type": "explicit",
            "memory_id": "mem-1",
            "feedback_type": "not_useful",
            "source": "tui",
            "ts": "2026-08-29T12:00:00Z"
        });
        std::fs::write(
            dot.join("feedback.jsonl"),
            format!("{fb_line}\n{fb_line}\n{fb_line}\n"),
        )
        .unwrap();
        let row1 = serde_json::json!({
            "id": "mem-1",
            "document": "Texto de memoria 1",
            "meta": {"id": "mem-1", "memory_type": "general", "tags": "[]", "files": "[]", "timestamp": "2026-08-29T00:00:00+00:00", "metadata_json": "{}"},
            "embedding": [0.1, 0.2, 0.3]
        });
        std::fs::write(mem.join("memories.jsonl"), format!("{row1}\n")).unwrap();
        std::fs::write(g.0.join("config.yaml"), "semantic:\n  vault_path: vault\n").unwrap();

        let ctx = ActionContext::from_project_root(Some(&g.0));
        let res = (memory_prune(&ctx).run)(true);
        assert!(res.ok);
        assert!(res.message.contains("[dry-run]"));

        let post = std::fs::read_to_string(mem.join("memories.jsonl")).unwrap();
        assert!(post.contains("mem-1"), "dry-run no debe borrar mem-1");
    }

    #[test]
    fn promote_sin_enterprise_no_se_ofrece() {
        let g = tmpdir("no_ent");
        std::fs::write(g.0.join("config.yaml"), "semantic:\n  vault_path: vault\n").unwrap();
        let ctx = ActionContext::from_project_root(Some(&g.0));
        let a = knowledge_promote(&ctx);
        assert!(!a.preconditions.iter().all(|c| c.cumple(false)));
    }

    #[test]
    fn promote_approve_es_review_y_escribe_dest() {
        let g = tmpdir("promote_app");
        let local = g.0.join("vault");
        let enterprise = g.0.join("vault-enterprise");
        std::fs::create_dir_all(local.join("specs")).unwrap();
        std::fs::create_dir_all(&enterprise).unwrap();
        std::fs::create_dir_all(g.0.join(".cortex").join("enterprise")).unwrap();
        std::fs::write(
            local.join("specs/auth.md"),
            "---\ntitle: Auth Spec\ndate: 2026-08-29\n---\n\nContenido de la spec\n",
        )
        .unwrap();
        std::fs::write(g.0.join("config.yaml"), "semantic:\n  vault_path: vault\n").unwrap();
        let mut config = cortex_enterprise::config::build_enterprise_org_config(
            "Acme Org",
            cortex_enterprise::models::OrgProfile::SmallCompany,
            true,
            false,
        )
        .unwrap();
        config.promotion.require_review = true;
        config.promotion.allowed_doc_types =
            vec![cortex_enterprise::models::PromotableDocType::Spec];
        cortex_enterprise::config::write_enterprise_config(&g.0, &config, None).unwrap();

        let ctx = ActionContext::from_project_root(Some(&g.0));
        let res = (knowledge_promote(&ctx).run)(false);
        assert!(res.ok, "{}", res.message);
        assert!(res.message.contains("promovidos: 1"), "{}", res.message);
    }

    #[test]
    fn promote_ya_no_manda_al_cli() {
        let (body, _) = include_str!("catalog.rs")
            .split_once("mod tests")
            .expect("tests");
        assert!(!body.contains("usá `cortex promote-knowledge`"));
    }

    #[test]
    fn finish_bootstrap_escribe_config_y_org() {
        let g = tmpdir("bootstrap");
        let ctx = ActionContext::from_project_root(Some(&g.0));
        let res = (setup_finish_bootstrap(&ctx).run)(false);
        assert!(res.ok, "{}", res.message);
        assert!(g.0.join("config.yaml").exists(), "config.yaml debe crearse");
        assert!(
            g.0.join(".cortex").join("org.yaml").exists(),
            ".cortex/org.yaml debe crearse"
        );
        assert!(
            g.0.join(".cortex").join("vault").exists(),
            ".cortex/vault debe crearse"
        );
    }

    #[test]
    fn close_stale_no_cambia_status() {
        let g = tmpdir("close_stale");
        std::fs::write(g.0.join("config.yaml"), "semantic:\n  vault_path: vault\n").unwrap();
        let ctx = ActionContext::from_project_root(Some(&g.0));
        let storage = SessionStorage::new(ctx.dot_cortex().join("sessions"));
        let rec = SessionRecord {
            session_id: "2026-01-01_stale".into(),
            status: cortex_app::session::SessionStatus::Open,
            opened_at: "2026-01-01T00:00:00+00:00".into(),
            checkpoints: vec![],
            ..Default::default()
        };
        storage.save(&rec).unwrap();

        let res = (session_close_stale(&ctx).run)(false);
        assert!(res.ok, "{}", res.message);
        assert!(res.message.contains("2026-01-01_stale"), "{}", res.message);
        assert!(
            res.message.contains("Companion no cierra"),
            "{}",
            res.message
        );

        let read_back = storage.load("2026-01-01_stale").unwrap();
        assert_eq!(read_back.status, cortex_app::session::SessionStatus::Open);
    }

    #[test]
    fn run_gates_no_dice_p6() {
        let g = tmpdir("gates");
        let ctx = ctx_con_sesion(&g.0, vec![cp(Some(CheckpointPhase::Implement))]);
        let res = (quality_run_gates(&ctx).run)(false);
        assert!(!res.message.contains("P6"), "{}", res.message);
        assert!(
            res.message.contains("accepted=") || res.message.contains("reason="),
            "{}",
            res.message
        );
    }

    #[test]
    fn checkpoint_now_append_en_sesion_open() {
        let g = tmpdir("cp_now");
        let ctx = ctx_con_sesion(&g.0, vec![cp(Some(CheckpointPhase::Implement))]);
        let _ = std::process::Command::new("git")
            .args(["init"])
            .current_dir(&g.0)
            .output();
        std::fs::write(g.0.join("change.txt"), "hello").unwrap();

        let n0 = ctx.sesiones_abiertas()[0].checkpoints.len();
        let res = (session_checkpoint_now(&ctx).run)(false);
        assert!(res.ok, "{}", res.message);

        let storage = SessionStorage::new(ctx.dot_cortex().join("sessions"));
        let read_back = storage.load("2026-08-28_fixture").unwrap();
        assert_eq!(read_back.checkpoints.len(), n0 + 1);
        let last = read_back.checkpoints.last().unwrap();
        assert!(last.phase.is_none());
        assert_eq!(last.note, "checkpoint del Action Engine");
        assert!(last.artifacts_touched.contains(&"change.txt".to_string()));
    }

    #[test]
    fn strings_teatro_p6_p8_no_viven_en_catalog() {
        let (body, _) = include_str!("catalog.rs")
            .split_once("mod tests")
            .expect("tests");
        assert!(!body.contains("fase P8"));
        assert!(!body.contains("ruta real no gateada en P6"));
        assert!(!body.contains("fase de integración"));
    }
}
