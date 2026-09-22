//! Catálogo de questions. Defaults embebidos; override opcional en workspace.

use std::collections::BTreeMap;
use std::path::Path;

use serde::Deserialize;
use serde_json::{json, Map, Value};

const EMBEDDED: &str = include_str!("../questions/default.yaml");

#[derive(Debug, Clone)]
pub struct Catalog {
    pub model: String,
    pub compass_confidence_below: f64,
    pub drop_below: f64,
    pub overfetch: usize,
    pub stage2_keep: usize,
    pub prompt_keep: usize,
    pub candidate_chars: usize,
    pub families: BTreeMap<String, String>,
    pub compass_question: String,
    pub compass_focus: String,
    pub noul_true: String,
    pub noul_false: String,
}

#[derive(Debug, Deserialize)]
struct Raw {
    #[serde(default)]
    model: Option<String>,
    #[serde(default)]
    thresholds: RawThresholds,
    #[serde(default)]
    families: BTreeMap<String, String>,
    #[serde(default)]
    compass: RawCompass,
    #[serde(default)]
    noul: RawNoul,
}

#[derive(Debug, Default, Deserialize)]
struct RawThresholds {
    #[serde(default)]
    compass_confidence_below: Option<f64>,
    #[serde(default)]
    drop_below: Option<f64>,
    #[serde(default)]
    overfetch: Option<usize>,
    #[serde(default)]
    stage2_keep: Option<usize>,
    #[serde(default)]
    prompt_keep: Option<usize>,
    #[serde(default)]
    candidate_chars: Option<usize>,
}

#[derive(Debug, Default, Deserialize)]
struct RawCompass {
    #[serde(default)]
    instructions: RawCompassInstructions,
}

#[derive(Debug, Default, Deserialize)]
struct RawCompassInstructions {
    #[serde(default)]
    question: Option<String>,
    #[serde(default)]
    focus: Option<String>,
}

#[derive(Debug, Default, Deserialize)]
struct RawNoul {
    #[serde(default)]
    criteria: RawNoulCriteria,
}

#[derive(Debug, Default, Deserialize)]
struct RawNoulCriteria {
    #[serde(default, rename = "true")]
    true_c: Option<String>,
    #[serde(default, rename = "false")]
    false_c: Option<String>,
}

impl Catalog {
    pub fn embedded() -> Result<Self, String> {
        Self::from_yaml(EMBEDDED)
    }

    /// Override de workspace si el archivo existe y parsea; si no, embebido.
    /// YAML corrupto ⇒ Err (el caller no prende el client).
    pub fn load(override_path: Option<&Path>) -> Result<Self, String> {
        if let Some(path) = override_path {
            if path.exists() {
                let text =
                    std::fs::read_to_string(path).map_err(|e| format!("questions.yaml: {e}"))?;
                return Self::from_yaml(&text);
            }
        }
        Self::embedded()
    }

    pub fn from_yaml(text: &str) -> Result<Self, String> {
        let raw: Raw = serde_yaml::from_str(text).map_err(|e| format!("questions.yaml: {e}"))?;
        let families = if raw.families.is_empty() {
            default_families()
        } else {
            raw.families
        };
        Ok(Self {
            model: raw.model.unwrap_or_else(|| "jev-1.13.0".into()),
            compass_confidence_below: raw.thresholds.compass_confidence_below.unwrap_or(0.50),
            drop_below: raw.thresholds.drop_below.unwrap_or(0.25),
            overfetch: raw.thresholds.overfetch.unwrap_or(30),
            stage2_keep: raw.thresholds.stage2_keep.unwrap_or(12),
            prompt_keep: raw.thresholds.prompt_keep.unwrap_or(8),
            candidate_chars: raw.thresholds.candidate_chars.unwrap_or(800),
            compass_question: raw
                .compass
                .instructions
                .question
                .unwrap_or_else(|| "Which Cortex subsystem is this query primarily about?".into()),
            compass_focus: raw.compass.instructions.focus.unwrap_or_else(|| {
                "The mechanism the user wants explained, not a UI that happens to mention it."
                    .into()
            }),
            noul_true: raw
                .noul
                .criteria
                .true_c
                .unwrap_or_else(|| "Explains the module or contract the query asks for.".into()),
            noul_false: raw.noul.criteria.false_c.unwrap_or_else(|| {
                "Keyword overlap, chrome, tests, or a neighboring subsystem.".into()
            }),
            families,
        })
    }

    pub fn compass_questions(&self) -> Value {
        json!({
            "family": {
                "type": "choice",
                "instructions": {
                    "question": self.compass_question,
                    "focus": self.compass_focus,
                },
                "criteria": self.families,
            }
        })
    }

    /// Instructions/criteria literales de squeeze.py `noul_batch`.
    pub fn noul_question(&self, query: &str, family: &str, cid: &str, use_body: bool) -> Value {
        let inspect = if use_body {
            "`title` + `text`"
        } else {
            "`title` + `path`"
        };
        json!({
            "type": "noul",
            "instructions": format!(
                "Query: {query}\nLikely subsystem: {family}.\nDoes candidates item `{cid}` ({inspect}) answer that query as the actual mechanism, not a UI/wrapper/test that shares a keyword?"
            ),
            "criteria": {
                "true": self.noul_true,
                "false": self.noul_false,
            }
        })
    }

    pub fn noul_questions(
        &self,
        query: &str,
        family: &str,
        ids: &[String],
        use_body: bool,
    ) -> Value {
        let mut q = Map::new();
        for cid in ids {
            q.insert(
                format!("rel_{cid}"),
                self.noul_question(query, family, cid, use_body),
            );
        }
        Value::Object(q)
    }

    /// Dual noul (keep_body + keep_ptr) en un solo request. Mismas instructions que squeeze.
    pub fn pack_noul_questions(&self, query: &str, family: &str, ids: &[String]) -> Value {
        let mut q = Map::new();
        for cid in ids {
            q.insert(
                format!("rel_{cid}_body"),
                self.noul_question(query, family, cid, true),
            );
            q.insert(
                format!("rel_{cid}_ptr"),
                self.noul_question(query, family, cid, false),
            );
        }
        Value::Object(q)
    }

    /// Un HTTP: choice work + noul needs_session / worth_remembering / needs_finish.
    pub fn utterance_questions(&self) -> Value {
        json!({
            "work": {
                "type": "choice",
                "instructions": {
                    "question": "What is the user doing in this message?",
                    "focus": "The act, not the topic. A question about a module is question, not implement."
                },
                "criteria": {
                    "question": "Asking how something works or requesting an explanation. No system change.",
                    "implement": "Asking to fix, build, change, or implement something in the system.",
                    "chore": "Housekeeping that is neither a spec nor a vault write.",
                    "done": "Declaring the work finished, ready to document or close."
                }
            },
            "needs_session": {
                "type": "noul",
                "instructions": "Does this act require an open work session (sync job) so the change is tracked?",
                "criteria": {
                    "true": "The user wants a system change that should be tracked as a work session.",
                    "false": "A question, chatter, or a chore that must not open a session."
                }
            },
            "worth_remembering": {
                "type": "noul",
                "instructions": "Is this worth storing in episodic memory, not ok/chatter/a question?",
                "criteria": {
                    "true": "A durable fact or decision worth retrieving later.",
                    "false": "Question, 'ok', trivial diff, or chatter."
                }
            },
            "needs_finish": {
                "type": "noul",
                "instructions": "Should Cortex run documenter/finish for this message?",
                "criteria": {
                    "true": "The user is declaring the work done and docs/session should close.",
                    "false": "Work is still in progress or this is not a close request."
                }
            }
        })
    }

    pub fn promotion_noul_question(&self, cid: &str) -> Value {
        json!({
            "type": "noul",
            "instructions": format!(
                "Is candidates item `{cid}` (`title` + `path`) organization-level knowledge worth promoting to the enterprise vault, not project-local noise, a session note, chrome, or a duplicate?"
            ),
            "criteria": {
                "true": "Organization-level knowledge worth promoting to the enterprise vault.",
                "false": "Project-local noise, session notes, chrome, or a duplicate of existing org docs.",
            }
        })
    }

    pub fn promotion_noul_questions(&self, ids: &[String]) -> Value {
        let mut q = Map::new();
        for cid in ids {
            q.insert(format!("rel_{cid}"), self.promotion_noul_question(cid));
        }
        Value::Object(q)
    }

    pub fn session_compact_questions(&self, candidates: &[crate::compact::CompactCandidate]) -> Value {
        let mut q = Map::new();
        for c in candidates {
            let snippet = if c.output.chars().count() > 200 {
                let prefix: String = c.output.chars().take(200).collect();
                format!("{prefix}...")
            } else {
                c.output.clone()
            };
            q.insert(
                format!("keep_call_{}", c.id),
                json!({
                    "type": "noul",
                    "instructions": format!(
                        "Is tool call `{}` (`{} {}`) essential context to preserve in the conversation history, or transient noise?",
                        c.id, c.tool, c.args
                    ),
                    "criteria": {
                        "true": "Essential tool call that explains critical context, decisions, or subsequent steps.",
                        "false": "Transient, repetitive, or irrelevant tool call."
                    }
                }),
            );
            q.insert(
                format!("keep_result_{}", c.id),
                json!({
                    "type": "noul",
                    "instructions": format!(
                        "Is the full result of tool `{}` (`{}`) essential to keep verbatim in the conversation context, or bulky intermediate output that should be truncated? Snippet: {}",
                        c.id, c.tool, snippet
                    ),
                    "criteria": {
                        "true": "Crucial output containing facts, findings, or answers still needed in context.",
                        "false": "Bulky intermediate output, repetitive search dump, large file listing, or raw log."
                    }
                }),
            );
        }
        Value::Object(q)
    }

    /// Genera la pregunta Choice para Model Routing entre candidatos válidos.
    pub fn model_routing_questions(
        &self,
        role: &str,
        task: &str,
        candidates: &[String],
    ) -> Value {
        let mut criteria = Map::new();
        for c in candidates {
            criteria.insert(c.clone(), json!(format!("Modelo candidato `{c}`")));
        }
        json!({
            "selected_model": {
                "type": "choice",
                "instructions": {
                    "question": format!("Which model should execute the task for role `{role}`? Task: {task}"),
                    "focus": "Choose the optimal model considering reasoning depth, cost, speed, and suitability."
                },
                "criteria": Value::Object(criteria),
            }
        })
    }

    /// Primitiva Score (escala 0..2) para clasificar el impacto arquitectónico de un cambio.
    pub fn adr_score_question(&self, decision_summary: &str) -> Value {
        json!({
            "adr_impact": {
                "type": "score",
                "instructions": format!("Rate the architectural impact of this decision on a 0 to 2 scale: {decision_summary}"),
                "criteria": {
                    "0": "Cosmetic or localized refactor without contract changes.",
                    "1": "Local architectural design decision affecting one module.",
                    "2": "Foundational architectural change, difficult to reverse, defines system invariants."
                }
            }
        })
    }
}

fn default_families() -> BTreeMap<String, String> {
    [
        (
            "session",
            "Session lifecycle, checkpoints, verification, quality gates",
        ),
        (
            "retrieval",
            "Hybrid search, RRF, intent, embeddings used for retrieve",
        ),
        (
            "documenter",
            "Finish-session, reconstruction, contradiction detection, ADRs",
        ),
        (
            "brain",
            "Local assistant router and tools, not the TUI chrome",
        ),
        (
            "enterprise",
            "Org vault, promotion, review-required, governance",
        ),
        ("autopilot", "Task detectors and policies over a session"),
        (
            "actions",
            "ActionEngine / cortex next scheduler and catalog",
        ),
        (
            "embeddings",
            "Choosing onnx/fastembed/openai embedders, per-language",
        ),
        ("mcp", "The MCP server, tool catalog, 32 tools"),
        ("webgraph", "Memory graph, wiki-links, cosine neighbors"),
        ("other", "None of the above / several families at once"),
    ]
    .into_iter()
    .map(|(k, v)| (k.to_string(), v.to_string()))
    .collect()
}
