//! Puerto de `cortex.services.spec_service.SpecService` (P12A-5).

use std::collections::{BTreeMap, BTreeSet};
use std::path::PathBuf;

use chrono::{DateTime, Utc};
use cortex_app::session::{SessionRecord, VerificationHook};
use serde_json::{Map, Value};

use crate::{persist_note, EpisodicPort, EpisodicRequest, SemanticPort, SessionOpener};

#[derive(Debug, Clone)]
pub struct SpecCreationResult {
    pub path: PathBuf,
    pub session: Option<SessionRecord>,
}

/// Input de hooks: instancia nativa o dict JSON auto-coercionado.
#[derive(Debug, Clone)]
pub enum HookInput {
    Hook(VerificationHook),
    Dict(Value),
}

#[derive(Debug, Clone)]
pub struct SpecCreate {
    pub title: String,
    pub goal: String,
    pub requirements: Vec<String>,
    pub files_in_scope: Vec<String>,
    pub constraints: Vec<String>,
    pub acceptance_criteria: Vec<String>,
    pub tags: Vec<String>,
    pub verification_hooks: Vec<HookInput>,
    pub sync_vault: bool,
    pub remember: bool,
    pub proposal_mode: String,
    pub proposal_confirmed: bool,
    pub with_tasks: bool,
}

impl SpecCreate {
    pub fn basic(title: impl Into<String>, goal: impl Into<String>) -> Self {
        Self {
            title: title.into(),
            goal: goal.into(),
            requirements: Vec::new(),
            files_in_scope: Vec::new(),
            constraints: Vec::new(),
            acceptance_criteria: Vec::new(),
            tags: Vec::new(),
            verification_hooks: Vec::new(),
            sync_vault: false,
            remember: true,
            proposal_mode: "optional".into(),
            proposal_confirmed: false,
            with_tasks: false,
        }
    }
}

pub struct SpecService<'a> {
    vault_path: PathBuf,
    semantic: &'a mut dyn SemanticPort,
    episodic: &'a mut dyn EpisodicPort,
    context_metadata: BTreeMap<String, Value>,
    session_opener: Option<&'a dyn SessionOpener>,
}

impl<'a> SpecService<'a> {
    pub fn new(
        vault_path: impl Into<PathBuf>,
        semantic: &'a mut dyn SemanticPort,
        episodic: &'a mut dyn EpisodicPort,
    ) -> Self {
        Self {
            vault_path: vault_path.into(),
            semantic,
            episodic,
            context_metadata: BTreeMap::new(),
            session_opener: None,
        }
    }

    pub fn with_context_metadata(mut self, metadata: BTreeMap<String, Value>) -> Self {
        self.context_metadata = metadata;
        self
    }

    pub fn with_session_opener(mut self, opener: &'a dyn SessionOpener) -> Self {
        self.session_opener = Some(opener);
        self
    }

    pub fn create(
        &mut self,
        args: SpecCreate,
        now: DateTime<Utc>,
    ) -> Result<SpecCreationResult, String> {
        validate_proposal(&args.proposal_mode, args.proposal_confirmed)?;
        let hooks = normalize_hooks(&args.verification_hooks)?;

        let mut final_tags = vec!["spec".to_string()];
        final_tags.extend(args.tags.iter().cloned());
        if args.with_tasks && !final_tags.iter().any(|t| t == "tasks-required") {
            final_tags.push("tasks-required".into());
        }

        let hooks_json = serde_json::to_value(&hooks).map_err(|e| e.to_string())?;
        let mut fields = Map::new();
        put_s(&mut fields, "title", &args.title);
        put_s(&mut fields, "status", "draft");
        put_list(&mut fields, "tags", &final_tags);
        put_s(&mut fields, "goal", &args.goal);
        put_list(&mut fields, "requirements", &args.requirements);
        put_list(&mut fields, "files_in_scope", &args.files_in_scope);
        put_list(&mut fields, "constraints", &args.constraints);
        put_list(
            &mut fields,
            "acceptance_criteria",
            &args.acceptance_criteria,
        );
        fields.insert("verification_hooks".into(), hooks_json);

        let mut req = cortex_setup::writers::NoteRequest::from_json("spec", fields)?;
        let path = persist_note(&mut req, &self.vault_path, now)?;
        let rel = path
            .strip_prefix(&self.vault_path)
            .map_err(|e| e.to_string())?
            .to_string_lossy()
            .replace('\\', "/");
        self.semantic.index_file(&rel)?;
        if args.sync_vault {
            self.semantic.sync()?;
        }

        // Session ANTES de episodic; error de open NO bloquea spec.
        let mut opened = None;
        if let Some(opener) = self.session_opener {
            let spec_id = path.file_stem().and_then(|s| s.to_str()).unwrap_or("");
            let summary = if args.goal.is_empty() {
                args.title.as_str()
            } else {
                args.goal.as_str()
            };
            if let Ok(session) = opener.open(spec_id, &path.display().to_string(), summary) {
                opened = Some(session);
            }
        }

        if args.remember {
            self.store_episodic(&args)?;
        }
        Ok(SpecCreationResult {
            path,
            session: opened,
        })
    }

    fn store_episodic(&mut self, args: &SpecCreate) -> Result<(), String> {
        let mut summary = vec![
            format!("Specification: {}", args.title),
            format!("Goal: {}", args.goal),
        ];
        if !args.requirements.is_empty() {
            summary.push(format!(
                "Requirements: {}",
                args.requirements
                    .iter()
                    .take(8)
                    .cloned()
                    .collect::<Vec<_>>()
                    .join("; ")
            ));
        }
        let mut tags = vec!["spec".to_string()];
        tags.extend(args.tags.iter().cloned());
        self.episodic.add(EpisodicRequest {
            content: summary.join("\n"),
            memory_type: "spec".into(),
            tags,
            files: args.files_in_scope.clone(),
            extra_metadata: self.context_metadata.clone(),
        })
    }
}

fn validate_proposal(mode: &str, confirmed: bool) -> Result<(), String> {
    const VALID: [&str; 3] = ["optional", "required", "skip"];
    if !VALID.contains(&mode) {
        return Err(format!(
            "proposal_mode must be one of ['optional', 'required', 'skip']; got '{mode}'"
        ));
    }
    if mode == "required" && !confirmed {
        return Err(
            "proposal_mode is 'required' but proposal was not confirmed; re-run cortex-sync to emit and confirm the proposal before creating the spec."
                .into(),
        );
    }
    Ok(())
}

pub fn normalize_hooks(inputs: &[HookInput]) -> Result<Vec<VerificationHook>, String> {
    let mut hooks = Vec::new();
    for input in inputs {
        let hook = match input {
            HookInput::Hook(h) => h.clone(),
            HookInput::Dict(v) => serde_json::from_value::<VerificationHook>(v.clone())
                .map_err(|e| format!("VerificationHook validation failed: {e}"))?,
        };
        hooks.push(hook);
    }
    let mut seen = BTreeSet::new();
    let mut duplicate = BTreeSet::new();
    for hook in &hooks {
        if !seen.insert(hook.name.clone()) {
            duplicate.insert(hook.name.clone());
        }
    }
    if !duplicate.is_empty() {
        let repr = duplicate
            .iter()
            .map(|n| format!("'{n}'"))
            .collect::<Vec<_>>()
            .join(", ");
        return Err(format!(
            "verification_hooks contains duplicate name(s): [{repr}]"
        ));
    }
    Ok(hooks)
}

fn put_s(fields: &mut Map<String, Value>, key: &str, value: &str) {
    fields.insert(key.into(), Value::String(value.into()));
}

fn put_list(fields: &mut Map<String, Value>, key: &str, values: &[String]) {
    fields.insert(
        key.into(),
        Value::Array(values.iter().cloned().map(Value::String).collect()),
    );
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn proposal_required_e_invalid() {
        assert!(validate_proposal("required", true).is_ok());
        assert_eq!(
            validate_proposal("required", false).unwrap_err(),
            "proposal_mode is 'required' but proposal was not confirmed; re-run cortex-sync to emit and confirm the proposal before creating the spec."
        );
        assert_eq!(
            validate_proposal("bad", false).unwrap_err(),
            "proposal_mode must be one of ['optional', 'required', 'skip']; got 'bad'"
        );
    }

    #[test]
    fn hooks_dict_defaults_y_duplicados() {
        let hooks = normalize_hooks(&[HookInput::Dict(serde_json::json!({
            "name": "tests", "command": "pytest"
        }))])
        .unwrap();
        assert_eq!(hooks.len(), 1);
        assert!(hooks[0].required);
        assert_eq!(hooks[0].timeout_seconds, 300);
        let err = normalize_hooks(&[
            HookInput::Hook(hooks[0].clone()),
            HookInput::Hook(hooks[0].clone()),
        ])
        .unwrap_err();
        assert_eq!(
            err,
            "verification_hooks contains duplicate name(s): ['tests']"
        );
    }
}
