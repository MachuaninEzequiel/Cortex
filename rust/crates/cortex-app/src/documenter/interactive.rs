//! Flujo interactivo de finish-session — réplica de
//! `cortex/documenter/interactive.py` (P12A-8, T4.1).
//!
//! Máquina de estados con I/O inyectable (`input_provider` / `editor`) para
//! ejercitarla en tests sin terminal. El RENDERING rich de Python NO es
//! contrato (rich vs texto plano difieren); aquí se produce un transcript
//! de texto plano no gateado. Lo gateado es el resultado de `prompt()` y
//! los consumos exactos de input.

use crate::documenter::ReconstructionOutput;
use crate::session::SessionStatus;

/// Decisión top-level del usuario.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum InteractiveAction {
    Approve,
    Edit,
    Handoff,
    Cancel,
}

impl InteractiveAction {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Approve => "approve",
            Self::Edit => "edit",
            Self::Handoff => "handoff",
            Self::Cancel => "cancel",
        }
    }
}

/// Resultado de una invocación a [`InteractiveSession::prompt`].
#[derive(Debug, Clone)]
pub struct InteractiveResult {
    pub action: InteractiveAction,
    pub approved_adr_indices: Option<Vec<usize>>,
    pub edited_note_title: Option<String>,
    pub edited_note_body: Option<String>,
    pub forced_status: Option<SessionStatus>,
}

impl InteractiveResult {
    pub fn cancelled(&self) -> bool {
        self.action == InteractiveAction::Cancel
    }

    /// Resultado mínimo por acción (campos None).
    fn bare(action: InteractiveAction) -> Self {
        Self {
            action,
            approved_adr_indices: None,
            edited_note_title: None,
            edited_note_body: None,
            forced_status: None,
        }
    }
}

/// Proveedor de input (stub en tests; consola en producción).
pub type InputProvider = Box<dyn FnMut(&str) -> String>;
/// Editor multi-línea (click.edit en producción). Recibe el seed como
/// String propio para evitar HRTB en los stubs de test.
pub type EditorOpener = Box<dyn FnMut(String) -> Option<String>>;

pub struct InteractiveSession {
    input: InputProvider,
    editor: EditorOpener,
    /// Transcript de texto plano del rendering (no contrato; rich en Python).
    pub transcript: String,
}

fn main_action_key(raw: &str) -> Option<InteractiveAction> {
    match raw {
        "a" | "approve" => Some(InteractiveAction::Approve),
        "e" | "edit" => Some(InteractiveAction::Edit),
        "h" | "handoff" => Some(InteractiveAction::Handoff),
        "c" | "cancel" => Some(InteractiveAction::Cancel),
        _ => None,
    }
}

fn after_edit_key(raw: &str) -> Option<InteractiveAction> {
    match raw {
        "a" | "approve" => Some(InteractiveAction::Approve),
        "h" | "handoff" => Some(InteractiveAction::Handoff),
        "c" | "cancel" => Some(InteractiveAction::Cancel),
        _ => None,
    }
}

impl InteractiveSession {
    pub fn new(input: InputProvider, editor: EditorOpener) -> Self {
        Self {
            input,
            editor,
            transcript: String::new(),
        }
    }

    /// Renderiza la reconstrucción y captura el veredicto del usuario.
    pub fn prompt(&mut self, reconstruction: &ReconstructionOutput) -> InteractiveResult {
        self.render(reconstruction);
        loop {
            let choice = self.ask_main_action();
            match choice {
                InteractiveAction::Approve => {
                    return InteractiveResult::bare(InteractiveAction::Approve)
                }
                InteractiveAction::Cancel => {
                    return InteractiveResult::bare(InteractiveAction::Cancel)
                }
                InteractiveAction::Handoff => {
                    if self.ask_handoff_reason().is_none() {
                        continue; // sub-flujo abortado → volver al menú principal
                    }
                    return InteractiveResult {
                        forced_status: Some(SessionStatus::Handoff),
                        ..InteractiveResult::bare(InteractiveAction::Handoff)
                    };
                }
                InteractiveAction::Edit => {
                    let title_override = self.maybe_edit_title(reconstruction);
                    let body_override = self.maybe_edit_body(reconstruction);
                    let approved_adrs = self.review_adrs(reconstruction);
                    self.print("[dim]Edits captured. Returning to main action prompt.[/dim]\n");
                    let final_choice = self.ask_main_action_after_edit();
                    match final_choice {
                        InteractiveAction::Cancel => {
                            return InteractiveResult::bare(InteractiveAction::Cancel);
                        }
                        InteractiveAction::Handoff => {
                            let _reason = self.ask_handoff_reason().unwrap_or_default();
                            return InteractiveResult {
                                action: InteractiveAction::Handoff,
                                forced_status: Some(SessionStatus::Handoff),
                                edited_note_title: title_override,
                                edited_note_body: body_override,
                                approved_adr_indices: approved_adrs,
                            };
                        }
                        // default: APPROVE con las ediciones aplicadas
                        _ => {
                            return InteractiveResult {
                                action: InteractiveAction::Approve,
                                edited_note_title: title_override,
                                edited_note_body: body_override,
                                approved_adr_indices: approved_adrs,
                                forced_status: None,
                            };
                        }
                    }
                }
            }
        }
    }

    // ── Internals: rendering (texto plano; NO contrato) ────────────────

    fn print(&mut self, s: &str) {
        self.transcript.push_str(s);
        self.transcript.push('\n');
    }

    fn render(&mut self, r: &ReconstructionOutput) {
        self.print("");
        self.print(&render_summary_panel(r));
        self.print(&render_draft_panel(r));
        if let Some(p) = render_adr_panel(r) {
            self.print(&p);
        }
        self.print(&render_actions_panel());
    }

    // ── Internals: prompts ─────────────────────────────────────────────

    fn ask_main_action(&mut self) -> InteractiveAction {
        loop {
            let raw = (self.input)("Action [A/E/H/C]: ").trim().to_lowercase();
            if let Some(a) = main_action_key(&raw) {
                return a;
            }
            self.print("[red]Invalid choice. Use A, E, H or C.[/red]");
        }
    }

    fn ask_main_action_after_edit(&mut self) -> InteractiveAction {
        loop {
            let raw = (self.input)("Confirm [A/H/C]: ").trim().to_lowercase();
            if let Some(a) = after_edit_key(&raw) {
                return a;
            }
            self.print("[red]Invalid choice. Use A, H or C.[/red]");
        }
    }

    fn ask_handoff_reason(&mut self) -> Option<String> {
        let reason = (self.input)("Reason for handoff (empty cancels): ")
            .trim()
            .to_string();
        if reason.is_empty() {
            None
        } else {
            Some(reason)
        }
    }

    fn maybe_edit_title(&mut self, r: &ReconstructionOutput) -> Option<String> {
        let current = spec_or_session_title(r);
        let raw = (self.input)(format!("Title [{current}]: ").as_str())
            .trim()
            .to_string();
        if raw.is_empty() || raw == current {
            return None;
        }
        Some(raw)
    }

    fn maybe_edit_body(&mut self, r: &ReconstructionOutput) -> Option<String> {
        let raw = (self.input)("Edit body in $EDITOR? [y/N]: ")
            .trim()
            .to_lowercase();
        if raw != "y" && raw != "yes" {
            return None;
        }
        let seed = seed_body_for_editor(r);
        let edited = (self.editor)(seed.clone())?;
        let edited = edited.trim().to_string();
        if edited.is_empty() || edited == seed.trim() {
            return None;
        }
        Some(edited)
    }

    fn review_adrs(&mut self, r: &ReconstructionOutput) -> Option<Vec<usize>> {
        let adrs = &r.suggested_adrs;
        if adrs.is_empty() {
            return None;
        }
        let mut approved: Vec<usize> = vec![];
        for (idx, adr) in adrs.iter().enumerate() {
            let raw = (self.input)(format!("Approve ADR {idx} '{}'? [Y/n]: ", adr.title).as_str())
                .trim()
                .to_lowercase();
            if raw.is_empty() || raw == "y" || raw == "yes" {
                approved.push(idx);
            }
        }
        Some(approved)
    }
}

fn spec_or_session_title(r: &ReconstructionOutput) -> String {
    if r.spec_title.is_empty() {
        r.session_id.clone()
    } else {
        r.spec_title.clone()
    }
}

/// Seed pasado al `$EDITOR`; las ediciones del usuario lo reemplazan.
pub fn seed_body_for_editor(r: &ReconstructionOutput) -> String {
    let title = spec_or_session_title(r);
    let mut lines = vec![
        format!("# {title}"),
        String::new(),
        "<!-- Edit this body. Lines starting with <!-- are kept as comments. -->".to_string(),
        String::new(),
    ];
    for note in &r.checkpoint_notes {
        lines.push(format!("- {note}"));
    }
    format!("{}\n", lines.join("\n"))
}

// ── Renderers de texto plano (NO contrato; rich en Python) ─────────────

fn render_summary_panel(r: &ReconstructionOutput) -> String {
    let title = spec_or_session_title(r);
    let diff_count = r.diff_entries.len();
    let files = r.files_touched.len();
    let hooks = &r.verification_results;
    let hook_passed = hooks.iter().filter(|x| x.passed).count();
    let mut lines = vec![
        format!("Session: {}", r.session_id),
        format!("Spec:    {title}"),
        format!("Diff:    {diff_count} entry(ies), {files} file(s)"),
        if hooks.is_empty() {
            "Hooks:   (none declared)".to_string()
        } else {
            format!("Hooks:   {hook_passed}/{} passed", hooks.len())
        },
    ];
    if !r.out_of_scope_files.is_empty() {
        lines.push(format!(
            "Scope drift:   {} file(s)",
            r.out_of_scope_files.len()
        ));
    }
    if !r.unimplemented_files.is_empty() {
        lines.push(format!(
            "Unimplemented: {} file(s)",
            r.unimplemented_files.len()
        ));
    }
    format!("[📋 Reconstruction summary]\n{}", lines.join("\n"))
}

fn render_draft_panel(r: &ReconstructionOutput) -> String {
    let mut lines: Vec<String> = vec![format!("# {}", spec_or_session_title(r))];
    if !r.spec_goal.is_empty() {
        lines.push(String::new());
        lines.push(format!("**Goal:** {}", r.spec_goal));
    }
    if !r.diff_entries.is_empty() {
        lines.push(String::new());
        lines.push("## Changes made".into());
        for entry in &r.diff_entries {
            lines.push(format!("- {}: `{}`", entry.action, entry.path));
        }
    }
    if !r.checkpoint_notes.is_empty() {
        lines.push(String::new());
        lines.push("## Key decisions (from checkpoints)".into());
        for note in &r.checkpoint_notes {
            lines.push(format!("- {note}"));
        }
    }
    if !r.unimplemented_files.is_empty() {
        lines.push(String::new());
        lines.push("## Unimplemented (next steps)".into());
        for path in &r.unimplemented_files {
            lines.push(format!("`{path}`"));
        }
    }
    format!("[📝 DRAFT session note]\n{}", lines.join("\n"))
}

fn render_adr_panel(r: &ReconstructionOutput) -> Option<String> {
    if r.suggested_adrs.is_empty() {
        return None;
    }
    let mut out = String::from("[📋 ADRs suggested]\n#  | Title | Why suggested");
    for (idx, adr) in r.suggested_adrs.iter().enumerate() {
        let rationale: String = adr.rationale.chars().take(120).collect();
        out.push_str(&format!("\n{idx} | {} | {rationale}", adr.title));
    }
    Some(out)
}

fn render_actions_panel() -> String {
    "[⚙ Actions]\nApprove — persist everything as-is\nEdit — review title / body / ADRs one by one\nHandoff — close as HANDOFF (work incomplete)\nCancel — leave session OPEN, no changes".to_string()
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::documenter::spec_loader::AdrSuggestion;
    use std::cell::RefCell;

    fn recon() -> ReconstructionOutput {
        ReconstructionOutput {
            session_id: "2026-05-16_demo".into(),
            handoff: crate::documenter::handoff::AgentHandoff {
                agent: "cortex-documenter".into(),
                status: "partial".into(),
                verified_claims: vec![],
                unverified_claims: vec![],
                artifacts_produced: vec![],
                context_for_next: vec![],
                suggested_adr: false,
                suggested_adr_reason: String::new(),
                suggested_context_terms: vec![],
            },
            spec_path_normalized: "vault/specs/2026-05-16_demo.md".into(),
            spec_title: "Demo Spec".into(),
            spec_goal: "goal".into(),
            files_in_scope_spec: vec!["src/a.py".into()],
            acceptance_criteria: vec![],
            status_session: "open".into(),
            diff_text: String::new(),
            diff_entries: vec![],
            files_touched: vec!["src/a.py".into()],
            in_scope_files: vec!["src/a.py".into()],
            out_of_scope_files: vec![],
            unimplemented_files: vec![],
            verification_results: vec![],
            suggested_status: "handoff".into(),
            suggested_adrs: vec![],
            end_commit: "b".repeat(40),
            gitless: false,
            files_verified_by_git: vec![],
            files_declared_only: vec![],
            checkpoint_notes: vec!["hardcoded the TTL for now".into()],
            phase_line: None,
            evidence_by_phase: vec![],
            close_phase_warning: None,
        }
    }

    fn session(
        queue: &RefCell<Vec<&'static str>>,
        editor_value: Option<&'static str>,
    ) -> InteractiveSession {
        let q = queue.clone();
        let input = Box::new(move |prompt: &str| -> String {
            let mut b = q.borrow_mut();
            if b.is_empty() {
                panic!("sin más input; prompt={prompt:?}");
            }
            b.remove(0).to_string()
        });
        let ev = editor_value;
        let editor = Box::new(move |_| ev.map(|s| s.to_string()));
        InteractiveSession::new(input, editor)
    }

    #[test]
    fn approve_y_cancel() {
        let q = RefCell::new(vec!["A"]);
        let out = session(&q, None).prompt(&recon());
        assert_eq!(out.action, InteractiveAction::Approve);
        assert!(!out.cancelled());
        assert!(out.forced_status.is_none());
        assert!(out.approved_adr_indices.is_none());

        let q = RefCell::new(vec!["c"]);
        let out = session(&q, None).prompt(&recon());
        assert_eq!(out.action, InteractiveAction::Cancel);
        assert!(out.cancelled());
    }

    #[test]
    fn handoff_razon_vacia_vuelve() {
        let q = RefCell::new(vec!["H", "", "A"]);
        let out = session(&q, None).prompt(&recon());
        assert_eq!(out.action, InteractiveAction::Approve);
    }

    #[test]
    fn edit_titulo_cuerpo_y_adrs() {
        let q = RefCell::new(vec!["E", "Nuevo título", "y", "y", "A"]);
        let mut r = recon();
        r.suggested_adrs = vec![AdrSuggestion {
            title: "ADR 1".into(),
            rationale: "r".into(),
            source_checkpoint_index: 0,
            evidence: "e".into(),
            confidence: "low".into(),
        }];
        let out = session(&q, Some("# body nuevo\n")).prompt(&r);
        assert_eq!(out.action, InteractiveAction::Approve);
        assert_eq!(out.edited_note_title.as_deref(), Some("Nuevo título"));
        assert_eq!(out.edited_note_body.as_deref(), Some("# body nuevo"));
        assert_eq!(out.approved_adr_indices, Some(vec![0]));
    }

    #[test]
    fn seed_incluye_notas_de_checkpoints() {
        let seed = seed_body_for_editor(&recon());
        assert!(seed.starts_with("# Demo Spec\n"));
        assert!(seed.contains("- hardcoded the TTL for now"));
        assert!(seed.ends_with('\n'));
    }
}
