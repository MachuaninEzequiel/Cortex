//! Checker P12A-8 — documenter::interactive (máquina de estados).
//! Uso: p12a8_check <golden_dir>

use std::cell::RefCell;
use std::process::exit;
use std::rc::Rc;

use cortex_app::documenter::handoff::AgentHandoff;
use cortex_app::documenter::interactive::{seed_body_for_editor, InteractiveSession};
use cortex_app::documenter::spec_loader::AdrSuggestion;
use cortex_app::documenter::ReconstructionOutput;

fn fail(s: &str) -> ! {
    eprintln!("❌ {s}");
    exit(1)
}

/// repr() de Python para strings: comillas simples, escapes \\ y \\n.
fn py_repr(s: &str) -> String {
    let mut out = String::from("'");
    for c in s.chars() {
        match c {
            '\'' => out.push_str("\\'"),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            c => out.push(c),
        }
    }
    out.push('\'');
    out
}

struct SessionFixture;

impl SessionFixture {
    fn reconstruction(
        suggested_adrs: Vec<AdrSuggestion>,
        unimplemented: Vec<String>,
        out_of_scope: Vec<String>,
    ) -> ReconstructionOutput {
        ReconstructionOutput {
            session_id: "2026-05-16_demo".into(),
            handoff: AgentHandoff {
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
            spec_goal: "Validate the interactive prompt".into(),
            files_in_scope_spec: vec!["src/a.py".into()],
            acceptance_criteria: vec!["a.py is touched".into()],
            status_session: "open".into(),
            diff_text: "diff --git a/src/a.py b/src/a.py\n+x\n".into(),
            diff_entries: vec![],
            files_touched: vec!["src/a.py".into()],
            in_scope_files: vec!["src/a.py".into()],
            out_of_scope_files: out_of_scope,
            unimplemented_files: unimplemented,
            verification_results: vec![],
            suggested_status: "handoff".into(),
            suggested_adrs,
            end_commit: "b".repeat(40),
            gitless: false,
            files_verified_by_git: vec![],
            files_declared_only: vec![],
            checkpoint_notes: vec!["hardcoded the TTL for now".into()],
        }
    }
}

fn adrs() -> Vec<AdrSuggestion> {
    vec![
        AdrSuggestion {
            title: "ADR 1".into(),
            rationale: "rationale 1".into(),
            source_checkpoint_index: 0,
            evidence: "evidence 1".into(),
            confidence: "low".into(),
        },
        AdrSuggestion {
            title: "ADR 2".into(),
            rationale: "rationale 2".into(),
            source_checkpoint_index: 0,
            evidence: "evidence 2".into(),
            confidence: "low".into(),
        },
    ]
}

type Queue = Rc<RefCell<Vec<String>>>;

fn make_session(inputs: &[&str], editor_value: Option<&str>) -> (InteractiveSession, Queue) {
    let queue: Queue = Rc::new(RefCell::new(inputs.iter().map(|s| s.to_string()).collect()));
    let q_in = queue.clone();
    let input_provider = Box::new(move |prompt: &str| -> String {
        let mut q = q_in.borrow_mut();
        if q.is_empty() {
            panic!("sin más input; prompt={prompt:?}");
        }
        q.remove(0)
    });
    let editor_value: Option<String> = editor_value.map(str::to_string);
    let editor = Box::new(move |_seed: String| -> Option<String> { editor_value.clone() });
    (InteractiveSession::new(input_provider, editor), queue)
}

fn result_repr(out: &cortex_app::documenter::interactive::InteractiveResult) -> String {
    let forced = out
        .forced_status
        .as_ref()
        .map(|s| s.as_str().to_string())
        .unwrap_or_else(|| "None".into());
    let body = match &out.edited_note_body {
        Some(b) => py_repr(b),
        None => "None".into(),
    };
    let title = match &out.edited_note_title {
        Some(t) => py_repr(t),
        None => "None".into(),
    };
    let adrs = match &out.approved_adr_indices {
        Some(v) => format!(
            "[{}]",
            v.iter()
                .map(|i| i.to_string())
                .collect::<Vec<_>>()
                .join(", ")
        ),
        None => "None".into(),
    };
    format!(
        "action={}\ncancelled={}\nforced={forced}\ntitle={title}\nbody={body}\nadrs={adrs}",
        out.action.as_str(),
        if out.cancelled() { "True" } else { "False" },
    )
}

const EMPTY: (&[&str], Option<&str>) = (&[], None);

fn main() {
    let a: Vec<String> = std::env::args().collect();
    if a.len() != 2 {
        fail("uso: p12a8_check <golden_dir>");
    }
    let gd = std::fs::canonicalize(&a[1]).unwrap();
    // El checker no escribe archivos; root sólo para uniformidad.
    let _root = std::env::temp_dir().join(format!("p12a8_{}", std::process::id()));

    let mut blocks: Vec<String> = Vec::new();
    macro_rules! emit {
        ($n:expr, $b:expr) => {{
            let r: Result<String, String> = ($b)();
            blocks.push(match r {
                Ok(x) => format!("### {}\nrc=0\n{x}", $n),
                Err(e) => format!("### {}\nrc=1\nException: {e}", $n),
            });
        }};
    }

    macro_rules! scenario {
        ($name:expr, $inputs:expr, $editor:expr, $recon:expr) => {{
            emit!($name, || -> Result<String, String> {
                let (mut sess, q) = make_session($inputs, $editor);
                let recon = $recon;
                let out = sess.prompt(&recon);
                Ok(format!(
                    "{}\ninputs_left={}",
                    result_repr(&out),
                    q.borrow().len()
                ))
            });
        }};
    }

    let plain = || SessionFixture::reconstruction(vec![], vec![], vec![]);
    let with_adrs = || SessionFixture::reconstruction(adrs(), vec![], vec![]);

    scenario!("S01 approve", &["A"], EMPTY.1, plain());
    scenario!(
        "S02 approve case-insensitive",
        &["approve"],
        EMPTY.1,
        plain()
    );
    scenario!("S03 cancel", &["C"], EMPTY.1, plain());
    scenario!(
        "S04 handoff con razón",
        &["H", "bcrypt incompatible with Lambda"],
        EMPTY.1,
        plain()
    );
    scenario!(
        "S05 handoff razón vacía vuelve al menú",
        &["H", "", "A"],
        EMPTY.1,
        plain()
    );
    scenario!(
        "S06 input inválido re-promptea",
        &["x", "?", "A"],
        EMPTY.1,
        plain()
    );
    scenario!(
        "S07 edit skip todo luego approve",
        &["E", "", "N", "A"],
        EMPTY.1,
        plain()
    );
    scenario!(
        "S08 edit reemplaza título",
        &["E", "Brand new title", "N", "A"],
        EMPTY.1,
        plain()
    );
    scenario!(
        "S09 edit cuerpo vía editor",
        &["E", "", "y", "A"],
        Some("# Brand new body\n\nNew content here.\n"),
        plain()
    );
    scenario!("S10 editor abortado", &["E", "", "y", "A"], None, plain());
    scenario!(
        "S11 edit luego cancel",
        &["E", "New Title", "N", "C"],
        EMPTY.1,
        plain()
    );
    scenario!(
        "S12 edit luego handoff",
        &["E", "", "N", "H", "blockers exist"],
        EMPTY.1,
        plain()
    );
    scenario!(
        "S13 approve default mantiene ADRs",
        &["A"],
        EMPTY.1,
        with_adrs()
    );
    scenario!(
        "S14 rechaza un ADR",
        &["E", "", "N", "y", "n", "A"],
        EMPTY.1,
        with_adrs()
    );
    scenario!(
        "S15 aprueba todos explícito",
        &["E", "", "N", "", "y", "A"],
        EMPTY.1,
        with_adrs()
    );

    emit!("S18 seed body", || -> Result<String, String> {
        Ok(seed_body_for_editor(&plain()))
    });

    emit!("S19 agotamiento de cola", || -> Result<String, String> {
        std::panic::set_hook(Box::new(|_| {}));
        let (mut sess, _q) = make_session(&["x", "zzz", "h"], None);
        let recon = plain();
        let res = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| sess.prompt(&recon)));
        match res {
            Err(payload) => {
                let msg = payload
                    .downcast_ref::<String>()
                    .cloned()
                    .or_else(|| payload.downcast_ref::<&str>().map(|s| s.to_string()))
                    .unwrap_or_default();
                Ok(format!(
                    "exhausted_ok={}",
                    if msg.contains("sin más input") {
                        "True"
                    } else {
                        "False"
                    }
                ))
            }
            Ok(_) => Err("unexpected".to_string()),
        }
    });

    let actual = blocks.join("\n") + "\n";
    let expected = std::fs::read_to_string(gd.join("golden_p12a8.txt")).unwrap();
    if actual == expected {
        println!("[PASS] golden_p12a8.txt\n\nPARIDAD P12A-8 COMPLETA ✅");
    } else {
        println!("[FAIL]");
        let mut n = 0;
        for (py, rust) in expected.lines().zip(actual.lines()) {
            if py != rust {
                println!("  py:   {py}\n  rust: {rust}");
                n += 1;
                if n >= 30 {
                    break;
                }
            }
        }
        fail("diferencias");
    }
}
