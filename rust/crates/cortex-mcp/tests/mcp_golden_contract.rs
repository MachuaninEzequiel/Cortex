//! Gate P9: contrato MCP byte-a-byte contra el oráculo Python.
//!
//! 1. `list_tools` — catálogo de 32 tools + server_version "2.2",
//!    serializados idénticos a `tests/unit/mcp/golden/list_tools.json`
//!    (json.dumps(indent=2, ensure_ascii=False) + \n final).
//! 2. Tabla de ruteo `_TOOL_ROUTES` idéntica a ROUTING_ESPERADO del test
//!    Python (32 rutas; sync_vault va inline).
//! 3. Mensaje estable para herramienta desconocida.
//! 4. Ruta inline `cortex_sync_vault` con backend stub.
//! 5. `cortex_ping` bare byte-a-byte vs `golden_setup/ping/bare_ping.txt`
//!    (capturado por bench/parity/p9_ping_golden.py), normalizando
//!    `uptime_seconds` → {{UPTIME}}.

use std::collections::BTreeMap;

use cortex_mcp::server::{tool_routes, CortexMcpServer};
use cortex_mcp::tools_catalog::{build_tool_definitions, SERVER_VERSION};

const GOLDEN_LIST_TOOLS: &str = concat!(
    env!("CARGO_MANIFEST_DIR"),
    "/../../../tests/unit/mcp/golden/list_tools.json"
);
const GOLDEN_PING: &str = concat!(
    env!("CARGO_MANIFEST_DIR"),
    "/../../../bench/parity/golden_setup/ping/bare_ping.txt"
);

/// ROUTING_ESPERADO del oráculo (test_golden_contract.py), ordenado.
const ROUTING_ESPERADO: &[(&str, &str)] = &[
    ("cortex_autopilot_checkpoint", "_autopilot_tools.checkpoint"),
    ("cortex_autopilot_finish", "_autopilot_tools.finish"),
    ("cortex_autopilot_preflight", "_autopilot_tools.preflight"),
    ("cortex_autopilot_start", "_autopilot_tools.start"),
    ("cortex_autopilot_status", "_autopilot_tools.status"),
    ("cortex_close_session", "_close_session_text"),
    ("cortex_context", "_context_text"),
    ("cortex_create_spec", "_create_spec_text"),
    ("cortex_documenter_briefing", "_documenter_briefing_text"),
    ("cortex_emit_proposal", "_emit_proposal_text"),
    ("cortex_finish_session", "_finish_session_text"),
    ("cortex_get_hu", "_get_hu_text"),
    ("cortex_import_hu", "_import_hu_text"),
    ("cortex_ping", "_ping_text"),
    (
        "cortex_review_checkpoint",
        "_session_review_checkpoint_text",
    ),
    ("cortex_save_session", "_save_session_text"),
    ("cortex_search", "_search_text_dispatch"),
    ("cortex_search_vector", "_search_vector_text"),
    ("cortex_self_review_note", "_self_review_note_text"),
    ("cortex_session_checkpoint", "_session_checkpoint_text"),
    ("cortex_session_close", "_session_close_text"),
    ("cortex_session_list", "_session_list_text"),
    ("cortex_session_open", "_session_open_text"),
    ("cortex_session_status", "_session_status_text"),
    ("cortex_session_task_list", "_session_task_list_text"),
    ("cortex_session_task_update", "_session_task_update_text"),
    ("cortex_sync_ticket", "_build_sync_ticket_context"),
    ("cortex_validate_handoff", "_validate_handoff_text"),
    (
        "cortex_verify_session_claims",
        "_verify_session_claims_text",
    ),
    ("cortex_write_doc", "_write_doc_text"),
    ("write_design_note_canonical", "_write_design_note_text"),
];

fn normalize_uptime(s: &str) -> String {
    // Espejo exacto de la regex del capturador Python.
    let mut out = String::with_capacity(s.len());
    let mut rest = s;
    while let Some(pos) = rest.find("\"uptime_seconds\": ") {
        let after = &rest[pos..];
        let value_end = after["\"uptime_seconds\": ".len()..]
            .find(|c: char| !(c.is_ascii_digit() || matches!(c, '.' | 'e' | 'E' | '+' | '-')))
            .map(|i| i + "\"uptime_seconds\": ".len())
            .unwrap_or(after.len());
        out.push_str(&rest[..pos]);
        out.push_str("\"uptime_seconds\": {{UPTIME}}");
        rest = &rest[pos + value_end..];
    }
    out.push_str(rest);
    out
}

#[test]
fn list_tools_byte_a_byte_vs_oraculo() {
    // El archivo commiteado ES la forma esperada: {server_version, tools}.
    let golden_raw = std::fs::read_to_string(GOLDEN_LIST_TOOLS)
        .unwrap_or_else(|e| panic!("falta golden {GOLDEN_LIST_TOOLS}: {e}"));
    let golden: serde_json::Value = serde_json::from_str(&golden_raw).expect("golden JSON");

    assert_eq!(
        SERVER_VERSION,
        golden["server_version"].as_str().expect("version str"),
        "SERVER_VERSION difiere del contrato"
    );

    let tools = build_tool_definitions();
    let golden_tools = golden["tools"].as_array().expect("tools array");
    assert_eq!(
        tools.len(),
        golden_tools.len(),
        "cantidad de tools anunciadas difiere"
    );
    for (i, (ours, theirs)) in tools.iter().zip(golden_tools.iter()).enumerate() {
        assert_eq!(ours, theirs, "tool #{i} difiere del contrato");
    }

    // BYTE-A-BYTE: misma serialización que json.dumps(indent=2,
    // ensure_ascii=False) de CPython + '\n' final del archivo.
    let doc = serde_json::json!({
        "server_version": SERVER_VERSION,
        "tools": tools,
    });
    let mut serialized = serde_json::to_string_pretty(&doc).expect("serializable");
    serialized.push('\n');
    assert_eq!(
        serialized, golden_raw,
        "el contrato MCP cambió. Si el cambio es intencional, regenerá el \
         snapshot y documentalo en docs/transformacion/; si no, hay una \
         regresión."
    );

    // Nombres sin duplicados (test_nombres_sin_duplicados espejo).
    let mut names: Vec<&str> = tools
        .iter()
        .map(|t| t["name"].as_str().expect("name"))
        .collect();
    names.sort_unstable();
    let before = names.len();
    names.dedup();
    assert_eq!(before, names.len(), "nombres duplicados en el catálogo");

    // Cada tool anunciado tiene schema objeto con properties (espejo).
    for t in build_tool_definitions() {
        assert_eq!(t["inputSchema"]["type"], "object");
        assert!(t["inputSchema"]["properties"].is_object());
    }
}

#[test]
fn routing_table_idéntica_al_oráculo() {
    let ours = tool_routes();
    let expected: BTreeMap<&str, &str> =
        ROUTING_ESPERADO.iter().copied().collect::<BTreeMap<_, _>>();
    // Los anunciados deben ser exactamente los ruteables + sync_vault.
    let announced: BTreeMap<String, ()> = build_tool_definitions()
        .iter()
        .map(|t| (t["name"].as_str().expect("name").to_string(), ()))
        .collect();

    for (name, route) in &expected {
        assert_eq!(
            ours.get(name),
            Some(route),
            "{name} NO llegó a su handler esperado ({route})"
        );
    }
    assert_eq!(
        ours.len(),
        expected.len(),
        "la tabla de ruteo difiere del oráculo"
    );

    let mut announced_minus_sync_vault: Vec<&String> = announced
        .keys()
        .filter(|n| *n != "cortex_sync_vault")
        .collect();
    announced_minus_sync_vault.sort();
    let mut routed: Vec<&&str> = ours.keys().collect();
    routed.sort();
    assert_eq!(announced_minus_sync_vault.len(), routed.len());
    for (a, r) in announced_minus_sync_vault.iter().zip(routed.iter()) {
        assert_eq!(a.as_str(), **r, "anunciado vs ruteable difiere");
    }
}

#[test]
fn dispatch_ping_y_casos_congelados() {
    let mut s = CortexMcpServer::new();

    // Ping responde JSON válido con las claves esperadas (espejo test_ping).
    let ping = s
        .dispatch_tool_sync("cortex_ping", &serde_json::json!({}))
        .expect("ping ok");
    let data: serde_json::Value = serde_json::from_str(&ping).expect("ping JSON parseable");
    let keys: Vec<&str> = data
        .as_object()
        .expect("objeto")
        .keys()
        .map(String::as_str)
        .collect();
    assert_eq!(
        keys,
        vec![
            "status",
            "version",
            "uptime_seconds",
            "indices_loaded",
            "models_loaded",
            "last_error_seen",
            "recent_errors_count",
            "error_window_seconds"
        ]
    );
    assert_eq!(data["version"], SERVER_VERSION);

    // Herramienta desconocida: mensaje estable congelado.
    assert_eq!(
        s.dispatch_tool_sync("cortex_no_existe", &serde_json::json!({}))
            .expect("mensaje estable"),
        "Herramienta desconocida: cortex_no_existe"
    );

    // Ruta inline sync_vault contra backend stub (espejo test con _Mem(7)).
    let mut m = CortexMcpServer::with_memory(cortex_mcp::server::CountingMemory { count: 7 });
    assert_eq!(
        m.dispatch_tool_sync("cortex_sync_vault", &serde_json::json!({}))
            .expect("sync ok"),
        "Vault synced - 7 documents indexed."
    );
}

#[test]
fn ping_bare_byte_a_byte_vs_oraculo() {
    // Fixture bare con uptime ~0: status "starting" como la captura Python
    // (server recién construido ⇒ uptime < grace de 2s; el valor exacto lo
    // normaliza {{UPTIME}} en ambos lados).
    let s = CortexMcpServer::new();
    let raw = s.ping_text();
    let ours = normalize_uptime(&raw);
    let golden = std::fs::read_to_string(GOLDEN_PING).unwrap_or_else(|e| {
        panic!(
            "falta golden {GOLDEN_PING}: {e} — corré \
                 bench/parity/p9_ping_golden.py primero"
        )
    });
    assert_eq!(ours, golden, "ping bare difiere del oráculo Python");
}
