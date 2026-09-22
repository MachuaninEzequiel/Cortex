use cortex_judgement::Catalog;

#[test]
fn embedded_catalog_has_squeeze_constants() {
    let c = Catalog::embedded().unwrap();
    assert_eq!(c.model, "jev-1.13.0");
    assert_eq!(c.drop_below, 0.25);
    assert_eq!(c.overfetch, 30);
    assert_eq!(c.stage2_keep, 12);
    assert_eq!(c.prompt_keep, 8);
    assert_eq!(c.candidate_chars, 800);
    assert!(c.families.contains_key("session"));
    assert!(c.families.contains_key("other"));
}

#[test]
fn corrupt_override_is_err() {
    let dir = std::env::temp_dir().join("cortex-judgement-bad-yaml");
    let _ = std::fs::create_dir_all(&dir);
    let path = dir.join("questions.yaml");
    std::fs::write(&path, "thresholds: [ unterminated").unwrap();
    assert!(
        Catalog::load(Some(&path)).is_err(),
        "YAML corrupto no debe prender el catálogo"
    );
}
