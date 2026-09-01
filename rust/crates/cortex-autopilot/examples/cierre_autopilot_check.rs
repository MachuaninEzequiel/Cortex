//! Checker CIERRE T3-PAR — paridad byte-a-byte del autopilot service +
//! tools MCP ×5 contra `bench/parity/.p12-cierre-autopilot/golden_cierre_autopilot.txt`
//! (oráculo: service.py + `_dispatch_tool_sync` Python REALES con sesiones
//! fixture reales).
//!
//! Uso: cargo run -p cortex-autopilot --example cierre_autopilot_check -- <golden_dir>
//!
//! Reproduce las partes [A] SERVICE y [B] MCP del golden (hasta el marcador
//! `[[CLI-PART]]`); la parte [C] CLI es dual py-vs-rs dentro del propio
//! golden (patrón P12B-8).

use std::path::Path;
use std::sync::{Arc, Mutex};

use cortex_app::session::SessionStorage;
use cortex_autopilot::policies::AutopilotMode;
use cortex_autopilot::service::{AutopilotService, ServiceError, StatusOutcome};
use cortex_mcp::handlers_autopilot::{
    AutopilotBackend, AutopilotToolError, CheckpointData, FinishData, PreflightData, StartData,
    StatusData,
};
use cortex_mcp::server::CortexMcpServer;
use regex::Regex;

const SPEC_ID: &str = "2026-05-16_demo";
const CLI_MARKER: &str = "[[CLI-PART]]";

// ---------------------------------------------------------------------------
// Helpers de proyección (espejo de las del golden Python)
// ---------------------------------------------------------------------------

fn py_repr_str(s: &str) -> String {
    // regla de repr de CPython: si contiene ' y no ", envuelve con ".
    if s.contains('\'') && !s.contains('"') {
        format!("\"{s}\"")
    } else {
        format!("'{s}'")
    }
}

fn py_list_repr(items: &[String]) -> String {
    let inner: Vec<String> = items.iter().map(|s| py_repr_str(s)).collect();
    format!("[{}]", inner.join(", "))
}

fn proj_start(session_id: &str, status: &str, mode: &str, warnings: &[String]) -> String {
    format!(
        "session={session_id}\nstatus={status}\nmode={mode}\nwarnings={}",
        py_list_repr(warnings)
    )
}

fn proj_checkpoint(count: usize, status: &str, warnings: &[String]) -> String {
    format!(
        "count={count}\nstatus={status}\nwarnings={}",
        py_list_repr(warnings)
    )
}

fn proj_finish(o: &cortex_autopilot::service::FinishOutcome) -> String {
    format!(
        "status={}\ndocumented={}\nblocked={}\nblocked_reason={}\nnote={}\nsummary={}\nwarnings={}",
        o.session.status.as_str(),
        if o.documented { "True" } else { "False" },
        if o.blocked { "True" } else { "False" },
        o.blocked_reason,
        o.session_note_path.clone().unwrap_or_default(),
        o.summary,
        py_list_repr(&o.warnings),
    )
}

fn proj_status(o: &StatusOutcome, mode: &str) -> String {
    if !o.active {
        return format!("active=False\nmode={mode}");
    }
    let s = o.session.as_ref().expect("activo implica record");
    format!(
        "active=True\nsession={}\nstatus={}\nmode={mode}\ninferred={}\ncount={}",
        s.session_id,
        s.status.as_str(),
        o.inferred_mode.clone().unwrap_or_default(),
        o.checkpoint_count,
    )
}

fn proj_detection(d: &cortex_autopilot::models::DetectionResult) -> String {
    // repr(float) de CPython == Display shortest-roundtrip de Rust para
    // los valores del dominio.
    format!(
        "task_type={}\nconfidence={}\nreason={}\nsuggested_complexity={}",
        d.task_type, d.confidence, d.reason, d.suggested_complexity
    )
}

fn map_err(e: ServiceError) -> AutopilotToolError {
    match e {
        ServiceError::NoActiveSession(m) => AutopilotToolError::NoActiveSession(m),
        ServiceError::Autopilot(m) => AutopilotToolError::Autopilot(m),
        ServiceError::SessionNotFound(m) => AutopilotToolError::SessionNotFound(m),
    }
}

// ---------------------------------------------------------------------------
// Backend nativo (service real → datos estructurados del handler)
// ---------------------------------------------------------------------------

struct NativeBackend {
    svc: AutopilotService,
}

impl AutopilotBackend for NativeBackend {
    fn start(&mut self, mode: Option<&str>) -> Result<StartData, AutopilotToolError> {
        let m = mode.map(|s| match s {
            "observe" => AutopilotMode::Observe,
            "autopilot" => AutopilotMode::Autopilot,
            _ => AutopilotMode::Assist,
        });
        self.svc
            .start(m)
            .map(|o| StartData {
                session_id: o.session.session_id.clone(),
                mode: self.svc.policy().mode.as_str().to_string(),
                status: o.session.status.as_str().to_string(),
                warnings: o.warnings,
            })
            .map_err(map_err)
    }

    fn preflight(
        &mut self,
        user_request: Option<&str>,
        changed_files: &[String],
        git_diff_stat: Option<&str>,
    ) -> Result<PreflightData, AutopilotToolError> {
        let o = self
            .svc
            .preflight(user_request, changed_files, git_diff_stat);
        Ok(PreflightData {
            task_type: o.detection.task_type.clone(),
            confidence: o.detection.confidence,
            reason: o.detection.reason.clone(),
            suggested_complexity: o.detection.suggested_complexity.clone(),
        })
    }

    #[allow(clippy::too_many_arguments)]
    fn checkpoint(
        &mut self,
        source: &str,
        verified_claims: Vec<String>,
        unverified_claims: Vec<String>,
        artifacts_touched: Vec<String>,
        note: &str,
        files_in_scope: Option<Vec<String>>,
    ) -> Result<CheckpointData, AutopilotToolError> {
        self.svc
            .checkpoint(
                source,
                verified_claims,
                unverified_claims,
                artifacts_touched,
                note,
                files_in_scope,
            )
            .map(|o| CheckpointData {
                session_id: o.session.session_id.clone(),
                total_checkpoints: o.session.checkpoints.len(),
                status: o.session.status.as_str().to_string(),
                warnings: o.warnings,
            })
            .map_err(map_err)
    }

    fn finish(
        &mut self,
        session_id: Option<&str>,
        auto: bool,
        intent: &str,
        _reason: &str,
    ) -> Result<FinishData, AutopilotToolError> {
        self.svc
            .finish(session_id, auto, intent)
            .map(|o| FinishData {
                session_id: o.session.session_id.clone(),
                status: o.session.status.as_str().to_string(),
                documented: o.documented,
                blocked: o.blocked,
                blocked_reason: o.blocked_reason.clone(),
                session_note_path: o.session_note_path.clone(),
                warnings: o.warnings,
            })
            .map_err(map_err)
    }

    fn status(&mut self, session_id: Option<&str>) -> Result<StatusData, AutopilotToolError> {
        self.svc
            .status(session_id)
            .map(|o| match o {
                StatusOutcome { active: false, .. } => StatusData {
                    active: false,
                    ..Default::default()
                },
                o => {
                    let s = o.session.as_ref().expect("activo implica record");
                    StatusData {
                        active: true,
                        session_id: s.session_id.clone(),
                        status: s.status.as_str().to_string(),
                        mode: Some(self.svc.policy().mode.as_str().to_string()),
                        inferred_mode: o.inferred_mode.clone().unwrap_or_default(),
                        checkpoint_count: o.checkpoint_count,
                        start_branch: s.start_branch.clone(),
                    }
                }
            })
            .map_err(map_err)
    }
}

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

fn seed_session(root: &Path, summary: &str) -> String {
    let layout = cortex_workspace::WorkspaceLayout::discover(root);
    let storage = SessionStorage::new(layout.repo_root.join(".cortex").join("sessions"));
    let svc = cortex_app::session::service::SessionService::new(storage, &layout.repo_root);
    svc.open(SPEC_ID, &format!("vault/specs/{SPEC_ID}.md"), summary)
        .expect("seed open")
        .session_id
}

fn write_autopilot_yaml(root: &Path, body: &str) {
    let dir = root.join(".cortex");
    std::fs::create_dir_all(&dir).unwrap();
    std::fs::write(dir.join("autopilot.yaml"), body).unwrap();
}

fn service_at(root: &Path) -> AutopilotService {
    AutopilotService::from_project_root(root, None).expect("servicio fixture")
}

/// A08: retroceder el timestamp del PRIMER checkpoint (-N min) editando el
/// YAML que el storage nativo escribió.
fn backdate_last_checkpoint(root: &Path, minutes: i64) {
    let path = root
        .join(".cortex")
        .join("sessions")
        .join(format!("{SPEC_ID}.yaml"));
    let text = std::fs::read_to_string(&path).unwrap();
    let idx = text.find("checkpoints:").expect("sección checkpoints");
    let rest = &text[idx..];
    let ts_idx = rest.find("timestamp:").expect("timestamp del cp");
    let value_start = idx + ts_idx + "timestamp:".len();
    let line_end = text[value_start..]
        .find('\n')
        .map(|p| value_start + p)
        .unwrap_or(text.len());
    let backdated = chrono::Utc::now() - chrono::Duration::minutes(minutes);
    let new_iso = backdated.to_rfc3339_opts(chrono::SecondsFormat::Micros, false);
    // Preservar el espacio separador del escalar YAML (`timestamp: <iso>`).
    std::fs::write(
        &path,
        format!("{} {}{}", &text[..value_start], new_iso, &text[line_end..]),
    )
    .unwrap();
}

// ---------------------------------------------------------------------------
// Escenarios A (SERVICE) + B (MCP) — mismo orden y nombres que el oráculo
// ---------------------------------------------------------------------------

fn run_scenarios(base: &Path) -> Result<String, String> {
    let iso_re = Regex::new(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(\+00:00|Z)")
        .map_err(|e| e.to_string())?;
    let min_re = Regex::new(r"\b\d+ minutes since").map_err(|e| e.to_string())?;
    let root_str = base.to_string_lossy().to_string();

    let mut section_a: Vec<(String, String)> = Vec::new();
    let mut section_b: Vec<(String, String)> = Vec::new();

    // norm(): {{TS}} → {{MIN}} → {{ROOT}}, igual que el oráculo.
    let norm = |body: String| -> String {
        min_re
            .replace_all(
                &iso_re.replace_all(&body, "{{TS}}"),
                "{{MIN}} minutes since",
            )
            .replace(&root_str, "{{ROOT}}")
            .to_string()
    };

    macro_rules! scenario {
        ($section:expr, $name:expr, $body:expr) => {{
            let body: String = norm($body);
            $section.push((($name).to_string(), body));
        }};
    }

    // ── Parte A ─────────────────────────────────────────────────────────
    let a01 = base.join("a01");
    std::fs::create_dir_all(&a01).unwrap();
    let r = service_at(&a01).start(None).err().map(|e| e.to_string());
    scenario!(
        &mut section_a,
        "A01 start sin activa",
        format!("NoActiveSessionError: {}", r.expect("se esperaba error"))
    );

    let a02 = base.join("a02");
    std::fs::create_dir_all(&a02).unwrap();
    seed_session(&a02, "Demo summary");
    let o = service_at(&a02).start(None).unwrap();
    scenario!(
        &mut section_a,
        "A02 start adopta assist",
        proj_start(
            &o.session.session_id,
            o.session.status.as_str(),
            "assist",
            &o.warnings
        )
    );

    let a03 = base.join("a03");
    std::fs::create_dir_all(&a03).unwrap();
    seed_session(&a03, "Implement password reset flow");
    let o = service_at(&a03).start(None).unwrap();
    scenario!(
        &mut section_a,
        "A03 start warning seguridad",
        proj_start(
            &o.session.session_id,
            o.session.status.as_str(),
            "assist",
            &o.warnings
        )
    );

    let a04 = base.join("a04");
    std::fs::create_dir_all(&a04).unwrap();
    let d = service_at(&a04).preflight(Some("What does this function do?"), &[], None);
    scenario!(
        &mut section_a,
        "A04 preflight question-only",
        proj_detection(&d.detection)
    );

    let a05 = base.join("a05");
    std::fs::create_dir_all(&a05).unwrap();
    seed_session(&a05, "Demo summary");
    let mut svc = service_at(&a05);
    let o = svc
        .checkpoint(
            "manual",
            vec!["claim uno".into()],
            vec![],
            vec![],
            "primer paso",
            None,
        )
        .unwrap();
    scenario!(
        &mut section_a,
        "A05 checkpoint manual ok",
        proj_checkpoint(
            o.session.checkpoints.len(),
            o.session.status.as_str(),
            &o.warnings
        )
    );

    let a06 = base.join("a06");
    std::fs::create_dir_all(&a06).unwrap();
    seed_session(&a06, "Demo summary");
    let mut svc = service_at(&a06);
    let o = svc
        .checkpoint(
            "manual",
            vec![],
            vec![],
            vec!["src/b.py".into(), "src/a.py".into()],
            "",
            Some(vec!["src/a.py".into()]),
        )
        .unwrap();
    scenario!(
        &mut section_a,
        "A06 checkpoint drift fuera de scope",
        proj_checkpoint(
            o.session.checkpoints.len(),
            o.session.status.as_str(),
            &o.warnings
        )
    );

    let a07 = base.join("a07");
    std::fs::create_dir_all(&a07).unwrap();
    seed_session(&a07, "Demo summary");
    let mut svc = service_at(&a07);
    svc.checkpoint(
        "manual",
        vec![],
        vec![],
        vec!["f1".into(), "f2".into(), "f3".into()],
        "",
        None,
    )
    .unwrap();
    let o = svc
        .checkpoint(
            "manual",
            vec![],
            vec![],
            vec!["f4".into(), "f5".into(), "f6".into()],
            "",
            None,
        )
        .unwrap();
    scenario!(
        &mut section_a,
        "A07 threshold archivos sin verificar",
        proj_checkpoint(
            o.session.checkpoints.len(),
            o.session.status.as_str(),
            &o.warnings
        )
    );

    let a08 = base.join("a08");
    std::fs::create_dir_all(&a08).unwrap();
    seed_session(&a08, "Demo summary");
    let mut svc = service_at(&a08);
    svc.checkpoint("manual", vec![], vec![], vec!["f1".into()], "", None)
        .unwrap();
    backdate_last_checkpoint(&a08, 20);
    let o = svc
        .checkpoint("manual", vec![], vec![], vec!["f2".into()], "", None)
        .unwrap();
    scenario!(
        &mut section_a,
        "A08 checkpoint espaciado minutos",
        proj_checkpoint(
            o.session.checkpoints.len(),
            o.session.status.as_str(),
            &o.warnings
        )
    );

    let a09 = base.join("a09");
    std::fs::create_dir_all(&a09).unwrap();
    seed_session(&a09, "Demo summary");
    let mut svc = service_at(&a09);
    let first = proj_finish(&svc.finish(None, false, "closed").unwrap());
    // Segundo finish con id explícito: ya terminal ⇒ no-op sin puntero.
    let again = proj_finish(&svc.finish(Some(SPEC_ID), false, "closed").unwrap());
    scenario!(
        &mut section_a,
        "A09 finish manual closed + no-op",
        format!("{first}\n---second---\n{again}")
    );

    let a10 = base.join("a10");
    std::fs::create_dir_all(&a10).unwrap();
    seed_session(&a10, "Demo summary");
    let o = service_at(&a10).finish(None, false, "handoff").unwrap();
    scenario!(&mut section_a, "A10 finish handoff", proj_finish(&o));

    let a11 = base.join("a11");
    std::fs::create_dir_all(&a11).unwrap();
    write_autopilot_yaml(&a11, "mode: autopilot\n");
    seed_session(&a11, "Demo summary");
    let o = service_at(&a11).finish(None, false, "closed").unwrap();
    scenario!(
        &mut section_a,
        "A11 blocked autopilot sin verificación",
        proj_finish(&o)
    );

    let a12 = base.join("a12");
    std::fs::create_dir_all(&a12).unwrap();
    seed_session(&a12, "Demo summary");
    let mut svc = service_at(&a12);
    let active = proj_status(&svc.status(None).unwrap(), "assist");
    let named = proj_status(&svc.status(Some(SPEC_ID)).unwrap(), "assist");
    let missing = proj_status(&svc.status(Some("2026-01-01_missing")).unwrap(), "assist");
    scenario!(
        &mut section_a,
        "A12 status activa/nombrada/faltante",
        format!("{active}\n---named---\n{named}\n---missing---\n{missing}")
    );

    let a13 = base.join("a13");
    std::fs::create_dir_all(&a13).unwrap();
    seed_session(&a13, "Demo summary");
    let err = service_at(&a13)
        .checkpoint("nope", vec![], vec![], vec![], "", None)
        .err()
        .map(|e| e.to_string());
    scenario!(
        &mut section_a,
        "A13 checkpoint fuente desconocida",
        match err {
            Some(m) => format!("AutopilotError: {m}"),
            None => panic!("se esperaba error"),
        }
    );

    let a14 = base.join("a14");
    std::fs::create_dir_all(&a14).unwrap();
    seed_session(&a14, "Demo summary");
    // Servicio con memory_factory=None explícito (constructor directo).
    let layout = cortex_workspace::WorkspaceLayout::discover(&a14);
    let storage = SessionStorage::new(layout.repo_root.join(".cortex").join("sessions"));
    let clock: Arc<dyn cortex_enterprise::clock::Clock> =
        Arc::new(cortex_enterprise::clock::SystemClock);
    let policy = cortex_autopilot::policies::AutopilotPolicy::from_config(
        &cortex_autopilot::config::AutopilotConfig::default(),
        clock,
    )
    .unwrap();
    let mut svc = AutopilotService::new(
        cortex_app::session::service::SessionService::new(storage, &layout.repo_root),
        policy,
        &layout.repo_root,
        None,
    );
    let err = svc
        .finish(None, true, "closed")
        .err()
        .map(|e| e.to_string());
    scenario!(
        &mut section_a,
        "A14 finish auto sin memory_factory",
        format!(
            "Exception: AutopilotError: {}",
            err.unwrap_or_else(|| panic!("se esperaba error"))
        )
    );

    let a15 = base.join("a15");
    std::fs::create_dir_all(&a15).unwrap();
    seed_session(&a15, "Demo summary");
    let mut svc = service_at(&a15);
    let started = svc.start(Some(AutopilotMode::Observe)).unwrap();
    let started_s = proj_start(
        &started.session.session_id,
        started.session.status.as_str(),
        "observe",
        &started.warnings,
    );
    let o = svc
        .checkpoint(
            "manual",
            vec![],
            vec![],
            vec!["src/out.py".into()],
            "",
            Some(vec!["src/in.py".into()]),
        )
        .unwrap();
    scenario!(
        &mut section_a,
        "A15 override a observe apaga warnings",
        format!(
            "{started_s}\n---after-drift---\n{}",
            proj_checkpoint(
                o.session.checkpoints.len(),
                o.session.status.as_str(),
                &o.warnings
            )
        )
    );

    // ── Parte B — MCP vía dispatcher real ──────────────────────────────

    fn make_server(root: &Path) -> CortexMcpServer<cortex_mcp::server::CountingMemory> {
        CortexMcpServer::new().with_autopilot_backend(Arc::new(Mutex::new(NativeBackend {
            svc: service_at(root),
        })))
    }

    fn call(
        srv: &mut CortexMcpServer<cortex_mcp::server::CountingMemory>,
        name: &str,
        args: serde_json::Value,
    ) -> String {
        srv.dispatch_tool_sync(name, &args)
            .unwrap_or_else(|e| format!("Error ejecutando {name}: {e}"))
    }

    let b01 = base.join("b01");
    std::fs::create_dir_all(&b01).unwrap();
    seed_session(&b01, "Demo summary");
    let mut srv = make_server(&b01);
    scenario!(
        &mut section_b,
        "B01 mcp start ok",
        call(&mut srv, "cortex_autopilot_start", serde_json::json!({}))
    );

    let b02 = base.join("b02");
    std::fs::create_dir_all(&b02).unwrap();
    let mut srv = make_server(&b02);
    scenario!(
        &mut section_b,
        "B02 mcp start sin activa",
        call(&mut srv, "cortex_autopilot_start", serde_json::json!({}))
    );

    let b03 = base.join("b03");
    std::fs::create_dir_all(&b03).unwrap();
    let mut srv = make_server(&b03);
    scenario!(
        &mut section_b,
        "B03 mcp start modo inválido",
        call(
            &mut srv,
            "cortex_autopilot_start",
            serde_json::json!({"mode": "turbo"})
        )
    );

    let b04 = base.join("b04");
    std::fs::create_dir_all(&b04).unwrap();
    let mut srv = make_server(&b04);
    scenario!(
        &mut section_b,
        "B04 mcp preflight formato",
        call(
            &mut srv,
            "cortex_autopilot_preflight",
            serde_json::json!({"user_request": "What does this function do?"})
        )
    );

    let b05 = base.join("b05");
    std::fs::create_dir_all(&b05).unwrap();
    seed_session(&b05, "Demo summary");
    let mut srv = make_server(&b05);
    scenario!(
        &mut section_b,
        "B05 mcp checkpoint drift warnings",
        call(
            &mut srv,
            "cortex_autopilot_checkpoint",
            serde_json::json!({
                "source": "manual",
                "verified_claims": ["claim uno"],
                "unverified_claims": [],
                "artifacts_touched": ["src/b.py", "src/a.py"],
                "files_in_scope": ["src/a.py"],
            })
        )
    );

    let b06 = base.join("b06");
    std::fs::create_dir_all(&b06).unwrap();
    seed_session(&b06, "Demo summary");
    let mut srv = make_server(&b06);
    scenario!(
        &mut section_b,
        "B06 mcp checkpoint fuente inválida",
        call(
            &mut srv,
            "cortex_autopilot_checkpoint",
            serde_json::json!({"source": "nope"})
        )
    );

    let b07 = base.join("b07");
    std::fs::create_dir_all(&b07).unwrap();
    seed_session(&b07, "Demo summary");
    let mut srv = make_server(&b07);
    let f = call(
        &mut srv,
        "cortex_autopilot_finish",
        serde_json::json!({"auto": false}),
    );
    let s = call(&mut srv, "cortex_autopilot_status", serde_json::json!({}));
    scenario!(
        &mut section_b,
        "B07 mcp finish manual + status",
        format!("{f}\n---status---\n{s}")
    );

    let b08 = base.join("b08");
    std::fs::create_dir_all(&b08).unwrap();
    write_autopilot_yaml(&b08, "mode: autopilot\n");
    seed_session(&b08, "Demo summary");
    let mut srv = make_server(&b08);
    scenario!(
        &mut section_b,
        "B08 mcp finish bloqueado",
        call(&mut srv, "cortex_autopilot_finish", serde_json::json!({}))
    );

    let b09 = base.join("b09");
    std::fs::create_dir_all(&b09).unwrap();
    seed_session(&b09, "Demo summary");
    let mut srv = make_server(&b09);
    call(
        &mut srv,
        "cortex_autopilot_finish",
        serde_json::json!({"auto": false}),
    );
    scenario!(
        &mut section_b,
        "B09 mcp finish doble no-op",
        call(
            &mut srv,
            "cortex_autopilot_finish",
            serde_json::json!({"session_id": SPEC_ID})
        )
    );

    let b10 = base.join("b10");
    std::fs::create_dir_all(&b10).unwrap();
    seed_session(&b10, "Demo summary");
    let mut srv = make_server(&b10);
    scenario!(
        &mut section_b,
        "B10 mcp status activa",
        call(&mut srv, "cortex_autopilot_status", serde_json::json!({}))
    );

    let b11 = base.join("b11");
    std::fs::create_dir_all(&b11).unwrap();
    let mut srv = make_server(&b11);
    scenario!(
        &mut section_b,
        "B11 mcp status inactiva",
        call(&mut srv, "cortex_autopilot_status", serde_json::json!({}))
    );

    let b12 = base.join("b12");
    std::fs::create_dir_all(&b12).unwrap();
    seed_session(&b12, "Demo summary");
    let mut srv = make_server(&b12);
    scenario!(
        &mut section_b,
        "B12 mcp finish id inexistente",
        call(
            &mut srv,
            "cortex_autopilot_finish",
            serde_json::json!({"session_id": "2026-01-01_x"})
        )
    );

    let b13 = base.join("b13");
    std::fs::create_dir_all(&b13).unwrap();
    seed_session(&b13, "Demo summary");
    let mut srv = make_server(&b13);
    scenario!(
        &mut section_b,
        "B13 mcp start override observe",
        call(
            &mut srv,
            "cortex_autopilot_start",
            serde_json::json!({"mode": "observe"})
        )
    );

    let b14 = base.join("b14");
    std::fs::create_dir_all(&b14).unwrap();
    seed_session(&b14, "Demo summary");
    let mut srv = make_server(&b14);
    scenario!(
        &mut section_b,
        "B14 mcp preflight coerción de tipos",
        call(
            &mut srv,
            "cortex_autopilot_preflight",
            serde_json::json!({"changed_files": "no-es-lista", "user_request": null})
        )
    );

    // Render final idéntico al oráculo:
    // "\n".join(f"### {n}\nrc=0\n{b}") + "\n" por sección.
    let render = |blocks: &[(String, String)]| -> String {
        let parts: Vec<String> = blocks
            .iter()
            .map(|(n, b)| format!("### {n}\nrc=0\n{b}"))
            .collect();
        format!("{}\n", parts.join("\n"))
    };
    let mut report = String::from("[SERVICE]\n");
    report.push_str(&render(&section_a));
    report.push_str("[MCP]\n");
    report.push_str(&render(&section_b));
    Ok(report)
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let golden_dir = args
        .get(1)
        .unwrap_or_else(|| panic!("uso: cierre_autopilot_check <golden_dir>"));
    let golden_path = format!("{golden_dir}/golden_cierre_autopilot.txt");
    let expected_full = std::fs::read_to_string(&golden_path)
        .unwrap_or_else(|e| panic!("falta golden {golden_path}: {e}"));

    // El checker reproduce SOLO [SERVICE]+[MCP]: recorta en el marcador CLI.
    let expected_prefix = expected_full
        .split(CLI_MARKER)
        .next()
        .expect("marcador CLI presente");

    let tmp = tempfile::tempdir().unwrap();
    let got_prefix = run_scenarios(tmp.path()).unwrap_or_else(|e| panic!("escenarios: {e}"));

    if got_prefix != expected_prefix {
        let _ = std::fs::write(
            std::env::temp_dir().join("ap_check_actual.txt"),
            &got_prefix,
        );
        let exp: Vec<&str> = expected_prefix.lines().collect();
        let got: Vec<&str> = got_prefix.lines().collect();
        for (i, (a, b)) in exp.iter().zip(got.iter()).enumerate() {
            if a != b {
                panic!(
                    "primera divergencia en línea {}:\n  esperado: {a:?}\n  obtenido: {b:?}",
                    i + 1
                );
            }
        }
        panic!("longitud difiere: {} vs {}", exp.len(), got.len());
    }
    println!(
        "[PASS] cierre_autopilot_check byte-parity vs golden_cierre_autopilot.txt ({} líneas A+B)",
        expected_prefix.lines().count()
    );
    println!("✅ PARIDAD CIERRE T3");
}
