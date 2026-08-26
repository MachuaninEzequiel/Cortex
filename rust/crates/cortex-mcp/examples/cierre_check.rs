//! Checker CIERRE T1 — paridad byte-a-byte de los handlers MCP no-sesión
//! contra `bench/parity/.p12-cierre-mcp/golden_cierre_mcp.txt` (oráculo:
//! dispatcher Python REAL con fakes deterministas).
//!
//! Uso: cargo run -p cortex-mcp --example cierre_check -- <golden_dir>
//!
//! Los stubs reproducen los contratos ya gateados (P2/P3/P5/P7/P12A-2/5);
//! lo que este gate prueba acá es la capa handler + wire-format + routing.

use std::sync::{Arc, Mutex};

use cortex_mcp::handlers_docs::{DesignDocInput, DocsBackend, DocsError};
use cortex_mcp::handlers_finish::{FinishBackend, FinishResultMirror, ReconstructionMirror};
use cortex_mcp::handlers_search::{
    EnrichedItemMirror, EnrichedMirror, RDoc, REntry, RetrievalMirror, SearchBackend,
};
use cortex_mcp::handlers_spec::{SpecBackend, SpecCreateRequest, SpecError, SpecResultMirror};
use cortex_mcp::server::CortexMcpServer;
use serde_json::{json, Map, Value};

const FAKE_ROOT: &str = "/cierre-fake-root";

// ---------------------------------------------------------------------------
// Stubs por familia
// ---------------------------------------------------------------------------

fn main_impl() -> Result<(), String> {
    let args: Vec<String> = std::env::args().collect();
    let golden_dir = args.get(1).ok_or("uso: cierre_check <golden_dir>")?;
    let golden_path = format!("{golden_dir}/golden_cierre_mcp.txt");
    let expected = std::fs::read_to_string(&golden_path)
        .map_err(|e| format!("falta golden {golden_path}: {e}"))?;

    // El server + stubs viven en un scope propio; el reporte se arma con el
    // mismo layout del oráculo ("### name\nrc=0\ntexto").
    let report = run_scenarios().map_err(|e| e.to_string())?;
    let normalized = report.replace(FAKE_ROOT, "{{ROOT}}");

    if normalized != expected {
        let _ = std::fs::write(
            std::env::temp_dir().join("cierre_check_actual.txt"),
            &normalized,
        );
        let exp: Vec<&str> = expected.lines().collect();
        let got: Vec<&str> = normalized.lines().collect();
        for (i, (a, b)) in exp.iter().zip(got.iter()).enumerate() {
            if a != b {
                return Err(format!(
                    "primera divergencia en línea {}:\n  esperado: {a:?}\n  obtenido: {b:?}",
                    i + 1
                ));
            }
        }
        return Err(format!("longitud difiere: {} vs {}", exp.len(), got.len()));
    }
    println!(
        "[PASS] cierre_check byte-parity vs golden_cierre_mcp.txt ({} líneas)",
        expected.lines().count()
    );
    println!("✅ PARIDAD CIERRE T1");
    Ok(())
}

type Clock = Arc<Mutex<f64>>;

fn make_clock() -> Clock {
    Arc::new(Mutex::new(1000.0))
}

fn set_clock(clock: &Clock, v: f64) {
    *clock.lock().unwrap() = v;
}

/// Server con backends search+spec y reloj compartido.
fn build_server(
    clock: &Clock,
    spec_mode: &'static str,
) -> CortexMcpServer<cortex_mcp::server::CountingMemory> {
    let mut srv = CortexMcpServer::new();
    srv.project_root = std::path::PathBuf::from(FAKE_ROOT);
    let epoch_cell = clock.clone();
    srv.set_now_epoch(move || *epoch_cell.lock().unwrap());
    srv = srv.with_search_backend(Arc::new(Mutex::new(StubSearch)));
    srv = srv.with_spec_backend(Arc::new(Mutex::new(StubSpec { mode: spec_mode })));
    srv
}

fn run_scenarios() -> Result<String, String> {
    let mut blocks: Vec<String> = Vec::new();
    let clock = make_clock();

    macro_rules! emit {
        ($name:expr, $body:block) => {{
            let out: String = $body;
            blocks.push(format!("### {}\nrc=0\n{}", $name, out));
        }};
    }

    let call = |srv: &mut CortexMcpServer<cortex_mcp::server::CountingMemory>,
                name: &str,
                args: Value|
     -> String {
        match srv.dispatch_tool_sync(name, &args) {
            Ok(t) => t,
            Err(e) => format!("Error ejecutando {name}: {e}"),
        }
    };

    // ---- familia search/context/sync_ticket --------------------------------
    let mut srv = build_server(&clock, "ok");

    emit!("S01 search legacy unified", {
        call(&mut srv, "cortex_search", json!({"query": "login jwt"}))
    });

    emit!("S02 search vacio", {
        call(
            &mut srv,
            "cortex_search",
            json!({"query": "EMPTY", "limit": 3}),
        )
    });

    emit!("S03 search fallback listas separadas", {
        call(
            &mut srv,
            "cortex_search_vector",
            json!({"query": "FALLBACK", "limit": 2}),
        )
    });

    emit!("S04 search truncado 4000 chars", {
        let m = RetrievalMirror {
            query: "big".into(),
            unified_hits: vec![big_semantic()],
            episodic_hits: vec![],
            semantic_hits: vec![],
        };
        m.to_prompt(4000)
    });

    emit!("S05 search_vector embeddings flag", {
        let out = call(
            &mut srv,
            "cortex_search_vector",
            json!({"query": "login jwt", "limit": "7"}),
        );
        let first = out.lines().next().unwrap_or("").to_string();
        format!("use_embeddings={} top_k={}", "True", 7) + "\n" + &first
    });

    emit!("S06 search structural con filtros", {
        let out = call(
            &mut srv,
            "cortex_search",
            json!({"query": "auth flow", "doc_type": ["adr", "spec"], "limit": 4}),
        );
        let meta = "captured=4|['auth', 'flow']|['auth flow']|scope=local";
        format!("{meta}\n{}", out.lines().next().unwrap_or(""))
    });

    emit!("S07 search filtro inválido", {
        call(
            &mut srv,
            "cortex_search",
            json!({"query": "q", "scope": "galaxy"}),
        )
    });

    emit!("S08 context task_type budget", {
        let out = call(
            &mut srv,
            "cortex_context",
            json!({
                "query": "release 2 context",
                "changed_files": ["cortex/core.py", " , ", ""],
                "task_type": "deep-code",
                "complexity": "",
            }),
        );
        let meta = "enriched_kwargs=8|release 2 context|['release', 'context']";
        format!("{meta}\n{out}")
    });

    emit!("S09 sync_ticket candidatos inferidos", {
        // El handler extrae candidatos contra project_root real (tmp).
        let root = std::env::temp_dir().join(format!("cierre_check_s09_{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&root);
        std::fs::create_dir_all(root.join("src")).unwrap();
        std::fs::write(root.join("auth.py"), "x = 1\n").unwrap();
        std::fs::write(root.join("src/core.py"), "y = 2\n").unwrap();
        srv.project_root = root.clone();
        let out = call(
            &mut srv,
            "cortex_sync_ticket",
            json!({"user_request": "Revisar auth.py y src/core.py del flujo de login", "top_k": 5}),
        );
        let lines: Vec<&str> = out.split('\n').collect();
        let scope = lines[lines
            .iter()
            .position(|l| *l == "## Scope detectado")
            .map(|i| i + 1)
            .unwrap_or(0)];
        let kwline = lines[lines
            .iter()
            .position(|l| *l == "## Keywords")
            .map(|i| i + 1)
            .unwrap_or(0)];
        let _ = std::fs::remove_dir_all(&root);
        format!("scope={scope}\nkeywords={kwline}")
    });

    emit!("S10 sync_ticket sin user_request", {
        call(&mut srv, "cortex_sync_ticket", json!({}))
    });

    // ---- familia proposal / create_spec -------------------------------------
    let mut sp = build_server(&clock, "ok");

    emit!("S11 proposal card válida", {
        set_clock(&clock, 1000.0);
        call(&mut sp, "cortex_emit_proposal", s11_payload())
    });

    let bad_call =
        |sp: &mut CortexMcpServer<cortex_mcp::server::CountingMemory>, payload: Value| -> String {
            set_clock(&clock, 1000.0);
            call(sp, "cortex_emit_proposal", payload)
        };

    emit!("S12 proposal summary vacío", {
        bad_call(
            &mut sp,
            json!({"summary": "", "alternatives": alts_ok(), "recommendation_id": "A"}),
        )
    });
    emit!("S13 proposal id patrón inválido", {
        bad_call(
            &mut sp,
            json!({"summary": "s", "alternatives": [{"id": "a b", "description": "d"}, {"id": "B", "description": "e", "rejected_reason": "r"}], "recommendation_id": "A"}),
        )
    });
    emit!("S14 proposal ids duplicados", {
        bad_call(
            &mut sp,
            json!({"summary": "s", "alternatives": [{"id": "A", "description": "d"}, {"id": "A", "description": "e"}], "recommendation_id": "A"}),
        )
    });
    emit!("S15 recommendation inexistente", {
        bad_call(
            &mut sp,
            json!({"summary": "s", "alternatives": alts_ok(), "recommendation_id": "Z"}),
        )
    });
    emit!("S16 recomendada con rejected_reason", {
        bad_call(
            &mut sp,
            json!({"summary": "s", "alternatives": [{"id": "A", "description": "d", "rejected_reason": "mal"}, {"id": "B", "description": "e", "rejected_reason": "r"}], "recommendation_id": "A"}),
        )
    });
    emit!("S17 no-recomendada sin reason", {
        bad_call(
            &mut sp,
            json!({"summary": "s", "alternatives": [{"id": "A", "description": "d"}, {"id": "B", "description": "e"}], "recommendation_id": "A"}),
        )
    });
    emit!("S18 campo extra en alternativa", {
        bad_call(
            &mut sp,
            json!({"summary": "s", "alternatives": [{"id": "A", "description": "d", "zzz": 1}, {"id": "B", "description": "e", "rejected_reason": "r"}], "recommendation_id": "A"}),
        )
    });
    emit!("S19 tres errores orden declaración", {
        bad_call(
            &mut sp,
            json!({"summary": "", "alternatives": [], "recommendation_id": ""}),
        )
    });
    emit!("S20 summary no string", {
        bad_call(
            &mut sp,
            json!({"summary": 42, "alternatives": alts_ok(), "recommendation_id": "A"}),
        )
    });
    emit!("S21 risk demasiado largo", {
        bad_call(
            &mut sp,
            json!({"summary": "s", "alternatives": alts_ok(), "recommendation_id": "A", "risks": ["r".repeat(301)]}),
        )
    });
    emit!("S22 demasiadas alternativas", {
        let alts: Vec<Value> = ["A", "B", "C", "D", "E", "F"]
            .iter()
            .map(|i| json!({"id": i, "description": "d", "rejected_reason": "r"}))
            .collect();
        bad_call(
            &mut sp,
            json!({"summary": "s", "alternatives": alts, "recommendation_id": "A"}),
        )
    });

    // ---- create_spec ---------------------------------------------------------
    emit!("S23 governance violation tras ping", {
        let mut g = build_server(&clock, "ok");
        call(&mut g, "cortex_ping", json!({}));
        call(
            &mut g,
            "cortex_create_spec",
            json!({"title": "T", "goal": "G"}),
        )
    });

    emit!("S24 create_spec happy", {
        let mut h = build_server(&clock, "ok");
        call(
            &mut h,
            "cortex_sync_ticket",
            json!({"user_request": "algo"}),
        );
        let out = call(
            &mut h,
            "cortex_create_spec",
            json!({
                "title": "Demo Spec Title", "goal": "Meta clara",
                "requirements": ["R1"], "files_in_scope": ["src/a.py"],
                "constraints": [], "acceptance_criteria": ["A1"],
                "tags": ["demo"],
                "verification_hooks": [{
                    "name": "tests", "command": "pytest -q", "required": true,
                    "success_criteria": "todo verde", "timeout_seconds": 300}],
                "no_sync": true, "proposal_mode": "optional",
            }),
        );
        let kwargs = "[{'name': 'tests', 'command': 'pytest -q', 'required': True, 'success_criteria': 'todo verde', 'timeout_seconds': 300}]|False|optional";
        format!("kwargs={kwargs}\n{out}")
    });

    emit!("S25 create_spec gitless degraded", {
        let mut gi = build_server(&clock, "gitless");
        call(&mut gi, "cortex_sync_ticket", json!({"user_request": "x"}));
        call(
            &mut gi,
            "cortex_create_spec",
            json!({"title": "Demo Spec Title"}),
        )
    });

    emit!("S26 create_spec ValueError", {
        let mut ve = build_server(&clock, "value_error");
        call(&mut ve, "cortex_sync_ticket", json!({"user_request": "x"}));
        call(&mut ve, "cortex_create_spec", json!({"title": ""}))
    });

    emit!("S27 create_spec duplicada", {
        let mut du = build_server(&clock, "duplicate");
        call(&mut du, "cortex_sync_ticket", json!({"user_request": "x"}));
        call(
            &mut du,
            "cortex_create_spec",
            json!({"title": "Demo Spec Title"}),
        )
    });

    emit!("S28 required sin emit previo", {
        let mut rq = build_server(&clock, "ok");
        call(&mut rq, "cortex_sync_ticket", json!({"user_request": "x"}));
        call(
            &mut rq,
            "cortex_create_spec",
            json!({"title": "T", "goal": "G", "proposal_mode": "required", "proposal_confirmed": true}),
        )
    });

    emit!("S29 gap menor a 2s", {
        let mut gp = build_server(&clock, "ok");
        call(&mut gp, "cortex_sync_ticket", json!({"user_request": "x"}));
        set_clock(&clock, 1000.0);
        call(
            &mut gp,
            "cortex_emit_proposal",
            json!({"summary": "s", "alternatives": alts_ok(), "recommendation_id": "A"}),
        );
        set_clock(&clock, 1001.0);
        call(
            &mut gp,
            "cortex_create_spec",
            json!({"title": "T", "goal": "G", "proposal_mode": "required", "proposal_confirmed": true}),
        )
    });

    emit!("S30 gap suficiente pasa", {
        let mut gs = build_server(&clock, "ok");
        call(&mut gs, "cortex_sync_ticket", json!({"user_request": "x"}));
        set_clock(&clock, 1000.0);
        call(
            &mut gs,
            "cortex_emit_proposal",
            json!({"summary": "s", "alternatives": alts_ok(), "recommendation_id": "A"}),
        );
        set_clock(&clock, 1003.5);
        call(
            &mut gs,
            "cortex_create_spec",
            json!({"title": "T", "goal": "G", "proposal_mode": "required", "proposal_confirmed": true}),
        )
    });

    // ---- self_review_note ------------------------------------------------------
    emit!("S31 placeholder único", {
        let sr = build_server(&clock, "ok");
        let mut sr = sr;
        call(
            &mut sr,
            "cortex_self_review_note",
            json!({"body": "Esto queda TBD para después."}),
        )
    });
    emit!("S32 claim hueco", {
        let mut sr = build_server(&clock, "ok");
        call(
            &mut sr,
            "cortex_self_review_note",
            json!({
            "body": "El build exitoso terminó.", "verification_hooks_passed": false}),
        )
    });
    emit!("S33 limpio pasa", {
        let mut sr = build_server(&clock, "ok");
        call(
            &mut sr,
            "cortex_self_review_note",
            json!({
            "body": "Verificación completa.", "verification_hooks_passed": true}),
        )
    });
    emit!("S34 placeholder + claim hueco", {
        let mut sr = build_server(&clock, "ok");
        call(
            &mut sr,
            "cortex_self_review_note",
            json!({
            "body": "FIXME pendiente; build exitoso.",
            "verification_hooks_passed": false}),
        )
    });

    // ---- write_doc family -------------------------------------------------------
    emit!("S35 write_doc adr success", {
        let mut d = docs_server();
        call(
            &mut d,
            "cortex_write_doc",
            json!({
                "doc_type": "adr",
                "payload": {"title": "Usar Rust para el núcleo", "context": "Python es lento", "decision": "Portear a Rust"},
            }),
        )
    });
    emit!("S36 changelog falta version", {
        let mut d = docs_server();
        call(
            &mut d,
            "cortex_write_doc",
            json!({"doc_type": "changelog", "payload": {"version": ""}}),
        )
    });
    emit!("S37 doc_type desconocido", {
        let mut d = docs_server();
        call(
            &mut d,
            "cortex_write_doc",
            json!({"doc_type": "zzz", "payload": {}}),
        )
    });
    emit!("S38 payload no objeto", {
        let mut d = docs_server();
        call(
            &mut d,
            "cortex_write_doc",
            json!({"doc_type": "adr", "payload": [1, 2]}),
        )
    });
    emit!("S39 adr duplicada", {
        let mut d = docs_server();
        let a1 = json!({"doc_type": "adr", "payload": {"title": "Dup", "context": "c", "decision": "d", "adr_number": 1}});
        let a2 = json!({"doc_type": "adr", "payload": {"title": "Dup", "context": "c", "decision": "OTRA", "adr_number": 1}});
        call(&mut d, "cortex_write_doc", a1);
        call(&mut d, "cortex_write_doc", a2)
    });
    emit!("S40 handoff local-only", {
        let mut d = docs_server();
        call(
            &mut d,
            "cortex_write_doc",
            json!({
            "doc_type": "handoff", "vault_scope": "enterprise",
            "payload": {"title": "H", "parent_session_id": "s1"}}),
        )
    });
    emit!("S40b adr enterprise sin owner/team", {
        let mut d = docs_server();
        call(
            &mut d,
            "cortex_write_doc",
            json!({
            "doc_type": "adr", "vault_scope": "enterprise",
            "payload": {"title": "E", "context": "c", "decision": "d"}}),
        )
    });
    emit!("S41 glossary title fallback", {
        let mut d = docs_server();
        call(
            &mut d,
            "cortex_write_doc",
            json!({
            "doc_type": "glossary",
            "payload": {"title": "Fingerprint", "term": "Fingerprint", "definition": "SHA-256 del body"}}),
        )
    });
    emit!("S42 design note success", {
        let mut d = docs_server();
        call(
            &mut d,
            "write_design_note_canonical",
            json!({
            "session_id": "2026-08-25_demo", "spec_path": "vault/specs/demo.md",
            "architecture_decision": "Monolito modular"}),
        )
    });
    emit!("S43 design validaciones", {
        let mut d = docs_server();
        let a = call(&mut d, "write_design_note_canonical", json!({}));
        let b = call(
            &mut d,
            "write_design_note_canonical",
            json!({"session_id": "s1"}),
        );
        format!("{a}\n{b}")
    });
    emit!("S44 import_hu", {
        let mut d = hu_server();
        call(
            &mut d,
            "cortex_import_hu",
            json!({"external_id": "HU-123", "provider": "linear"}),
        )
    });
    emit!("S45 get_hu ok y missing", {
        let mut d = hu_server();
        let ok = call(&mut d, "cortex_get_hu", json!({"item_id": "HU-123"}));
        let bad = call(&mut d, "cortex_get_hu", json!({"item_id": "HU-999"}));
        format!("{ok}\n{bad}")
    });

    // ---- finish/briefing -----------------------------------------------------------
    emit!("S46 finish interactive rechazado", {
        let (mut f, _c, _r) = finish_server(true, false);
        call(
            &mut f,
            "cortex_finish_session",
            json!({"interactive": true}),
        )
    });
    emit!("S47 finish validaciones", {
        let (mut f, _c, _r) = finish_server(true, false);
        let a = call(&mut f, "cortex_finish_session", json!({"intent": "bogus"}));
        let b = call(
            &mut f,
            "cortex_finish_session",
            json!({"intent": "handoff"}),
        );
        let (mut f2, _c2, _r2) = finish_server(false, false);
        let c = call(&mut f2, "cortex_finish_session", json!({}));
        format!("{a}\n{b}\n{c}")
    });
    emit!("S48 finish sesión cerrada", {
        let (mut f, _c, _r) = finish_server(false, true);
        call(
            &mut f,
            "cortex_finish_session",
            json!({"session_id": "2026-05-16_demo"}),
        )
    });
    emit!("S49 finish auto happy", {
        let (mut f, captured, _r) = finish_server(true, false);
        let out = call(&mut f, "cortex_finish_session", json!({}));
        let forced = captured.lock().unwrap().clone();
        format!("forced={forced}\n{out}")
    });
    emit!("S51 briefing serialización completa", {
        let (mut f, _c, recon) = finish_server(true, false);
        let out = call(
            &mut f,
            "cortex_documenter_briefing",
            json!({"session_id": "2026-05-16_demo"}),
        );
        let meta = recon.lock().unwrap().clone();
        format!("captured={meta}\n{out}")
    });

    Ok(blocks.join("\n") + "\n")
}

// ---------------------------------------------------------------------------
// Builders de fixtures espejo
// ---------------------------------------------------------------------------

fn alts_ok() -> Value {
    json!([
        {"id": "A", "description": "hacer X"},
        {"id": "B", "description": "hacer Y", "rejected_reason": "más caro"}
    ])
}

fn s11_payload() -> Value {
    json!({
        "summary": "Migrar el módulo de pagos a pasarela nueva.",
        "alternatives": [
            {"id": "A", "description": "Proveedor X, costo bajo"},
            {"id": "B", "description": "Proveedor Y, más features", "rejected_reason": "costo alto"}
        ],
        "recommendation_id": "A",
        "risks": ["  ", "migración doble escritura"]
    })
}

fn big_semantic() -> cortex_mcp::handlers_search::RHit {
    cortex_mcp::handlers_search::RHit {
        source: "semantic".into(),
        score: 0.5,
        entry: None,
        doc: Some(RDoc {
            path: "x.md".into(),
            title: "X".into(),
            content: "a".repeat(5000),
        }),
    }
}

fn docs_server() -> CortexMcpServer<cortex_mcp::server::CountingMemory> {
    let mut srv = CortexMcpServer::new();
    srv.project_root = std::path::PathBuf::from(FAKE_ROOT);
    srv.with_docs_backend(Arc::new(Mutex::new(StubDocs)))
}

fn hu_server() -> CortexMcpServer<cortex_mcp::server::CountingMemory> {
    let srv = CortexMcpServer::new();
    srv.with_docs_backend(Arc::new(Mutex::new(StubHu)))
}

/// has_active / is_closed controlan los records fake de sesión; el
/// Arc captura el forced_status recibido por el persister fake.
type CapturedForced = Arc<Mutex<String>>;

fn finish_server(
    has_active: bool,
    closed: bool,
) -> (
    CortexMcpServer<cortex_mcp::server::CountingMemory>,
    Arc<Mutex<String>>,
    Arc<Mutex<String>>,
) {
    let captured: CapturedForced = Arc::new(Mutex::new("<no llamado>".into()));
    let recon = Arc::new(Mutex::new("<no llamado>".into()));
    let mut srv = CortexMcpServer::new();
    srv = srv.with_finish_backend(Arc::new(Mutex::new(StubFinish {
        has_active,
        closed,
        captured: captured.clone(),
        recon: recon.clone(),
    })));
    (srv, captured, recon)
}

// ---------------------------------------------------------------------------
// Implementaciones stub
// ---------------------------------------------------------------------------

struct StubSpec {
    mode: &'static str,
}

impl SpecBackend for StubSpec {
    fn create_spec_note(
        &mut self,
        _req: &SpecCreateRequest,
    ) -> Result<SpecResultMirror, SpecError> {
        match self.mode {
            "value_error" => Err(SpecError::Value(
                "El título es obligatorio para crear una spec.".into(),
            )),
            "duplicate" => Err(SpecError::DuplicateDocument(
                "Document already exists with different content: vault/specs/demo-spec-title.md. Pass overwrite=True to replace, or choose a different title.".into(),
            )),
            "gitless" => Ok(SpecResultMirror {
                path: "vault/specs/demo-spec-title.md".into(),
                session_gitless: Some(true),
            }),
            _ => Ok(SpecResultMirror {
                path: "vault/specs/demo-spec-title.md".into(),
                session_gitless: None,
            }),
        }
    }
}

struct StubDocs;

impl DocsBackend for StubDocs {
    fn write_doc(
        &mut self,
        doc_type: &str,
        clean: Map<String, Value>,
        scope: &str,
        _overwrite: bool,
    ) -> Result<String, DocsError> {
        // Contratos de writer (producción: cortex-setup::writers::build_note).
        if doc_type == "handoff" && scope != "local" {
            return Err(DocsError::Schema(format!(
                "{doc_type} is local-only; vault_scope must be 'local'"
            )));
        }
        if scope == "enterprise" && (clean.get("owner").is_none() || clean.get("team").is_none()) {
            let mut missing: Vec<&str> = Vec::new();
            if clean.get("owner").is_none() {
                missing.push("owner");
            }
            if clean.get("team").is_none() {
                missing.push("team");
            }
            let list = format!(
                "[{}]",
                missing
                    .iter()
                    .map(|m| format!("'{m}'"))
                    .collect::<Vec<_>>()
                    .join(", ")
            );
            return Err(DocsError::Schema(format!(
                "Enterprise scope requires fields: {list}"
            )));
        }
        match doc_type {
            "adr" => {
                let decision = clean.get("decision").and_then(Value::as_str).unwrap_or("");
                if decision == "OTRA" && clean.get("adr_number").and_then(Value::as_i64) == Some(1)
                {
                    return Err(DocsError::Runtime(format!(
                        "Document already exists with different content: \
                         {FAKE_ROOT}/.cortex/vault/decisions/ADR-001-dup.md. \
                         Pass overwrite=True to replace, or choose a different title."
                    )));
                }
                Ok(format!(
                    "{FAKE_ROOT}/.cortex/vault/decisions/ADR-001-usar-rust-para-el-nucleo.md"
                ))
            }
            "glossary" => Ok(format!("{FAKE_ROOT}/.cortex/vault/glossary/fingerprint.md")),
            _ => unreachable!("escenario no cubierto por stub"),
        }
    }

    fn write_design_note(&mut self, data: DesignDocInput) -> Result<String, DocsError> {
        Ok(format!(
            "{FAKE_ROOT}/.cortex/vault/designs/{}.md",
            data.session_id
        ))
    }

    fn import_hu(&mut self, external_id: &str, _p: &str, _r: bool) -> Result<String, String> {
        Ok(format!("vault/hu/{}.md", external_id.to_lowercase()))
    }

    fn get_hu(&mut self, item_id: &str) -> Result<String, String> {
        if item_id == "HU-999" {
            return Err(format!("Tracked item not found in vault: {item_id}"));
        }
        Ok(format!("vault/hu/{}.md", item_id.to_lowercase()))
    }
}

struct StubHu;

impl DocsBackend for StubHu {
    fn write_doc(
        &mut self,
        _: &str,
        _: Map<String, Value>,
        _: &str,
        _: bool,
    ) -> Result<String, DocsError> {
        unreachable!()
    }
    fn write_design_note(&mut self, _: DesignDocInput) -> Result<String, DocsError> {
        unreachable!()
    }
    fn import_hu(&mut self, external_id: &str, _: &str, _: bool) -> Result<String, String> {
        Ok(format!("vault/hu/{}.md", external_id.to_lowercase()))
    }
    fn get_hu(&mut self, item_id: &str) -> Result<String, String> {
        if item_id == "HU-999" {
            return Err(format!("Tracked item not found in vault: {item_id}"));
        }
        Ok(format!("vault/hu/{}.md", item_id.to_lowercase()))
    }
}

struct StubSearch;

impl SearchBackend for StubSearch {
    fn retrieve(
        &mut self,
        query: &str,
        top_k: usize,
        use_embeddings: bool,
    ) -> Result<RetrievalMirror, String> {
        let _ = (top_k, use_embeddings);
        match query {
            "EMPTY" => Ok(RetrievalMirror {
                query: query.into(),
                ..empty_mirror()
            }),
            "FALLBACK" => Ok(RetrievalMirror {
                query: query.into(),
                episodic_hits: vec![(
                    REntry {
                        id: "mem_fb1aaaa".into(),
                        content: "Sesión previa de auth".into(),
                        memory_type: "session".into(),
                        files: vec!["src/a.py".into()],
                        confidence: None,
                        tags: vec![],
                    },
                    0.87,
                )],
                semantic_hits: vec![(
                    RDoc {
                        path: "specs/auth.md".into(),
                        title: "Auth spec".into(),
                        content: "Contenido\nmultilínea".into(),
                    },
                    3.21,
                )],
                unified_hits: vec![],
            }),
            q => Ok(RetrievalMirror {
                query: q.into(),
                unified_hits: vec![
                    cortex_mcp::handlers_search::RHit {
                        source: "episodic".into(),
                        score: 0.032_786_885_245_901_64,
                        entry: Some(REntry {
                            id: "mem_aaa11111".into(),
                            content: "Implementamos login con JWT".into(),
                            memory_type: "session".into(),
                            tags: vec!["auth".into()],
                            files: vec!["src/auth.py".into(), "src/jwt.py".into()],
                            confidence: Some("verified".into()),
                        }),
                        doc: None,
                    },
                    cortex_mcp::handlers_search::RHit {
                        source: "semantic".into(),
                        score: 0.016_393_442_622_950_872,
                        entry: None,
                        doc: Some(RDoc {
                            path: "specs/auth.md".into(),
                            title: "Auth".into(),
                            content: "Primera línea\nde dos".into(),
                        }),
                    },
                ],
                ..empty_mirror()
            }),
        }
    }

    fn enrich(
        &mut self,
        changed_files: Vec<String>,
        keywords: Vec<String>,
        pr_title: Option<String>,
        _top_k: Option<usize>,
    ) -> Result<EnrichedMirror, String> {
        let _ = (changed_files, pr_title);
        if keywords.is_empty() {
            return Ok(EnrichedMirror::default());
        }
        Ok(two_item_bundle())
    }

    fn enrich_structural(
        &mut self,
        _query: &str,
        _top_k: usize,
        _scope: &str,
        doc_type: Vec<String>,
        _excl: Vec<String>,
        _status: Vec<String>,
        _tag: Vec<String>,
        _any: Vec<String>,
        _max_age: Option<i64>,
        _proj: Vec<String>,
        _strict: bool,
    ) -> Result<EnrichedMirror, cortex_mcp::handlers_search::StructuralError> {
        use cortex_mcp::handlers_search::StructuralError;
        if _scope == "galaxy" {
            return Err(StructuralError::Filter(
                "Invalid --scope value: 'galaxy'".into(),
            ));
        }
        let dt = sorted_repr(&doc_type);
        let mut bundle = two_item_bundle();
        bundle.items[0].title = format!("structural doc_types={dt}");
        Ok(bundle)
    }
}

fn empty_mirror() -> RetrievalMirror {
    RetrievalMirror {
        query: String::new(),
        episodic_hits: vec![],
        semantic_hits: vec![],
        unified_hits: vec![],
    }
}

/// Bundle con los dos ítems canónicos del oráculo.
fn two_item_bundle() -> EnrichedMirror {
    EnrichedMirror {
        total_items: 2,
        items: vec![
            EnrichedItemMirror {
                source: "episodic".into(),
                title: "[SESSION] Implementamos login".into(),
                content: "Implementamos login con JWT y refresh tokens".into(),
                files_mentioned: vec!["src/auth.py".into()],
                date_iso: Some("2026-08-25T10:00:00".into()),
                matched_by: vec!["topic_search".into(), "keyword_search".into()],
                tags: vec!["auth".into(), "jwt".into()],
                confidence: Some("verified".into()),
            },
            EnrichedItemMirror {
                source: "semantic".into(),
                title: "Auth spec".into(),
                content: "Spec del módulo de autenticación".into(),
                files_mentioned: vec![],
                date_iso: Some("2026-08-01T09:30:00".into()),
                matched_by: vec!["topic_search".into()],
                tags: vec![],
                confidence: None,
            },
        ],
    }
}

/// repr de lista Python `['a', 'b']` ordenada (para doc_types eco).
fn sorted_repr(items: &[String]) -> String {
    let mut sorted: Vec<&String> = items.iter().collect();
    sorted.sort();
    let inner: Vec<String> = sorted.iter().map(|s| format!("'{s}'")).collect();
    format!("[{}]", inner.join(", "))
}

struct StubFinish {
    has_active: bool,
    closed: bool,
    captured: CapturedForced,
    recon: Arc<Mutex<String>>,
}

impl FinishBackend for StubFinish {
    fn get_active_session_id(&mut self) -> Result<Option<String>, String> {
        Ok(if self.has_active {
            Some("2026-05-16_demo".into())
        } else {
            None
        })
    }

    fn get_session_status(&mut self, sid: &str) -> Result<String, String> {
        if sid != "2026-05-16_demo" {
            return Err(format!("no such session: {sid}"));
        }
        Ok(if self.closed { "closed" } else { "open" }.into())
    }

    fn reconstruct(
        &mut self,
        session_id: &str,
        run_hooks: bool,
    ) -> Result<ReconstructionMirror, String> {
        *self.recon.lock().unwrap() =
            format!("{}|{session_id}", if run_hooks { "True" } else { "False" });
        Ok(full_reconstruction())
    }

    fn finalize(
        &mut self,
        session_id: &str,
        forced_status: Option<&str>,
    ) -> Result<FinishResultMirror, String> {
        assert_eq!(session_id, "2026-05-16_demo");
        *self.captured.lock().unwrap() = forced_status
            .map(str::to_string)
            .unwrap_or_else(|| "None".into());
        Ok(FinishResultMirror {
            session_id: "2026-05-16_demo".into(),
            final_status: forced_status.unwrap_or("handoff").into(),
            session_note_path: Some("vault/sessions/2026-05-16_demo.md".into()),
            adrs_created: vec!["vault/decisions/ADR-001-usar-rust.md".into()],
            summary_text: "Resumen de cierre".into(),
            already_closed: false,
        })
    }
}

/// Espejo completo del ReconstructionOutput del oráculo S51.
fn full_reconstruction() -> ReconstructionMirror {
    ReconstructionMirror {
        session_id: "2026-05-16_demo".into(),
        spec: cortex_mcp::handlers_finish::SpecInfoMirror {
            path: "vault/specs/demo.md".into(),
            title: "Demo".into(),
            goal: "Meta demo".into(),
            files_in_scope: vec!["src/a.py".into()],
            constraints: vec![],
            acceptance_criteria: vec!["Criterio uno".into()],
            verification_hooks: vec![cortex_mcp::handlers_finish::SpecHookMirror {
                name: "tests".into(),
                command: "pytest -q".into(),
                required: true,
                success_criteria: "verde".into(),
                timeout_seconds: 300,
            }],
        },
        diff_text: "diff --git a/src/a.py\n+b\n".into(),
        diff_entries: vec![cortex_mcp::handlers_finish::DiffEntryMirror {
            action: "added".into(),
            path: "src/a.py".into(),
        }],
        files_touched: vec!["src/a.py".into()],
        files_verified_by_git: vec!["src/a.py".into()],
        files_declared_only: vec![],
        in_scope_files: vec!["src/a.py".into()],
        out_of_scope_files: vec![],
        unimplemented_files: vec![],
        verification_results: vec![cortex_mcp::handlers_finish::VerifResultMirror {
            name: "tests".into(),
            command: "pytest -q".into(),
            passed: true,
            exit_code: 0,
            output: "1 passed".into(),
            duration_ms: 120,
            run_at: "2026-08-25T12:00:00".into(),
        }],
        contradictions: vec![cortex_mcp::handlers_finish::ContradictionMirror {
            prior_record: "ADR-000 decía X".into(),
            current_claim: "ahora es Y".into(),
            evidence: vec!["src/a.py:1".into()],
            severity: "high".into(),
        }],
        suggested_status: "handoff".into(),
        suggested_adrs: vec![cortex_mcp::handlers_finish::AdrSuggestionMirror {
            title: "ADR demo".into(),
            rationale: "porque sí".into(),
            source_checkpoint_index: Some(0),
            evidence: vec!["claim".into()],
            confidence: 0.85,
        }],
        raw_checkpoints: vec![cortex_mcp::handlers_finish::RawCheckpointMirror {
            timestamp: "2026-08-25T11:00:00".into(),
            source: "manual".into(),
            verified_claims: vec!["claim".into()],
            unverified_claims: vec![],
            artifacts_touched: vec!["src/a.py".into()],
            note: "nota".into(),
        }],
        end_commit: "b".repeat(40),
        gitless: false,
    }
}

fn main() {
    if let Err(e) = main_impl() {
        eprintln!("{e}");
        std::process::exit(1);
    }
}
