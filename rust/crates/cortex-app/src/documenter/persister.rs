//! Puerto de `DocumenterPersister._write_session_note` hasta la llamada a
//! `create()` + self-review + resumen de tasks (Obra 07 fase P5c).

use serde::Serialize;

use super::ReconstructionOutput;
use crate::session::{TaskStatus, VerificationHookResult};

pub const PLACEHOLDER_TOKENS: [&str; 7] = [
    "tbd",
    "todo",
    "fixme",
    "xxx",
    "???",
    "fill me",
    "[pendiente]",
];
pub const SUCCESS_CLAIM_PATTERNS: [&str; 9] = [
    "tests pass",
    "test passed",
    "tests passed",
    "build exitoso",
    "build successful",
    "linter clean",
    "lint passed",
    "checks pass",
    "ci passed",
];
pub const SELF_REVIEW_TAG: &str = "auto-draft";

/// Kwargs canónicos de `NoteService.create`.
#[derive(Debug, Clone, PartialEq, Serialize)]
pub struct CreateArgs {
    pub title: String,
    pub spec_summary: String,
    pub changes_made: Vec<String>,
    pub files_touched: Vec<String>,
    pub key_decisions: Vec<String>,
    pub next_steps: Vec<String>,
    pub tags: Vec<String>,
    pub sync_vault: bool,
    pub remember: bool,
    pub handoff: bool,
    pub blockers: Vec<String>,
    pub verified_state: Vec<String>,
    pub unverified_claims: Vec<String>,
    pub suggested_skills: Vec<String>,
    pub task_type: String,
    pub tasks: Vec<TaskOut>,
    pub tasks_total: usize,
    pub tasks_done: usize,
    pub tasks_skipped: usize,
    pub gitless: bool,
}

#[derive(Debug, Clone, PartialEq, Serialize)]
pub struct TaskOut {
    pub id: String,
    pub description: String,
    pub status: String,
}

pub fn summarize_tasks(tasks: &[crate::session::Task]) -> (Vec<TaskOut>, usize, usize, usize) {
    if tasks.is_empty() {
        return (vec![], 0, 0, 0);
    }
    let out = tasks
        .iter()
        .map(|t| TaskOut {
            id: t.id.clone(),
            description: t.description.clone(),
            status: match t.status {
                TaskStatus::Pending => "pending".into(),
                TaskStatus::InProgress => "in-progress".into(),
                TaskStatus::Done => "done".into(),
                TaskStatus::Skipped => "skipped".into(),
                TaskStatus::Blocked => "blocked".into(),
            },
        })
        .collect();
    let done = tasks
        .iter()
        .filter(|t| t.status == TaskStatus::Done)
        .count();
    let skipped = tasks
        .iter()
        .filter(|t| t.status == TaskStatus::Skipped)
        .count();
    (out, tasks.len(), done, skipped)
}

#[allow(clippy::too_many_arguments)]
fn draft_body_for_review(
    spec_summary: &str,
    changes_made: &[String],
    key_decisions: &[String],
    next_steps: &[String],
    blockers: &[String],
    verified_state: &[String],
    unverified_claims: &[String],
) -> String {
    let mut parts: Vec<String> = vec![spec_summary.to_string()];
    parts.extend(changes_made.iter().cloned());
    parts.extend(key_decisions.iter().cloned());
    parts.extend(next_steps.iter().cloned());
    parts.extend(blockers.iter().cloned());
    parts.extend(verified_state.iter().cloned());
    parts.extend(unverified_claims.iter().cloned());
    parts.join("\n")
}

/// Puerto de `_self_review_draft` (3 checks informativos).
pub fn self_review_draft(reconstruction: &ReconstructionOutput, draft_body: &str) -> Vec<String> {
    let mut warnings: Vec<String> = Vec::new();
    let body_lower = draft_body.to_lowercase();

    let mut found: Vec<&str> = PLACEHOLDER_TOKENS
        .iter()
        .copied()
        .filter(|t| body_lower.contains(t))
        .collect();
    found.sort_unstable();
    found.dedup();
    if !found.is_empty() {
        warnings.push(format!("Placeholders detected in draft: {found:?}"));
    }

    let body_paths: std::collections::BTreeSet<String> =
        reconstruction.files_touched.iter().cloned().collect();
    let missing: Vec<String> = body_paths
        .iter()
        .filter(|p| !draft_body.contains(p.as_str()))
        .cloned()
        .collect();
    if !missing.is_empty() {
        warnings.push(format!(
            "Files touched but not mentioned in body: {missing:?}"
        ));
    }

    let has_claim = SUCCESS_CLAIM_PATTERNS
        .iter()
        .any(|c| body_lower.contains(c));
    let has_verified = reconstruction
        .verification_results
        .iter()
        .any(|r: &VerificationHookResult| r.passed);
    if has_claim && !has_verified {
        warnings.push("Success claim in body without any verified hook result".into());
    }
    warnings
}

/// Puerto de `_write_session_note` hasta (sin incluir) la llamada create().
#[must_use]
pub fn build_create_args(reconstruction: &ReconstructionOutput) -> (CreateArgs, Vec<String>) {
    let is_handoff = reconstruction.suggested_status == "handoff";
    let title = if reconstruction.spec_title.is_empty() {
        reconstruction.session_id.clone()
    } else {
        reconstruction.spec_title.clone()
    };
    let spec_summary = if reconstruction.spec_goal.is_empty() {
        reconstruction.spec_title.clone()
    } else {
        reconstruction.spec_goal.clone()
    };

    let changes_made: Vec<String> = reconstruction
        .diff_entries
        .iter()
        .map(|e| format!("{}: {}", e.action, e.path))
        .collect();

    let verified_keys: std::collections::BTreeSet<&String> =
        reconstruction.files_verified_by_git.iter().collect();
    let mut files_touched_marked: Vec<String> = Vec::new();
    for p in &reconstruction.files_touched {
        let marker = if verified_keys.contains(p) {
            "\u{2713}"
        } else {
            "\u{25cc}"
        };
        files_touched_marked.push(format!("{marker} {p}"));
    }
    let declared_only_paths = reconstruction.files_declared_only.clone();
    let key_decisions = reconstruction.checkpoint_notes.clone();

    let mut next_steps: Vec<String> = Vec::new();
    for p in &reconstruction.unimplemented_files {
        next_steps.push(format!("Implement: {p}"));
    }
    if !reconstruction.out_of_scope_files.is_empty() {
        next_steps.push(format!(
            "Decide if scope drift is intentional: {}",
            reconstruction.out_of_scope_files.join(", ")
        ));
    }
    if !declared_only_paths.is_empty() {
        next_steps.push(format!(
            "Commit (or revert) declared-only files: {}",
            declared_only_paths.join(", ")
        ));
    }

    let blockers: Vec<String> = reconstruction
        .verification_results
        .iter()
        .filter(|r| !r.passed)
        .map(|r| format!("{} failed (exit {})", r.name, r.exit_code))
        .collect();

    let mut tags: Vec<String> = vec!["session".into()];
    tags.push(
        if reconstruction.checkpoint_notes.is_empty() {
            "byo"
        } else {
            "with-checkpoints"
        }
        .into(),
    );
    if reconstruction.gitless {
        tags.push("gitless".into());
    }

    let verified_state = reconstruction.handoff.verified_claims.clone();
    let unverified_claims = reconstruction.handoff.unverified_claims.clone();

    let draft_body = draft_body_for_review(
        &spec_summary,
        &changes_made,
        &key_decisions,
        &next_steps,
        &blockers,
        &verified_state,
        &unverified_claims,
    );
    let warnings = self_review_draft(reconstruction, &draft_body);
    if !warnings.is_empty() {
        tags.push(SELF_REVIEW_TAG.into());
        let extra = warnings.iter().map(|w| format!("[self-review] {w}"));
        next_steps.extend(extra);
    }

    (
        CreateArgs {
            title,
            spec_summary,
            changes_made,
            files_touched: files_touched_marked,
            key_decisions,
            next_steps,
            tags,
            sync_vault: false,
            remember: true,
            handoff: is_handoff,
            blockers,
            verified_state,
            unverified_claims,
            suggested_skills: vec![],
            task_type: String::new(),
            tasks: vec![],
            tasks_total: 0,
            tasks_done: 0,
            tasks_skipped: 0,
            gitless: reconstruction.gitless,
        },
        warnings,
    )
}
