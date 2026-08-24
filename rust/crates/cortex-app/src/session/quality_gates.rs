//! Puerto de `cortex/session/quality_gates.py` — review de checkpoints en
//! dos etapas (spec compliance + calidad). Funciones puras, sin I/O.

use serde::Serialize;

pub const PLACEHOLDER_TOKENS: [&str; 3] = ["tbd", "fixme", "???"];
pub const TEST_CLAIM_KEYWORDS: [&str; 5] = ["test", "build", "lint", "check", "ci"];
const MIN_NON_TRIVIAL_CLAIM_LEN: usize = 10;

const PROCESS_ARTIFACT_PREFIXES: [&str; 12] = [
    ".cortex/vault/designs/",
    ".cortex/vault/sessions/",
    ".cortex/vault/handoffs/",
    ".cortex/vault/specs/",
    ".cortex/vault/decisions/",
    ".cortex/vault/postmortems/",
    ".cortex/vault/incidents/",
    ".cortex/vault/changelog/",
    ".cortex/vault/glossary/",
    ".cortex/vault/runbooks/",
    ".cortex/vault/architecture/",
    ".cortex/vault/hu/",
];

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
#[serde(rename_all = "lowercase")]
pub enum ReviewAction {
    Accept,
    Redelegate,
    Warn,
}

#[derive(Debug, Clone, PartialEq, Serialize)]
pub struct ReviewVerdict {
    pub accepted: bool,
    pub stage_1_passed: bool,
    pub stage_2_passed: bool,
    pub reason: String,
    pub action: ReviewAction,
}

/// `_is_process_artifact`: prefijos canónicos `.cortex/vault/<sub>/`.
fn is_process_artifact(path: &str) -> bool {
    let p = path.trim_start_matches("./");
    PROCESS_ARTIFACT_PREFIXES
        .iter()
        .any(|prefix| p.starts_with(prefix))
}

/// Stage 1: artifacts dentro del scope (scope vacío = wildcard) y al menos
/// una señal de progreso.
fn stage_1_spec_compliance(
    checkpoint: &super::Checkpoint,
    files_in_scope: &[String],
) -> (bool, String) {
    let scope: std::collections::BTreeSet<String> =
        files_in_scope.iter().map(|p| path_posix(p)).collect();

    if !scope.is_empty() {
        let out_of_scope: Vec<&str> = checkpoint
            .artifacts_touched
            .iter()
            .map(|s| s.as_str())
            .filter(|p| !scope.contains(&path_posix(p)) && !is_process_artifact(p))
            .collect();
        if !out_of_scope.is_empty() {
            return (
                false,
                format!(
                    "files touched outside spec scope: {}",
                    out_of_scope.join(", ")
                ),
            );
        }
    }

    if checkpoint.verified_claims.is_empty() && checkpoint.artifacts_touched.is_empty() {
        return false_check("checkpoint has neither verified_claims nor artifacts_touched");
    }

    (true, "spec compliance OK".into())
}

fn stage_2_quality(checkpoint: &super::Checkpoint) -> (bool, String) {
    let note_lower = checkpoint.note.to_lowercase();
    let placeholders: Vec<&str> = PLACEHOLDER_TOKENS
        .iter()
        .copied()
        .filter(|t| note_lower.contains(t))
        .collect();
    if !placeholders.is_empty() {
        return (
            false,
            format!("placeholders in note: {}", placeholders.join(", ")),
        );
    }

    let mentions_tests = checkpoint.verified_claims.iter().any(|claim| {
        TEST_CLAIM_KEYWORDS
            .iter()
            .any(|kw| claim.to_lowercase().contains(kw))
    });
    if mentions_tests
        && !checkpoint
            .verified_claims
            .iter()
            .any(|claim| claim.len() > MIN_NON_TRIVIAL_CLAIM_LEN)
    {
        return false_check("test/build claim too short to be auditable evidence");
    }

    (true, "quality OK".into())
}

/// Puerto de `review_checkpoint` — `files_in_scope` es lo único que usa
/// del LoadedSpec Python.
pub fn review_checkpoint(
    checkpoint: &super::Checkpoint,
    files_in_scope: &[String],
) -> ReviewVerdict {
    let (stage_1_ok, stage_1_reason) = stage_1_spec_compliance(checkpoint, files_in_scope);
    if !stage_1_ok {
        return ReviewVerdict {
            accepted: false,
            stage_1_passed: false,
            stage_2_passed: false,
            reason: stage_1_reason,
            action: ReviewAction::Redelegate,
        };
    }

    let (stage_2_ok, stage_2_reason) = stage_2_quality(checkpoint);
    if !stage_2_ok {
        return ReviewVerdict {
            accepted: false,
            stage_1_passed: true,
            stage_2_passed: false,
            reason: stage_2_reason,
            action: ReviewAction::Warn,
        };
    }

    ReviewVerdict {
        accepted: true,
        stage_1_passed: true,
        stage_2_passed: true,
        reason: "checkpoint passed both gates".into(),
        action: ReviewAction::Accept,
    }
}

fn path_posix(p: &str) -> String {
    // Path::as_posix() de Python: separadores normalizados a '/'.
    p.replace('\\', "/")
}

fn false_check(reason: &str) -> (bool, String) {
    (false, reason.to_string())
}
