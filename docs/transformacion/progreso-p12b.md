# Progreso STREAM B — Obra 07 fase P12 (dual-stream)

> Stream B de P12 (territorios §7 del doc 09). Este archivo es el único
> registro de progreso de este stream: NO actualiza ESTADO-ACTUAL.md,
> HANDOFF.md ni el doc 09. Crates propios: `cortex-workspace`,
> `cortex-webgraph-server`, `cortex-enterprise`, `cortex-doctor`,
> `cortex-autopilot`, `cortex-pipeline`, reescritura de `cortex-cli`.
> PROHIBIDO editar `cortex-app`/`cortex-mcp`/`cortex-actions` (stream A).

## Decisiones de implementación

- **Emisor PyYAML propio (`cortex-workspace::pyyaml`)**: serde_yaml NO
  replica el formato de PyYAML (folding a 80 col, quoting de indicadores,
  sequences indentless, indent+2 alrededor de escalares vía
  `expect_scalar→increase_indent(flow=True)`). Se portó fielmente el
  subconjunto del emisor + resolver implícito de PyYAML 6.x instalado
  (fuente leída en `.venv`). Lo consumirá todo lo que emita YAML paridad
  (doctor/handoff/webgraph-workspace).
- **skills embebidos con `include_str!`** (mismo patrón que cortex-setup
  desde P8): cero dependencias nuevas; los recursos quedan byte-idénticos
  por construcción y el gate verifica hashes SHA-256 contra los recursos
  Python.
- **`resolve_safe` NO se duplica**: es territorio de A (cortex-app);
  cortex-workspace no lo contiene por diseño.
- **runtime_context hace shell-out a `git`** con timeout de 5s replicado
  por polling (`try_wait`), sin dependencias nuevas; fallbacks idénticos
  (`no-git-branch`, project_root como toplevel).
- **Cargo.lock compartido**: el diff actual contiene un hunk ajeno de A
  (`cortex-setup` en deps de cortex-app) ⇒ se commitea SIN lock hasta que
  A integre los suyos (regla §7.2.2).
- **[P12B-2] sum() de CPython ≥3.12 usa Neumaier**: `_cosine_similarity`
  del oráculo NO es suma ingenua — el builtin suma floats con compensación.
  Por eso los scores salen del kernel G4 (`cortex_core::webgraph`, Neumaier)
  y NO debe portearse nunca con `fold(0.0, +)` (divergencia 1 ULP verificada
  empíricamente contra Python 3.12.14).
- **[P12B-2] serde_json feature `float_roundtrip`**: sin ella, el re-parseo
  del caché de snapshots perdía 1 ULP en floats como 0.9526919036834995
  (parser default no correctamente redondeado) ⇒ respuestas cacheadas ≠
  frescas y gate S07/F01 rojo. Con la feature, round-trip exacto. Sin deps
  nuevas (feature de serde_json ya aprobado).
- **[P12B-2] federación resuelve memoria por config**: workspace.yaml sin
  clave `memory:` ⇒ resolver `resolve_episodic_persist_dir` (default
  `memory/`) igual que EpisodicSource Python; NO devolver vacío.

### Diseño aprobado P12B-3 — cortex-enterprise

- **Arquitectura**: crate profundo `cortex-enterprise` con módulos `models`,
  `config`, `governance`, `promotion_models`, `knowledge_promotion`,
  `promotion_doctype`, `maintenance`, `retrieval`, `reporting` y
  `review_knowledge`. Consume `cortex-workspace`, `cortex-setup` y
  `cortex-app` read-only. `review_knowledge` porta operaciones y presentación
  comprobable, pero el registro clap queda para P12B-8 (CLI nativo último).
- **Seam enterprise→doctor**: `reporting` define `DoctorBackend` y vistas
  neutrales `DoctorReportView`/`DoctorCheckView`. El backend por defecto falla
  explícitamente con `doctor backend unavailable until P12B-4`; el gate usa un
  snapshot del doctor Python y P12B-4 implementará `NativeDoctorBackend` desde
  `cortex-doctor`. Así las dependencias quedan `doctor → enterprise/webgraph`,
  nunca `enterprise → doctor`, y `build_memory_report` ejecuta doctor una vez.
- **Seams de testabilidad**: reloj inyectable para promoción/review/retención;
  `SearchBackend` inyectable para fuentes semánticas/episódicas. El adapter
  nativo usa BM25/export episódico sin embeddings y ONNX cuando recibe
  `model_dir`; ausencia de backend requerido falla explícitamente.
- **Paridad y gate**: `bench/parity/enterprise_golden_p12b.py` +
  `examples/enterprise_check.rs`, byte-a-byte con solo `{{ROOT}}`/`{{TS}}`.
  Cubre config/YAML, validaciones, gobernanza, promoción legacy y DocType,
  review queue/salida/path traversal, retención/archivo, retrieval/RRF y
  reporting local/all con snapshot real, más fallo del backend default.
- **Errores/dependencias**: `EnterpriseError` manual (sin dependencia nueva),
  mensajes contractuales preservados, omisión tolerante solo donde Python la
  tiene. YAML PyYAML-compatible mediante `cortex_setup::yaml::dump_with`,
  incluido `allow_unicode=false` para `org.yaml`.

## Cortex Enterprise P12B-3 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** portar `cortex/enterprise/` y la lógica de
`cortex/cli/review_knowledge.py` a `cortex-enterprise` con paridad byte-a-byte,
sin adelantar la reescritura clap de P12B-8 ni crear un ciclo con doctor.

**Architecture:** el crate concentra modelos, config, gobernanza, promoción,
retención, retrieval y reporting tras interfaces pequeñas. `SearchBackend` y
`DoctorBackend` son seams reales (adapter nativo + fake/snapshot); clocks
inyectables fijan timestamps. Doctor dependerá de enterprise en P12B-4.

**Tech Stack:** Rust 2021, serde/serde_json `float_roundtrip`, serde_yaml,
chrono, sha2, regex, `cortex-workspace`, `cortex-setup`, `cortex-app` y
`cortex-embed`; Python/PyYAML/Pydantic como oráculo.

**Spec:** sección “Diseño aprobado P12B-3 — cortex-enterprise” de este archivo.

### Global Constraints

- Territorio de escritura: nuevo `rust/crates/cortex-enterprise/`, hunk propio
  append-only de `rust/Cargo.toml`, gate `bench/parity/*p12b*` y este archivo.
- `cortex-app`, `cortex-mcp`, `cortex-actions` y artefactos P12A son read-only.
- No duplicar `DocValidator`; consumirlo solo cuando el commit atómico de A lo
  haga parte de HEAD. Si sigue únicamente en WIP de A, avanzar módulos
  independientes y detener el commit final.
- Un gate por commit P12B: los checkpoints internos no se commitean. El commit
  feature ocurre solo cuando el gate completo está verde.
- Antes de cargo/pytest pesado: `free -m` con al menos 4000 MB disponibles,
  lock `.cortex/heavy.lock`, timeout 1200 s y variables de threads pactadas.
- Suite Python completa exactamente una vez, inmediatamente antes del commit
  feature. Durante iteración usar tests Rust del crate y Python focalizados.
- Staging quirúrgico; `Cargo.lock` entra solo si todo su diff es atribuible a B.

---

### Task 1: Crate, modelos, config y gobernanza

**Files:**
- Create: `rust/crates/cortex-enterprise/Cargo.toml`
- Create: `rust/crates/cortex-enterprise/src/{lib,error,clock,models,config,governance}.rs`
- Create: `rust/crates/cortex-enterprise/tests/models_config_governance.rs`
- Modify: `rust/Cargo.toml` (solo member `crates/cortex-enterprise`)

**Interfaces:**
- Produces: `EnterpriseOrgConfig::validate`, resolvers de paths,
  `build/load/write/render/describe_enterprise_*`, helpers de governance,
  `Clock`, `SystemClock`, `FixedClock`, `EnterpriseError`.

- [ ] **Step 1: escribir tests rojos de defaults, invariantes y bytes YAML**

```rust
#[test]
fn small_company_and_unicode_yaml_match_oracle() {
    let cfg = build_enterprise_org_config("Ácme Platform", OrgProfile::SmallCompany, true, false).unwrap();
    assert_eq!(cfg.organization.slug, "acme-platform");
    assert!(render_enterprise_config_yaml(&cfg).starts_with(
        "# Cortex enterprise memory topology\n# This file governs organization-level memory, promotion and governance behavior.\n# Local runtime mechanics still live in config.yaml.\n\n"
    ));
}

#[test]
fn promotion_requires_semantic_target() {
    let mut cfg = EnterpriseOrgConfig::default();
    cfg.memory.enterprise_semantic_enabled = false;
    assert_eq!(cfg.validate().unwrap_err().to_string(),
        "promotion.enabled requires memory.enterprise_semantic_enabled=true so promoted knowledge has a target");
}
```

- [ ] **Step 2: ejecutar el test y comprobar RED**

Run: `cd rust && cargo test -p cortex-enterprise --test models_config_governance`
Expected: FAIL porque crate/tipos aún no existen.

- [ ] **Step 3: implementar la interfaz mínima completa**

```rust
pub trait Clock: Send + Sync { fn now(&self) -> chrono::DateTime<chrono::Utc>; }
pub struct FixedClock(chrono::DateTime<chrono::Utc>);
impl FixedClock { pub fn parse(value: &str) -> Result<Self, EnterpriseError>; }
pub enum EnterpriseError {
    Validation(String), Permission(String), NotFound(String),
    BackendUnavailable(&'static str), Backend(String), Io(String),
}
pub fn build_enterprise_org_config(
    project_name: &str, profile: OrgProfile,
    github_actions_enabled: bool, branch_isolation_enabled: bool,
) -> Result<EnterpriseOrgConfig, EnterpriseError>;
impl EnterpriseOrgConfig {
    pub fn validate(&self) -> Result<(), EnterpriseError>;
    pub fn resolve_enterprise_vault_path(&self, project_root: &Path, workspace_root: Option<&Path>) -> Option<PathBuf>;
    pub fn resolve_enterprise_memory_path(&self, project_root: &Path, workspace_root: Option<&Path>) -> Option<PathBuf>;
}
pub fn render_enterprise_config_yaml(config: &EnterpriseOrgConfig) -> String;
pub fn load_enterprise_config(project_root: &Path, required: bool,
    path: Option<&Path>, layout: Option<&cortex_workspace::WorkspaceLayout>)
    -> Result<Option<EnterpriseOrgConfig>, EnterpriseError>;
pub fn write_enterprise_config(project_root: &Path, config: &EnterpriseOrgConfig,
    layout: Option<&cortex_workspace::WorkspaceLayout>) -> Result<PathBuf, EnterpriseError>;
```

Usar `#[serde(default)]`, enums case-sensitive y validación manual para `gt=0`,
`ge=0`, team-id y reglas cruzadas. Convertir el valor serde a
`cortex_setup::yaml::Yaml` preservando orden y emitir con
`dump_with(node, false)`. Governance preserva primer match, orden y mensajes
`actor 'x' (team=None) cannot ...`.

- [ ] **Step 4: ejecutar GREEN y clippy focalizado**

Run: `cd rust && cargo test -p cortex-enterprise --test models_config_governance && cargo clippy -p cortex-enterprise --all-targets -- -D warnings`
Expected: PASS.

- [ ] **Step 5: checkpoint sin commit**

Run: `git diff --check && git status --short`
Expected: solo archivos B previstos; nada staged.

### Task 2: Promoción legacy append-only

**Files:**
- Create: `rust/crates/cortex-enterprise/src/frontmatter.rs`
- Create: `rust/crates/cortex-enterprise/src/promotion_models.rs`
- Create: `rust/crates/cortex-enterprise/src/knowledge_promotion.rs`
- Create: `rust/crates/cortex-enterprise/tests/knowledge_promotion.rs`
- Modify: `rust/crates/cortex-enterprise/src/lib.rs`

**Interfaces:**
- Consumes: config/layout/clock de Task 1 y
  `cortex_app::doc_validator::DocValidator` read-only.
- Produces: `PromotionRepository`, `PromotionRulesEngine`,
  `KnowledgePromotionService`, `PromotionCandidate`, `PromotionRecord`.

- [ ] **Step 1: confirmar que DocValidator ya pertenece a HEAD**

Run: `git log -1 --oneline -- rust/crates/cortex-app/src/doc_validator.rs && grep -n 'pub mod doc_validator' rust/crates/cortex-app/src/lib.rs`
Expected: commit de A visible y módulo público. Si no, no duplicar ni stagear WIP A.

- [ ] **Step 2: escribir tests rojos de discovery/review/apply**

```rust
fn fixture_service(require_review: bool) -> (tempfile::TempDir, KnowledgePromotionService) {
    let tmp = tempfile::tempdir().unwrap();
    let local = tmp.path().join("vault");
    let enterprise = tmp.path().join("vault-enterprise");
    std::fs::create_dir_all(local.join("specs")).unwrap();
    std::fs::create_dir_all(&enterprise).unwrap();
    std::fs::write(local.join("specs/auth.md"),
        "---\ntitle: Auth\ntags: [spec]\n---\n\nInitial spec body\n").unwrap();
    let mut config = build_enterprise_org_config(
        "Acme Org", OrgProfile::SmallCompany, true, false).unwrap();
    config.promotion.require_review = require_review;
    config.promotion.allowed_doc_types = vec![PromotableDocType::Spec];
    let paths = PromotionPaths { project_root: tmp.path().to_path_buf(),
        local_vault: local, enterprise_vault: enterprise.clone(),
        records_path: enterprise.join("promotion/records.jsonl") };
    let clock = std::sync::Arc::new(
        FixedClock::parse("2026-08-25T12:00:00+00:00").unwrap());
    let service = KnowledgePromotionService::new(paths, config, clock);
    (tmp, service)
}
#[test]
fn reviewed_candidate_promotes_once_and_records_jsonl() {
    let (_tmp, svc) = fixture_service(true);
    let candidate = svc.discover_candidates().unwrap().remove(0);
    assert!(svc.plan_promotion().unwrap().is_empty());
    svc.review(&candidate.origin_id, true, "tester", Some("ok")).unwrap();
    let written = svc.apply_promotion(&svc.plan_promotion().unwrap(), "tester").unwrap();
    assert_eq!(written.len(), 1);
    assert!(svc.discover_candidates().unwrap().is_empty());
}
```

Añadir casos: session excluida por default, `.cortex/` excluido, fingerprint
normaliza CRLF/body, JSONL inválido se omite, cambio de contenido exige nueva
review y error de validación impide review.

- [ ] **Step 3: ejecutar RED**

Run: `cd rust && cargo test -p cortex-enterprise --test knowledge_promotion`
Expected: FAIL por símbolos no definidos.

- [ ] **Step 4: implementar parser/frontmatter, records y módulo profundo**

```rust
impl PromotionRepository {
    pub fn iter_records(&self) -> Result<Vec<PromotionRecord>, EnterpriseError>;
    pub fn load_latest_by_origin_id(&self) -> Result<Vec<(String, PromotionRecord)>, EnterpriseError>;
    pub fn append(&self, record: &PromotionRecord) -> Result<(), EnterpriseError>;
}
pub struct KnowledgePromotionService {
    pub paths: PromotionPaths,
    pub org_slug: String,
    pub require_review: bool,
    config: EnterpriseOrgConfig,
    clock: std::sync::Arc<dyn Clock>,
}
impl KnowledgePromotionService {
    pub fn new(paths: PromotionPaths, config: EnterpriseOrgConfig,
        clock: std::sync::Arc<dyn Clock>) -> Self;
    pub fn with_clock(self, clock: std::sync::Arc<dyn Clock>) -> Self;
    pub fn discover_candidates(&self) -> Result<Vec<PromotionCandidate>, EnterpriseError>;
    pub fn review(&self, selector: &str, approve: bool, actor: &str, reason: Option<&str>) -> Result<PromotionRecord, EnterpriseError>;
    pub fn plan_promotion(&self) -> Result<Vec<PromotionCandidate>, EnterpriseError>;
    pub fn apply_promotion(&self, candidates: &[PromotionCandidate], actor: &str) -> Result<Vec<PromotionRecord>, EnterpriseError>;
}
```

Preservar orden sorted de Markdown, orden de campos Pydantic en JSON, newline
final y append-only. Formatear clocks legacy con segundos y `+00:00`.

- [ ] **Step 5: ejecutar GREEN**

Run: `cd rust && cargo test -p cortex-enterprise --test knowledge_promotion`
Expected: PASS.

### Task 3: Promoción DocType, review queue y mantenimiento

**Files:**
- Create: `rust/crates/cortex-enterprise/src/promotion_doctype.rs`
- Create: `rust/crates/cortex-enterprise/src/review_knowledge.rs`
- Create: `rust/crates/cortex-enterprise/src/maintenance.rs`
- Create: `rust/crates/cortex-enterprise/tests/doctype_review_maintenance.rs`
- Modify: `rust/crates/cortex-enterprise/src/lib.rs`

**Interfaces:**
- Consumes: governance/config/frontmatter/clock y rutas de `cortex-setup`.
- Produces: `promote_note_doctype_aware`, `mark_as_accepted`,
  `mark_as_rejected`, `list_pending_drafts`, `scan_retention_violations`,
  `archive_violations`, renderers command-neutral de review.

- [ ] **Step 1: escribir tests rojos de modos, seguridad y retención**

```rust
#[test]
fn session_summarizes_and_runbook_becomes_draft() {
    let tmp = tempfile::tempdir().unwrap();
    let source = tmp.path().join("session.md");
    std::fs::write(&source,
        "---\ndoc_type: session\ntitle: Sprint\nstatus: active\n---\n\n## Key Decisions\n\nKeep Rust\n\n## Noise\n\nDrop me\n").unwrap();
    let clock = FixedClock::parse("2026-08-25T12:00:00+00:00").unwrap();
    let result = promote_note_doctype_aware(PromoteArgs {
        source_path: &source, enterprise_vault_root: &tmp.path().join("enterprise"),
        org: &EnterpriseOrgConfig::default(), project_id: "api", actor: "tester",
        reason: None, dry_run: false, clock: &clock,
    }).unwrap();
    let bytes = std::fs::read_to_string(result.target_path).unwrap();
    assert!(result.summarized && bytes.contains("## Key Decisions\n\nKeep Rust"));
    assert!(!bytes.contains("Drop me"));
}
#[test]
fn approve_rejects_escape_from_enterprise_vault() {
    let tmp = tempfile::tempdir().unwrap();
    std::fs::write(tmp.path().join("config.yaml"), "semantic:\n  vault_path: vault\n").unwrap();
    let layout = cortex_workspace::WorkspaceLayout::discover(tmp.path());
    let clock = FixedClock::parse("2026-08-25T12:00:00+00:00").unwrap();
    assert_eq!(approve_output(&layout, "../outside.md", "tester", "", &clock).unwrap_err().to_string(),
        "Path escapes enterprise vault: ../outside.md");
}
#[test]
fn retention_boundary_is_inclusive() {
    let tmp = tempfile::tempdir().unwrap();
    std::fs::write(tmp.path().join("old.md"),
        "---\ndoc_type: hu\ncreated_at: '2026-08-24T00:00:00+00:00'\nretention_days: 1\n---\nBody\n").unwrap();
    let now = chrono::DateTime::parse_from_rfc3339("2026-08-25T00:00:00+00:00").unwrap().to_utc();
    let hits = scan_retention_violations(tmp.path(), None, None, now);
    assert_eq!(hits.len(), 1);
    assert_eq!(hits[0].days_overdue, 0);
}
```

Cubrir ADR as-is, incident low bloqueado, handoff no promovible, actor sin
permiso, dry-run sin writes, audit append, reject move/delete, rejected folder
excluido, filtro DocType, archive dry-run/paths y strings CLI exactos.

- [ ] **Step 2: ejecutar RED**

Run: `cd rust && cargo test -p cortex-enterprise --test doctype_review_maintenance`
Expected: FAIL por módulos ausentes.

- [ ] **Step 3: implementar interfaces y política local de promoción**

```rust
pub struct PromoteArgs<'a> {
    pub source_path: &'a Path, pub enterprise_vault_root: &'a Path,
    pub org: &'a EnterpriseOrgConfig, pub project_id: &'a str,
    pub actor: &'a str, pub reason: Option<&'a str>, pub dry_run: bool,
    pub clock: &'a dyn Clock,
}
pub fn promote_note_doctype_aware(args: PromoteArgs<'_>) -> Result<PromotionResult, EnterpriseError>;
pub fn mark_as_accepted(path: &Path, reviewer: &str, reason: &str,
    clock: &dyn Clock) -> Result<(), EnterpriseError>;
pub fn mark_as_rejected(path: &Path, reviewer: &str, reason: &str,
    delete: bool, clock: &dyn Clock) -> Result<Option<PathBuf>, EnterpriseError>;
pub fn list_pending_drafts(root: &Path, doc_types: Option<&[String]>) -> Vec<PendingDraft>;
pub fn approve_output(layout: &cortex_workspace::WorkspaceLayout, path: &str,
    reviewer: &str, reason: &str, clock: &dyn Clock) -> Result<String, EnterpriseError>;
pub fn reject_output(layout: &cortex_workspace::WorkspaceLayout, path: &str,
    reviewer: &str, reason: &str, delete: bool, clock: &dyn Clock)
    -> Result<String, EnterpriseError>;
pub fn scan_retention_violations(root: &Path, org: Option<&EnterpriseOrgConfig>, defaults: Option<&RetentionPolicy>, now: DateTime<Utc>) -> Vec<RetentionViolation>;
```

Usar `cortex_setup::routing::resolve_route` para promotable/subfolder y match
local exhaustivo para `summarize` (session), `review-required` (runbook) y
`requires_review` (postmortem/runbook). Resolver/canonicalizar path antes de
mutar; no registrar clap en `cortex-cli`.

- [ ] **Step 4: ejecutar GREEN**

Run: `cd rust && cargo test -p cortex-enterprise --test doctype_review_maintenance`
Expected: PASS.

### Task 4: Fuentes y retrieval multi-scope

**Files:**
- Create: `rust/crates/cortex-enterprise/src/sources.rs`
- Create: `rust/crates/cortex-enterprise/src/retrieval.rs`
- Create: `rust/crates/cortex-enterprise/tests/retrieval.rs`
- Modify: `rust/crates/cortex-enterprise/src/lib.rs`

**Interfaces:**
- Consumes: `SemanticIndex`, `NativeEpisodicStore`, `OnnxEmbedder` read-only.
- Produces: source/hit/result owned, `SearchBackend`, `NativeSearchBackend`,
  `EnterpriseRetrievalService::search`.

- [ ] **Step 1: escribir tests rojos con backend fake**

```rust
struct DuplicateBackend;
impl SearchBackend for DuplicateBackend {
    fn search_vault(&mut self, source: &VaultSource, _: &str, _: usize, _: bool)
        -> Result<Vec<SemanticHit>, EnterpriseError> {
        Ok(vec![SemanticHit::new("runbook/auth.md", "Auth", source.scope.as_str(), 0.9)])
    }
    fn search_episodic(&mut self, _: &EpisodicSource, _: &str, _: usize, _: bool)
        -> Result<Vec<EpisodicHit>, EnterpriseError> { Ok(vec![]) }
}
#[test]
fn all_scope_deduplicates_same_semantic_path_preferring_enterprise() {
    let config = build_enterprise_org_config(
        "Acme", OrgProfile::MultiProjectTeam, true, false).unwrap();
    let mut service = EnterpriseRetrievalService::new(config, "acme-project".into(),
        std::env::current_dir().unwrap(), std::env::current_dir().unwrap(),
        "vault".into(), ".memory/chroma".into(), "cortex_episodic".into(),
        None, DuplicateBackend);
    let result = service.search("auth", RetrievalScope::All, 5, true, None).unwrap();
    assert_eq!(result.unified_hits.iter().filter(|h| h.source == "semantic").count(), 1);
    assert_eq!(result.unified_hits[0].metadata["scope"], "enterprise");
}
```

Cubrir local/all, filtro project_id, enterprise sin fuentes (error exacto),
source annotations, keys semantic/episodic, pesos 1.0/1.2 y desempate estable.

- [ ] **Step 2: ejecutar RED**

Run: `cd rust && cargo test -p cortex-enterprise --test retrieval`
Expected: FAIL por tipos ausentes.

- [ ] **Step 3: implementar seam y RRF**

```rust
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum SourceScope { Local, Enterprise }
pub struct VaultSource { pub path: String, pub scope: SourceScope, pub project_id: String }
pub struct EpisodicSource {
    pub persist_dir: String, pub scope: SourceScope,
    pub project_id: String, pub collection_name: String,
}
pub struct SemanticHit {
    pub path: String, pub title: String, pub content: String, pub score: f64,
    pub origin_scope: SourceScope, pub origin_project_id: String,
    pub origin_vault: String, pub origin_persist_dir: String,
}
pub struct EpisodicHit {
    pub entry: cortex_app::episodic::MemoryEntry, pub score: f64,
    pub origin_scope: SourceScope, pub origin_project_id: String,
    pub origin_vault: String, pub origin_persist_dir: String,
}
pub struct UnifiedHit {
    pub source: String, pub score: f64,
    pub entry: Option<cortex_app::episodic::MemoryEntry>,
    pub doc: Option<SemanticHit>, pub metadata: serde_json::Map<String, serde_json::Value>,
}
pub struct RetrievalResult {
    pub query: String, pub episodic_hits: Vec<EpisodicHit>,
    pub semantic_hits: Vec<SemanticHit>, pub unified_hits: Vec<UnifiedHit>,
    pub source_breakdown: std::collections::BTreeMap<String, usize>,
}
impl SourceScope { pub fn as_str(self) -> &'static str; }
impl SemanticHit {
    pub fn new(path: impl Into<String>, title: impl Into<String>,
        content: impl Into<String>, score: f64) -> Self;
}
pub trait SearchBackend: Send {
    fn search_vault(&mut self, source: &VaultSource, query: &str, top_k: usize, use_embeddings: bool) -> Result<Vec<SemanticHit>, EnterpriseError>;
    fn search_episodic(&mut self, source: &EpisodicSource, query: &str, top_k: usize, use_embeddings: bool) -> Result<Vec<EpisodicHit>, EnterpriseError>;
}
pub struct EnterpriseRetrievalService<B: SearchBackend> {
    config: EnterpriseOrgConfig,
    local_project_id: String,
    project_root: PathBuf,
    workspace_root: PathBuf,
    local_vault_path: String,
    local_episodic_dir: String,
    local_collection_name: String,
    source_config: RetrievalSourceConfig,
    backend: B,
}
impl<B: SearchBackend> EnterpriseRetrievalService<B> {
    pub fn new(config: EnterpriseOrgConfig, local_project_id: String,
        project_root: PathBuf, workspace_root: PathBuf,
        local_vault_path: String, local_episodic_dir: String,
        local_collection_name: String,
        source_config: Option<RetrievalSourceConfig>, backend: B) -> Self;
    pub fn search(&mut self, query: &str, scope: RetrievalScope, top_k: usize,
        use_embeddings: bool, project_id: Option<&str>) -> Result<RetrievalResult, EnterpriseError>;
}
```

El adapter nativo carga `episodic_export.jsonl`; keyword/BM25 funcionan sin
modelo. `use_embeddings=true` exige backend ONNX abierto con `model_dir` y
falla explícitamente si no está configurado. RRF usa k=60, rank desde 1,
orden de inserción estable y preferencia enterprise solo para el objeto
unificado, no para el score acumulado.

- [ ] **Step 4: ejecutar GREEN y smoke <0.5 s con fake**

Run: `cd rust && cargo test -p cortex-enterprise --test retrieval`
Expected: PASS, incluido smoke determinista.

### Task 5: Reporting con DoctorBackend

**Files:**
- Create: `rust/crates/cortex-enterprise/src/reporting.rs`
- Create: `rust/crates/cortex-enterprise/tests/reporting.rs`
- Modify: `rust/crates/cortex-enterprise/src/lib.rs`

**Interfaces:**
- Consumes: config/promotion y `DoctorBackend` inyectado.
- Produces: `DoctorCheckView`, `DoctorReportView`, `DoctorBackend`,
  `UnavailableDoctorBackend`, `EnterpriseReportingService`.

- [ ] **Step 1: escribir tests rojos del seam**

```rust
struct CountingBackend(std::sync::Arc<std::sync::atomic::AtomicUsize>);
impl DoctorBackend for CountingBackend {
    fn run(&self, root: &Path, _: DoctorScope) -> Result<DoctorReportView, EnterpriseError> {
        self.0.fetch_add(1, std::sync::atomic::Ordering::SeqCst);
        Ok(DoctorReportView { project_root: root.to_path_buf(), checks: vec![],
            has_failures: false, has_warnings: false })
    }
}
#[test]
fn all_scope_calls_doctor_once_and_reports_both_vaults() {
    let tmp = tempfile::tempdir().unwrap();
    std::fs::write(tmp.path().join("config.yaml"), "semantic:\n  vault_path: vault\n").unwrap();
    std::fs::create_dir_all(tmp.path().join("vault/specs")).unwrap();
    std::fs::write(tmp.path().join("vault/specs/spec.md"), "# Spec\n").unwrap();
    let cfg = build_enterprise_org_config(
        "Acme", OrgProfile::SmallCompany, true, false).unwrap();
    write_enterprise_config(tmp.path(), &cfg, None).unwrap();
    std::fs::create_dir_all(tmp.path().join("vault-enterprise")).unwrap();
    let calls = std::sync::Arc::new(std::sync::atomic::AtomicUsize::new(0));
    let service = EnterpriseReportingService::from_project_root(tmp.path(), None).unwrap()
        .with_doctor_backend(CountingBackend(calls.clone()));
    let report = service.build_memory_report(ReportingScope::All).unwrap();
    assert_eq!(calls.load(std::sync::atomic::Ordering::SeqCst), 1);
    assert_eq!(report.sources.iter().map(|s| s.scope.clone()).collect::<Vec<_>>(),
        vec![ReportingScope::Local, ReportingScope::Enterprise]);
}
#[test]
fn default_backend_fails_explicitly() {
    let tmp = tempfile::tempdir().unwrap();
    std::fs::write(tmp.path().join("config.yaml"), "semantic:\n  vault_path: vault\n").unwrap();
    std::fs::create_dir_all(tmp.path().join("vault")).unwrap();
    let err = EnterpriseReportingService::from_project_root(tmp.path(), None)
        .unwrap().build_memory_report(ReportingScope::Local).unwrap_err();
    assert_eq!(err.to_string(), "doctor backend unavailable until P12B-4");
}
```

Cubrir extracción de conteos desde detail, flags failures/warnings, promotion
disabled/missing y sort de latest events.

- [ ] **Step 2: ejecutar RED**

Run: `cd rust && cargo test -p cortex-enterprise --test reporting`
Expected: FAIL por módulo ausente.

- [ ] **Step 3: implementar interfaz aprobada**

```rust
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum DoctorScope { Project, Enterprise }
pub struct DoctorCheckView {
    pub name: String, pub ok: bool, pub severity: String, pub detail: String,
}
pub struct DoctorReportView {
    pub project_root: PathBuf, pub checks: Vec<DoctorCheckView>,
    pub has_failures: bool, pub has_warnings: bool,
}
pub trait DoctorBackend: Send + Sync {
    fn run(&self, project_root: &Path, scope: DoctorScope) -> Result<DoctorReportView, EnterpriseError>;
}
pub struct EnterpriseReportingService {
    project_root: PathBuf,
    layout: cortex_workspace::WorkspaceLayout,
    doctor: Box<dyn DoctorBackend>,
}
impl EnterpriseReportingService {
    pub fn from_project_root(project_root: &Path,
        layout: Option<cortex_workspace::WorkspaceLayout>) -> Result<Self, EnterpriseError>;
    pub fn with_doctor_backend(self, backend: impl DoctorBackend + 'static) -> Self;
    pub fn build_memory_report(&self, scope: ReportingScope) -> Result<MemoryReportPayload, EnterpriseError>;
}
```

Ejecutar doctor una vez; mapear local→project y enterprise/all→enterprise.

- [ ] **Step 4: ejecutar GREEN**

Run: `cd rust && cargo test -p cortex-enterprise --test reporting`
Expected: PASS.

### Task 6: Gate byte-parity P12B-3

**Files:**
- Create: `bench/parity/enterprise_golden_p12b.py`
- Create: `rust/crates/cortex-enterprise/examples/enterprise_check.rs`

**Interfaces:**
- Consumes: todas las interfaces Tasks 1–5.
- Produces: `golden_enterprise.txt` y checker Rust byte-a-byte.

- [ ] **Step 1: escribir el oráculo Python determinista**

Emitir JSONL/segmentos ordenados para: presets + unicode YAML + invalid configs;
governance; promotion legacy/DocType/review; retention; retrieval con hits fake;
reporting local/all usando `run_doctor` Python real convertido a snapshot.
Normalizar solo root y timestamps pactados.

- [ ] **Step 2: construir y verificar el golden Python**

Run: `.venv/bin/python bench/parity/enterprise_golden_p12b.py build --out bench/parity/.p12b-enterprise && .venv/bin/python bench/parity/enterprise_golden_p12b.py verify --out bench/parity/.p12b-enterprise`
Expected: `[PASS] golden_enterprise.txt`.

- [ ] **Step 3: escribir checker Rust que recorra los mismos escenarios**

```rust
let expected = fs::read_to_string(golden_dir.join("golden_enterprise.txt"))?;
let actual = normalize(run_all_scenarios()?);
if actual != expected { print_first_diff(&expected, &actual); std::process::exit(1); }
println!("[PASS] enterprise_check byte-parity vs golden_enterprise.txt");
println!("✅ PARIDAD P12B-3");
```

El reporting checker carga el snapshot real del golden mediante un
`StaticDoctorBackend`; incluir escenario separado del backend default.

- [ ] **Step 4: ejecutar checker y corregir únicamente divergencias demostradas**

Run: `cd rust && cargo run -p cortex-enterprise --example enterprise_check -- ../../bench/parity/.p12b-enterprise`
Expected: dos líneas PASS indicadas arriba.

### Task 7: Verificación, commit atómico y progreso

**Files:**
- Modify: `docs/transformacion/progreso-p12b.md` después del commit feature
- Modify conditionally: `rust/Cargo.lock` únicamente cuando su diff completo sea atribuible a B

- [ ] **Step 1: verificar recursos y ejecutar controles Rust bajo lock**

Run after `free -m` reports available ≥4000 MB:

```bash
flock .cortex/heavy.lock -c 'cd rust && timeout 1200 env OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 NUMEXPR_NUM_THREADS=2 CARGO_BUILD_JOBS=6 cargo fmt --all --check && timeout 1200 env OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 NUMEXPR_NUM_THREADS=2 CARGO_BUILD_JOBS=6 cargo clippy -p cortex-enterprise --all-targets -- -D warnings && timeout 1200 env OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 NUMEXPR_NUM_THREADS=2 CARGO_BUILD_JOBS=6 cargo test -p cortex-enterprise'
```

Expected: fmt/clippy/tests PASS.

- [ ] **Step 2: ejecutar gates Python/Rust finales**

Run: los dos comandos de Task 6, sin regenerar expectativas desde Rust.
Expected: verify Python PASS y `✅ PARIDAD P12B-3`.

- [ ] **Step 3: ejecutar suite Python completa una única vez**

Run bajo lock/timeout/thread limits:

```bash
flock .cortex/heavy.lock -c 'timeout 1200 env OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 NUMEXPR_NUM_THREADS=2 .venv/bin/python -m pytest -q'
```

Expected: rc=0; registrar passed/skipped.

- [ ] **Step 4: revisar diff y staging quirúrgico**

Run: `git diff --check`, `git status --short`, `git diff -- rust/Cargo.toml rust/Cargo.lock`, `git diff --name-only`.
Expected: ningún archivo A staged; lock solo si atribuible íntegramente a B.

- [ ] **Step 5: commit feature atómico**

```bash
git add -- rust/Cargo.toml rust/crates/cortex-enterprise bench/parity/enterprise_golden_p12b.py
git add -- rust/Cargo.lock  # solo si Step 4 demuestra diff 100% B
git commit -m "feat(obra07 P12B-3): crate cortex-enterprise y review knowledge nativos"
```

- [ ] **Step 6: actualizar progreso inmediatamente y commit docs**

Cambiar la fila P12B-3 a ✅, registrar gate, tests, suite Python y hash feature;
luego:

```bash
git add -- docs/transformacion/progreso-p12b.md
git commit -m "docs(obra07 P12B): progreso P12B-3 completada — enterprise y review knowledge"
```

- **[P12B-3] Seam enterprise→doctor con inversión de dependencia**: reporting
  define `DoctorBackend` + vistas neutrales; default falla con
  "doctor backend unavailable until P12B-4"; el gate usa snapshot estático del
  doctor Python real. En P12B-4 cortex-doctor implementa `NativeDoctorBackend`
  ⇒ dependencia queda doctor→enterprise sin ciclo.
- **[P12B-3] promotion_mode/requires_review espejados localmente**: RouteSpec
  nativo (cortex-setup, crate ajeno) aún no trae esos campos; la tabla
  session=summarize / runbook=review-required / postmortem+runbook
  requires_review se matchea 1:1 desde routing.py dentro de promotion_doctype.
- **[P12B-3] Path::file_name() devuelve None con ".." final**: el resolve tipo
  Python para validar escape del vault en review-knowledge debía recorrer
  Components explícitos (el loop por parent()/file_name() cortaba sin
  normalizar y dejaba pasar escapes léxicos).
- **[P12B-3] json.dumps(indent=1/sort_keys) replicado**: writer PyVal propio
  en el checker para orden de inserción Python (breakdown local→enterprise,
  rows governance); sort_keys=True solo en el payload curado de reporting.

### Diseño aprobado P12B-4 — cortex-doctor

- **Crate** `rust/crates/cortex-doctor` (deps: workspace/app/enterprise/config;
  dirección doctor→enterprise, sin ciclo). Tipos `DoctorCheck{name,ok,severity,detail}`
  y `DoctorReport{project_root,checks,has_failures,has_warnings}`.
- **Nativos completos**: project_root, layout_mode, config_yaml,
  config_validation (`cortex-config`), vault_dir, episodic_store
  (`resolve_episodic_persist_dir` + GITHUB_ACTIONS), cortex_workspace,
  agent_guidelines, workspace_yaml/layout_version, git_repository/branch,
  gitignore:* (git_policy), vault_markdown+validaciones (DocValidator),
  pm_workspace_layout_v2, pm_documenter_default_mode, pm_git_available y TODO
  el bloque enterprise (scope enterprise/all).
- **Stubs contractuales** (patrón P6/P9; backend Python sin porteño):
  webgraph_dependencies, sessions_* profundos, autopilot_policy/typo (real en
  P12B-5), session_hooks_*, pm_documenter_module/interactive,
  pm_verification_runner, pm_mcp_tools_registered. Texto congelado:
  severity contractual + detail "backend no nativo aún (<módulo>)"; el
  oráculo normaliza esos checks al mismo texto antes de comparar.
- **Seam**: `NativeDoctorBackend` implementa
  `cortex_enterprise::reporting::DoctorBackend` (local→Project,
  enterprise/all→Enterprise).
- **Gate**: `bench/parity/doctor_golden_p12b.py` (fixtures legacy+new-layout;
  scopes project/enterprise/all; oráculo = doctor Python real + tabla de
  normalización de stubs) + `examples/doctor_check.rs` byte-parity con solo
  {{ROOT}}/{{TS}}. Fuera de alcance: clap `cortex doctor` (P12B-8).

- **[P12B-4] NativeDoctorBackend cierra el seam de P12B-3**: cortex-doctor
  implementa `cortex_enterprise::reporting::DoctorBackend` mapeando
  local→Project y enterprise/all→Enterprise; el default "unavailable" de
  reporting queda reemplazable en producción sin tocar enterprise.
- **[P12B-4] STUB_TABLE como contrato**: los checks con backend Python sin
  porteño (webgraph deps, sessions profundos, autopilot policy, hooks,
  documenter module/interactive, verification, mcp tools) emiten
  `(false, severity, "backend no nativo aún (<módulo>)")`; el oráculo
  normaliza por nombre antes de comparar. autopilot_policy pasa a real en
  P12B-5 actualizando ambos lados.
- **[P12B-4] json.dumps default separators**: el checker serializa checks a
  mano (`", "` / `": "` + ensure_ascii=True) porque serde_json::to_string es
  compacto y mantiene unicode crudo.

### Diseño aprobado P12B-5 — cortex-autopilot (capa de decisión)

- **Alcance** (decisión del dueño): capa de decisión pura. Crate
  `rust/crates/cortex-autopilot` con: config (`AutopilotConfig` +
  `load_autopilot_config`, error "Failed to parse autopilot config"),
  errors, models (DetectionRequest/Result), **modelos de sesión mínimos**
  (SessionStatus/CheckpointSource/Checkpoint/SessionRecord — solo los
  campos que policies/lifecycle consumen), detectors (base resolve_detectors
  + 7 default + ambiguous, reglas §7.1.2), policies (AutopilotPolicy
  from_config con fallback seguro a ASSIST, validaciones de thresholds,
  PolicyEnforcer hooks on_session_open/on_checkpoint/on_pre_close con reloj
  inyectable), lifecycle (tipos start/preflight/finish/status).
- **service/cli/mcp_tools**: fallo explícito documentado hasta que exista el
  motor de sesiones nativo (SessionService/Storage/AgentMemory no porteños;
  handlers mcp de sessions son territorio A). CLI clap en P12B-8.
- **doctor.py de autopilot**: parcial nativo (config/sessions_dir writability);
  last_finish/adapters/hooks → stub hasta motor de sesiones.
- **Llena el stub de P12B-4**: cortex-doctor pasa a cargar
  `load_autopilot_config` + `AutopilotPolicy::from_config` reales
  (info `mode=…, budget_profile=…`; warn "could not load/build"; typo check
  `autopilot_mode_typo`) y la STUB_TABLE del oráculo pierde esa entrada.
- **Gate**: `bench/parity/autopilot_golden_p12b.py` (detección con requests
  canónicos, enforcement con clock fijo, config inválida/válida,
  autopilot_policy real del doctor) + `examples/autopilot_check.rs`
  byte-parity con solo {{ROOT}}/{{TS}}.

- **[P12B-5] Alcance decisión del dueño**: autopilot se portea como capa
  de decisión pura; service/cli/mcp_tools requieren el motor de sesiones
  (SessionService/Storage/AgentMemory, no porteño y territorio ambiguo con
  A) ⇒ fallo explícito documentado. El stub autopilot_policy de P12B-4 pasa
  a real y la STUB_TABLE del oráculo pierde esa entrada.
- **[P12B-5] session-models mínimos**: SessionRecord/Checkpoint porteñados
  como subconjunto fiel de los campos que policies/lifecycle consumen;
  invariante lifecycle defensivo incluido para el doctor futuro.

### Diseño P12B-6 — cortex-pipeline

- **Hallazgo**: runners/github.py es un GENERADOR PURO de workflow YAML
  (sin cliente HTTP); los stages ejecutan comandos locales vía subprocess.
  ⇒ NO se requiere reqwest (la nota §7.2.8 anticipaba API client que el
  código Python nunca tuvo). Sin deps nuevas.
- **Crate** `rust/crates/cortex-pipeline`: domain/types (StageType/Status,
  StageResult con icon/passed/failed/to_dict, PipelineReport con
  summary/to_markdown/to_dict), domain/context (PipelineContext +
  stage_outputs compartido), trait PipelineStage (structural → trait),
  orchestrator (gate enforcement: abort al fallar bloqueante y marcar
  restantes SKIPPED; abort_early=false corre todo).
- **Stages nativos**: Test/Lint/Security (detección de comando por tipo de
  proyecto, subprocess con timeout por polling, parsing de salida pytest/
  ruff/pip-audit, coverage threshold) y Documentation (lectura vault).
- **runners/github**: generador byte-parity del workflow PR
  (_build_steps/_step_security/_step_lint/_step_test/_step_documentation).
- **Gate**: `bench/parity/pipeline_golden_p12b.py` — generator YAML para
  sets canónicos de stages + orquestador con stages falsos (pass/fail/
  skip flows) + renderings summary/markdown/dict con clock fijo;
  `examples/pipeline_check.rs` byte-parity.

- **[P12B-6] Sin reqwest**: el "cliente HTTP" anticipado en §3.7/§7.2.8 no
  existe — runners/github.py genera el workflow YAML y GitHub ejecuta los
  comandos vía CLI cortex (passthrough actual). El gate congela los bytes
  del YAML generado; si en el futuro aparece un cliente real, se agrega
  con ADR propio.
- **[P12B-6] json.dumps(indent=1) anidado**: el to_dict de Flow A se emite
  a mano en el checker (artifacts anidados a 4 espacios, último elemento
  sin coma) — BTreeMap no preserva orden de inserción Python.

- **[P12B-7] El tutor era portear-barato**: los 3 escenarios dramáticos del
  doc 09 se resolvieron con exploración — sin SessionService ni AgentMemory,
  solo layout + contenido. Lección: verificar deps reales antes de heredar
  advertencias históricas.
- **[P12B-7] Fixtures de hints FUERA del repo**: `ProjectState.detect` vía
  `discover()` camina hacia arriba; fixtures dentro del árbol de Cortex
  heredaban `has_config=true` del repo de desarrollo (L0 nunca matcheaba).
  Regla para gates futuros con detección de estado: mkdtemp externo.
- **[P12B-7] Contenido como include_str!**: los cuerpos renderizados se
  capturan una vez con rich `record=True + export_text()` y se embeben;
  paridad de contenido garantizada por construcción, divergencia solo en
  estilos ANSI.

### Diseño aprobado P12B-8 — cortex-cli clap nativo (cierre del Stream B)

- **ADR chico — activación de clap 4 en cortex-cli**: clap 4 ya figuraba
  como dependencia declarada del crate desde G6 (sin uso). Se activa la
  feature `derive` (única adición real al árbol de deps: `clap_derive` +
  transitivas de proc-macro), manteniendo `default-features = false`
  (sin color ni sugerencias ⇒ help/errores deterministas y self-golden
  estables). Sin más deps nuevas: el passthrough usa std::process::Command,
  el JSON paridad se emite con writers propios y la TUI no se toca.
- **Arquitectura de dispatch (routing manual previo a clap)**:
  `CORTEX_PY=1` → passthrough TOTAL inmediato; `--cli-version` → línea
  nativa (compat contrato fachada); argv vacío (Home TUI) → passthrough;
  `--help/-h` solos → help clap (self-golden); primer token ∈ wireados →
  clap parsea ESE subárbol y ejecuta nativo; cualquier otra cosa →
  reenvío del argv ORIGINAL byte-idéntico al CLI Python (`CORTEX_BIN`
  override o `cortex` en PATH, mensaje 127 actual). Así los errores de
  comando desconocido/args de comandos NO wireados salen del propio Typer
  (paridad gratis) y clap solo gobierna lo que ejecuta nativo.
- **Paridad (decisión del dueño)**: comandos funcionales wireados =
  byte-parity stdout/stderr/rc vs oráculo Python. Textos `--help` y errores
  de args de comandos wireados = **self-golden** (snapshots congelados en
  tests/checker Rust): Typer y clap formatean distinto por diseño;
  divergencia cosmética documentada (precedente: ANSI del tutor).
- **Alcance Tier 1 estricto (decisión del dueño)**: se wirean SOLO
  comandos de crates B: doctor, tutor (+menú EOF), hint, org-config,
  promote-knowledge, review-knowledge ×4, memory-report, webgraph export,
  autopilot preflight, agent-guidelines, install-skills. Todo lo demás
  (session/ide/ci/docs/pr-context/hu/next/brain/setup/embedding/mcp/
  documenting trio/search/context/remember/stats/Home TUI/-V) queda
  PASSTHROUGH residual post-P12, inventariado al cierre.
- **Writers JSON duales**: (1) `pydantic_json(indent=2)` para
  `model_dump_json(indent=2)` — UTF-8 crudo, orden de campos serde=
declaración pydantic; (2) `stdlib_json(indent=2)` para `json.dumps(...,
indent=2)` — ensure_ascii=True con pares sustitutos >0xFFFF, separadores
de indent anidados. Lección #1 aplica.
- **Panel rich para hint**: réplica del Panel(width=80 non-tty,
  padding=(1,2), title="{icon} {title}") sin ANSI; líneas en blanco
  alrededor. El oráculo corre pipado en ambos lados ⇒ determinista.
- **Fixtures FUERA del repo** (lección #3): mkdtemp externo porque
  hint/doctor detectan estado caminando hacia arriba. Normalización
  {{ROOT}}/{{TS}} pactada.
- **Cold start**: medición documentada sobre binario release (`hint` y
  `--cli-version`, mediana N≈20); objetivo <100 ms; rollback CORTEX_PY=1
  probado en gate.

## Cortex CLI P12B-8 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:executing-plans (inline; los subagentes medium del paquete
> fueron borrados y el cupo falló 3× en sesión anterior). Steps usan
> checkbox (`- [ ]`).

**Goal:** binario clap nivel-1 con subcomandos nativos que consumen los
crates B, passthrough residual al CLI Python y rollback CORTEX_PY=1,
con cold start <100 ms medido.

**Architecture:** routing manual de primer token → clap derive solo para
subárboles wireados → ejecución nativa por crate; catch-all passthrough
byte-idéntico. Writers JSON propios para las dos semánticas de Python.

**Tech Stack:** clap 4 (derive, default-features=false), crates
workspace read-only (doctor/tutor/enterprise/workspace/webgraph-server/
autopilot/setup), serde_json float_roundtrip; oráculo `.venv/bin/cortex`.

**Spec:** sección “Diseño aprobado P12B-8” de este archivo.

### Global Constraints

- Territorio: `rust/crates/cortex-cli/` + hunk propio de deps en su
  Cargo.toml + `bench/parity/cli_golden_p12b.py` + este archivo.
  cortex-app/mcp/actions/services INTACTOS (A cerró).
- Un gate por commit: commit feature atómico recién con TODO verde.
- Suite Python completa UNA vez pre-commit bajo
  `flock .cortex/heavy.lock` + `timeout 1200` + threads=2 +
  `CARGO_BUILD_JOBS=6`; baseline trunk conocida (e2e setup/autopilot/
  artefact_integrity preexistentes).
- Staging quirúrgico; Cargo.lock solo si diff 100% atribuible a B
  (clap_derive lo es).

---

### Task 1: Esqueleto dispatch + passthrough + rollback

**Files:**
- Rewrite: `rust/crates/cortex-cli/src/main.rs`
- Create: `rust/crates/cortex-cli/src/fallback.rs`
- Modify: `rust/crates/cortex-cli/Cargo.toml` (clap += "derive"; deps
  workspace crates se agregan por tarea según se wirean)
- Test: `rust/crates/cortex-cli/tests/cli_dispatch.rs`

**Interfaces:**
- Produces: `fallback::passthrough(argv) -> !` (hereda stdio, propaga rc,
  mensaje 127 actual si no hay binario), `fallback::python_bin() -> String`.

- [ ] **Step 1: tests rojos de dispatch**

```rust
// tests/cli_dispatch.rs
use std::process::Command;
fn bin() -> Command { Command::new(env!("CARGO_BIN_EXE_cortex-cli")) }

#[test]n cli_version_native() {
    let out = bin().arg("--cli-version").output().unwrap();
    assert_eq!(String::from_utf8_lossy(&out.stdout).trim(), "cortex-cli 0.1.0");
}
#[test]n cortex_py_forces_passthrough() {
    // CORTEX_PY=1 + --cli-version DELEGA al CLI python (que no conoce ese flag
    // ⇒ error de Typer, exit≠0): prueba que el env se chequea ANTES del dispatch.
    let out = bin().env("CORTEX_PY", "1")
        .env("CORTEX_BIN", "/bin/false")   // binario que existe y falla
        .arg("--cli-version").output().unwrap();
    assert_eq!(out.status.code(), Some(1)); // rc de /bin/false, NO 0 nativo
}
#[test]n unknown_command_passes_through_original_argv() {
    let out = bin().env("CORTEX_PY", "1")
        .env("CORTEX_BIN", "/bin/echo")
        .args(["frobnicate", "--x", "1"]).output().unwrap();
    assert_eq!(String::from_utf8_lossy(&out.stdout), "frobnicate --x 1\n");
}
```

- [ ] **Step 2: RED visible** — `cargo test -p cortex-cli` FAIL.

- [ ] **Step 3: implementar main.rs mínimo**: check CORTEX_PY → fallback;
  `--cli-version`; argv==["--help"]/["-h"] → clap help del Parser raíz;
  resto → fallback::passthrough(argv original). Routing por primer token
  queda como match abierto para Tasks 2–7.

- [ ] **Step 4: GREEN + clippy/fmt focalizado.**

### Task 2: doctor + agent-guidelines + install-skills

**Files:** Create `src/commands/{mod,doctor,misc}.rs`; Test
`tests/cli_commands_basic.rs`. Deps += cortex-doctor, cortex-workspace.

**Interfaces:**
- Consumes: `cortex_doctor::{run_doctor, DoctorScope}`,
  `cortex_workspace::skills::install_skills(&Path) -> Vec<String>`;
  recurso `include_str!("../../../cortex/agent_guidelines.md")`.

- [ ] **Step 1: test rojo** — `doctor --project-root <tmp vacío>` imprime
  `[FAIL] config_yaml: ...` a stderr, `[OK] project_root...`? NO: replica
  EXACTA de main.py: ok→`[OK] name: detail` stdout GREEN(no-tty=plain);
  fail→stderr `[FAIL] ...`; warn→stdout `[WARN]`; info→stdout `[INFO]`;
  rc=1 si has_failures; strict+warnings→rc=1. Assert contra salida
  esperada literal de un fixture vacío (root inexistente → todos fails).
- [ ] **Step 2: RED → Step 3: implementar render loop + rc** → **Step 4:
  GREEN**. `agent-guidelines`: bytes completos del recurso + `\n`?
  typer.echo añade newline final — verificar contra oráculo antes de
  fijar. `install-skills [--dest]`: mensajes ✅/bullets/“All skills
  already installed.” idénticos.

### Task 3: tutor + hint (panel rich)

**Files:** Create `src/commands/tutor.rs`, `src/rich_panel.rs`; Test
`tests/cli_tutor_hint.rs`. Deps += cortex-tutor.

**Interfaces:**
- Consumes: `cortex_tutor::engine::{render_menu, show_topic_by_slug}`,
  `cortex_tutor::hint::{ProjectState::detect, get_hint}`.
- Produces: `rich_panel::render(icon,title,body,command,width=80) -> String`.

- [ ] **Step 1: test rojo hint-L0**: fixture mkdtemp VACÍO fuera del repo;
  salida esperada generada por oráculo Python (`HintEngine().get_hint(...).render()`) congelada en el test tras primera verificación manual.
- [ ] **Step 2: RED → Step 3: panel renderer** (borde ─│┌┐└┘, título
  inline en borde superior con espacios, padding 1/2, wrap greedy de
  palabras a 80−4 columnas, `$ command` línea propia, print en blanco
  antes/después) `→ Step 4: GREEN`. Tutor: slug directo (no encontrado →
  stderr `Tópico 'x' no encontrado. Disponibles: …` rc=1) + menú EOF
  (stdin cerrado → menú + línea en blanco + rc 0).

### Task 4: org-config + promote-knowledge (pyjson)

**Files:** Create `src/pyjson.rs`, `src/commands/{org_config,promote}.rs`;
Test `tests/cli_enterprise_cmds.rs`. Deps += cortex-enterprise,
serde_json float_roundtrip.

**Interfaces:**
- Produces: `pyjson::stdlib_dumps_indent2(&PyVal) -> String`
  (ensure_ascii+pares sustitutos) y `pyjson::pydantic_pretty(v:
  &serde_json::Value) -> String` (UTF-8 crudo, 2-indent, {} [] compactos).
- Consumes: enterprise `config` (load/describe/topology YAML safe_dump vía
  `cortex_setup::yaml`), `KnowledgePromotionService::from_project_root`.

- [ ] **Step 1: tests rojos de writers** — `assert_eq!(stdlib_dumps("
  á😀"), "\"\\u00e1\\ud83d\\ude00\"")`; orden de inserción preservado.
- [ ] **Step 2–4: RED→implementar→GREEN** para org-config (texto:
  4 líneas header + blank + yaml.safe_dump(sort_keys=False,
  allow_unicode=False) vía dump_with; --required missing → stderr
  `Enterprise config not found under <root>/.cortex/org.yaml` rc=1) y
  promote-knowledge (--dry-run default: plan vacío → “No reviewed
  candidates ready for promotion.”; con records.jsonl revisado → líneas
  “Planned promotions: N” + bullets; --json payload dict ordenado +
  default=str).

### Task 5: review-knowledge ×4

**Files:** Create `src/commands/review.rs`; Test extiende
`tests/cli_enterprise_cmds.rs`.

- [ ] pending (tabla `  - {path:<60} doc_type={…:<10} owner={…}` /
  “No drafts pending review.” / --json list), approve/reject
  (`approve_output`/`reject_output` existentes + “Recorded review…” del
  candidate legacy vía service.review), candidate (--approve/--reject,
  model_dump_json(indent=2)), errores rc=1 (path escape). Fixture org con
  drafts + records.jsonl. RED→GREEN por subcomando.

### Task 6: memory-report (cierra seam DoctorBackend)

**Files:** Create `src/commands/memory_report.rs`; Test
`tests/cli_memory_report.rs`. Deps ya presentes.

- [ ] **Step 1: test rojo**: texto bloque completo (“Cortex Enterprise
  Memory Report” … Promotion … warnings:) y --json (payload
  model_dump(mode="json") + stdlib writer). Scope inválido → stderr
  `Invalid --scope value. Use one of: local, enterprise, all.` rc=1.
- [ ] **Step 2: implementar** con
  `EnterpriseReportingService::from_project_root(root, layout)
  .with_doctor_backend(NativeDoctorBackend::new())`; {{TS}} solo en
  oráculo. **Step 3: GREEN.**

### Task 7: webgraph export + autopilot preflight

**Files:** Create `src/commands/{webgraph,autopilot}.rs`; Test
`tests/cli_webgraph_autopilot.rs`. Deps += cortex-webgraph-server,
cortex-autopilot.

- [ ] webgraph export: single-project (`_require_config` → stderr
  “No Cortex configuration found at …” rc=1 si falta; OK →
  “Webgraph snapshot exported -> <path>”), flags mode/output/--no-cache/
  --project-root/--workspace-file. Grupos `webgraph`/`autopilot` llevan
  external_subcommand interno → serve/doctor/start/etc. caen a passthrough.
- [ ] autopilot preflight: `default_detectors()+resolve_detectors` sobre
  DetectionRequest{user_request, changed_files}; _emit texto `k: v` o
  stdlib JSON (confidence f64 → formato repr Python verificado contra
  oráculo). start/checkpoint/finish/status/doctor → passthrough.

### Task 8: Gate cli_golden_p12b.py + checker + self-golden

**Files:** Create `bench/parity/cli_golden_p12b.py`,
`rust/crates/cortex-cli/examples/cli_check.rs`,
`tests/cli_self_golden.rs` (help root/doctor, missing-arg approve —
snapshots inline).

- [ ] Gate: fixtures mkdtemp externos (L0 vacío / full / org+records);
  casos S01–S28 del diseño (11 wireados × texto/--json, errores, unknown
  command, CORTEX_PY=1 ×2); oráculo `.venv/bin/cortex` vs binario
  construido; normaliza {{ROOT}}/{{TS}}; build/verify determinista.
- [ ] `examples/cli_check.rs`: recorre golden_cli.txt + self-golden
  inline → `✅ PARIDAD P12B-8`.

### Task 9: Cold start + verificación + commits + cierre

- [ ] Medición release: `hyperfine --warmup 3 './target/release/cortex-cli
  hint'` (o loop bash `date +%s%N` N=20, mediana) en fixture L0; número
  y comando anotados acá; objetivo <100 ms.
- [ ] fmt/clippy/tests workspace-B focalizados bajo lock R3; gates
  build/verify; suite Python completa UNA vez (baseline trunk idéntica).
- [ ] Commit atómico `feat(obra07 P12B-8): CLI clap nativo — sincronización
  final con A` + docs inmediato (fila ✅ con evidencia) + sección
  “Stream B completo” (inventario entregado + passthrough residual
  post-P12). HANDOFF/ESTADO-ACTUAL/doc 09 intactos.

## Tabla de tareas P12B

| Tarea | Estado | Evidencia | Commit |
|---|---|---|---|
| P12B-1 crate cortex-workspace (layout 564 + handoff 121 + git_policy 111 + skills 98 + runtime_context 58 ≈ 1076 LOC py) | ✅ | Gate: `bench/parity/workspace_golden_p12b.py` build/verify determinista + `examples/workspace_check.rs` **byte-parity** sobre 8 escenarios de discovery + handoff H01–H06 (zoo quoting/folding/multilínea/tab congelados vs PyYAML real) + validaciones inválidas + snippets/gitignore + slugify/persist-modes (fake-git y repo REAL `feature/Mi_Rama`) + skills con hashes. Suite Python oráculo verde: **2455 passed, 18 skipped**. `cargo test -p cortex-workspace`: 27 tests ✅ · clippy `-D warnings` ✅ · fmt ✅ | (este commit) |
| P12B-2 webgraph-server axum (~2202) | ✅ | Gate: `bench/parity/webgraph_golden_p12b.py` build/verify determinista + `examples/webgraph_check.rs` **byte-parity** vs `golden_webgraph.txt` (server real axum/Flask en puertos efímeros, fixture fake_embed SHA-256 + export P3, normalización {{ROOT}}/{{TS}}/{{FP}}; 19 casos single + 3 federados). Suite Python oráculo rc=0. clippy `-D warnings` ✅ fmt ✅ tests 3 ✅ | `2761356` |
| P12B-3 enterprise/review_knowledge (~2441) | ✅ | Gate: `bench/parity/enterprise_golden_p12b.py` build/verify determinista (8 segmentos; oráculo real incl. `run_doctor`) + `examples/enterprise_check.rs` **byte-parity** → `[PASS] enterprise_check byte-parity vs golden_enterprise.txt` / `✅ PARIDAD P12B-3`. Suite Rust crate: 32 tests ✅ · clippy `-D warnings` ✅ · fmt ✅. Suite Python: 2571 collected, **0 fallos enterprise/promotion/review_knowledge**; 32 fallos PREEXISTENTES de trunk en e2e setup/autopilot/tui/artefact_integrity (commit "recatorizacion" borró módulos que esos tests importan; árbol Python verificado idéntico a HEAD). | `1ce45ca` |
| P12B-4 doctor (~925) | ✅ | Gate: `bench/parity/doctor_golden_p12b.py` (5 escenarios: legacy/all/enterprise-sin-org/new-layout/con-sessions; oráculo doctor Python real + STUB_TABLE contractual) + `examples/doctor_check.rs` **byte-parity** → `✅ PARIDAD P12B-4`. Suite Rust crate: 5 tests ✅ · clippy `-D warnings` ✅ · fmt ✅. Suite Python: mismo set de fallos preexistentes de trunk que el baseline previo (29F+3E e2e setup/autopilot/tui/artefact); **0 regresiones B**. | `31b3f3c` |
| P12B-5 autopilot (~1902, capa de decisión) | ✅ | Gate: `doctor_golden_p12b.py` ampliado a 6 escenarios (autopilot_policy REAL + autopilot_mode_typo) + `doctor_check.rs` byte-parity `✅ PARIDAD P12B-4`. Suite Rust: autopilot 5 + doctor 5 tests ✅ · clippy/fmt ✅. Suite Python: mismo set preexistente de trunk (29F+3E e2e); unit tests/unit/autopilot sin fallos. service/cli/mcp_tools con fallo explícito hasta motor de sesiones nativo. | `8bc4c6d` |
| P12B-6 pipeline SDDwork (~1708) | ✅ | Gate: `bench/parity/pipeline_golden_p12b.py` (2 workflows GH Actions byte-exactos + flows pass/fail-bloqueante/skip + abort_early + no-bloqueante + summary/markdown/to_dict con clock fijo) + `examples/pipeline_check.rs` **byte-parity** → `✅ PARIDAD P12B-6`. Suite Rust crate: 4 tests ✅ · clippy `-D warnings` ✅ · fmt ✅. **Sin reqwest**: el runner Python es generador puro de YAML, nunca hubo cliente HTTP (hallazgo vs §7.2.8). Documentation stage stub hasta AgentMemory nativo. | `c8a04d3` |
| P12B-7 tutor (~862, porte fiel — opción A) | ✅ | Gate: `bench/parity/tutor_golden_p12b.py` (metadata JSON de 7 topics por introspección + hints L0/L1/L7 en fixtures FUERA del repo) + `examples/tutor_check.rs` **byte-parity** → `✅ PARIDAD P12B-7`. Suite Rust crate: 4 tests ✅ · clippy/fmt ✅. Hallazgo: dependencias reales = layout + contenido estático (sin sesiones/AgentMemory) ⇒ el "NO portear ciego" del doc 09 queda desmontado. Divergencia cosmética: cuerpos embebidos vía rich `export_text()` sin ANSI. | `0e6b936`+`2fd035c`/`600cc04` |
| P12B-8 CLI clap nativo (~2995, ÚLTIMO) | 🚧 en curso | punto de sincronización final; CORTEX_PY=1 rollback; cold-start <100ms | — |

## Notas de coordinación dual-stream

- Consumo de cortex-app como dep normal de Cargo (read-only); nada de A fue
  editado por B.
- El gate P12B-1 corre en <2s y no colisiona con los goldens `*p12a*` de A.
- Al commitear `rust/Cargo.toml` se incluyeron SOLO las líneas de mi miembro;
  `Cargo.lock` queda fuera de este commit por hunks ajenos de A (ver
  decisiones).
