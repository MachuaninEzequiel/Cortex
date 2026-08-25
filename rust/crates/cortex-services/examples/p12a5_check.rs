//! Checker P12A-5 — SpecService + NoteService.
//! Uso: p12a5_check <golden_dir>

use std::cell::RefCell;
use std::collections::BTreeMap;
use std::path::Path;
use std::process::exit;
use std::rc::Rc;

use chrono::{TimeZone, Utc};
use cortex_app::session::{SessionRecord, VerificationHook};
use cortex_services::note::{NoteCreate, NoteService};
use cortex_services::spec::{HookInput, SpecCreate, SpecService};
use cortex_services::{EpisodicPort, EpisodicRequest, SemanticPort, SessionOpener};
use regex::Regex;
use serde_json::{json, Value};

fn fail(s: &str) -> ! {
    eprintln!("❌ {s}");
    exit(1)
}
fn py_bool(b: bool) -> &'static str {
    if b {
        "True"
    } else {
        "False"
    }
}
fn py_list(xs: &[String]) -> String {
    format!(
        "[{}]",
        xs.iter()
            .map(|x| format!("'{x}'"))
            .collect::<Vec<_>>()
            .join(", ")
    )
}
fn fixed() -> chrono::DateTime<Utc> {
    Utc.with_ymd_and_hms(2026, 6, 1, 12, 0, 0).unwrap()
}

type Events = Rc<RefCell<Vec<String>>>;
struct Sem {
    events: Events,
    fail: bool,
    indexed: Vec<String>,
    synced: usize,
}
impl Sem {
    fn new(e: Events) -> Self {
        Self {
            events: e,
            fail: false,
            indexed: vec![],
            synced: 0,
        }
    }
}
impl SemanticPort for Sem {
    fn index_file(&mut self, r: &str) -> Result<bool, String> {
        self.events.borrow_mut().push("index".into());
        if self.fail {
            return Err("semantic indexing failed".into());
        }
        self.indexed.push(r.into());
        Ok(true)
    }
    fn sync(&mut self) -> Result<usize, String> {
        self.events.borrow_mut().push("sync".into());
        self.synced += 1;
        Ok(0)
    }
}
struct Ep {
    events: Events,
    fail: bool,
    added: Vec<EpisodicRequest>,
}
impl Ep {
    fn new(e: Events) -> Self {
        Self {
            events: e,
            fail: false,
            added: vec![],
        }
    }
}
impl EpisodicPort for Ep {
    fn add(&mut self, r: EpisodicRequest) -> Result<(), String> {
        self.events.borrow_mut().push("episodic".into());
        if self.fail {
            return Err("episodic add failed".into());
        }
        self.added.push(r);
        Ok(())
    }
}
struct Sessions {
    events: Events,
    fail: bool,
    calls: RefCell<Vec<(String, String, String)>>,
}
impl SessionOpener for Sessions {
    fn open(&self, id: &str, path: &str, sum: &str) -> Result<SessionRecord, String> {
        self.events.borrow_mut().push("session".into());
        self.calls
            .borrow_mut()
            .push((id.into(), path.into(), sum.into()));
        if self.fail {
            return Err("session open failed".into());
        }
        Ok(SessionRecord {
            session_id: id.into(),
            ..Default::default()
        })
    }
}

fn req_report(xs: &[EpisodicRequest]) -> String {
    if xs.is_empty() {
        return "episodic=[]".into();
    }
    let r = &xs[0];
    format!("episodic_content={}\nepisodic_type={}\nepisodic_tags={}\nepisodic_files={}\nepisodic_meta={}",serde_json::to_string(&r.content).unwrap(),r.memory_type,py_list(&r.tags),py_list(&r.files),serde_json::to_string(&r.extra_metadata).unwrap())
}
fn fresh(root: &Path, n: &str) -> std::path::PathBuf {
    let p = root.join(n);
    std::fs::create_dir_all(&p).unwrap();
    p
}

fn main() {
    let a: Vec<String> = std::env::args().collect();
    if a.len() != 2 {
        fail("uso: p12a5_check <golden_dir>")
    }
    let gd = std::fs::canonicalize(&a[1]).unwrap();
    let root = std::env::temp_dir().join(format!("p12a5_{}", std::process::id()));
    let _ = std::fs::remove_dir_all(&root);
    std::fs::create_dir_all(&root).unwrap();
    let mut blocks = Vec::new();
    macro_rules! emit {
        ($n:expr,$b:expr) => {{
            let r: Result<String, String> = ($b)();
            blocks.push(match r {
                Ok(x) => format!("### {}\nrc=0\n{x}", $n),
                Err(e) => format!("### {}\nrc=1\nException: {e}", $n),
            });
        }};
    }
    emit!("S01 spec básica", || -> Result<String, String> {
        let v = fresh(&root, "s01");
        let ev = Rc::new(RefCell::new(vec![]));
        let mut s = Sem::new(ev.clone());
        let mut ep = Ep::new(ev);
        let mut svc = SpecService::new(&v, &mut s, &mut ep).with_context_metadata(BTreeMap::from(
            [("workspace".into(), Value::String("obra07".into()))],
        ));
        let mut x = SpecCreate::basic("Auth JWT", "Refresh tokens");
        x.requirements = vec!["rotar".into(), "revocar".into()];
        x.files_in_scope = vec!["src/auth.py".into()];
        x.tags = vec!["backend".into()];
        let r = svc.create(x, fixed())?;
        drop(svc);
        Ok(format!(
            "path={}\nsession=None\nindexed={}\n{}\n---\n{}",
            r.path.display(),
            py_list(&s.indexed),
            req_report(&ep.added),
            std::fs::read_to_string(&r.path).unwrap()
        ))
    });
    emit!("S02 proposal", || -> Result<String, String> {
        let v = fresh(&root, "s02");
        let mut out = vec![];
        for (m, c) in [("required", false), ("invalid-mode", false)] {
            let e = Rc::new(RefCell::new(vec![]));
            let mut s = Sem::new(e.clone());
            let mut ep = Ep::new(e);
            let mut svc = SpecService::new(&v, &mut s, &mut ep);
            let mut x = SpecCreate::basic("X", "Y");
            x.proposal_mode = m.into();
            x.proposal_confirmed = c;
            if let Err(er) = svc.create(x, fixed()) {
                out.push(format!("{m}=ValueError: {er}"))
            }
        }
        let e = Rc::new(RefCell::new(vec![]));
        let mut s = Sem::new(e.clone());
        let mut ep = Ep::new(e);
        let mut svc = SpecService::new(&v, &mut s, &mut ep);
        let mut x = SpecCreate::basic("Req OK", "Y");
        x.proposal_mode = "required".into();
        x.proposal_confirmed = true;
        x.remember = false;
        let r = svc.create(x, fixed())?;
        out.push(format!("confirmed_exists={}", py_bool(r.path.exists())));
        Ok(out.join("\n"))
    });
    emit!("S03 hooks tasks", || -> Result<String, String> {
        let v = fresh(&root, "s03");
        let e = Rc::new(RefCell::new(vec![]));
        let mut s = Sem::new(e.clone());
        let mut ep = Ep::new(e);
        let mut svc = SpecService::new(&v, &mut s, &mut ep);
        let mut x = SpecCreate::basic("Hooks", "Probar");
        x.verification_hooks = vec![
            HookInput::Hook(VerificationHook {
                name: "tests".into(),
                command: "pytest".into(),
                required: true,
                success_criteria: "exit code 0".into(),
                timeout_seconds: 300,
            }),
            HookInput::Dict(json!({"name":"lint","command":"ruff check .","required":false})),
        ];
        x.with_tasks = true;
        x.remember = false;
        let r = svc.create(x, fixed())?;
        drop(svc);
        Ok(format!(
            "path={}\nindexed={}\n---\n{}",
            r.path.display(),
            py_list(&s.indexed),
            std::fs::read_to_string(&r.path).unwrap()
        ))
    });
    emit!("S04 session order", || -> Result<String, String> {
        let ev = Rc::new(RefCell::new(vec![]));
        let v = fresh(&root, "s04");
        let mut s = Sem::new(ev.clone());
        let mut ep = Ep::new(ev.clone());
        let ss = Sessions {
            events: ev.clone(),
            fail: false,
            calls: RefCell::new(vec![]),
        };
        let mut svc = SpecService::new(&v, &mut s, &mut ep).with_session_opener(&ss);
        let mut x = SpecCreate::basic("Ordered", "Goal");
        x.sync_vault = true;
        let r = svc.create(x, fixed())?;
        drop(svc);
        let call = ss.calls.borrow()[0].clone();
        let ev2 = Rc::new(RefCell::new(vec![]));
        let v2 = fresh(&root, "s04fail");
        let mut s2 = Sem::new(ev2.clone());
        let mut ep2 = Ep::new(ev2.clone());
        let ss2 = Sessions {
            events: ev2.clone(),
            fail: true,
            calls: RefCell::new(vec![]),
        };
        let mut svc2 = SpecService::new(&v2, &mut s2, &mut ep2).with_session_opener(&ss2);
        let r2 = svc2.create(SpecCreate::basic("Resilient", ""), fixed())?;
        Ok(format!("events={}\nsession_id={}\nopen_summary={}\nfail_events={}\nfail_session=None\nfail_exists={}",py_list(&ev.borrow()),r.session.unwrap().session_id,call.2,py_list(&ev2.borrow()),py_bool(r2.path.exists())))
    });
    emit!("S05 hooks errors", || -> Result<String, String> {
        let v = fresh(&root, "s05");
        let mut out = vec![];
        let e = Rc::new(RefCell::new(vec![]));
        let mut s = Sem::new(e.clone());
        let mut ep = Ep::new(e);
        let mut svc = SpecService::new(&v, &mut s, &mut ep);
        let mut x = SpecCreate::basic("Dup", "x");
        x.verification_hooks = vec![
            HookInput::Dict(json!({"name":"tests","command":"a"})),
            HookInput::Dict(json!({"name":"tests","command":"b"})),
        ];
        if let Err(er) = svc.create(x, fixed()) {
            out.push(format!("dup=ValueError: {er}"))
        }
        let mut y = SpecCreate::basic("Bad", "x");
        y.verification_hooks = vec![HookInput::Dict(json!({"name":"tests"}))];
        if svc.create(y, fixed()).is_err() {
            out.push("invalid=ValidationError: {{HOOK_ERR}}".into())
        }
        Ok(out.join("\n"))
    });
    emit!("S06 note básica", || -> Result<String, String> {
        let v = fresh(&root, "n06");
        let e = Rc::new(RefCell::new(vec![]));
        let mut s = Sem::new(e.clone());
        let mut ep = Ep::new(e);
        let mut svc = NoteService::new(&v, &mut s, &mut ep).with_context_metadata(BTreeMap::from(
            [("workspace".into(), Value::String("obra07".into()))],
        ));
        let mut x = NoteCreate::basic("Happy", "Survive");
        x.changes_made = vec!["uno".into(), "dos".into()];
        x.files_touched = vec!["src/a.py".into()];
        x.key_decisions = vec!["usar Rust".into()];
        x.tags = vec!["backend".into()];
        let p = svc.create_with_id(x, "abcdef123456", fixed())?;
        drop(svc);
        Ok(format!(
            "path={}\nindexed={}\n{}\n---\n{}",
            p.display(),
            py_list(&s.indexed),
            req_report(&ep.added),
            std::fs::read_to_string(&p).unwrap()
        ))
    });
    emit!("S07 note handoff", || -> Result<String, String> {
        let v = fresh(&root, "n07");
        let e = Rc::new(RefCell::new(vec![]));
        let mut s = Sem::new(e.clone());
        let mut ep = Ep::new(e);
        let mut svc = NoteService::new(&v, &mut s, &mut ep);
        let mut x = NoteCreate::basic("Handoff", "seguir");
        x.handoff = true;
        x.blockers = vec!["B1".into()];
        x.verified_state = vec!["tests".into()];
        x.unverified_claims = vec!["perf".into()];
        x.suggested_skills = vec!["rust".into()];
        x.tags = vec!["x".into()];
        x.remember = false;
        x.gitless = true;
        x.task_type = "bugfix".into();
        x.tasks = vec![json!({"id":"T1","status":"done"})];
        x.tasks_total = 1;
        x.tasks_done = 1;
        let p = svc.create_with_id(x, "abcdef123456", fixed())?;
        drop(svc);
        Ok(format!(
            "path={}\nindexed={}\n---\n{}",
            p.display(),
            py_list(&s.indexed),
            std::fs::read_to_string(&p).unwrap()
        ))
    });
    emit!("S08 rollback semantic", || -> Result<String, String> {
        let v = fresh(&root, "n08");
        let e = Rc::new(RefCell::new(vec![]));
        let mut s = Sem::new(e.clone());
        s.fail = true;
        let mut ep = Ep::new(e);
        let mut svc = NoteService::new(&v, &mut s, &mut ep);
        let mut out = vec![];
        if let Err(er) = svc.create_with_id(
            NoteCreate::basic("Rollback semantic", "x"),
            "abcdef123456",
            fixed(),
        ) {
            out.push(format!("error=RuntimeError: {er}"))
        }
        let files = std::fs::read_dir(v.join("sessions"))
            .map(|rd| {
                rd.flatten()
                    .filter(|x| x.path().extension().and_then(|x| x.to_str()) == Some("md"))
                    .map(|x| x.path().display().to_string())
                    .collect()
            })
            .unwrap_or_else(|_| Vec::<String>::new());
        out.push(format!("files={}", py_list(&files)));
        Ok(out.join("\n"))
    });
    emit!("S09 rollback episodic", || -> Result<String, String> {
        let v = fresh(&root, "n09");
        let e = Rc::new(RefCell::new(vec![]));
        let mut s = Sem::new(e.clone());
        let mut ep = Ep::new(e);
        ep.fail = true;
        let mut svc = NoteService::new(&v, &mut s, &mut ep);
        let mut out = vec![];
        if let Err(er) = svc.create_with_id(
            NoteCreate::basic("Rollback episodic", "x"),
            "abcdef123456",
            fixed(),
        ) {
            out.push(format!("error=RuntimeError: {er}"))
        }
        let files = std::fs::read_dir(v.join("sessions"))
            .map(|rd| {
                rd.flatten()
                    .filter(|x| x.path().extension().and_then(|x| x.to_str()) == Some("md"))
                    .map(|x| x.path().display().to_string())
                    .collect()
            })
            .unwrap_or_else(|_| Vec::<String>::new());
        out.push(format!("files={}", py_list(&files)));
        Ok(out.join("\n"))
    });
    emit!("S10 note no-remember sync", || -> Result<String, String> {
        let ev = Rc::new(RefCell::new(vec![]));
        let v = fresh(&root, "n10");
        let mut s = Sem::new(ev.clone());
        let mut ep = Ep::new(ev.clone());
        let mut svc = NoteService::new(&v, &mut s, &mut ep);
        let mut x = NoteCreate::basic("No remember", "x");
        x.remember = false;
        x.sync_vault = true;
        let p = svc.create_with_id(x, "abcdef123456", fixed())?;
        drop(svc);
        Ok(format!(
            "events={}\nepisodic={}\nexists={}",
            py_list(&ev.borrow()),
            py_list(&[]),
            py_bool(p.exists())
        ))
    });
    let mut actual = blocks.join("");
    actual = normalize(actual, &root);
    if !actual.ends_with('\n') {
        actual.push('\n')
    }
    let expected = std::fs::read_to_string(gd.join("golden_p12a5.txt")).unwrap();
    if actual == expected {
        println!("[PASS] golden_p12a5.txt\n\nPARIDAD P12A-5 COMPLETA ✅")
    } else {
        println!("[FAIL]");
        for (a, b) in expected
            .lines()
            .zip(actual.lines())
            .filter(|(a, b)| a != b)
            .take(30)
        {
            println!("  py:   {a}\n  rust: {b}")
        }
        fail("diferencias")
    }
    let _ = std::fs::remove_dir_all(root);
}
fn normalize(mut s: String, root: &Path) -> String {
    s = s.replace(&root.display().to_string(), "{{ROOT}}");
    let ts = Regex::new(r"(created_at|updated_at): '[^']+'").unwrap();
    s = ts.replace_all(&s, "$1: '{{TS}}'").into_owned();
    let fp = Regex::new(r"fingerprint: [0-9a-f]{64}").unwrap();
    s = fp.replace_all(&s, "fingerprint: {{FP}}").into_owned();
    let sid = Regex::new(r"[0-9a-f]{12}").unwrap();
    s = sid.replace_all(&s, "{{SID}}").into_owned();
    let date = Regex::new(r"\d{4}-\d{2}-\d{2}").unwrap();
    date.replace_all(&s, "{{DATE}}").into_owned()
}
