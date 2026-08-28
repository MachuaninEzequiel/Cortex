//! Puerto del `Reconstructor` de 8 pasos (`cortex/documenter/reconstruction.py`).
//!
//! P5a: gitless mode. P5b: git-aware mode (diff real + name-status +
//! provenance union vía subprocess git, timeout 10s como Python).

pub mod diff_parser;
pub mod handoff;
pub mod interactive;
pub mod persister;
pub mod spec_loader;

use std::path::{Path, PathBuf};

use serde::Serialize;

use crate::git;
use crate::session::{
    Checkpoint, CheckpointPhase, SessionRecord, SessionStatus, VerificationHookResult,
};
use diff_parser::{DiffAction, DiffEntry};
use handoff::AgentHandoff;
use spec_loader::{AdrSuggestion, LoadedSpec};

const CORTEX_INTERNAL_PATHS: [&str; 1] = [".cortex/session.lock"];

#[derive(Debug, Clone, Serialize)]
pub struct ReconstructionOutput {
    pub session_id: String,
    pub handoff: AgentHandoff,
    pub spec_path_normalized: String,
    pub spec_title: String,
    pub spec_goal: String,
    pub files_in_scope_spec: Vec<String>,
    pub acceptance_criteria: Vec<String>,
    pub status_session: String,
    pub diff_text: String,
    pub diff_entries: Vec<DiffEntrySer>,
    /// Rutas posix EN ORDEN (el orden es parte de la paridad).
    pub files_touched: Vec<String>,
    pub in_scope_files: Vec<String>,
    pub out_of_scope_files: Vec<String>,
    pub unimplemented_files: Vec<String>,
    pub verification_results: Vec<VerificationHookResult>,
    pub suggested_status: String,
    pub suggested_adrs: Vec<AdrSuggestion>,
    pub end_commit: String,
    pub gitless: bool,
    pub files_verified_by_git: Vec<String>,
    pub files_declared_only: Vec<String>,
    /// Notas no-vacías de los checkpoints (para key_decisions del persister).
    #[serde(skip)]
    pub checkpoint_notes: Vec<String>,
    /// Línea de fases COMPOSED (None ⇒ sesión sin fases; no serializado).
    #[serde(skip)]
    pub phase_line: Option<String>,
    /// Evidencia por fase (vacío ⇒ sin fases; no serializado).
    #[serde(skip)]
    pub evidence_by_phase: Vec<(CheckpointPhase, Vec<String>)>,
    /// Warning de fase close faltante (None ⇒ sin warning; no serializado).
    #[serde(skip)]
    pub close_phase_warning: Option<String>,
}

#[derive(Debug, Clone, PartialEq, Serialize)]
pub struct DiffEntrySer {
    pub action: String,
    pub path: String,
    pub old_path: Option<String>,
}

fn is_cortex_internal_path(p: &Path) -> bool {
    let posix = p.to_string_lossy().replace('\\', "/");
    CORTEX_INTERNAL_PATHS.contains(&posix.as_str())
}

/// Línea de fases COMPOSED: `"grill → spec → plan → implement → review"`;
/// `None` si ningún checkpoint tiene `phase`.
///
/// Orden = orden de aparición en los checkpoints; duplicados colapsados
/// preservando la primera aparición (la línea refleja el flujo que el dev
/// compuso, no el conteo de checkpoints por fase).
pub fn phase_line(checkpoints: &[Checkpoint]) -> Option<String> {
    let mut seen: Vec<CheckpointPhase> = Vec::new();
    for cp in checkpoints {
        if let Some(p) = cp.phase {
            if !seen.contains(&p) {
                seen.push(p);
            }
        }
    }
    if seen.is_empty() {
        return None;
    }
    Some(
        seen.iter()
            .map(|p| p.as_str())
            .collect::<Vec<_>>()
            .join(" → "),
    )
}

/// Claims verificadas agrupadas por fase, en orden de aparición de las
/// fases; SOLO fases con al menos una claim (evidencia = claims, no fases).
/// Checkpoints sin `phase` se ignoran (emisores legados).
pub fn evidence_by_phase(checkpoints: &[Checkpoint]) -> Vec<(CheckpointPhase, Vec<String>)> {
    let mut order: Vec<CheckpointPhase> = Vec::new();
    let mut claims: Vec<Vec<String>> = Vec::new();
    for cp in checkpoints {
        let p = match cp.phase {
            Some(p) => p,
            None => continue,
        };
        let idx = match order.iter().position(|&x| x == p) {
            Some(i) => i,
            None => {
                order.push(p);
                claims.push(Vec::new());
                order.len() - 1
            }
        };
        claims[idx].extend(cp.verified_claims.iter().cloned());
    }
    order
        .into_iter()
        .zip(claims)
        .filter(|(_, c)| !c.is_empty())
        .collect()
}

fn files_touched_from_checkpoints(checkpoints: &[Checkpoint]) -> Vec<PathBuf> {
    let mut seen: std::collections::HashSet<String> = std::collections::HashSet::new();
    let mut ordered = Vec::new();
    for cp in checkpoints {
        for raw in &cp.artifacts_touched {
            let key = raw.replace('\\', "/");
            if seen.insert(key) {
                ordered.push(PathBuf::from(raw));
            }
        }
    }
    ordered
}

pub fn scope_cross_check(
    files_touched: &[PathBuf],
    files_in_scope: &[String],
) -> (Vec<PathBuf>, Vec<PathBuf>, Vec<PathBuf>) {
    let scope_set: std::collections::BTreeSet<String> = files_in_scope
        .iter()
        .map(|p| p.replace('\\', "/"))
        .collect();
    let touched_set: std::collections::BTreeSet<String> = files_touched
        .iter()
        .map(|p| p.to_string_lossy().replace('\\', "/"))
        .collect();

    let in_scope = files_touched
        .iter()
        .filter(|p| scope_set.contains(&p.to_string_lossy().replace('\\', "/")))
        .cloned()
        .collect();
    let out_of_scope = files_touched
        .iter()
        .filter(|p| !scope_set.contains(&p.to_string_lossy().replace('\\', "/")))
        .cloned()
        .collect();
    let unimplemented = files_in_scope
        .iter()
        .filter(|p| !touched_set.contains(&p.replace('\\', "/")))
        .map(PathBuf::from)
        .collect();
    (in_scope, out_of_scope, unimplemented)
}

/// CLOSED si todos los hooks pasan Y no hay unimplemented Y el cierre de fase
/// close está OK (no exigida o presente); si no HANDOFF.
pub fn decide_status(
    verification_results: &[VerificationHookResult],
    unimplemented: &[PathBuf],
    require_close_phase: bool,
    has_close_phase: bool,
) -> SessionStatus {
    let required_passed = verification_results.iter().all(|r| r.passed);
    let close_ok = !require_close_phase || has_close_phase;
    if required_passed && unimplemented.is_empty() && close_ok {
        SessionStatus::Closed
    } else {
        SessionStatus::Handoff
    }
}

/// Warning soft de fase close faltante (spec 13 §1.3): se registra cuando la
/// sesión es COMPOSED sin phase=close, o cuando la spec la exige y falta.
/// Bloquear (HANDOFF) es decisión de `decide_status`; acá solo el aviso.
pub fn close_phase_warning(
    has_close_phase: bool,
    phase_present: bool,
    require_close_phase: bool,
) -> Option<String> {
    if has_close_phase {
        return None;
    }
    if !phase_present && !require_close_phase {
        return None;
    }
    Some(format!(
        "Session closed without a phase=close checkpoint (require_close_phase: {require_close_phase})"
    ))
}

fn diff_action_to_handoff(action: &DiffAction) -> &'static str {
    match action {
        DiffAction::Added => "created",
        DiffAction::Deleted => "deleted",
        DiffAction::Renamed => "renamed",
        DiffAction::Copied => "created",
        DiffAction::Modified => "modified",
    }
}

#[allow(clippy::too_many_arguments)]
fn build_handoff(
    spec: &LoadedSpec,
    diff_entries: &[DiffEntry],
    verification_results: &[VerificationHookResult],
    checkpoints: &[Checkpoint],
    in_scope: &[PathBuf],
    out_of_scope: &[PathBuf],
    unimplemented: &[PathBuf],
    suggested_adrs: &[AdrSuggestion],
    suggested_status: SessionStatus,
) -> AgentHandoff {
    let mut verified_claims: Vec<String> = Vec::new();
    if !in_scope.is_empty() {
        verified_claims.push(format!(
            "Modified {} file(s) inside spec scope",
            in_scope.len()
        ));
    }
    for r in verification_results {
        if r.passed {
            verified_claims.push(format!("verification hook '{}' passed", r.name));
        }
    }

    let mut unverified_claims: Vec<String> = Vec::new();
    for r in verification_results {
        if !r.passed {
            unverified_claims.push(format!(
                "verification hook '{}' did not pass (exit={})",
                r.name, r.exit_code
            ));
        }
    }
    for ac in &spec.acceptance_criteria {
        unverified_claims.push(format!("acceptance criterion: {ac}"));
    }

    let artifacts = diff_entries
        .iter()
        .map(|e| handoff::ArtifactProduced {
            path: e.path.to_string_lossy().replace('\\', "/"),
            action: diff_action_to_handoff(&e.action).into(),
            lines_changed: 0,
            lines_added: 0,
        })
        .collect();

    let mut context_for_next: Vec<String> = checkpoints
        .iter()
        .filter(|c| !c.note.is_empty())
        .map(|c| c.note.clone())
        .collect();
    if !out_of_scope.is_empty() {
        context_for_next.push(format!(
            "Scope drift: {}",
            out_of_scope
                .iter()
                .map(|p| p.to_string_lossy().replace('\\', "/"))
                .collect::<Vec<_>>()
                .join(", ")
        ));
    }
    if !unimplemented.is_empty() {
        context_for_next.push(format!(
            "Unimplemented files in scope: {}",
            unimplemented
                .iter()
                .map(|p| p.to_string_lossy().replace('\\', "/"))
                .collect::<Vec<_>>()
                .join(", ")
        ));
    }

    let handoff_status = match suggested_status {
        SessionStatus::Closed => "complete",
        SessionStatus::Handoff => "partial",
        _ => "blocked",
    };

    AgentHandoff {
        agent: "cortex-documenter".into(),
        status: handoff_status.into(),
        verified_claims,
        unverified_claims,
        artifacts_produced: artifacts,
        context_for_next,
        suggested_adr: !suggested_adrs.is_empty(),
        suggested_adr_reason: suggested_adrs
            .iter()
            .map(|s| s.title.clone())
            .collect::<Vec<_>>()
            .join("; "),
        suggested_context_terms: vec![],
    }
}

#[allow(clippy::too_many_arguments)]
fn finish_output(
    session: &SessionRecord,
    spec: &LoadedSpec,
    verification_results: Vec<VerificationHookResult>,
    diff_text: String,
    diff_entries: Vec<DiffEntry>,
    end_commit: String,
    gitless: bool,
    files_verified_by_git: Vec<PathBuf>,
    files_declared_only: Vec<PathBuf>,
    files_touched: Vec<PathBuf>,
    checkpoints: Vec<Checkpoint>,
) -> ReconstructionOutput {
    let filter_internal = |v: Vec<PathBuf>| -> Vec<PathBuf> {
        v.into_iter()
            .filter(|p| !is_cortex_internal_path(p))
            .collect()
    };
    let files_verified_by_git = filter_internal(files_verified_by_git);
    let files_declared_only = filter_internal(files_declared_only);
    let files_touched = filter_internal(files_touched);

    let phase_line = phase_line(&checkpoints);
    let evidence_by_phase = evidence_by_phase(&checkpoints);
    let has_close_phase = checkpoints
        .iter()
        .any(|c| c.phase == Some(CheckpointPhase::Close));
    let close_phase_warning = close_phase_warning(
        has_close_phase,
        phase_line.is_some(),
        spec.require_close_phase,
    );

    let (in_scope, out_of_scope, unimplemented) =
        scope_cross_check(&files_touched, &spec.files_in_scope);

    let suggested_adrs = spec_loader::suggest_adrs(&checkpoints);
    let suggested_status = decide_status(
        &verification_results,
        &unimplemented,
        spec.require_close_phase,
        has_close_phase,
    );
    let handoff = build_handoff(
        spec,
        &diff_entries,
        &verification_results,
        &checkpoints,
        &in_scope,
        &out_of_scope,
        &unimplemented,
        &suggested_adrs,
        suggested_status,
    );

    let ser_entries = |es: &[DiffEntry]| -> Vec<DiffEntrySer> {
        es.iter()
            .map(|e| DiffEntrySer {
                action: diff_action_to_handoff(&e.action).into(),
                path: e.path.to_string_lossy().replace('\\', "/"),
                old_path: e
                    .old_path
                    .as_ref()
                    .map(|o| o.to_string_lossy().replace('\\', "/")),
            })
            .collect()
    };
    let posix_list = |v: &[PathBuf]| -> Vec<String> {
        v.iter()
            .map(|p| p.to_string_lossy().replace('\\', "/"))
            .collect()
    };

    ReconstructionOutput {
        session_id: session.session_id.clone(),
        handoff,
        spec_path_normalized: "{{ROOT}}/".to_string()
            + &session
                .spec_path
                .rsplit_once("/specs/")
                .map(|(_, rest)| format!("specs/{rest}"))
                .unwrap_or_else(|| session.spec_path.clone()),
        spec_title: spec.title.clone(),
        spec_goal: spec.goal.clone(),
        files_in_scope_spec: spec.files_in_scope.clone(),
        acceptance_criteria: spec.acceptance_criteria.clone(),
        status_session: session.status.as_str().into(),
        diff_text,
        diff_entries: ser_entries(&diff_entries),
        files_touched: posix_list(&files_touched),
        in_scope_files: posix_list(&in_scope),
        out_of_scope_files: posix_list(&out_of_scope),
        unimplemented_files: posix_list(&unimplemented),
        verification_results,
        suggested_status: suggested_status.as_str().into(),
        suggested_adrs,
        end_commit,
        gitless,
        files_verified_by_git: posix_list(&files_verified_by_git),
        files_declared_only: posix_list(&files_declared_only),
        checkpoint_notes: checkpoints
            .iter()
            .filter(|c| !c.note.is_empty())
            .map(|c| c.note.clone())
            .collect(),
        phase_line,
        evidence_by_phase,
        close_phase_warning,
    }
}

/// P5a: reconstrucción gitless (diff vacío; touched desde checkpoints).
pub fn reconstruct_gitless(
    session: &SessionRecord,
    spec: &LoadedSpec,
    verification_results: Vec<VerificationHookResult>,
) -> Result<ReconstructionOutput, String> {
    if !session.is_gitless() {
        return Err("reconstruct_gitless exige sesión gitless".into());
    }
    let checkpoints = session.checkpoints.clone();
    let diff_text = String::new();
    let diff_entries: Vec<DiffEntry> = vec![];
    let end_commit = session
        .end_commit
        .clone()
        .unwrap_or_else(|| session.start_commit.clone());
    let files_verified_by_git: Vec<PathBuf> = vec![];
    let files_declared_only = files_touched_from_checkpoints(&checkpoints);
    let files_touched = files_declared_only.clone();

    Ok(finish_output(
        session,
        spec,
        verification_results,
        diff_text,
        diff_entries,
        end_commit,
        true,
        files_verified_by_git,
        files_declared_only,
        files_touched,
        checkpoints,
    ))
}

/// P5b: reconstrucción git-aware — STEP 2 con git real como ground truth.
pub fn reconstruct_git(
    session: &SessionRecord,
    spec: &LoadedSpec,
    repo_root: &Path,
    verification_results: Vec<VerificationHookResult>,
) -> Result<ReconstructionOutput, String> {
    if session.is_gitless() {
        return Err("reconstruct_git exige sesión NO gitless".into());
    }
    let checkpoints = session.checkpoints.clone();

    let end_ref = session.end_commit.clone().unwrap_or_else(|| "HEAD".into());
    let diff_text =
        git::diff(&session.start_commit, &end_ref, repo_root).map_err(|e| format!("diff: {e}"))?;
    let ns_text = git::diff_name_status(&session.start_commit, &end_ref, repo_root)
        .map_err(|e| format!("name-status: {e}"))?;
    let diff_entries = diff_parser::parse_name_status(&ns_text);
    let end_commit = match &session.end_commit {
        Some(c) => c.clone(),
        None => git::get_head_commit(repo_root).map_err(|e| format!("head: {e}"))?,
    };
    let files_verified_by_git: Vec<PathBuf> = diff_entries.iter().map(|e| e.path.clone()).collect();
    let verified_keys: std::collections::BTreeSet<String> = files_verified_by_git
        .iter()
        .map(|p| p.to_string_lossy().replace('\\', "/"))
        .collect();
    let declared_all = files_touched_from_checkpoints(&checkpoints);
    let files_declared_only: Vec<PathBuf> = declared_all
        .iter()
        .filter(|p| !verified_keys.contains(&p.to_string_lossy().replace('\\', "/")))
        .cloned()
        .collect();
    // Unión preservando orden: verificados primero, luego declarados-only.
    let mut files_touched = files_verified_by_git.clone();
    files_touched.extend(files_declared_only.iter().cloned());

    Ok(finish_output(
        session,
        spec,
        verification_results,
        diff_text,
        diff_entries,
        end_commit,
        false,
        files_verified_by_git,
        files_declared_only,
        files_touched,
        checkpoints,
    ))
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::session::CheckpointSource;

    fn cp(phase: Option<CheckpointPhase>, claims: &[&str]) -> Checkpoint {
        Checkpoint {
            timestamp: "2026-08-27T12:00:00Z".into(),
            source: CheckpointSource::UserSkill,
            verified_claims: claims.iter().map(|s| s.to_string()).collect(),
            unverified_claims: vec![],
            artifacts_touched: vec![],
            note: String::new(),
            phase,
        }
    }

    #[test]
    fn phase_line_joins_in_order() {
        let cps = vec![
            cp(Some(CheckpointPhase::Spec), &["a"]),
            cp(Some(CheckpointPhase::Implement), &["b"]),
            cp(Some(CheckpointPhase::Review), &["c"]),
        ];
        assert_eq!(
            phase_line(&cps),
            Some("spec → implement → review".to_string())
        );
        // Sin fases ⇒ None (emisores legados).
        let legacy = vec![cp(None, &["x"]), cp(None, &["y"])];
        assert_eq!(phase_line(&legacy), None);
        // Vacío ⇒ None.
        assert_eq!(phase_line(&[]), None);
    }

    #[test]
    fn phase_line_collapses_duplicates_preserving_first_appearance() {
        let cps = vec![
            cp(Some(CheckpointPhase::Review), &["r1"]),
            cp(Some(CheckpointPhase::Spec), &["s1"]),
            cp(Some(CheckpointPhase::Review), &["r2"]),
        ];
        assert_eq!(phase_line(&cps), Some("review → spec".to_string()));
    }

    #[test]
    fn evidence_grouped_by_phase_in_order() {
        let cps = vec![
            cp(Some(CheckpointPhase::Spec), &["a", "zz"]),
            cp(None, &["ignored claim"]),
            cp(Some(CheckpointPhase::Review), &["b", "c"]),
            cp(Some(CheckpointPhase::Spec), &["w"]),
        ];
        assert_eq!(
            evidence_by_phase(&cps),
            vec![
                (
                    CheckpointPhase::Spec,
                    vec!["a".to_string(), "zz".to_string(), "w".to_string()]
                ),
                (
                    CheckpointPhase::Review,
                    vec!["b".to_string(), "c".to_string()]
                )
            ]
        );
    }

    #[test]
    fn evidence_empty_without_phases() {
        assert!(evidence_by_phase(&[cp(None, &["x"])]).is_empty());
        assert!(evidence_by_phase(&[]).is_empty());
    }

    #[test]
    fn evidence_omits_phases_without_claims() {
        // Fase presente en la línea pero sin claims ⇒ no aparece como evidencia.
        let cps = vec![
            cp(Some(CheckpointPhase::Plan), &[]),
            cp(Some(CheckpointPhase::Implement), &["impl done"]),
        ];
        assert_eq!(
            evidence_by_phase(&cps),
            vec![(CheckpointPhase::Implement, vec!["impl done".to_string()])]
        );
        assert_eq!(phase_line(&cps), Some("plan → implement".to_string()));
    }

    #[test]
    fn decide_status_honors_require_close_phase() {
        let no_hooks: Vec<VerificationHookResult> = vec![];
        let not_implemented: Vec<PathBuf> = vec![];
        // flag=true sin fase close ⇒ HANDOFF (bloquea Closed; spec 13 §1.3).
        assert_eq!(
            decide_status(&no_hooks, &not_implemented, true, false),
            SessionStatus::Handoff
        );
        // flag=true con fase close ⇒ CLOSED (resto en verde).
        assert_eq!(
            decide_status(&no_hooks, &not_implemented, true, true),
            SessionStatus::Closed
        );
        // flag=false sin fase close ⇒ CLOSED (soft; comportamiento actual).
        assert_eq!(
            decide_status(&no_hooks, &not_implemented, false, false),
            SessionStatus::Closed
        );
        // flag=false con fase close ⇒ CLOSED.
        assert_eq!(
            decide_status(&no_hooks, &not_implemented, false, true),
            SessionStatus::Closed
        );
        // Hooks fallidos mandan aunque haya close + flag.
        let failed = vec![VerificationHookResult {
            name: "verif".into(),
            command: "exit 1".into(),
            passed: false,
            exit_code: 1,
            output: String::new(),
            duration_ms: 10,
            run_at: "2026-08-27T12:00:00Z".into(),
        }];
        assert_eq!(
            decide_status(&failed, &not_implemented, true, true),
            SessionStatus::Handoff
        );
    }

    #[test]
    fn close_phase_warning_soft_and_flag_driven() {
        // Sesión legada sin fases y sin flag: sin warning (no es COMPOSED).
        assert_eq!(close_phase_warning(false, false, false), None);
        // COMPOSED sin fase close: warning soft (con o sin flag).
        assert!(close_phase_warning(false, true, false).is_some());
        assert!(close_phase_warning(false, true, true).is_some());
        // Flag exigido sin close aunque no haya otras fases: warning (HANDOFF explicado).
        assert!(close_phase_warning(false, false, true).is_some());
        // Con fase close: nunca warning.
        assert_eq!(close_phase_warning(true, false, true), None);
        assert_eq!(close_phase_warning(true, true, false), None);
    }
}
