//! Pack enricher (spec 07): fail-open, omitido ≡ nativo, dual noul.

use std::sync::Mutex;

use cortex_judgement::{
    Candidate, Catalog, JudgementClient, JudgementError, JudgementRequest, JudgementResponse,
    NullClient, Purpose,
};

struct ScriptClient {
    calls: Mutex<Vec<Result<JudgementResponse, JudgementError>>>,
    context_pack: bool,
}

impl ScriptClient {
    fn pack(calls: Vec<Result<JudgementResponse, JudgementError>>) -> Self {
        Self {
            calls: Mutex::new(calls),
            context_pack: true,
        }
    }
}

impl JudgementClient for ScriptClient {
    fn enabled(&self, purpose: Purpose) -> bool {
        self.context_pack && matches!(purpose, Purpose::ContextPack)
    }
    fn evaluate(&self, _request: &JudgementRequest) -> Result<JudgementResponse, JudgementError> {
        let mut g = self.calls.lock().unwrap();
        if g.is_empty() {
            return Err(JudgementError::Http(429));
        }
        g.remove(0)
    }
}

fn cands() -> Vec<Candidate> {
    vec![
        Candidate {
            id: "0".into(),
            path: "sessions.rs.md".into(),
            title: "sessions tui".into(),
            text: "mcp sessions backend wrapper chrome".into(),
        },
        Candidate {
            id: "1".into(),
            path: "verification.md".into(),
            title: "verification".into(),
            text: "checkpoint verification quality gates native".into(),
        },
        Candidate {
            id: "2".into(),
            path: "other.md".into(),
            title: "other".into(),
            text: "unrelated keyword overlap".into(),
        },
    ]
}

fn family_resp(choice: &str) -> JudgementResponse {
    let mut answers = serde_json::Map::new();
    answers.insert(
        "family".into(),
        serde_json::json!({"choice": choice, "confidence": 1.0}),
    );
    JudgementResponse {
        model: "jev-1.13.0".into(),
        answers,
        usage: Default::default(),
        backend: "typesafe".into(),
    }
}

fn noul_dual(pairs: &[(&str, f64)]) -> JudgementResponse {
    let mut answers = serde_json::Map::new();
    for (k, n) in pairs {
        answers.insert((*k).into(), serde_json::json!({ "noul": n }));
    }
    JudgementResponse {
        model: "jev-1.13.0".into(),
        answers,
        usage: Default::default(),
        backend: "typesafe".into(),
    }
}

#[test]
fn pack_off_returns_none() {
    let catalog = Catalog::embedded().unwrap();
    let out = cortex_judgement::pack_context(&NullClient, &catalog, "q", &[], cands(), &[]);
    assert!(out.is_none(), "purpose off / NullClient ⇒ presenter nativo");
}

#[test]
fn pack_429_returns_none() {
    let catalog = Catalog::embedded().unwrap();
    let client = ScriptClient::pack(vec![Err(JudgementError::Http(429))]);
    let out = cortex_judgement::pack_context(
        &client,
        &catalog,
        "checkpoint verification",
        &[],
        cands(),
        &[],
    );
    assert!(
        out.is_none(),
        "429 ⇒ compact nativo, nunca lista vacía de Jev"
    );
}

#[test]
fn pack_selects_canonical_and_pointers() {
    let catalog = Catalog::embedded().unwrap();
    let client = ScriptClient::pack(vec![
        Ok(family_resp("session")),
        Ok(noul_dual(&[
            ("rel_c0_body", 0.10),
            ("rel_c0_ptr", 0.40),
            ("rel_c1_body", 0.92),
            ("rel_c1_ptr", 0.95),
            ("rel_c2_body", 0.05),
            ("rel_c2_ptr", 0.10),
        ])),
    ]);
    let out = cortex_judgement::pack_context(
        &client,
        &catalog,
        "checkpoint verification",
        &[],
        cands(),
        &[],
    )
    .expect("pack on + HTTP ok");
    assert_eq!(out.family, "session");
    assert_eq!(out.canonical.len(), 1, "0 files ⇒ 1 canónico máx");
    assert_eq!(out.canonical[0].candidate.path, "verification.md");
    assert!(out.canonical[0].noul >= cortex_judgement::KEEP_BODY);
    assert_eq!(out.pointers.len(), 1);
    assert_eq!(out.pointers[0].path, "sessions.rs.md");
    assert_eq!(out.pointers[0].rel, "related");
    assert!(out.pointers[0].line.chars().count() <= 80);
    assert!(out.dropped >= 1);
    assert!(out.canonical.len() <= 2);
    assert!(out.pointers.len() <= 6);
}

struct CaptureClient {
    inner: ScriptClient,
    captured: Mutex<Vec<JudgementRequest>>,
}

impl CaptureClient {
    fn new(inner: ScriptClient) -> Self {
        Self {
            inner,
            captured: Mutex::new(Vec::new()),
        }
    }
}

impl JudgementClient for CaptureClient {
    fn enabled(&self, purpose: Purpose) -> bool {
        self.inner.enabled(purpose)
    }
    fn evaluate(&self, request: &JudgementRequest) -> Result<JudgementResponse, JudgementError> {
        self.captured.lock().unwrap().push(request.clone());
        self.inner.evaluate(request)
    }
}

#[test]
fn pack_payload_has_state_and_questions() {
    let catalog = Catalog::embedded().unwrap();
    let client = CaptureClient::new(ScriptClient::pack(vec![
        Ok(family_resp("session")),
        Ok(noul_dual(&[
            ("rel_c0_body", 0.10),
            ("rel_c0_ptr", 0.40),
            ("rel_c1_body", 0.92),
            ("rel_c1_ptr", 0.95),
            ("rel_c2_body", 0.05),
            ("rel_c2_ptr", 0.10),
        ])),
    ]));
    let _ = cortex_judgement::pack_context(
        &client,
        &catalog,
        "checkpoint verification",
        &["verification.md".into()],
        cands(),
        &[],
    );
    let captured = client.captured.lock().unwrap();
    assert!(captured.len() >= 2, "compass + dual noul");
    for req in captured.iter() {
        assert!(req.body.get("state").is_some(), "golden: state");
        assert!(req.body.get("questions").is_some(), "golden: questions");
        assert!(req.body.get("model").is_some());
    }
    let noul = &captured[1].body;
    assert!(noul["questions"].get("rel_c0_body").is_some());
    assert!(noul["questions"].get("rel_c0_ptr").is_some());
    assert!(noul["state"].get("goal").is_some());
    assert!(noul["state"].get("candidates").is_some());
}

#[test]
fn pack_nobody_passing_returns_none() {
    let catalog = Catalog::embedded().unwrap();
    let client = ScriptClient::pack(vec![
        Ok(family_resp("other")),
        Ok(noul_dual(&[
            ("rel_c0_body", 0.01),
            ("rel_c0_ptr", 0.02),
            ("rel_c1_body", 0.01),
            ("rel_c1_ptr", 0.02),
            ("rel_c2_body", 0.01),
            ("rel_c2_ptr", 0.02),
        ])),
    ]);
    let out = cortex_judgement::pack_context(&client, &catalog, "q", &[], cands(), &[]);
    assert!(out.is_none(), "nadie pasa umbral ⇒ formato nativo");
}

#[test]
fn pack_pin_never_dropped() {
    let catalog = Catalog::embedded().unwrap();
    let client = ScriptClient::pack(vec![
        Ok(family_resp("session")),
        Ok(noul_dual(&[
            ("rel_c0_body", 0.10),
            ("rel_c0_ptr", 0.40),
            ("rel_c1_body", 0.92),
            ("rel_c1_ptr", 0.95),
            ("rel_c2_body", 0.05),
            ("rel_c2_ptr", 0.10),
        ])),
    ]);
    let out = cortex_judgement::pack_context(
        &client,
        &catalog,
        "checkpoint verification",
        &[],
        cands(),
        &["other.md".into()],
    )
    .unwrap();
    assert!(
        out.pointers.iter().any(|p| p.path == "other.md"),
        "pin baja a puntero, no desaparece"
    );
}

#[test]
fn pack_fetch_k_overfetches() {
    assert_eq!(cortex_judgement::pack_fetch_k(8), 16);
    assert_eq!(cortex_judgement::pack_fetch_k(20), 40);
}

#[test]
fn pack_with_typed_edges_sets_correct_rel() {
    use cortex_judgement::PackEdge;

    let catalog = Catalog::embedded().unwrap();
    let client = ScriptClient::pack(vec![
        Ok(family_resp("session")),
        Ok(noul_dual(&[
            ("rel_c0_body", 0.90),
            ("rel_c0_ptr", 0.95),
            ("rel_c1_body", 0.20),
            ("rel_c1_ptr", 0.70),
            ("rel_c2_body", 0.10),
            ("rel_c2_ptr", 0.60),
        ])),
    ]);
    let edges = vec![
        PackEdge::new("sessions.rs.md", "verification.md", "implements"),
        PackEdge::with_line("sessions.rs.md", "docs/wiki.md", "wikilink", "Wiki note on sessions"),
        PackEdge::new("sessions.rs.md", "docs/adr/001.md", "constrains"),
    ];

    let out = cortex_judgement::pack_context_with_edges(
        &client,
        &catalog,
        "checkpoint verification",
        &[],
        cands(),
        &[],
        &edges,
    )
    .expect("pack with edges");

    assert_eq!(out.canonical.len(), 1);
    assert_eq!(out.canonical[0].candidate.path, "sessions.rs.md");

    // Pointers: 3 validated edges + candidate c2 as fallback related
    let ptr_types: Vec<(&str, &str)> = out
        .pointers
        .iter()
        .map(|p| (p.path.as_str(), p.rel.as_str()))
        .collect();

    assert!(
        ptr_types.contains(&("verification.md", "implements")),
        "implements edge found on candidate"
    );
    assert!(
        ptr_types.contains(&("docs/wiki.md", "wikilink")),
        "wikilink edge from neighborhood not in candidates"
    );
    assert!(
        ptr_types.contains(&("docs/adr/001.md", "constrains")),
        "constrains edge from neighborhood not in candidates"
    );

    let related_ptrs: Vec<&str> = out
        .pointers
        .iter()
        .filter(|p| p.rel == "related")
        .map(|p| p.path.as_str())
        .collect();
    assert_eq!(related_ptrs, vec!["other.md"], "c2 falls back to related");
    assert!(out.pointers.len() <= 6);
}

#[test]
fn pack_max_two_related_fallback_when_edges_present() {
    use cortex_judgement::PackEdge;

    let catalog = Catalog::embedded().unwrap();
    let client = ScriptClient::pack(vec![
        Ok(family_resp("session")),
        Ok(noul_dual(&[
            ("rel_c0_body", 0.90),
            ("rel_c0_ptr", 0.95),
            ("rel_c1_body", 0.10),
            ("rel_c1_ptr", 0.85),
            ("rel_c2_body", 0.10),
            ("rel_c2_ptr", 0.75),
            ("rel_c3_body", 0.10),
            ("rel_c3_ptr", 0.65),
            ("rel_c4_body", 0.10),
            ("rel_c4_ptr", 0.55),
        ])),
    ]);

    let candidates = vec![
        Candidate {
            id: "0".into(),
            path: "main.rs".into(),
            title: "main".into(),
            text: "canonical mechanism".into(),
        },
        Candidate {
            id: "1".into(),
            path: "auth.md".into(),
            title: "auth".into(),
            text: "implements edge".into(),
        },
        Candidate {
            id: "2".into(),
            path: "rel1.md".into(),
            title: "rel1".into(),
            text: "related 1".into(),
        },
        Candidate {
            id: "3".into(),
            path: "rel2.md".into(),
            title: "rel2".into(),
            text: "related 2".into(),
        },
        Candidate {
            id: "4".into(),
            path: "rel3.md".into(),
            title: "rel3".into(),
            text: "related 3 should be dropped".into(),
        },
    ];

    let edges = vec![PackEdge::new("main.rs", "auth.md", "implements")];

    let out = cortex_judgement::pack_context_with_edges(
        &client,
        &catalog,
        "query",
        &[],
        candidates,
        &[],
        &edges,
    )
    .expect("pack with edges");

    assert_eq!(out.canonical.len(), 1);
    assert_eq!(out.canonical[0].candidate.path, "main.rs");

    let related_count = out.pointers.iter().filter(|p| p.rel == "related").count();
    assert_eq!(
        related_count,
        cortex_judgement::MAX_RELATED_POINTERS,
        "strictly max 2 related pointers fallback per pack"
    );

    // Total pointers: 1 implements + 2 related = 3
    assert_eq!(out.pointers.len(), 3);
    assert_eq!(out.pointers[0].path, "auth.md");
    assert_eq!(out.pointers[0].rel, "implements");
    assert_eq!(out.pointers[1].path, "rel1.md");
    assert_eq!(out.pointers[1].rel, "related");
    assert_eq!(out.pointers[2].path, "rel2.md");
    assert_eq!(out.pointers[2].rel, "related");
}

#[test]
fn pack_ignores_invalid_edge_types() {
    use cortex_judgement::PackEdge;

    let catalog = Catalog::embedded().unwrap();
    let client = ScriptClient::pack(vec![
        Ok(family_resp("session")),
        Ok(noul_dual(&[
            ("rel_c0_body", 0.90),
            ("rel_c0_ptr", 0.95),
            ("rel_c1_body", 0.10),
            ("rel_c1_ptr", 0.40),
            ("rel_c2_body", 0.05),
            ("rel_c2_ptr", 0.10),
        ])),
    ]);

    // Invalid edge types per spec 07 §5: cosine-neighbor, co-occurrence, same_folder
    let edges = vec![
        PackEdge::new("sessions.rs.md", "neighbor.md", "semantic_neighbor"),
        PackEdge::new("sessions.rs.md", "cooc.md", "co_occurrence"),
        PackEdge::new("sessions.rs.md", "same.md", "same_folder"),
    ];

    let out = cortex_judgement::pack_context_with_edges(
        &client,
        &catalog,
        "checkpoint verification",
        &[],
        cands(),
        &[],
        &edges,
    )
    .expect("pack");

    // Invalid edges must NEVER be added
    for p in &out.pointers {
        assert!(
            cortex_judgement::VALID_PACK_RELATIONS.contains(&p.rel.as_str()) || p.rel == "related",
            "rel must be valid or related, got {}",
            p.rel
        );
        assert_ne!(p.path, "neighbor.md");
        assert_ne!(p.path, "cooc.md");
        assert_ne!(p.path, "same.md");
    }
}

#[test]
fn pack_max_six_total_pointers() {
    use cortex_judgement::PackEdge;

    let catalog = Catalog::embedded().unwrap();
    let client = ScriptClient::pack(vec![
        Ok(family_resp("session")),
        Ok(noul_dual(&[
            ("rel_c0_body", 0.90),
            ("rel_c0_ptr", 0.95),
            ("rel_c1_body", 0.10),
            ("rel_c1_ptr", 0.80),
            ("rel_c2_body", 0.10),
            ("rel_c2_ptr", 0.70),
        ])),
    ]);

    // 7 edges connected to canonical
    let edges = vec![
        PackEdge::new("sessions.rs.md", "e1.md", "wikilink"),
        PackEdge::new("sessions.rs.md", "e2.md", "wikilink"),
        PackEdge::new("sessions.rs.md", "e3.md", "implements"),
        PackEdge::new("sessions.rs.md", "e4.md", "implements"),
        PackEdge::new("sessions.rs.md", "e5.md", "constrains"),
        PackEdge::new("sessions.rs.md", "e6.md", "constrains"),
        PackEdge::new("sessions.rs.md", "e7.md", "wikilink"),
    ];

    let out = cortex_judgement::pack_context_with_edges(
        &client,
        &catalog,
        "checkpoint",
        &[],
        cands(),
        &[],
        &edges,
    )
    .expect("pack");

    assert!(out.pointers.len() <= cortex_judgement::MAX_POINTERS);
    assert_eq!(out.pointers.len(), 6, "strictly capped at 6 pointers");
}

#[test]
fn pack_deduplication_and_canonical_exclusion() {
    use cortex_judgement::PackEdge;

    let catalog = Catalog::embedded().unwrap();
    // 2 files in work ⇒ up to 2 canonicals
    let client = ScriptClient::pack(vec![
        Ok(family_resp("session")),
        Ok(noul_dual(&[
            ("rel_c0_body", 0.90),
            ("rel_c0_ptr", 0.95),
            ("rel_c1_body", 0.85),
            ("rel_c1_ptr", 0.90),
            ("rel_c2_body", 0.10),
            ("rel_c2_ptr", 0.70),
        ])),
    ]);

    // Edge between the two canonicals, plus duplicate edge to c2
    let edges = vec![
        PackEdge::new("sessions.rs.md", "verification.md", "wikilink"),
        PackEdge::new("sessions.rs.md", "other.md", "implements"),
        PackEdge::new("sessions.rs.md", "other.md", "implements"),
    ];

    let out = cortex_judgement::pack_context_with_edges(
        &client,
        &catalog,
        "checkpoint",
        &["file1.rs".into(), "file2.rs".into()],
        cands(),
        &[],
        &edges,
    )
    .expect("pack");

    assert_eq!(out.canonical.len(), 2);
    // verification.md is canonical, so it must NOT appear in pointers
    assert!(
        !out.pointers.iter().any(|p| p.path == "verification.md"),
        "canonical must not appear in pointers"
    );
    // other.md should appear only once (dedup)
    let other_count = out.pointers.iter().filter(|p| p.path == "other.md").count();
    assert_eq!(other_count, 1, "other.md deduplicated");
}
