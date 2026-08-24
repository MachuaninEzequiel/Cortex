//! Paridad P8c: renderers de setup/templates byte-a-byte contra el oráculo
//! Python (bench/parity/golden_setup/setup).

use std::path::PathBuf;

use cortex_setup::detector::{EnvInfo, ProjectContext};
use cortex_setup::setup_templates;

const GOLDEN: &str = concat!(
    env!("CARGO_MANIFEST_DIR"),
    "/../../../bench/parity/golden_setup/setup"
);

fn create_project(base: &std::path::Path, name: &str, markers: &[String], new_layout: bool) -> PathBuf {
    let root = base.join(name);
    std::fs::create_dir_all(&root).unwrap();
    for rel in markers {
        let p = root.join(rel);
        if rel.ends_with('/') {
            std::fs::create_dir_all(&p).unwrap();
        } else {
            if let Some(parent) = p.parent() {
                std::fs::create_dir_all(parent).unwrap();
            }
            // El contenido de los marcadores no afecta la detección salvo
            // package.json/go.mod/Cargo.toml/Gemfile; se recrean desde el
            // fixture embebido (mismos bytes que el capturador).
            std::fs::write(&p, marker_content(rel)).unwrap();
        }
    }
    if new_layout {
        let ws = root.join(".cortex").join("workspace.yaml");
        std::fs::create_dir_all(ws.parent().unwrap()).unwrap();
        std::fs::write(ws, "layout_version: 2\n").unwrap();
    }
    root
}

/// Contenidos de los marcadores (deben ser idénticos a p8_setup_golden.py).
fn marker_content(rel: &str) -> &'static str {
    match rel {
        "pyproject.toml" => "[project]\nname = \"demo-api\"\n",
        "package.json" => concat!(
            "{\n",
            " \"name\": \"web-app\",\n",
            " \"scripts\": {\n",
            "  \"test\": \"vitest run\",\n",
            "  \"lint\": \"eslint .\",\n",
            "  \"build\": \"vite build\"\n",
            " },\n",
            " \"dependencies\": {\n",
            "  \"react\": \"^18\"\n",
            " },\n",
            " \"devDependencies\": {\n",
            "  \"vite\": \"^5\",\n",
            "  \"typescript\": \"^5\"\n",
            " }\n",
            "}"
        ),
        "go.mod" => "module ejemplo/api\n\ngo 1.22\n",
        "Cargo.toml" => "[package]\nname = \"ejemplo-core\"\n",
        "pom.xml" => "<project/>",
        "Gemfile" => "gem 'rails'\ngem 'rspec'\n",
        other => panic!("marcador sin contenido definido: {other}"),
    }
}

#[test]
fn setup_renderers_byte_parity() {
    let raw = std::fs::read_to_string(format!("{GOLDEN}/inputs.json")).unwrap();
    let doc: serde_json::Value = serde_json::from_str(&raw).unwrap();

    let base = std::env::temp_dir().join(format!("cortex-setup-parity-{}", std::process::id()));
    let _ = std::fs::remove_dir_all(&base);

    // Env congelado SIN OPENAI_API_KEY, igual que el capturador.
    let env = EnvInfo::default();

    for case in doc["cases"].as_array().unwrap() {
        let name = case["case"].as_str().unwrap();
        let markers: Vec<String> = case["markers"]
            .as_array()
            .unwrap()
            .iter()
            .map(|m| m.as_str().unwrap().to_string())
            .collect();
        let new_layout = case["new_layout"].as_bool().unwrap();

        // El capturador crea el proyecto SIN workspace.yaml y luego lo
        // agrega para los casos *_new_layout; replicamos exactamente eso.
        let clean_name = name.strip_suffix("_new_layout").unwrap_or(name);
        let root = create_project(&base, clean_name, &markers, new_layout);

        let ctx = ProjectContext::detect_with(&root, &env);

        let outputs: Vec<(&str, String)> = vec![
            ("config_yaml", setup_templates::render_config_yaml(&ctx)),
            (
                "enterprise_vault_readme",
                setup_templates::render_enterprise_vault_readme(&ctx),
            ),
            (
                "ci_pull_request",
                setup_templates::render_ci_pull_request(&ctx),
            ),
            (
                "ci_enterprise_governance",
                setup_templates::render_ci_enterprise_governance(&ctx),
            ),
            ("ci_feature", setup_templates::render_ci_feature(&ctx)),
            ("cd_deploy", setup_templates::render_cd_deploy(&ctx)),
            (
                "architecture_md",
                setup_templates::render_architecture_md(&ctx),
            ),
            ("decisions_md", setup_templates::render_decisions_md()),
            ("context_md", setup_templates::render_context_md(&ctx)),
            ("runbooks_md", setup_templates::render_runbooks_md(&ctx)),
            (
                "enterprise_runbook_md",
                setup_templates::render_enterprise_runbook_md(&ctx),
            ),
            (
                "git_vault_policy_md",
                setup_templates::render_git_vault_policy_md(),
            ),
            ("workspace_yaml", setup_templates::render_workspace_yaml()),
        ];

        for (rname, content) in outputs {
            let golden_path = format!("{GOLDEN}/{name}/{rname}.out");
            let expected = std::fs::read(&golden_path)
                .unwrap_or_else(|e| panic!("falta golden {golden_path}: {e}"));
            assert_eq!(
                content.as_bytes(),
                expected.as_slice(),
                "{name}/{rname}: difiere del oráculo Python"
            );
        }
    }
    let _ = std::fs::remove_dir_all(&base);
}

#[test]
fn org_yaml_byte_parity() {
    let raw = std::fs::read_to_string(format!("{GOLDEN}/org_inputs.json")).unwrap();
    let doc: serde_json::Value = serde_json::from_str(&raw).unwrap();
    let project_name = doc["project_name"].as_str().unwrap();

    for case in doc["cases"].as_array().unwrap() {
        let profile = case["profile"].as_str().unwrap();
        let gh = case["github_actions_enabled"].as_bool().unwrap();
        // En Python: branch_isolation_enabled = profile == "regulated-organization".
        let out = setup_templates::render_org_yaml(
            project_name,
            profile,
            gh,
            profile == "regulated-organization",
        )
        .expect("org yaml");
        let file = case["file"].as_str().unwrap();
        let expected = std::fs::read(format!("{GOLDEN}/_org/{file}")).expect("golden org existe");
        assert_eq!(
            out.as_bytes(),
            expected.as_slice(),
            "org.yaml {file}: difiere del oráculo"
        );
    }
}
