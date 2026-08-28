//! Catálogo v1 del ActionEngine (plan §3.3) — puerto de
//! `cortex/action_engine/actions/catalog.py`: 10 acciones sobre servicios.
//!
//! Cada fábrica recibe el `ActionContext` y devuelve la `Action` con
//! precondiciones baratas (on-open), dry-run nativo y delegación en los
//! servicios de Cortex. Report-only ⇒ reversible con undo no-op para
//! satisfacer el contrato sin fingir cambios que no hay.
//!
//! NOTA DE ALCANCE P6: los run() que delegan en servicios todavía no
//! nativos (AgentMemory.sync_vault, DocValidator, inject_all) devuelven
//! fallo explícito; precondiciones y dry-runs son idénticos al oráculo.

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
        ActionResult::fail(
            "setup.finish_bootstrap real requiere SetupOrchestrator nativo (fase P8)",
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
    // Espejo de _report_action: reversible formal + undo no-op + instant +
    // auto-ok. El run ignora dry_run y devuelve la guía (o "sin sesiones").
    report_action(
        "session.close_stale",
        &format!("Cerrar sesiones OPEN de más de {DIAS_STALE} días sin checkpoints"),
        Categoria::Maintenance,
        &format!("muestra guía de finish/abandon para sesiones OPEN >{DIAS_STALE} días"),
        vec![Check::new(
            format!("hay sesiones OPEN >{DIAS_STALE}d sin checkpoints"),
            hay_stale,
        )],
        move |_dry_run| {
            let ids = stale_ids(&run_ctx, DIAS_STALE);
            if ids.is_empty() {
                return ActionResult::new(true, "sin sesiones stale");
            }
            let guia: Vec<String> = ids
                .iter()
                .map(|i| format!("{i} → `cortex autopilot finish --session-id {i}` o abandon"))
                .collect();
            ActionResult::new(
                true,
                format!("Cerrá las sesiones stale: {}", guia.join("; ")),
            )
        },
    )
}

pub fn session_checkpoint_now(ctx: &ActionContext) -> Action {
    fn hay_cambios(ctx: &ActionContext) -> bool {
        if ctx.sesiones_abiertas().is_empty() {
            return false;
        }
        let repo = std::env::current_dir().unwrap_or_else(|_| PathBuf::from("."));
        if !repo.join(".git").exists() {
            return false;
        }
        // git status --porcelain (timeout 5s en Python); vacío ⇒ sin cambios.
        std::process::Command::new("git")
            .args(["status", "--porcelain"])
            .current_dir(&repo)
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
        ActionResult::fail("checkpoint real requiere SessionService nativo (fase de integración)")
    })
    .checked()
}

pub fn vault_reindex(_ctx: &ActionContext) -> Action {
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
    .run_fn(|dry_run| {
        if dry_run {
            return ActionResult::dry("re-indexar el vault (sync_vault)");
        }
        ActionResult::fail("sync_vault real requiere AgentMemory nativo (P12)")
    })
    .checked()
}

pub fn vault_validate_docs(ctx: &ActionContext) -> Action {
    fn contar_md(vault: &Path) -> usize {
        rglob_count(vault)
    }

    let hay_ctx = ctx.clone();
    let hay_docs = move || {
        let vault = hay_ctx.vault_path();
        vault.exists() && contar_md(&vault) > 0
    };

    let run_ctx = ctx.clone();
    report_action(
        "vault.validate_docs",
        "Validar los documentos del vault",
        Categoria::Quality,
        "corre DocValidator sobre hasta 200 .md del vault e informa errores",
        vec![Check::new("hay .md en el vault", hay_docs)],
        move |dry_run| {
            if dry_run {
                let total = contar_md(&run_ctx.vault_path());
                return ActionResult::new(
                    true,
                    format!("[dry-run] validaría ~{} docs", total.min(200)),
                );
            }
            ActionResult::fail("DocValidator nativo aún no existe (cola larga P11)")
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
            // Nota P6: el Python acá compara un ReviewVerdict con "accept"
            // (siempre False) e interpola el repr del objeto — ruta no
            // gateada y ya quirk en el oráculo. El puerto lo declara
            // explícitamente en vez de fingir paridad.
            let _ = run_ctx;
            ActionResult::fail("ruta real no gateada en P6 (verdict requiere LoadedSpec)")
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

    report_action(
        "knowledge.promote",
        "Revisar pendientes de promoción enterprise",
        Categoria::Knowledge,
        "abre el flujo guiado de revisión de knowledge enterprise",
        vec![Check::new("workspace enterprise presente", hay_enterprise)],
        |dry_run| {
            if dry_run {
                ActionResult::new(true, "[dry-run] flujo review-knowledge guiado")
            } else {
                ActionResult::new(true, "usá `cortex promote-knowledge` — flujo interactivo")
            }
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
    report_action(
        "memory.prune",
        "Revisar memorias con feedback negativo",
        Categoria::Quality,
        "lista memorias candidatas a forget según feedback persistido (no borra)",
        vec![Check::new(
            "≥3 feedbacks negativos registrados",
            hay_feedback_negativo,
        )],
        move |_dry_run| {
            let mut conteo = conteo_candidatos(&run_ctx);
            // sorted(conteo, key=conteo.get, reverse=True)[:5] — estable:
            // iguales conteos conservan orden de primera aparición.
            conteo.sort_by_key(|b| std::cmp::Reverse(b.1));
            conteo.truncate(5);
            let candidatos: Vec<String> = conteo.into_iter().map(|(k, _)| k).collect();
            let mut details = BTreeMap::new();
            details.insert(
                "candidatos".to_string(),
                serde_json::to_value(&candidatos).unwrap_or_default(),
            );
            ActionResult::new(
                true,
                format!(
                    "candidatos a olvidar (requiere confirmación aparte): {}",
                    candidatos.join(", ")
                ),
            )
            .with_details(details)
        },
    )
}

pub fn ide_resync(ctx: &ActionContext) -> Action {
    fn hay_workspace_ide(ctx: &ActionContext) -> bool {
        let cortex_dir = ctx.workspace_root.join(".cortex");
        rglob_count_ext(&cortex_dir, "md") > 0 && ctx.dot_cortex().join("workspace.yaml").exists()
    }

    let pre_ctx = ctx.clone();
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
    .run_fn(|dry_run| {
        if dry_run {
            return ActionResult::dry("re-inyectar skills/config en los IDEs configurados");
        }
        ActionResult::fail("inject_all real requiere cortex-setup nativo (P8)")
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

fn rglob_count(dir: &Path) -> usize {
    rglob_count_ext(dir, "md")
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
}
