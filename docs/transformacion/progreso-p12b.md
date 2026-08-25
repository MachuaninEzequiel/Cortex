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

## Tabla de tareas P12B

| Tarea | Estado | Evidencia | Commit |
|---|---|---|---|
| P12B-1 crate cortex-workspace (layout 564 + handoff 121 + git_policy 111 + skills 98 + runtime_context 58 ≈ 1076 LOC py) | ✅ | Gate: `bench/parity/workspace_golden_p12b.py` build/verify determinista + `examples/workspace_check.rs` **byte-parity** sobre 8 escenarios de discovery + handoff H01–H06 (zoo quoting/folding/multilínea/tab congelados vs PyYAML real) + validaciones inválidas + snippets/gitignore + slugify/persist-modes (fake-git y repo REAL `feature/Mi_Rama`) + skills con hashes. Suite Python oráculo verde: **2455 passed, 18 skipped**. `cargo test -p cortex-workspace`: 27 tests ✅ · clippy `-D warnings` ✅ · fmt ✅ | (este commit) |
| P12B-2 webgraph-server axum (~2202) | ✅ | Gate: `bench/parity/webgraph_golden_p12b.py` build/verify determinista + `examples/webgraph_check.rs` **byte-parity** vs `golden_webgraph.txt` (server real axum/Flask en puertos efímeros, fixture fake_embed SHA-256 + export P3, normalización {{ROOT}}/{{TS}}/{{FP}}; 19 casos single + 3 federados). Suite Python oráculo rc=0. clippy `-D warnings` ✅ fmt ✅ tests 3 ✅ | `2761356` |
| P12B-3 enterprise/review_knowledge (~2441) | ✅ | Gate: `bench/parity/enterprise_golden_p12b.py` build/verify determinista (8 segmentos; oráculo real incl. `run_doctor`) + `examples/enterprise_check.rs` **byte-parity** → `[PASS] enterprise_check byte-parity vs golden_enterprise.txt` / `✅ PARIDAD P12B-3`. Suite Rust crate: 32 tests ✅ · clippy `-D warnings` ✅ · fmt ✅. Suite Python: 2571 collected, **0 fallos enterprise/promotion/review_knowledge**; 32 fallos PREEXISTENTES de trunk en e2e setup/autopilot/tui/artefact_integrity (commit "recatorizacion" borró módulos que esos tests importan; árbol Python verificado idéntico a HEAD). | `1ce45ca` |
| P12B-4 doctor (~925) | ⏳ pendiente | golden P0 congela salida; checks sin backend nativo ⇒ fail explícito documentado (patrón P6/P9) | — |
| P12B-5 autopilot (~1902) | ⏳ pendiente | spec: tests/unit/autopilot | — |
| P12B-6 pipeline SDDwork (~1708) | ⏳ pendiente | reqwest aprobado §7.2.8; stages gh API con fixtures/dry-run | — |
| P12B-7 tutor (~862) | ⏳ decisión del dueño pendiente | se documentarán las 3 opciones (porte fiel vs ratatui vs no migrar) aquí al cierre | — |
| P12B-8 CLI clap nativo (~2995, ÚLTIMO) | ⏳ pendiente | punto de sincronización final; CORTEX_PY=1 rollback; cold-start <100ms | — |

## Notas de coordinación dual-stream

- Consumo de cortex-app como dep normal de Cargo (read-only); nada de A fue
  editado por B.
- El gate P12B-1 corre en <2s y no colisiona con los goldens `*p12a*` de A.
- Al commitear `rust/Cargo.toml` se incluyeron SOLO las líneas de mi miembro;
  `Cargo.lock` queda fuera de este commit por hunks ajenos de A (ver
  decisiones).
