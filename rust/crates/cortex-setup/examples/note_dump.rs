//! Debug/paridad de una nota: imprime el contenido construido para un caso
//! del fixture writers (inputs.json). Uso:
//!   cargo run -q -p cortex-setup --example note_dump -- <case>

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let case_name = args.get(1).cloned().unwrap_or_default();
    let golden = concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/../../../bench/parity/golden_setup/writers"
    );
    let raw = std::fs::read_to_string(format!("{golden}/inputs.json")).unwrap();
    let doc: serde_json::Value = serde_json::from_str(&raw).unwrap();
    let case = doc["cases"]
        .as_array()
        .unwrap()
        .iter()
        .find(|c| c["case"].as_str() == Some(case_name.as_str()))
        .unwrap_or_else(|| panic!("caso {case_name} no encontrado"));
    use chrono::{DateTime, Utc};
    let now: DateTime<Utc> = DateTime::parse_from_rfc3339(doc["now"].as_str().unwrap())
        .unwrap()
        .with_timezone(&Utc);
    let fields = case["fields"].as_object().unwrap().clone();
    let mut req =
        cortex_setup::writers::NoteRequest::from_json(case["doc_type"].as_str().unwrap(), fields)
            .unwrap();
    let vault = std::path::Path::new("/tmp/p8-debug-vault");
    let _ = std::fs::create_dir_all(vault.join("decisions"));
    // sembrar ADR-001 para auto-numbering como el capturador
    if case_name == "adr_auto_number" {
        std::fs::create_dir_all(vault.join("decisions")).unwrap();
        std::fs::write(
            vault.join("decisions/ADR-001-previo.md"),
            "---\nprevia\n---\n",
        )
        .unwrap();
    }
    let out = cortex_setup::writers::build_note(
        &mut req,
        vault,
        case["scope"].as_str().unwrap(),
        case["project_id"].as_str(),
        case["actor"].as_str(),
        now,
    )
    .unwrap();
    print!("{}", out.content);
}
