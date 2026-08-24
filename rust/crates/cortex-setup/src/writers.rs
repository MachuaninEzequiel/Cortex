//! Writers canónicos — porteo de `cortex/documentation/writers.py` +
//! `data.py` + `schemas/*.py` (orden de campos del frontmatter incluido).
//!
//! Contrato de paridad: dado el mismo `NoteRequest` (doc_type + kwargs del
//! dataclass XData), el mismo reloj `now` y el mismo vault en disco, el
//! archivo producido es byte-a-byte idéntico al que escribe Python:
//! `---\n` + `yaml_dump_safe(fm.model_dump(mode="json"))` + `---\n\n` + body.

use std::path::Path;

use chrono::{DateTime, Utc};
use serde_json::{Map, Value};
use sha2::{Digest, Sha256};

use crate::doc_type::DocType;
use crate::jinja;
use crate::routing::{resolve_route, resolve_target_path, FilenameCtx};
use crate::slug::slugify;
use crate::yaml::Yaml;

/// Request de escritura: tipo + campos crudos (kwargs del dataclass XData).
#[derive(Debug, Clone)]
pub struct NoteRequest {
    pub doc_type: DocType,
    pub fields: Map<String, Value>,
}

impl NoteRequest {
    pub fn from_json(doc_type: &str, fields: Map<String, Value>) -> Result<Self, String> {
        let dt =
            DocType::parse(doc_type).ok_or_else(|| format!("unknown doc_type {doc_type:?}"))?;
        Ok(NoteRequest {
            doc_type: dt,
            fields,
        })
    }

    // ── accesores tipados con defaults de CommonWriteData ──────────

    fn s(&self, key: &str) -> String {
        match self.fields.get(key) {
            Some(Value::String(v)) => v.clone(),
            Some(Value::Null) | None => String::new(),
            Some(other) => other.to_string(),
        }
    }

    fn opt_s(&self, key: &str) -> Option<String> {
        match self.fields.get(key) {
            Some(Value::String(v)) => Some(v.clone()),
            _ => None,
        }
    }

    fn str_list(&self, key: &str) -> Vec<String> {
        match self.fields.get(key) {
            Some(Value::Array(items)) => items
                .iter()
                .filter_map(|v| v.as_str().map(str::to_string))
                .collect(),
            _ => Vec::new(),
        }
    }

    /// Datetime opcional normalizado como `pydantic model_dump(mode="json")`:
    /// ISO-8601 UTC con 'Z'; OMITE microsegundos cuando son cero.
    fn opt_dt(&self, key: &str) -> Option<String> {
        let raw = self.opt_s(key)?;
        Some(normalize_pydantic_datetime(&raw))
    }

    fn int(&self, key: &str) -> i64 {
        self.fields.get(key).and_then(|v| v.as_i64()).unwrap_or(0)
    }

    fn bool(&self, key: &str) -> bool {
        self.fields
            .get(key)
            .and_then(|v| v.as_bool())
            .unwrap_or(false)
    }

    /// `asdict(data)` para este DocType: TODOS los campos del dataclass con
    /// sus defaults (los que no vengan en `fields`). Orden de inserción =
    /// orden de definición en data.py.
    pub fn template_vars(&self) -> Value {
        let mut m = Map::new();
        macro_rules! put {
            ($k:expr, $v:expr $(,)?) => {
                m.insert($k.to_string(), $v);
            };
        }
        let dt = self.doc_type;

        // CommonWriteData (todas las clases lo heredan primero).
        put!("title", Value::String(self.s("title")));
        put!(
            "tags",
            Value::Array(
                self.str_list("tags")
                    .into_iter()
                    .map(Value::String)
                    .collect()
            )
        );
        put!(
            "links",
            Value::Array(
                self.str_list("links")
                    .into_iter()
                    .map(Value::String)
                    .collect()
            )
        );
        put!("status", Value::String(self.s("status")));
        // Enterprise-only (presentes en todos los dataclasses).
        put!(
            "owner",
            self.opt_s("owner")
                .map(Value::String)
                .unwrap_or(Value::Null)
        );
        put!(
            "team",
            self.opt_s("team").map(Value::String).unwrap_or(Value::Null)
        );
        put!(
            "classification",
            self.opt_s("classification")
                .map(Value::String)
                .unwrap_or(Value::Null)
        );
        put!(
            "retention_days",
            self.fields
                .get("retention_days")
                .cloned()
                .unwrap_or(Value::Null)
        );

        match dt {
            DocType::Session => {
                put!("session_id", Value::String(self.s("session_id")));
                put!("spec_summary", Value::String(self.s("spec_summary")));
                put_list(&mut m, "changes_made", &self.str_list("changes_made"));
                put_list(&mut m, "files_touched", &self.str_list("files_touched"));
                put_list(&mut m, "key_decisions", &self.str_list("key_decisions"));
                put_list(&mut m, "next_steps", &self.str_list("next_steps"));
                put!("pr", opt_null(self.opt_s("pr")));
                put!("branch", opt_null(self.opt_s("branch")));
                put!("commit", opt_null(self.opt_s("commit")));
                put_list(&mut m, "verified_state", &self.str_list("verified_state"));
                put_list(
                    &mut m,
                    "unverified_claims",
                    &self.str_list("unverified_claims"),
                );
                put_list(&mut m, "blockers", &self.str_list("blockers"));
                put_list(
                    &mut m,
                    "suggested_skills",
                    &self.str_list("suggested_skills"),
                );
                put!(
                    "cortex_telemetry",
                    self.fields
                        .get("cortex_telemetry")
                        .cloned()
                        .unwrap_or(Value::Null),
                );
                put!("task_type", Value::String(self.s("task_type")));
                put!(
                    "tasks",
                    self.fields
                        .get("tasks")
                        .cloned()
                        .unwrap_or(Value::Array(vec![])),
                );
                put!("tasks_total", Value::from(self.int("tasks_total") as u64));
                put!("tasks_done", Value::from(self.int("tasks_done") as u64));
                put!(
                    "tasks_skipped",
                    Value::from(self.int("tasks_skipped") as u64)
                );
                put!("gitless", Value::Bool(self.bool("gitless")));
            }
            DocType::Handoff => {
                put!(
                    "parent_session_id",
                    Value::String(self.s("parent_session_id"))
                );
                put_list(
                    &mut m,
                    "next_session_needs",
                    &self.str_list("next_session_needs"),
                );
                put_list(&mut m, "blockers", &self.str_list("blockers"));
                put_list(&mut m, "verified_state", &self.str_list("verified_state"));
                put_list(
                    &mut m,
                    "unverified_claims",
                    &self.str_list("unverified_claims"),
                );
                put_list(
                    &mut m,
                    "suggested_skills",
                    &self.str_list("suggested_skills"),
                );
                put!(
                    "context_required",
                    Value::String(self.s("context_required"))
                );
            }
            DocType::Spec => {
                put!("goal", Value::String(self.s("goal")));
                put_list(&mut m, "requirements", &self.str_list("requirements"));
                put_list(&mut m, "files_in_scope", &self.str_list("files_in_scope"));
                put_list(&mut m, "constraints", &self.str_list("constraints"));
                put_list(
                    &mut m,
                    "acceptance_criteria",
                    &self.str_list("acceptance_criteria"),
                );
                put!(
                    "verification_hooks",
                    normalized_hooks(self.fields.get("verification_hooks"))
                );
            }
            DocType::Design => {
                // DesignDocData sobreescribe el default de status a "draft"
                // (ya viene vacío ⇒ se completa abajo).
                if self.s("status").is_empty() {
                    m.insert("status".into(), Value::String("draft".into()));
                }
                put!("session_id", Value::String(self.s("session_id")));
                put!("spec_path", Value::String(self.s("spec_path")));
                put!(
                    "architecture_decision",
                    Value::String(self.s("architecture_decision")),
                );
                put_list(
                    &mut m,
                    "data_model_changes",
                    &self.str_list("data_model_changes"),
                );
                put_list(&mut m, "api_contracts", &self.str_list("api_contracts"));
                put_list(&mut m, "test_plan", &self.str_list("test_plan"));
                put_list(&mut m, "risks", &self.str_list("risks"));
            }
            DocType::Adr => {
                put!("context", Value::String(self.s("context")));
                put!("decision", Value::String(self.s("decision")));
                put_list(
                    &mut m,
                    "alternatives_considered",
                    &self.str_list("alternatives_considered"),
                );
                put!("consequences", Value::String(self.s("consequences")));
                put!("adr_number", Value::from(self.int("adr_number") as u64));
                put_list(&mut m, "supersedes", &self.str_list("supersedes"));
                put!("superseded_by", opt_null(self.opt_s("superseded_by")));
                put!(
                    "acceptance_criteria_met",
                    Value::Bool(self.bool("acceptance_criteria_met")),
                );
            }
            DocType::Decision => {
                put!("context", Value::String(self.s("context")));
                put!("decision", Value::String(self.s("decision")));
                put!(
                    "alternative_rejected",
                    Value::String(self.s("alternative_rejected"))
                );
                put!("reason", Value::String(self.s("reason")));
                put!(
                    "reversible_within_days",
                    Value::from(self.int("reversible_within_days") as u64),
                );
            }
            DocType::Incident => {
                put!(
                    "incident_number",
                    Value::from(self.int("incident_number") as u64)
                );
                put!(
                    "severity",
                    Value::String(severity_or_default(&self.s("severity")))
                );
                put!("opened_at", opt_null(self.opt_s("opened_at")));
                put!("closed_at", opt_null(self.opt_s("closed_at")));
                put_list(
                    &mut m,
                    "affected_services",
                    &self.str_list("affected_services"),
                );
                put_list(&mut m, "timeline", &self.str_list("timeline"));
                put!("impact", Value::String(self.s("impact")));
                put!(
                    "short_description",
                    Value::String(self.s("short_description"))
                );
                put!(
                    "root_cause_postmortem",
                    opt_null(self.opt_s("root_cause_postmortem")),
                );
            }
            DocType::Postmortem => {
                put!(
                    "incident_number",
                    Value::from(self.int("incident_number") as u64)
                );
                put!("incident_path", Value::String(self.s("incident_path")));
                put!("root_cause", Value::String(self.s("root_cause")));
                put_list(
                    &mut m,
                    "contributing_factors",
                    &self.str_list("contributing_factors"),
                );
                put_list(&mut m, "what_went_well", &self.str_list("what_went_well"));
                put_list(&mut m, "what_went_wrong", &self.str_list("what_went_wrong"));
                put_list(&mut m, "action_items", &self.str_list("action_items"));
                put_list(&mut m, "timeline", &self.str_list("timeline"));
                put!(
                    "severity",
                    Value::String(severity_or_default(&self.s("severity")))
                );
            }
            DocType::Runbook => {
                put!(
                    "runbook_kind",
                    Value::String(runbook_kind_or_default(&self.s("runbook_kind")))
                );
                put!("description", Value::String(self.s("description")));
                put_list(&mut m, "prerequisites", &self.str_list("prerequisites"));
                put_list(&mut m, "procedure", &self.str_list("procedure"));
                put_list(
                    &mut m,
                    "rollback_procedure",
                    &self.str_list("rollback_procedure"),
                );
                put_list(&mut m, "verification", &self.str_list("verification"));
                put_list(&mut m, "applies_to", &self.str_list("applies_to"));
                put!(
                    "estimated_duration_minutes",
                    Value::from(self.int("estimated_duration_minutes") as u64),
                );
                put!("last_verified_at", opt_null(self.opt_s("last_verified_at")));
            }
            DocType::Architecture => {
                put!("summary", Value::String(self.s("summary")));
                put_list(&mut m, "components", &self.str_list("components"));
                put_list(&mut m, "diagrams", &self.str_list("diagrams"));
                put_list(&mut m, "contracts", &self.str_list("contracts"));
                put!("rationale", Value::String(self.s("rationale")));
                put_list(&mut m, "related_adrs", &self.str_list("related_adrs"));
            }
            DocType::Changelog => {
                put!("version", Value::String(self.s("version")));
                put!("release_date", opt_null(self.opt_s("release_date")));
                put_list(&mut m, "added", &self.str_list("added"));
                put_list(&mut m, "changed", &self.str_list("changed"));
                put_list(&mut m, "deprecated", &self.str_list("deprecated"));
                put_list(&mut m, "removed", &self.str_list("removed"));
                put_list(&mut m, "fixed", &self.str_list("fixed"));
                put_list(&mut m, "security", &self.str_list("security"));
            }
            DocType::Hu => {
                put!("external_id", Value::String(self.s("external_id")));
                put!("source", Value::String(self.s("source")));
                put!("kind", Value::String(hu_kind_or_default(&self.s("kind"))));
                put!("description", Value::String(self.s("description")));
                put_list(
                    &mut m,
                    "acceptance_criteria",
                    &self.str_list("acceptance_criteria"),
                );
                put!("assignee", opt_null(self.opt_s("assignee")));
                put!("external_url", opt_null(self.opt_s("external_url")));
                put!("synced_at", opt_null(self.opt_s("synced_at")));
            }
            DocType::Glossary => {
                put!("term", Value::String(self.s("term")));
                put!("definition", Value::String(self.s("definition")));
                put_list(&mut m, "examples", &self.str_list("examples"));
                put_list(&mut m, "related_terms", &self.str_list("related_terms"));
                put!("domain", opt_null(self.opt_s("domain")));
            }
        }
        Value::Object(m)
    }
}

fn put_list(m: &mut Map<String, Value>, key: &str, list: &[String]) {
    m.insert(
        key.to_string(),
        Value::Array(list.iter().map(|s| Value::String(s.clone())).collect()),
    );
}

fn opt_null(v: Option<String>) -> Value {
    v.map(Value::String).unwrap_or(Value::Null)
}

fn severity_or_default(v: &str) -> String {
    if v.is_empty() {
        "medium".to_string()
    } else {
        v.to_string()
    }
}

fn runbook_kind_or_default(v: &str) -> String {
    if v.is_empty() {
        "operational".to_string()
    } else {
        v.to_string()
    }
}

fn hu_kind_or_default(v: &str) -> String {
    if v.is_empty() {
        "story".to_string()
    } else {
        v.to_string()
    }
}

/// Normaliza verification_hooks al formato `VerificationHook.model_dump(mode="json")`
/// (claves en orden de definición del modelo).
fn normalized_hooks(v: Option<&Value>) -> Value {
    let empty = Vec::new();
    let items = v.and_then(|x| x.as_array()).unwrap_or(&empty);
    Value::Array(
        items
            .iter()
            .map(|h| {
                let obj = h.as_object();
                let get = |k: &str| {
                    obj.and_then(|o| o.get(k)).cloned().unwrap_or(match k {
                        "required" => Value::Bool(true),
                        "success_criteria" => Value::String("exit code 0".into()),
                        "timeout_seconds" => Value::from(300u64),
                        _ => Value::Null,
                    })
                };
                let mut m = Map::new();
                m.insert("name".into(), get("name"));
                m.insert("command".into(), get("command"));
                m.insert("required".into(), get("required"));
                m.insert("success_criteria".into(), get("success_criteria"));
                m.insert("timeout_seconds".into(), get("timeout_seconds"));
                Value::Object(m)
            })
            .collect(),
    )
}

// ---------------------------------------------------------------------------
// Frontmatter
// ---------------------------------------------------------------------------

/// Normaliza un ISO-8601 a la forma que emite pydantic v2 para UTC:
/// `%Y-%m-%dT%H:%M:%S[.%f]Z`, sin fracción cuando es 0.
pub fn normalize_pydantic_datetime(raw: &str) -> String {
    match DateTime::parse_from_rfc3339(raw) {
        Ok(dt) => {
            let utc = dt.with_timezone(&Utc);
            if utc.timestamp_subsec_nanos() == 0 {
                utc.format("%Y-%m-%dT%H:%M:%SZ").to_string()
            } else {
                utc.format("%Y-%m-%dT%H:%M:%S%.6fZ").to_string()
            }
        }
        Err(_) => raw.to_string(),
    }
}

fn iso_z(dt: DateTime<Utc>) -> String {
    // Formato pydantic mode="json" para UTC: 2026-08-24T12:34:56.789012Z
    dt.format("%Y-%m-%dT%H:%M:%S%.6fZ").to_string()
}

fn coerce_status(dt: DocType, requested: &str) -> String {
    let valid = dt.valid_statuses();
    if !requested.is_empty() && valid.contains(&requested) {
        return requested.to_string();
    }
    valid.first().unwrap().to_string()
}

fn yarr(items: &[String]) -> Yaml {
    Yaml::Seq(items.iter().map(|s| Yaml::Str(s.clone())).collect())
}

fn yopt(v: Option<String>) -> Yaml {
    v.map(Yaml::Str).unwrap_or(Yaml::Null)
}

fn yint(v: i64) -> Yaml {
    Yaml::Int(v)
}

/// Campos comunes (CommonFrontmatter) en orden de definición.
#[allow(clippy::too_many_arguments)]
fn common_fields(
    out: &mut Vec<(String, Yaml)>,
    dt: DocType,
    title: &str,
    tags: &[String],
    status: &str,
    links: &[String],
    vault_scope: &str,
    fingerprint: &str,
    now: DateTime<Utc>,
) {
    let now_iso = iso_z(now);
    out.push(("schema_version".into(), Yaml::Int(1)));
    out.push(("doc_type".into(), Yaml::Str(dt.as_str().into())));
    out.push(("title".into(), Yaml::Str(title.into())));
    out.push(("created_at".into(), Yaml::Str(now_iso.clone())));
    out.push(("updated_at".into(), Yaml::Str(now_iso)));
    out.push(("tags".into(), yarr(tags)));
    out.push(("status".into(), Yaml::Str(status.into())));
    out.push(("links".into(), yarr(links)));
    out.push(("vault_scope".into(), Yaml::Str(vault_scope.into())));
    out.push(("fingerprint".into(), Yaml::Str(fingerprint.into())));
}

/// Tail enterprise (EnterpriseFrontmatter) + audit_trail con evento creado.
fn enterprise_fields(
    out: &mut Vec<(String, Yaml)>,
    owner: &str,
    team: &str,
    classification: Option<&str>,
    retention_days: Option<i64>,
    actor: Option<&str>,
    now: DateTime<Utc>,
) {
    out.push(("owner".into(), Yaml::Str(owner.into())));
    out.push(("team".into(), Yaml::Str(team.into())));
    out.push((
        "classification".into(),
        Yaml::Str(classification.unwrap_or("internal").into()),
    ));
    out.push((
        "retention_days".into(),
        Yaml::Int(retention_days.unwrap_or(0)),
    ));
    // audit_trail: la validación parte de [], y append_audit_event agrega
    // SIEMPRE un evento "created".
    let trail = vec![
        (
            "actor".to_string(),
            Yaml::Str(actor.unwrap_or("unknown").into()),
        ),
        ("action".to_string(), Yaml::Str("created".into())),
        ("timestamp".to_string(), Yaml::Str(iso_z(now))),
        ("reason".to_string(), Yaml::Null),
    ];
    out.push(("audit_trail".into(), Yaml::Seq(vec![Yaml::Map(trail)])));
}

/// Campos específicos por DocType en orden de definición del schema
/// (`_XSpecific`), usando overrides del filename context cuando aplica.
fn type_specific_fields(
    req: &NoteRequest,
    ctx: &FilenameCtx,
    now: DateTime<Utc>,
) -> Vec<(String, Yaml)> {
    let mut out: Vec<(String, Yaml)> = Vec::new();
    let mut push = |k: &str, v: Yaml| out.push((k.to_string(), v));
    match req.doc_type {
        DocType::Adr => {
            push("adr_number", yint(ctx.number));
            push("supersedes", yarr(&req.str_list("supersedes")));
            push("superseded_by", yopt(req.opt_s("superseded_by")));
            push(
                "alternatives_considered",
                yarr(&req.str_list("alternatives_considered")),
            );
            push(
                "acceptance_criteria_met",
                Yaml::Bool(req.bool("acceptance_criteria_met")),
            );
        }
        DocType::Decision => {
            push(
                "reversible_within_days",
                yint(req.int("reversible_within_days")),
            );
        }
        DocType::Incident => {
            push("incident_number", yint(ctx.number));
            push(
                "severity",
                Yaml::Str(severity_or_default(&req.s("severity"))),
            );
            push(
                "opened_at",
                Yaml::Str(req.opt_dt("opened_at").unwrap_or_else(|| iso_z(now))),
            );
            push("closed_at", yopt(req.opt_dt("closed_at")));
            push(
                "affected_services",
                yarr(&req.str_list("affected_services")),
            );
            push(
                "root_cause_postmortem",
                yopt(req.opt_s("root_cause_postmortem")),
            );
        }
        DocType::Postmortem => {
            push("incident_number", yint(ctx.incident_number));
            push("incident_path", Yaml::Str(req.s("incident_path")));
            push(
                "severity",
                Yaml::Str(severity_or_default(&req.s("severity"))),
            );
        }
        DocType::Runbook => {
            push(
                "runbook_kind",
                Yaml::Str(runbook_kind_or_default(&req.s("runbook_kind"))),
            );
            push("applies_to", yarr(&req.str_list("applies_to")));
            push(
                "estimated_duration_minutes",
                yint(req.int("estimated_duration_minutes")),
            );
            push("last_verified_at", yopt(req.opt_dt("last_verified_at")));
        }
        DocType::Architecture => {
            push("related_adrs", yarr(&req.str_list("related_adrs")));
        }
        DocType::Changelog => {
            push("version", Yaml::Str(req.s("version")));
            push("release_date", yopt(req.opt_dt("release_date")));
        }
        DocType::Hu => {
            push("external_id", Yaml::Str(req.s("external_id")));
            push("source", Yaml::Str(req.s("source")));
            push("kind", Yaml::Str(hu_kind_or_default(&req.s("kind"))));
            push("assignee", yopt(req.opt_s("assignee")));
            push("external_url", yopt(req.opt_s("external_url")));
            push("synced_at", yopt(req.opt_dt("synced_at")));
        }
        DocType::Glossary => {
            push("term", Yaml::Str(req.s("term")));
            push("domain", yopt(req.opt_s("domain")));
            push("related_terms", yarr(&req.str_list("related_terms")));
        }
        DocType::Handoff => {
            push("parent_session_id", Yaml::Str(req.s("parent_session_id")));
        }
        DocType::Session => {
            push("session_id", Yaml::Str(req.s("session_id")));
            push("pr", yopt(req.opt_s("pr")));
            push("branch", yopt(req.opt_s("branch")));
            push("commit", yopt(req.opt_s("commit")));
            push(
                "cortex_telemetry",
                json_value_to_yaml(
                    &req.fields
                        .get("cortex_telemetry")
                        .cloned()
                        .unwrap_or(Value::Null),
                ),
            );
        }
        DocType::Spec => {
            // Orden pydantic real: `verification_hooks` es campo DEFINIDO del
            // modelo (aparece junto al bloque común); goal/files/constraints/
            // acceptance_criteria son extras (extra=allow) y conservan el
            // orden de inserción del dict de entrada, AL FINAL.
            push(
                "verification_hooks",
                json_value_to_yaml(&normalized_hooks(req.fields.get("verification_hooks"))),
            );
            push("goal", Yaml::Str(req.s("goal")));
            push("files_in_scope", yarr(&req.str_list("files_in_scope")));
            push("constraints", yarr(&req.str_list("constraints")));
            push(
                "acceptance_criteria",
                yarr(&req.str_list("acceptance_criteria")),
            );
        }
        DocType::Design => {
            push("session_id", Yaml::Str(req.s("session_id")));
            push("spec_path", Yaml::Str(req.s("spec_path")));
        }
    }
    out
}

/// Convierte un Value JSON arbitrario (telemetría, hooks) a Yaml preservando
/// el orden de las claves (serde_json preserve_order activo).
fn json_value_to_yaml(v: &Value) -> Yaml {
    match v {
        Value::Null => Yaml::Null,
        Value::Bool(b) => Yaml::Bool(*b),
        Value::Number(n) => match n.as_i64() {
            Some(i) => Yaml::Int(i),
            None => Yaml::Float(n.as_f64().unwrap_or(0.0)),
        },
        Value::String(s) => Yaml::Str(s.clone()),
        Value::Array(items) => Yaml::Seq(items.iter().map(json_value_to_yaml).collect()),
        Value::Object(map) => Yaml::Map(
            map.iter()
                .map(|(k, val)| (k.clone(), json_value_to_yaml(val)))
                .collect(),
        ),
    }
}

/// sha256 hex (compute_fingerprint).
pub fn compute_fingerprint(content: &str) -> String {
    let digest = Sha256::digest(content.as_bytes());
    digest.iter().map(|b| format!("{b:02x}")).collect()
}

/// `_next_number`: máximo prefijo numérico +1 en la carpeta.
fn next_number(folder: &Path, prefix: &str) -> i64 {
    let mut used: Vec<i64> = Vec::new();
    if let Ok(entries) = std::fs::read_dir(folder) {
        for entry in entries.flatten() {
            let path = entry.path();
            if !path.is_file() {
                continue;
            }
            let stem = path
                .file_stem()
                .map(|s| s.to_string_lossy().to_string())
                .unwrap_or_default();
            if let Some(rest) = stem
                .strip_prefix(prefix)
                .or_else(|| stem.strip_prefix(&prefix.to_lowercase()))
            {
                let digits: String = rest.chars().take_while(|c| c.is_ascii_digit()).collect();
                if let Ok(n) = digits.parse::<i64>() {
                    used.push(n);
                }
            }
        }
    }
    used.iter().max().copied().unwrap_or(0) + 1
}

/// Contexto de filename (`_build_filename_context`).
fn build_filename_ctx(req: &NoteRequest, vault_root: &Path, now: DateTime<Utc>) -> FilenameCtx {
    let today = now.format("%Y-%m-%d").to_string();
    let title_slug = {
        let s = slugify(&req.s("title"));
        if s.is_empty() {
            "untitled".to_string()
        } else {
            s
        }
    };
    let mut ctx = FilenameCtx {
        date: today,
        slug: title_slug,
        ..Default::default()
    };
    match req.doc_type {
        DocType::Adr => {
            ctx.number = if req.int("adr_number") > 0 {
                req.int("adr_number")
            } else {
                next_number(&vault_root.join("decisions"), "ADR-")
            };
        }
        DocType::Incident => {
            ctx.number = if req.int("incident_number") > 0 {
                req.int("incident_number")
            } else {
                next_number(&vault_root.join("incidents"), "INC-")
            };
            ctx.incident_number = ctx.number;
        }
        DocType::Postmortem => {
            ctx.incident_number = req.int("incident_number");
        }
        DocType::Session | DocType::Design => {
            ctx.session_id = req.s("session_id");
        }
        DocType::Hu => {
            ctx.external_id = req.s("external_id");
        }
        DocType::Runbook | DocType::Architecture => {
            ctx.date.clear(); // ctx reemplazado por {"slug"}
        }
        DocType::Changelog => {
            ctx.version = req.s("version");
            ctx.date.clear();
            ctx.slug.clear();
        }
        DocType::Glossary => {
            ctx.term_slug = slugify(&req.s("term"));
            ctx.date.clear();
            ctx.slug.clear();
        }
        DocType::Handoff | DocType::Spec | DocType::Decision => {}
    }
    ctx
}

/// Validaciones del writer público (requisitos previos a `_write_canonical`)
/// + mutaciones de defaults (glossary/design title).
fn preconditions(req: &mut NoteRequest) -> Result<(), String> {
    let missing_title = req.s("title").is_empty();
    match req.doc_type {
        DocType::Session if req.s("session_id").is_empty() => {
            return Err("session requires session_id".into());
        }
        DocType::Handoff if req.s("parent_session_id").is_empty() => {
            return Err("handoff requires parent_session_id".into());
        }
        DocType::Handoff => {}
        DocType::Changelog if req.s("version").is_empty() => {
            return Err("changelog requires version".into());
        }
        DocType::Changelog => {}
        DocType::Glossary => {
            if req.s("term").is_empty() {
                return Err("glossary entry requires term".into());
            }
            if req.s("definition").is_empty() {
                return Err("glossary entry requires definition".into());
            }
            if missing_title {
                let term = req.s("term");
                req.fields.insert("title".into(), Value::String(term));
            }
        }
        DocType::Hu => {
            if req.s("external_id").is_empty() {
                return Err("hu requires external_id".into());
            }
            if req.s("source").is_empty() {
                return Err("hu requires source".into());
            }
        }
        DocType::Design => {
            if req.s("session_id").is_empty() {
                return Err("design requires session_id".into());
            }
            if req.s("spec_path").is_empty() {
                return Err("design requires spec_path".into());
            }
            if missing_title {
                let sid = req.s("session_id");
                req.fields
                    .insert("title".into(), Value::String(format!("Design for {sid}")));
            }
        }
        DocType::Postmortem => {
            if req.s("incident_path").is_empty() {
                return Err("postmortem requires incident_path".into());
            }
            if req.int("incident_number") <= 0 {
                return Err("postmortem requires incident_number >= 1".into());
            }
        }
        _ => {}
    }
    if req.doc_type != DocType::Glossary
        && req.doc_type != DocType::Design
        && req.s("title").is_empty()
    {
        return Err(format!("{} requires a title", req.doc_type.as_str()));
    }
    Ok(())
}

/// Resultado de construir una nota canónica.
pub struct WriteOutcome {
    pub path: std::path::PathBuf,
    pub content: String,
}

/// `_write_canonical` completo: body → fingerprint → filename → frontmatter
/// → contenido final (`---\n{yaml}---\n\n{body}`).
///
/// `overwrite` sólo afecta la semántica de duplicados del Python; para
/// paridad devolvemos siempre el contenido construido.
pub fn build_note(
    req: &mut NoteRequest,
    vault_root: &Path,
    vault_scope: &str,
    project_id: Option<&str>,
    actor: Option<&str>,
    now: DateTime<Utc>,
) -> Result<WriteOutcome, String> {
    preconditions(req)?;
    if vault_scope == "enterprise" && (req.opt_s("owner").is_none() || req.opt_s("team").is_none())
    {
        let mut missing = Vec::new();
        if req.opt_s("owner").is_none() {
            missing.push("owner");
        }
        if req.opt_s("team").is_none() {
            missing.push("team");
        }
        return Err(format!(
            "Enterprise scope requires fields: [{}]",
            missing
                .iter()
                .map(|m| format!("'{m}'"))
                .collect::<Vec<_>>()
                .join(", ")
        ));
    }

    let route = resolve_route(req.doc_type);
    let vars = req.template_vars();
    let body = jinja::render_template(
        route.template_name,
        &minijinja::Value::from_serialize(&vars),
    )?;
    let fingerprint = compute_fingerprint(&body);
    let ctx = build_filename_ctx(req, vault_root, now);

    let mut fm: Vec<(String, Yaml)> = Vec::new();
    common_fields(
        &mut fm,
        req.doc_type,
        &req.s("title"),
        &req.str_list("tags"),
        &coerce_status(req.doc_type, &req.s("status")),
        &req.str_list("links"),
        vault_scope,
        &fingerprint,
        now,
    );
    if vault_scope == "enterprise" {
        enterprise_fields(
            &mut fm,
            &req.s("owner"),
            &req.s("team"),
            req.opt_s("classification").as_deref(),
            req.fields.get("retention_days").and_then(|v| v.as_i64()),
            actor,
            now,
        );
    }
    fm.extend(type_specific_fields(req, &ctx, now));

    let target = resolve_target_path(&route, &ctx, vault_root, vault_scope, project_id)?;

    let yaml_str = crate::yaml::dump(&Yaml::Map(fm));
    let content = format!("---\n{yaml_str}---\n\n{body}");
    Ok(WriteOutcome {
        path: target,
        content,
    })
}
