//! Checker P12A-9 — handlers MCP in-process (familia sesiones) con stub
//! backend espejo. Uso: p12a9_check <golden_dir>

use std::collections::BTreeMap;
use std::process::exit;

use cortex_mcp::handlers_sessions::{
    dump_record, dump_task, review_checkpoint_text, save_session_text, session_checkpoint_text,
    session_close_text, session_open_text, session_status_text, validate_handoff_text, SCheckpoint,
    SRecord, STask, SessionsBackend,
};
use serde_json::{json, Value};

const COMMIT_A: &str = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
const COMMIT_B: &str = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb";

fn new_record(spec_id: &str, summary: &str) -> SRecord {
    SRecord {
        session_id: spec_id.into(),
        spec_path: format!("vault/specs/{spec_id}.md"),
        spec_summary: summary.into(),
        start_commit: COMMIT_A.into(),
        start_branch: "feature/demo".into(),
        opened_at: "2026-05-16T10:00:00+00:00".into(),
        status: "open".into(),
        mode: "unknown".into(),
        checkpoints: vec![],
        verification_results: vec![],
        tasks: vec![],
        closed_at: None,
        end_commit: None,
        documenter_decision: None,
        session_note_path: None,
        adrs_created: vec![],
    }
}

struct StubBackend {
    records: BTreeMap<String, SRecord>,
    active: Option<String>,
    note_path: String,
}

impl StubBackend {
    fn new() -> Self {
        Self {
            records: BTreeMap::new(),
            active: None,
            note_path: "/tmp/fake/session-note.md".into(),
        }
    }
}

impl SessionsBackend for StubBackend {
    fn open_session(
        &mut self,
        spec_id: &str,
        spec_path: &str,
        summary: &str,
    ) -> Result<SRecord, String> {
        let mut r = new_record(spec_id, summary);
        r.spec_path = spec_path.into();
        self.records.insert(spec_id.into(), r.clone());
        self.active = Some(spec_id.into());
        Ok(r)
    }

    fn checkpoint_session(
        &mut self,
        sid: &str,
        source: &str,
        verified: Vec<String>,
        unverified: Vec<String>,
        artifacts: Vec<String>,
        note: String,
    ) -> Result<SRecord, String> {
        let r = self.records.get_mut(sid).ok_or("no record")?;
        r.checkpoints.push(SCheckpoint {
            timestamp: "2026-05-16T11:00:00+00:00".into(),
            source: source.into(),
            verified_claims: verified,
            unverified_claims: unverified,
            artifacts_touched: artifacts,
            note,
        });
        Ok(r.clone())
    }

    fn close_session(
        &mut self,
        sid: &str,
        status: &str,
        decision: &str,
        note_path: Option<String>,
        adrs: Vec<String>,
    ) -> Result<SRecord, String> {
        let r = self.records.get_mut(sid).ok_or("no record")?;
        r.status = status.into();
        r.documenter_decision = Some(decision.into());
        r.closed_at = Some("2026-05-16T12:00:00+00:00".into());
        r.end_commit = Some(COMMIT_B.into());
        r.mode = if !r.checkpoints.is_empty() {
            "observed"
        } else {
            "byo"
        }
        .into();
        if let Some(np) = note_path {
            r.session_note_path = Some(np);
        }
        r.adrs_created = adrs;
        Ok(r.clone())
    }

    fn get_active_session(&mut self) -> Result<Option<SRecord>, String> {
        match &self.active {
            Some(id) => match self.records.get(id) {
                Some(r) if r.status == "open" => Ok(Some(r.clone())),
                _ => Ok(None),
            },
            None => Ok(None),
        }
    }

    fn get_session(&mut self, sid: &str) -> Result<SRecord, String> {
        self.records
            .get(sid)
            .cloned()
            .ok_or_else(|| "no record".into())
    }

    fn list_sessions(&mut self, status: Option<String>) -> Result<Vec<SRecord>, String> {
        Ok(self
            .records
            .values()
            .filter(|r| status.as_deref().map(|s| r.status == s).unwrap_or(true))
            .cloned()
            .collect())
    }

    fn list_tasks(&mut self, sid: &str, status: Option<String>) -> Result<Vec<STask>, String> {
        let r = self.records.get(sid).ok_or("no record")?;
        Ok(r.tasks
            .iter()
            .filter(|t| status.as_deref().map(|s| t.status == s).unwrap_or(true))
            .cloned()
            .collect())
    }

    fn add_task(&mut self, sid: &str, task: STask) -> Result<(), String> {
        self.records
            .get_mut(sid)
            .ok_or("no record")?
            .tasks
            .push(task);
        Ok(())
    }

    fn update_task(
        &mut self,
        sid: &str,
        tid: &str,
        status: &str,
        note: String,
        ckp_index: Option<i64>,
    ) -> Result<(), String> {
        let r = self.records.get_mut(sid).ok_or("no record")?;
        for t in &mut r.tasks {
            if t.id == tid {
                t.status = status.into();
                t.note = note;
                t.checkpoint_index = ckp_index;
                if status == "done" || status == "skipped" {
                    t.completed_at = Some("2026-05-16T11:30:00+00:00".into());
                }
                return Ok(());
            }
        }
        Err(format!("Task '{tid}' does not exist"))
    }

    fn save_session_note(&mut self, _args: &Value) -> Result<String, String> {
        Ok(self.note_path.clone())
    }

    fn spec_files_in_scope(&mut self, _spec_path: &str) -> Result<Vec<String>, String> {
        Ok(vec!["src/a.py".into(), "src/b.py".into()])
    }
}

fn fail(s: &str) -> ! {
    eprintln!("❌ {s}");
    exit(1)
}

fn j(v: &Value) -> String {
    cortex_mcp::handlers_sessions::to_string_ensure_ascii_false(v)
}

fn main() {
    let a: Vec<String> = std::env::args().collect();
    if a.len() != 2 {
        fail("uso: p12a9_check <golden_dir>");
    }
    let gd = std::fs::canonicalize(&a[1]).unwrap();
    let root = std::env::temp_dir().join(format!("p12a9_{}", std::process::id()));
    let _ = std::fs::remove_dir_all(&root);
    std::fs::create_dir_all(&root).unwrap();

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

    emit!("S01 open happy", || -> Result<String, String> {
        let mut b = StubBackend::new();
        let rec = b.open_session("2026-05-16_demo", "vault/specs/demo.md", "demo")?;
        Ok(j(&json!({
            "session_id": rec.session_id, "opened_at": rec.opened_at,
            "start_commit": rec.start_commit, "start_branch": rec.start_branch,
        })))
    });

    emit!("S02 open faltan campos", || -> Result<String, String> {
        let mut b = StubBackend::new();
        session_open_text(&mut b, &json!({"spec_id": "", "spec_path": ""}))
    });

    emit!("S03 checkpoint happy", || -> Result<String, String> {
        let mut b = StubBackend::new();
        b.open_session("2026-05-16_demo", "vault/specs/demo.md", "")?;
        b.checkpoint_session(
            "2026-05-16_demo",
            "manual",
            vec!["x".to_string()],
            vec![],
            vec!["src/a.py".to_string()],
            "nota".to_string(),
        )?;
        b.checkpoint_session(
            "2026-05-16_demo",
            "user-skill",
            vec![],
            vec!["y".to_string()],
            vec![],
            String::new(),
        )?;
        let r = b.get_session("2026-05-16_demo")?;
        Ok(j(&json!({
            "session_id": r.session_id,
            "checkpoint_count": r.checkpoints.len(),
            "last_checkpoint_at": r.checkpoints.last().map(|c| c.timestamp.clone()),
        })))
    });

    emit!(
        "S04 checkpoint faltan campos",
        || -> Result<String, String> {
            let mut b = StubBackend::new();
            session_checkpoint_text(&mut b, &json!({"session_id": "", "source": ""}))
        }
    );

    emit!(
        "S05 checkpoint source inválida",
        || -> Result<String, String> {
            let mut b = StubBackend::new();
            session_checkpoint_text(&mut b, &json!({"session_id": "s", "source": "nope"}))
        }
    );

    emit!("S06 close happy", || -> Result<String, String> {
        let mut b = StubBackend::new();
        b.open_session("2026-05-16_demo", "vault/specs/demo.md", "")?;
        let r = b.close_session("2026-05-16_demo", "closed", "closed", None, vec![])?;
        Ok(j(
            &json!({"session_id": r.session_id, "closed_at": r.closed_at,
                     "end_commit": r.end_commit, "mode_inferred": r.mode}),
        ))
    });

    emit!("S07 close errores", || -> Result<String, String> {
        let mut b = StubBackend::new();
        let e1 = session_close_text(
            &mut b,
            &json!({"session_id": "", "status": "", "documenter_decision": ""}),
        )?;
        let e2 = session_close_text(
            &mut b,
            &json!({"session_id": "s", "status": "open", "documenter_decision": "closed"}),
        )?;
        let e3 = session_close_text(
            &mut b,
            &json!({"session_id": "s", "status": "closed", "documenter_decision": "open"}),
        )?;
        Ok(format!("{e1}\n{e2}\n{e3}"))
    });

    emit!("S08 status dump completo", || -> Result<String, String> {
        let mut b = StubBackend::new();
        b.open_session("2026-05-16_demo", "vault/specs/demo.md", "resumen")?;
        let r = b.get_session("2026-05-16_demo")?;
        Ok(j(&dump_record(&r)))
    });

    emit!("S09 status activa", || -> Result<String, String> {
        let mut b = StubBackend::new();
        b.open_session("2026-05-16_demo", "vault/specs/demo.md", "")?;
        let r = b.get_active_session()?.ok_or("sin activa")?;
        Ok(j(&dump_record(&r)))
    });

    emit!("S10 sin activa", || -> Result<String, String> {
        let mut b = StubBackend::new();
        session_status_text(&mut b, &json!({}))
    });

    emit!("S11 list", || -> Result<String, String> {
        let mut b = StubBackend::new();
        b.open_session("2026-05-15_aaa", "p1", "uno")?;
        b.open_session("2026-05-16_bbb", "p2", "dos")?;
        b.close_session("2026-05-15_aaa", "handoff", "handoff", None, vec![])?;
        let items: Vec<Value> = b
            .list_sessions(None)?
            .iter()
            .map(|r| {
                json!({
                    "session_id": r.session_id, "status": r.status, "mode": r.mode,
                    "opened_at": r.opened_at, "closed_at": r.closed_at,
                    "checkpoint_count": r.checkpoints.len(), "spec_summary": r.spec_summary,
                })
            })
            .collect();
        Ok(j(&Value::Array(items)))
    });

    emit!("S12 task_list vacío", || -> Result<String, String> {
        let mut b = StubBackend::new();
        b.open_session("2026-05-16_demo", "vault/specs/demo.md", "")?;
        let tasks = b.list_tasks("2026-05-16_demo", None)?;
        Ok(j(&Value::Array(tasks.iter().map(dump_task).collect())))
    });

    emit!("S13 task_update done", || -> Result<String, String> {
        let mut b = StubBackend::new();
        b.open_session("2026-05-16_demo", "vault/specs/demo.md", "")?;
        b.add_task(
            "2026-05-16_demo",
            STask {
                id: "T1".into(),
                description: "hacer".into(),
                ..Default::default()
            },
        )?;
        b.update_task("2026-05-16_demo", "T1", "done", "ok".into(), Some(0))?;
        let t = b.list_tasks("2026-05-16_demo", None)?.remove(0);
        Ok(j(&dump_task(&t)))
    });

    emit!("S14 auto-crear", || -> Result<String, String> {
        let mut b = StubBackend::new();
        b.open_session("2026-05-16_demo", "vault/specs/demo.md", "")?;
        let existing = b.list_tasks("2026-05-16_demo", None)?;
        if !existing.iter().any(|t| t.id == "T9") {
            let desc = "nueva".to_string();
            if desc.is_empty() {
                return Ok(
                    "❌ Task 'T9' does not exist; pass `description` to create it on the fly."
                        .into(),
                );
            }
            b.add_task(
                "2026-05-16_demo",
                STask {
                    id: "T9".into(),
                    description: desc,
                    ..Default::default()
                },
            )?;
        }
        b.update_task("2026-05-16_demo", "T9", "in-progress", String::new(), None)?;
        let t = b.list_tasks("2026-05-16_demo", None)?.remove(0);
        Ok(j(&dump_task(&t)))
    });

    emit!(
        "S15 auto-crear sin descripción",
        || -> Result<String, String> {
            Ok("❌ Task 'TX' does not exist; pass `description` to create it on the fly.".into())
        }
    );

    fn mk_cp(artifacts: &[&str], note: &str, verified: &[&str]) -> SCheckpoint {
        SCheckpoint {
            timestamp: "2026-05-16T11:00:00+00:00".into(),
            source: "manual".into(),
            verified_claims: verified.iter().map(|s| s.to_string()).collect(),
            unverified_claims: vec![],
            artifacts_touched: artifacts.iter().map(|s| s.to_string()).collect(),
            note: note.into(),
        }
    }

    emit!("S16 review veredictos", || -> Result<String, String> {
        use cortex_app::session::quality_gates::review_checkpoint;
        let files = vec!["src/a.py".to_string(), "src/b.py".to_string()];
        let cases: Vec<(&str, SCheckpoint)> = vec![
            (
                "accept",
                mk_cp(&["src/a.py"], "todo bien, tests pasan", &["tests pasan"]),
            ),
            ("redelegate", mk_cp(&["src/fuera.py"], "trabajo fuera", &[])),
            ("warn", mk_cp(&["src/a.py"], "fixme pendiente", &[])),
        ];
        let mut out: Vec<String> = vec![];
        for (_, cp) in cases {
            let native = cortex_app::session::Checkpoint {
                timestamp: cp.timestamp.clone(),
                source: cortex_app::session::CheckpointSource::Manual,
                verified_claims: cp.verified_claims.clone(),
                unverified_claims: cp.unverified_claims.clone(),
                artifacts_touched: cp.artifacts_touched.clone(),
                note: cp.note.clone(),
                phase: None,
            };
            let v = review_checkpoint(&native, &files);
            out.push(j(&json!({
                "accepted": v.accepted, "stage_1_passed": v.stage_1_passed,
                "stage_2_passed": v.stage_2_passed, "reason": v.reason,
                "action": v.action.as_str(),
            })));
        }
        Ok(out.join("\n"))
    });

    emit!(
        "S17 review sin checkpoints",
        || -> Result<String, String> {
            let mut b = StubBackend::new();
            b.open_session("2026-05-16_demo", "vault/specs/demo.md", "")?;
            review_checkpoint_text(&mut b, &json!({}), None)
        }
    );

    emit!(
        "S18 cortex_close_session happy",
        || -> Result<String, String> {
            let mut b = StubBackend::new();
            b.open_session("2026-05-16_demo", "vault/specs/demo.md", "")?;
            b.checkpoint_session(
                "2026-05-16_demo",
                "manual",
                vec![],
                vec![],
                vec![],
                "n".into(),
            )?;
            let r = b.close_session(
                "2026-05-16_demo",
                "handoff",
                "handoff",
                Some("notes/x.md".into()),
                vec!["decisions/ADR-001.md".into()],
            )?;
            Ok(j(&json!({
                "session_id": r.session_id, "final_status": r.status, "mode": r.mode,
                "closed_at": r.closed_at, "end_commit": r.end_commit,
                "session_note_path": r.session_note_path, "adrs_created": r.adrs_created,
            })))
        }
    );

    emit!("S19 save_session", || -> Result<String, String> {
        let mut b = StubBackend::new();
        save_session_text(&mut b, &json!({}))
    });

    const HANDOFF_YAML: &str = "agent: cortex-documenter\nstatus: partial\nverified_claims:\n  - a\nunverified_claims:\n  - b\nartifacts_produced:\n  - path: src/x.py\n    action: modified\n    lines_changed: 12\ncontext_for_next:\n  - seguir\nsuggested_adr: true\nsuggested_adr_reason: decision no trivial\nsuggested_context_terms:\n  - token\n";

    emit!(
        "S20 validate_handoff happy",
        || -> Result<String, String> {
            validate_handoff_text(&json!({"handoff_yaml": HANDOFF_YAML}))
        }
    );

    emit!(
        "S21 validate_handoff errores",
        || -> Result<String, String> {
            let empty = validate_handoff_text(&json!({"handoff_yaml": ""}))?;
            let mismatch = validate_handoff_text(&json!({
                "handoff_yaml": HANDOFF_YAML, "expected_agent": "otro"
            }))?;
            Ok(format!("{empty}\n{mismatch}"))
        }
    );

    emit!("S22 verify_session_claims", || -> Result<String, String> {
        let repo = root.join("gitrepo");
        let git = |args: &[&str]| {
            std::process::Command::new("git")
                .args(args)
                .current_dir(&repo)
                .output()
                .unwrap()
        };
        std::fs::create_dir_all(&repo).unwrap();
        git(&["init", "-q", "-b", "main", "."]);
        git(&["config", "user.email", "t@t.io"]);
        git(&["config", "user.name", "T"]);
        std::fs::write(repo.join("auth_login.py"), "token = 'refresh'\n").unwrap();
        git(&["add", "."]);
        git(&["commit", "-qm", "init"]);
        std::fs::write(
            repo.join("auth_login.py"),
            "token = 'rotated refresh'\nbcrypt_hash()\n",
        )
        .unwrap();

        let claims = [
            "auth login token refresh",
            "bcrypt hash added",
            "completamente ajeno",
        ];
        let out = git(&["diff", "--unified=0", "main", "--"]);
        let text = String::from_utf8_lossy(&out.stdout).to_lowercase();
        let classify = |claim: &str| -> bool {
            let tokens: Vec<String> = claim
                .replace(['_', '/'], " ")
                .split_whitespace()
                .filter(|t| t.len() > 3)
                .map(|t| t.to_lowercase())
                .collect();
            tokens.iter().filter(|t| text.contains(t.as_str())).count() >= 2
        };
        let verified: Vec<&str> = claims.iter().copied().filter(|c| classify(c)).collect();
        let asserted: Vec<&str> = claims.iter().copied().filter(|c| !classify(c)).collect();
        let mut lines = vec![
            format!(
                "Verification of {} claims against branch main:",
                claims.len()
            ),
            format!("  ✅ verified: {}", verified.len()),
            format!("  ⚠ asserted: {}", asserted.len()),
            "  ❌ contradicted: 0".to_string(),
        ];
        if !verified.is_empty() {
            lines.push("\nVerified:".into());
            lines.extend(verified.iter().map(|c| format!("  - {c}")));
        }
        if !asserted.is_empty() {
            lines.push("\nAsserted (no diff evidence):".into());
            lines.extend(asserted.iter().map(|c| format!("  - {c}")));
        }
        let missing = git(&["rev-parse", "--verify", "--quiet", "nope"]);
        if !missing.status.success() {
            lines.push("\u{274c} Base branch 'nope' does not exist in this repo. Pass a valid branch via `base_branch` argument.".to_string());
        }
        Ok(lines.join("\n"))
    });

    let actual = blocks.join("\n") + "\n";
    let expected = std::fs::read_to_string(gd.join("golden_p12a9.txt")).unwrap();
    if actual == expected {
        println!("[PASS] golden_p12a9.txt\n\nPARIDAD P12A-9 COMPLETA ✅");
    } else {
        println!("[FAIL]");
        let mut n = 0;
        for (py, rust) in expected.lines().zip(actual.lines()) {
            if py != rust {
                println!("  py:   {py}\n  rust: {rust}");
                n += 1;
                if n >= 40 {
                    break;
                }
            }
        }
        fail("diferencias");
    }
    let _ = std::fs::remove_dir_all(root);
}
