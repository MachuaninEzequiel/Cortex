//! Default-off: YAML sin bloque `judgement` ≡ community (enabled=false).
//! El dump canónico de fixtures viejos no debe ganar un campo nuevo.

use cortex_config::{CortexConfig, JudgementProvider, PurposeMode};

#[test]
fn omitted_judgement_block_equals_disabled() {
    let cfg: CortexConfig = serde_yaml::from_str("semantic:\n  vault_path: vault\n")
        .expect("YAML sin judgement debe parsear");
    assert!(
        !cfg.judgement.enabled,
        "omitir el bloque ≡ enabled=false, no un default-on"
    );
    assert_eq!(cfg.judgement.provider, JudgementProvider::None);
    assert_eq!(cfg.judgement.purposes.search_squeeze, PurposeMode::Off);
    assert!(!cfg.judgement.search_squeeze_on());
}

#[test]
fn empty_yaml_equals_disabled() {
    let cfg: CortexConfig = serde_yaml::from_str("{}").unwrap();
    assert!(!cfg.judgement.enabled);
    assert_eq!(cfg.judgement.provider, JudgementProvider::None);
}

#[test]
fn dump_without_judgement_block_omits_the_field() {
    let out = cortex_config::load_and_dump("");
    assert!(
        !out.contains("judgement"),
        "dump de YAML viejo no debe emitir judgement (paridad): {out}"
    );
}

#[test]
fn explicit_off_still_disabled() {
    let yaml = r#"
judgement:
  enabled: false
  provider: none
  purposes:
    search_squeeze: off
"#;
    let cfg: CortexConfig = serde_yaml::from_str(yaml).unwrap();
    assert!(!cfg.judgement.enabled);
    assert!(!cfg.judgement.search_squeeze_on());
}

#[test]
fn typesafe_on_requires_purpose() {
    let yaml = r#"
judgement:
  enabled: true
  provider: typesafe
  model: jev-1.13.0
  timeout_ms: 2000
  fail: open
  api_key_env: TYPESAFE_API_KEY
  purposes:
    search_squeeze: on
"#;
    let cfg: CortexConfig = serde_yaml::from_str(yaml).unwrap();
    assert!(cfg.judgement.enabled);
    assert_eq!(cfg.judgement.provider, JudgementProvider::Typesafe);
    assert_eq!(cfg.judgement.model, "jev-1.13.0");
    assert_eq!(cfg.judgement.timeout_ms, 2000);
    assert_eq!(cfg.judgement.api_key_env, "TYPESAFE_API_KEY");
    assert_eq!(cfg.judgement.purposes.search_squeeze, PurposeMode::On);
    assert!(cfg.judgement.search_squeeze_on());
}

#[test]
fn omitted_context_pack_equals_off() {
    let yaml = r#"
judgement:
  enabled: true
  provider: typesafe
  purposes:
    search_squeeze: on
"#;
    let cfg: CortexConfig = serde_yaml::from_str(yaml).unwrap();
    assert_eq!(cfg.judgement.purposes.context_pack, PurposeMode::Off);
    assert!(
        !cfg.judgement.context_pack_on(),
        "YAML sin context_pack ≡ off; no se prende por search_squeeze"
    );
}

#[test]
fn context_pack_on_requires_enabled_typesafe() {
    let yaml = r#"
judgement:
  enabled: true
  provider: typesafe
  purposes:
    context_pack: on
"#;
    let cfg: CortexConfig = serde_yaml::from_str(yaml).unwrap();
    assert_eq!(cfg.judgement.purposes.context_pack, PurposeMode::On);
    assert!(cfg.judgement.context_pack_on());
}

#[test]
fn omitted_utterance_equals_off() {
    let yaml = r#"
judgement:
  enabled: true
  provider: typesafe
  purposes:
    search_squeeze: on
"#;
    let cfg: CortexConfig = serde_yaml::from_str(yaml).unwrap();
    assert_eq!(cfg.judgement.purposes.utterance, PurposeMode::Off);
    assert!(
        !cfg.judgement.utterance_on(),
        "YAML sin utterance ≡ Direct; cero HTTP de portero"
    );
}

#[test]
fn omitted_session_compact_equals_off() {
    let yaml = r#"
judgement:
  enabled: true
  provider: typesafe
  purposes:
    search_squeeze: on
"#;
    let cfg: CortexConfig = serde_yaml::from_str(yaml).unwrap();
    assert_eq!(cfg.judgement.purposes.session_compact, PurposeMode::Off);
    assert!(
        !cfg.judgement.session_compact_on(),
        "YAML sin session_compact ≡ off; no se prende solo"
    );
}

#[test]
fn session_compact_on_requires_enabled_typesafe() {
    let yaml = r#"
judgement:
  enabled: true
  provider: typesafe
  purposes:
    session_compact: on
"#;
    let cfg: CortexConfig = serde_yaml::from_str(yaml).unwrap();
    assert_eq!(cfg.judgement.purposes.session_compact, PurposeMode::On);
    assert!(cfg.judgement.session_compact_on());
}

#[test]
fn model_routing_and_system_one_alias_parses_properly() {
    let yaml = r#"
system_one:
  enabled: true
  provider: typesafe
  purposes:
    model_routing: on
  model_router:
    enabled: true
    hosts:
      antigravity:
        designer: "google:gemini-2.5-pro"
        documenter: "google:gemini-2.5-flash"
      pi:
        designer: "openrouter:anthropic/claude-3.5-sonnet"
        documenter: "openai-codex:gpt-4o-mini"
"#;
    let cfg: CortexConfig = serde_yaml::from_str(yaml).expect("system_one alias debe parsear");
    assert!(cfg.system_one().enabled);
    assert!(cfg.system_one().model_routing_on());
    assert!(cfg.system_one().model_router.enabled);

    let hosts = &cfg.system_one().model_router.hosts;
    assert_eq!(hosts.get("antigravity").unwrap().designer.as_deref(), Some("google:gemini-2.5-pro"));
    assert_eq!(hosts.get("antigravity").unwrap().documenter.as_deref(), Some("google:gemini-2.5-flash"));
    assert_eq!(hosts.get("pi").unwrap().designer.as_deref(), Some("openrouter:anthropic/claude-3.5-sonnet"));
    assert_eq!(hosts.get("pi").unwrap().documenter.as_deref(), Some("openai-codex:gpt-4o-mini"));
}

