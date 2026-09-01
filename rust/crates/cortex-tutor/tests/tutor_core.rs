use cortex_tutor::hint::{get_hint, Hint, ProjectState};
use cortex_tutor::topics::get_all_topics;

#[test]
fn seven_topics_in_canonical_order_with_python_metadata() {
    let topics = get_all_topics();
    assert_eq!(topics.len(), 7);

    // Metadatos extraídos por introspección del oráculo Python.
    let esperados = [
        (
            "🚀",
            "start",
            "Primeros Pasos",
            Some("docs/guides/getting-started.md"),
        ),
        ("📋", "commands", "Comandos Esenciales", None),
        (
            "🔄",
            "workflow",
            "Flujo de Trabajo",
            Some("docs/enterprise/MANIFIESTO-CORTEX-ENTERPRISE.md"),
        ),
        (
            "⚙️",
            "pipeline",
            "Pipeline CI/CD",
            Some("docs/guides/pipeline-setup.md"),
        ),
        (
            "📁",
            "vault",
            "Vault y Documentación",
            Some("docs/guides/vault-structure.md"),
        ),
        (
            "🏢",
            "enterprise",
            "Enterprise Memory",
            Some("docs/guides/enterprise-vault.md"),
        ),
        ("🔌", "ide", "Integración IDE", None),
    ];
    for (t, (icon, slug, title, guide)) in topics.iter().zip(esperados.iter()) {
        assert_eq!(t.icon, *icon);
        assert_eq!(t.slug, *slug);
        assert_eq!(t.title, *title);
        assert_eq!(t.guide_path, *guide);
    }
    // Cuerpos embebidos byte-exacto desde content/.
    assert!(topics[0].body.starts_with("╭─"));
    assert!(topics[0].body.contains("cortex doctor"));
}

#[test]
fn hint_l0_not_initialized() {
    let tmp = tempfile::tempdir().unwrap();
    let state = ProjectState::detect(tmp.path());
    let hint = get_hint(&state);
    assert_eq!(hint.icon, "🚀");
    assert_eq!(hint.title, "Cortex no está inicializado en este proyecto");
    assert!(hint.allowed_command_starts_with("cortex setup agent"));
}

trait HintExt {
    fn allowed_command_starts_with(&self, prefix: &str) -> bool;
}
impl HintExt for Hint {
    fn allowed_command_starts_with(&self, prefix: &str) -> bool {
        self.command.starts_with(prefix)
    }
}

#[test]
fn hint_l1_no_specs_after_init() {
    let tmp = tempfile::tempdir().unwrap();
    let root = tmp.path().join("proj");
    std::fs::create_dir_all(&root).unwrap();
    std::fs::write(root.join("config.yaml"), "semantic:\n  vault_path: vault\n").unwrap();
    let state = ProjectState::detect(&root);
    assert!(state.has_config);
    let hint = get_hint(&state);
    assert_eq!(hint.icon, "📝");
    assert_eq!(hint.title, "No hay especificaciones creadas");
}

#[test]
fn hint_l2_counts_interpolated_and_chain_order() {
    // Estado construido a mano (campos pub) para probar interpolación y
    // orden de la cadena sin ambigüedad de layout en fixtures.
    let state = ProjectState {
        has_config: true,
        has_specs: true,
        spec_count: 2,
        ..Default::default()
    };
    let hint = get_hint(&state);
    assert_eq!(hint.icon, "💾");
    assert_eq!(hint.title, "Tenés 2 spec(s) pero 0 sesiones guardadas");

    // Con sesiones y mcp configurado + pocos docs ⇒ L6 (sin IDE).
    let state = ProjectState {
        has_config: true,
        has_specs: true,
        has_sessions: true,
        session_count: 1,
        spec_count: 2,
        vault_doc_count: 3,
        has_mcp_config: false,
        ..Default::default()
    };
    assert_eq!(get_hint(&state).icon, "🔌");

    // Todo bien ⇒ L7 con conteos interpolados.
    let state = ProjectState {
        has_config: true,
        has_specs: true,
        has_sessions: true,
        session_count: 4,
        spec_count: 2,
        vault_doc_count: 12,
        has_github_workflows: true,
        has_org_yaml: true,
        has_enterprise_vault: true,
        has_mcp_config: true,
        ..Default::default()
    };
    let hint = get_hint(&state);
    assert_eq!(hint.icon, "✅");
    assert_eq!(
        hint.body,
        "Vault: 12 docs | Specs: 2 | Sessions: 4\nBuscá algo en tu memoria para verificar que todo funciona."
    );
}
