//! Los 7 detectores built-in de `detectors/default.py`.

use super::AutopilotDetector;
use crate::models::{DetectionRequest, DetectionResult};

pub const CODE_EXTS: &[&str] = &[
    ".py", ".ts", ".js", ".jsx", ".tsx", ".go", ".rs", ".java", ".cpp", ".c", ".h",
];
pub const DOCS_EXTS: &[&str] = &[".md", ".rst", ".txt", ".adoc"];

type R = Result<DetectionResult, cortex_enterprise::error::EnterpriseError>;

pub struct CodeChangeDetector;
impl AutopilotDetector for CodeChangeDetector {
    fn name(&self) -> &'static str {
        "code_change"
    }
    fn detect(&self, request: &DetectionRequest) -> R {
        if !request.changed_files.is_empty() {
            let code_files: Vec<&String> = request
                .changed_files
                .iter()
                .filter(|f| CODE_EXTS.iter().any(|ext| f.ends_with(ext)))
                .collect();
            if !code_files.is_empty() {
                let count = code_files.len();
                return Ok(if count > 3 {
                    DetectionResult {
                        task_type: "deep-code".into(),
                        confidence: 0.6,
                        reason: format!("{count} code files changed"),
                        suggested_complexity: "deep".into(),
                    }
                } else {
                    DetectionResult {
                        task_type: "fast-code".into(),
                        confidence: 0.7,
                        reason: format!("{count} code files changed"),
                        suggested_complexity: "fast".into(),
                    }
                });
            }
        }
        if let Some(req) = &request.user_request {
            let lower = req.to_lowercase();
            const KEYWORDS: &[&str] = &[
                "implement",
                "refactor",
                "add feature",
                "bugfix",
                "fix bug",
                "crear",
                "implementar",
            ];
            if KEYWORDS.iter().any(|kw| lower.contains(kw)) {
                return Ok(DetectionResult {
                    task_type: "fast-code".into(),
                    confidence: 0.5,
                    reason: "Code-related keywords detected in request".into(),
                    suggested_complexity: "fast".into(),
                });
            }
        }
        Ok(DetectionResult::noop("No code changes detected"))
    }
}

pub struct DocsOnlyDetector;
impl AutopilotDetector for DocsOnlyDetector {
    fn name(&self) -> &'static str {
        "docs_only"
    }
    fn detect(&self, request: &DetectionRequest) -> R {
        if !request.changed_files.is_empty() {
            let docs: Vec<&String> = request
                .changed_files
                .iter()
                .filter(|f| DOCS_EXTS.iter().any(|ext| f.ends_with(ext)))
                .collect();
            let non_docs = request.changed_files.len() - docs.len();
            if !docs.is_empty() && non_docs == 0 {
                return Ok(DetectionResult {
                    task_type: "docs-only".into(),
                    confidence: 0.8,
                    reason: format!("Only documentation files changed ({})", docs.len()),
                    suggested_complexity: "none".into(),
                });
            }
        }
        if let Some(req) = &request.user_request {
            let lower = req.to_lowercase();
            const DOC_KW: &[&str] = &[
                "document",
                "docs",
                "readme",
                "changelog",
                "guia",
                "guía",
                "manual",
            ];
            const CODE_KW: &[&str] = &["implement", "fix", "refactor", "bug"];
            if DOC_KW.iter().any(|kw| lower.contains(kw))
                && !CODE_KW.iter().any(|kw| lower.contains(kw))
            {
                return Ok(DetectionResult {
                    task_type: "docs-only".into(),
                    confidence: 0.6,
                    reason: "Documentation keywords detected".into(),
                    suggested_complexity: "none".into(),
                });
            }
        }
        Ok(DetectionResult::noop(
            "No documentation-only changes detected",
        ))
    }
}

pub struct QuestionOnlyDetector;
impl AutopilotDetector for QuestionOnlyDetector {
    fn name(&self) -> &'static str {
        "question_only"
    }
    fn detect(&self, request: &DetectionRequest) -> R {
        if !request.changed_files.is_empty() {
            return Ok(DetectionResult::noop("Files changed — not a pure question"));
        }
        let Some(req) = &request.user_request else {
            return Ok(DetectionResult::noop("No user request to evaluate"));
        };
        let lower = req.to_lowercase().trim().to_string();
        const STARTS: &[&str] = &[
            "what",
            "how",
            "why",
            "when",
            "where",
            "who",
            "which",
            "can you",
            "could you",
            "explain",
            "describe",
        ];
        const MARKERS: &[&str] = &["?", "what is", "how to", "how do", "how does"];
        let is_question = lower.ends_with('?')
            || STARTS.iter().any(|qs| lower.starts_with(qs))
            || MARKERS.iter().any(|qm| lower.contains(qm));
        Ok(if is_question {
            DetectionResult {
                task_type: "question-only".into(),
                confidence: 0.75,
                reason: "Pure question without file changes".into(),
                suggested_complexity: "none".into(),
            }
        } else {
            DetectionResult::noop("Not detected as a question")
        })
    }
}

pub struct SecuritySensitiveDetector;
impl AutopilotDetector for SecuritySensitiveDetector {
    fn name(&self) -> &'static str {
        "security_sensitive"
    }
    fn detect(&self, request: &DetectionRequest) -> R {
        const SECURITY_FILES: &[&str] = &[
            "auth",
            "authentication",
            "authorization",
            "login",
            "logout",
            "password",
            "secret",
            "key",
            "token",
            "jwt",
            "oauth",
            "crypto",
            "encrypt",
            "decrypt",
            "hash",
            "salt",
            "permission",
            "acl",
            "rbac",
            "role",
        ];
        const SECURITY_KEYWORDS: &[&str] = &[
            "password",
            "secret",
            "token",
            "jwt",
            "encrypt",
            "hash",
            "permission",
            "role",
            "security",
            "vulnerability",
            "cve",
            "exploit",
            "csrf",
            "xss",
            "sql injection",
        ];
        const SECONDARY: &[&str] = &["auth", "login", "oauth"];

        for f in &request.changed_files {
            let fl = f.to_lowercase();
            if SECURITY_FILES.iter().any(|kw| fl.contains(kw)) {
                return Ok(DetectionResult {
                    task_type: "security".into(),
                    confidence: 0.8,
                    reason: format!("Security-sensitive file: {f}"),
                    suggested_complexity: "deep".into(),
                });
            }
        }
        if let Some(req) = &request.user_request {
            let lower = req.to_lowercase();
            if SECURITY_KEYWORDS.iter().any(|kw| lower.contains(kw)) {
                return Ok(DetectionResult {
                    task_type: "security".into(),
                    confidence: 0.7,
                    reason: "Security keywords in request".into(),
                    suggested_complexity: "deep".into(),
                });
            }
            if SECONDARY.iter().any(|kw| lower.contains(kw)) {
                return Ok(DetectionResult {
                    task_type: "security".into(),
                    confidence: 0.45,
                    reason: "Secondary security keywords in request".into(),
                    suggested_complexity: "deep".into(),
                });
            }
        }
        Ok(DetectionResult::noop("No security indicators detected"))
    }
}

pub struct LargeRefactorDetector;
impl AutopilotDetector for LargeRefactorDetector {
    fn name(&self) -> &'static str {
        "large_refactor"
    }
    fn detect(&self, request: &DetectionRequest) -> R {
        const DEEP_THRESHOLD: usize = 5;
        const REFACTOR_KW: &[&str] = &[
            "refactor",
            "rewrite",
            "rearchitecture",
            "migrate",
            "upgrade",
            "modernize",
        ];
        if request.changed_files.len() >= DEEP_THRESHOLD {
            return Ok(DetectionResult {
                task_type: "deep-code".into(),
                confidence: 0.65,
                reason: format!(
                    "{} files changed — large scope",
                    request.changed_files.len()
                ),
                suggested_complexity: "deep".into(),
            });
        }
        if let Some(req) = &request.user_request {
            let lower = req.to_lowercase();
            if REFACTOR_KW.iter().any(|kw| lower.contains(kw)) {
                return Ok(DetectionResult {
                    task_type: "deep-code".into(),
                    confidence: 0.55,
                    reason: "Refactor keywords detected".into(),
                    suggested_complexity: "deep".into(),
                });
            }
        }
        Ok(DetectionResult::noop("No large refactor indicators"))
    }
}

pub struct NoopDetector;
impl AutopilotDetector for NoopDetector {
    fn name(&self) -> &'static str {
        "noop"
    }
    fn detect(&self, _request: &DetectionRequest) -> R {
        Ok(DetectionResult::noop("Noop fallback"))
    }
}
