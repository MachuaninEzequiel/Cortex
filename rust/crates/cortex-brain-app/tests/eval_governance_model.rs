//! Harness de Evaluación Empírica de Gobernanza y Tools (Obra 20 / Línea A).
//!
//! Evalúa 20 escenarios de intención en lenguaje natural para verificar que el
//! protocolo de herramientas de Cortex Brain (sesiones, auditoría, grafo, memoria)
//! se despacha y procesa correctamente con cero alucinaciones.

use cortex_brain_app::chat::{build_all_tools, dispatch_tool, BrainEngine, ToolCall};
use cortex_brain_app::graph::{extract_project_graph, inspect_doctor_health, inspect_session_status};
use std::fs;
use std::path::Path;
use std::time::Duration;

#[test]
fn eval_01_catalogo_contiene_todas_las_tools_de_gobernanza() {
    let tools = build_all_tools();
    assert!(tools.contains_key("session.status"));
    assert!(tools.contains_key("session.checkpoint"));
    assert!(tools.contains_key("session.finish_and_document"));
    assert!(tools.contains_key("doctor.inspect"));
    assert!(tools.contains_key("webgraph.query"));
    assert!(tools.contains_key("memory.search"));
    assert!(tools.contains_key("vault.stats"));
}

#[test]
fn eval_02_session_status_en_proyecto_sin_sesion() {
    let temp = std::env::temp_dir().join(format!("cortex_eval_sess_02_{}", std::process::id()));
    let _ = fs::create_dir_all(&temp);

    let status = inspect_session_status(&temp);
    assert!(!status.active);
    assert_eq!(status.checkpoints_count, 0);

    let res = dispatch_tool("session.status", "", &temp).unwrap();
    assert!(res.contains("No hay ninguna sesión de trabajo activa"));

    let _ = fs::remove_dir_all(&temp);
}

#[test]
fn eval_03_session_status_en_proyecto_con_sesion_activa() {
    let temp = std::env::temp_dir().join(format!("cortex_eval_sess_03_{}", std::process::id()));
    let sessions_dir = temp.join(".cortex").join("sessions");
    let _ = fs::create_dir_all(&sessions_dir);

    let session_file = sessions_dir.join("042-refactor-ipc.jsonl");
    fs::write(
        &session_file,
        "{\"checkpoint\":\"Inicio de refactor\"}\n{\"checkpoint\":\"Handlers conectados\"}\n",
    )
    .unwrap();

    let status = inspect_session_status(&temp);
    assert!(status.active);
    assert_eq!(status.checkpoints_count, 2);

    let res = dispatch_tool("session.status", "", &temp).unwrap();
    assert!(res.contains("Sesión Activa"));
    assert!(res.contains("042-refactor-ipc"));

    let _ = fs::remove_dir_all(&temp);
}

#[test]
fn eval_04_doctor_inspect_detecta_salud_y_anomalias() {
    let temp = std::env::temp_dir().join(format!("cortex_eval_doc_04_{}", std::process::id()));
    let _ = fs::create_dir_all(&temp);

    let report_fail = inspect_doctor_health(&temp);
    assert!(!report_fail.is_healthy); // Falta .cortex

    let _ = fs::create_dir_all(temp.join(".cortex"));
    let report_ok = inspect_doctor_health(&temp);
    assert!(report_ok.is_healthy);

    let res = dispatch_tool("doctor.inspect", "", &temp).unwrap();
    assert!(res.contains("Auditoría de Salud de Cortex"));

    let _ = fs::remove_dir_all(&temp);
}

#[test]
fn eval_05_webgraph_query_filtra_nodos_por_termino() {
    let temp = std::env::temp_dir().join(format!("cortex_eval_wg_05_{}", std::process::id()));
    let specs_dir = temp.join("vault").join("specs");
    let _ = fs::create_dir_all(&specs_dir);
    fs::write(specs_dir.join("spec-auth.md"), "# Spec Auth").unwrap();

    let res = dispatch_tool("webgraph.query", "auth", &temp).unwrap();
    assert!(res.contains("Nodos encontrados"));
    assert!(res.contains("spec-auth"));

    let _ = fs::remove_dir_all(&temp);
}

#[test]
fn eval_06_extractor_de_grafo_detecta_modulos_y_crates() {
    let temp = std::env::temp_dir().join(format!("cortex_eval_wg_06_{}", std::process::id()));
    let crates_dir = temp.join("rust").join("crates").join("cortex-sample");
    let _ = fs::create_dir_all(&crates_dir);

    let graph = extract_project_graph(&temp);
    assert!(graph.nodes.iter().any(|n| n.label == "cortex-sample" && n.kind == "module"));

    let _ = fs::remove_dir_all(&temp);
}

#[test]
fn eval_07_engine_ejecuta_scripted_con_session_status() {
    let temp = std::env::temp_dir().join(format!("cortex_eval_turn_07_{}", std::process::id()));
    let sessions_dir = temp.join(".cortex").join("sessions");
    let _ = fs::create_dir_all(&sessions_dir);
    fs::write(sessions_dir.join("session-001.jsonl"), "{\"step\": 1}\n").unwrap();

    let engine = BrainEngine::with_factory(Duration::from_secs(90), |_| None);
    let backend = cortex_brain::chat::ScriptedBackend::new(
        "scripted-eval",
        vec!["TOOL: session.status"],
    );
    engine.insert_backend(temp.to_str().unwrap(), Box::new(backend));

    let turn = engine.respond(temp.to_str().unwrap(), "qué sesión está abierta?").unwrap();
    assert!(turn.text.contains("Sesión Activa"));
    assert!(turn.text.contains("session-001"));

    let _ = fs::remove_dir_all(&temp);
}

#[test]
fn eval_08_engine_ejecuta_scripted_con_doctor_inspect() {
    let temp = std::env::temp_dir().join(format!("cortex_eval_turn_08_{}", std::process::id()));
    let _ = fs::create_dir_all(temp.join(".cortex"));

    let engine = BrainEngine::with_factory(Duration::from_secs(90), |_| None);
    let backend = cortex_brain::chat::ScriptedBackend::new(
        "scripted-eval",
        vec!["TOOL: doctor.inspect"],
    );
    engine.insert_backend(temp.to_str().unwrap(), Box::new(backend));

    let turn = engine.respond(temp.to_str().unwrap(), "cómo está el proyecto?").unwrap();
    assert!(turn.text.contains("Auditoría de Salud"));

    let _ = fs::remove_dir_all(&temp);
}

#[test]
fn eval_09_engine_intercepta_safe_action_session_checkpoint() {
    let engine = BrainEngine::with_factory(Duration::from_secs(90), |_| None);
    let backend = cortex_brain::chat::ScriptedBackend::new(
        "scripted-eval",
        vec!["TOOL: session.checkpoint refactor completado"],
    );
    engine.insert_backend("test_proj", Box::new(backend));

    let turn = engine.respond("test_proj", "anotá checkpoint").unwrap();
    assert_eq!(
        turn.tool_calls,
        vec![ToolCall {
            tool: "session.checkpoint".into(),
            args: "refactor completado".into(),
        }]
    );
}

#[test]
fn eval_10_engine_intercepta_safe_action_session_finish() {
    let engine = BrainEngine::with_factory(Duration::from_secs(90), |_| None);
    let backend = cortex_brain::chat::ScriptedBackend::new(
        "scripted-eval",
        vec!["TOOL: session.finish_and_document"],
    );
    engine.insert_backend("test_proj", Box::new(backend));

    let turn = engine.respond("test_proj", "cerrar sesión").unwrap();
    assert_eq!(
        turn.tool_calls,
        vec![ToolCall {
            tool: "session.finish_and_document".into(),
            args: "".into(),
        }]
    );
}

#[test]
fn eval_11_engine_responde_conversacion_sin_tools() {
    let engine = BrainEngine::with_factory(Duration::from_secs(90), |_| None);
    let backend = cortex_brain::chat::ScriptedBackend::new(
        "scripted-eval",
        vec!["Hola! Soy Cortex Brain, tu asistente de código."],
    );
    engine.insert_backend("test_proj", Box::new(backend));

    let turn = engine.respond("test_proj", "hola").unwrap();
    assert!(turn.text.contains("Hola! Soy Cortex Brain"));
    assert!(turn.tool_calls.is_empty());
}

#[test]
fn eval_12_vault_stats_cuenta_notas_correctamente() {
    let temp = std::env::temp_dir().join(format!("cortex_eval_vstats_12_{}", std::process::id()));
    let vault = temp.join("vault");
    let _ = fs::create_dir_all(&vault);
    fs::write(vault.join("nota1.md"), "a").unwrap();
    fs::write(vault.join("nota2.md"), "b").unwrap();

    let res = dispatch_tool("vault.stats", "", &temp).unwrap();
    assert!(res.contains("2"));

    let _ = fs::remove_dir_all(&temp);
}

#[test]
fn eval_13_webgraph_query_vacio_retorna_primeros_nodos() {
    let temp = std::env::temp_dir().join(format!("cortex_eval_wg_13_{}", std::process::id()));
    let _ = fs::create_dir_all(temp.join("src"));
    fs::write(temp.join("src").join("lib.rs"), "pub fn main() {}").unwrap();

    let res = dispatch_tool("webgraph.query", "", &temp).unwrap();
    assert!(res.contains("Nodos encontrados"));
    assert!(res.contains("lib.rs"));

    let _ = fs::remove_dir_all(&temp);
}

#[test]
fn eval_14_tool_inexistente_se_reporta_sin_panico() {
    let res = dispatch_tool("tool_fantasma_invalida", "arg", Path::new("."));
    assert!(res.is_err());
}

#[test]
fn eval_15_graph_payload_serializa_json_limpio() {
    let payload = cortex_brain_app::graph::ProjectGraphPayload {
        nodes: vec![cortex_brain_app::graph::GraphNode {
            id: "src/lib.rs".into(),
            label: "lib.rs".into(),
            kind: "file".into(),
            path: "/path/lib.rs".into(),
        }],
        edges: vec![],
    };
    let json = serde_json::to_string(&payload).unwrap();
    assert!(json.contains("lib.rs"));
}

#[test]
fn eval_16_session_status_payload_serializa_json() {
    let payload = cortex_brain_app::graph::SessionStatusPayload {
        active: true,
        session_id: Some("014".into()),
        spec_path: Some("vault/specs/auth.md".into()),
        checkpoints_count: 3,
        last_checkpoint: Some("Token validator".into()),
    };
    let json = serde_json::to_string(&payload).unwrap();
    assert!(json.contains("014"));
}

#[test]
fn eval_17_doctor_report_payload_serializa_json() {
    let payload = cortex_brain_app::graph::DoctorReportPayload {
        is_healthy: true,
        checks: vec![cortex_brain_app::graph::DoctorCheck {
            name: "Vault".into(),
            status: "ok".into(),
            message: "Sano".into(),
            auto_fix_tool: None,
        }],
    };
    let json = serde_json::to_string(&payload).unwrap();
    assert!(json.contains("Vault"));
}

#[test]
fn eval_18_engine_mantiene_aislamiento_entre_proyectos_distintos() {
    let engine = BrainEngine::with_factory(Duration::from_secs(90), |_| None);
    engine.insert_backend("proj_alpha", Box::new(cortex_brain::chat::ScriptedBackend::new("b1", vec!["Respuesta Alpha"])));
    engine.insert_backend("proj_beta", Box::new(cortex_brain::chat::ScriptedBackend::new("b2", vec!["Respuesta Beta"])));

    let t1 = engine.respond("proj_alpha", "q").unwrap();
    let t2 = engine.respond("proj_beta", "q").unwrap();

    assert_eq!(t1.text.trim(), "Respuesta Alpha");
    assert_eq!(t2.text.trim(), "Respuesta Beta");
}

#[test]
fn eval_19_slash_quit_no_mata_el_proceso() {
    let engine = BrainEngine::with_factory(Duration::from_secs(90), |_| None);
    engine.insert_backend("test", Box::new(cortex_brain::chat::ScriptedBackend::new("b", vec!["/quit"])));

    let turn = engine.respond("test", "/quit").unwrap();
    assert!(!turn.text.is_empty());
}

#[test]
fn eval_20_streaming_con_tool_governance_integra_resultado() {
    let temp = std::env::temp_dir().join(format!("cortex_eval_stream_20_{}", std::process::id()));
    let _ = fs::create_dir_all(temp.join(".cortex"));

    let engine = BrainEngine::with_factory(Duration::from_secs(90), |_| None);
    engine.insert_backend(
        temp.to_str().unwrap(),
        Box::new(cortex_brain::chat::ScriptedBackend::new("b", vec!["TOOL: doctor.inspect"])),
    );

    let mut pieces = Vec::new();
    let turn = engine
        .respond_streaming(temp.to_str().unwrap(), "salud", &mut |p| pieces.push(p.to_string()))
        .unwrap();

    assert_eq!(pieces, vec!["TOOL: doctor.inspect"]);
    assert!(turn.text.contains("Auditoría de Salud"));

    let _ = fs::remove_dir_all(&temp);
}
