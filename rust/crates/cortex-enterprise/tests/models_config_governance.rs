use std::path::Path;

use cortex_enterprise::config::{
    build_enterprise_org_config, describe_enterprise_topology, load_enterprise_config,
    render_enterprise_config_yaml, write_enterprise_config,
};
use cortex_enterprise::governance::{
    allowed_classifications_for, assert_can_promote, assert_can_review, user_team,
};
use cortex_enterprise::models::{EnterpriseOrgConfig, EnterprisePolicies, OrgProfile, TeamConfig};

#[test]
fn small_company_and_unicode_yaml_match_oracle() {
    let cfg = build_enterprise_org_config("Ácme Platform", OrgProfile::SmallCompany, true, false)
        .unwrap();
    // Oráculo Python: slugify('Ácme Platform') == 'cme-platform' (la Á no
    // translitera; se cae y deja '-' que se recorta).
    assert_eq!(cfg.organization.slug, "cme-platform");
    let yaml = render_enterprise_config_yaml(&cfg);
    assert!(yaml.starts_with(
        "# Cortex enterprise memory topology\n# This file governs organization-level memory, promotion and governance behavior.\n# Local runtime mechanics still live in config.yaml.\n\n"
    ));
    assert!(yaml
        .contains("name: \"\\xC1cme Platform\"\n  slug: cme-platform\n  profile: small-company\n"));
    assert!(yaml.ends_with("glossary: 0\n"));
}

#[test]
fn defaults_invariants_and_case_sensitive_enums_match_oracle() {
    let mut cfg = EnterpriseOrgConfig::default();
    assert_eq!(cfg.retention_defaults.adr, 2555);
    assert_eq!(cfg.promotion.allowed_doc_types[3].to_string(), "hu");
    cfg.memory.enterprise_semantic_enabled = false;
    assert_eq!(cfg.validate().unwrap_err().to_string(),
        "promotion.enabled requires memory.enterprise_semantic_enabled=true so promoted knowledge has a target");

    let invalid: Result<EnterpriseOrgConfig, _> =
        serde_yaml::from_str("organization:\n  profile: Small-Company\n");
    assert!(invalid.is_err());
    let invalid_team: Result<EnterpriseOrgConfig, _> =
        serde_yaml::from_str("teams:\n- id: Bad_team\n");
    assert_eq!(
        invalid_team.unwrap().validate().unwrap_err().to_string(),
        "teams[].id must match ^[a-z0-9-]+$ and contain at least one character"
    );
}

#[test]
fn paths_round_trip_and_governance_preserve_first_match() {
    let temp = tempfile::tempdir().unwrap();
    let root = temp.path();
    let cfg = EnterpriseOrgConfig {
        teams: vec![
            TeamConfig {
                id: "first".into(),
                members: vec!["alice".into()],
                can_promote: false,
                can_review: true,
            },
            TeamConfig {
                id: "second".into(),
                members: vec!["alice".into()],
                can_promote: true,
                can_review: false,
            },
        ],
        policies: EnterprisePolicies {
            confidential_visible_to: vec!["first".into()],
        },
        ..EnterpriseOrgConfig::default()
    };
    assert_eq!(user_team(Some("alice"), &cfg), Some("first".to_string()));
    assert_eq!(
        allowed_classifications_for(Some("first"), &cfg)
            .iter()
            .map(|c| c.as_str())
            .collect::<Vec<_>>(),
        vec!["public", "internal", "confidential"]
    );
    assert_eq!(
        assert_can_promote("alice", &cfg).unwrap_err().to_string(),
        "actor 'alice' (team='first') cannot promote"
    );
    assert_eq!(assert_can_review("alice", &cfg).unwrap(), "first");

    let written = write_enterprise_config(root, &cfg, None).unwrap();
    assert_eq!(written, root.join(".cortex/org.yaml"));
    assert_eq!(
        load_enterprise_config(root, true, None, None)
            .unwrap()
            .unwrap(),
        cfg
    );
    assert_eq!(
        cfg.resolve_enterprise_vault_path(root, None),
        Some(root.join("vault-enterprise"))
    );
    assert!(
        describe_enterprise_topology(Some(&cfg), Some(Path::new("/repo")), None)
            .contains("profile=small-company")
    );
}
