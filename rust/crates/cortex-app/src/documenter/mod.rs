//! Puerto del `Reconstructor` de 8 pasos (`cortex/documenter/reconstruction.py`).
//!
//! P5a cubre: gitless mode completo (diff vacío, files desde checkpoints),
//! scope cross-check, decide_status, build_handoff, suggest_adrs y el filtro
//! de paths internos de Cortex. El modo git-aware entra con P5b
//! (subprocess `git diff` + `--name-status`).

pub mod diff_parser;
pub mod handoff;
pub mod spec_loader;

use std::path::{Path, PathBuf};

use serde::Serialize;

use crate::session::{Checkpoint, SessionRecord, SessionStatus, VerificationHookResult};
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
}

#[derive(Debug, Clone, PartialEq, Serialize)]
pub struct DiffEntrySer {
    pub action: String,
    pub path: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub old_path: Option<String>,
}

fn is_cortex_internal_path(p: &Path) -> bool {
    let posix = p.to_string_lossy().replace('\\', "/");
    CORTEX_INTERNAL_PATHS.contains(&posix.as_str())
}

/// `_files_touched_from_checkpoints`: dedupe POSIX preservando primer orden.
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

/// `(in_scope, out_of_scope, unimplemented)` — orden de entrada preservado.
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

/// CLOSED si todos los hooks requeridos pasan Y no hay unimplemented.
/// Los resultados no llevan flag `required` ⇒ todo se trata como requerido.
pub fn decide_status(
    verification_results: &[VerificationHookResult],
    unimplemented: &[PathBuf],
) -> SessionStatus {
    let required_passed = verification_results.iter().all(|r| r.passed);
    if required_passed && unimplemented.is_empty() {
        SessionStatus::Closed
    } else {
        SessionStatus::Handoff
    }
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

/// Entrada mínima del reconstructor (P5a): sesión ya cargada + spec ya
/// cargada + resultados de hooks inyectables. La resolución fs/git vive en
/// el oráculo Python (paridad por fixture commiteado).
#[allow(clippy::too_many_arguments)]
pub fn reconstruct_gitless(
    session: &SessionRecord,
    spec: &LoadedSpec,
    verification_results: Vec<VerificationHookResult>,
) -> Result<ReconstructionOutput, String> {
    if !session.is_gitless() {
        return Err("reconstruct_gitless exige sesión gitless".into());
    }
    let checkpoints = session.checkpoints.clone();

    // STEP 2 (gitless): diff vacío, touched desde checkpoints.
    let diff_text = String::new();
    let diff_entries: Vec<DiffEntry> = vec![];
    let end_commit = session
        .end_commit
        .clone()
        .unwrap_or_else(|| session.start_commit.clone());
    let files_verified_by_git: Vec<PathBuf> = vec![];
    let files_declared_only = files_touched_from_checkpoints(&checkpoints);
    let files_touched = files_declared_only.clone();

    // Filtro de paths internos.
    let filter_internal = |v: Vec<PathBuf>| -> Vec<PathBuf> {
        v.into_iter()
            .filter(|p| !is_cortex_internal_path(p))
            .collect()
    };
    let files_verified_by_git = filter_internal(files_verified_by_git);
    let files_declared_only = filter_internal(files_declared_only);
    let files_touched = filter_internal(files_touched);

    // STEP 3: los results llegan inyectados (run_hooks lo maneja el caller).
    // STEP 4: cross-check contra la spec.
    let (in_scope, out_of_scope, unimplemented) =
        scope_cross_check(&files_touched, &spec.files_in_scope);

    // STEP 5: contradicciones — NoOp detector por defecto (igual que Python).
    // STEP 5: contradicciones — NoOp detector (default Python).

    // STEP 6/7: ADRs + handoff + status.
    let suggested_adrs = spec_loader::suggest_adrs(&checkpoints);
    let suggested_status = decide_status(&verification_results, &unimplemented);
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

    Ok(ReconstructionOutput {
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
        gitless: true,
        files_verified_by_git: posix_list(&files_verified_by_git),
        files_declared_only: posix_list(&files_declared_only),
    })
}
