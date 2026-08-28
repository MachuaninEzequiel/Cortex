//! Puerto de `stages/documentation.py` — verificación de docs de agente y
//! nota de sesión fallback wireada al persister/reconstructor nativos (P5).
//!
//! Sustituye el stub contractual (P6/P9) por una implementación real:
//! - paso 1 `_store_pr_with_results` → `cortex_app::pr::PRService::store_pr_context`
//!   sobre la memoria episódica nativa (`NativeEpisodicStore` JSONL).
//! - paso 2 `_verify_docs` → `cortex_app::doc_verifier::DocVerifier`.
//! - paso 3 `_index_docs`  → `cortex_app::semantic::SemanticIndex::build`
//!   (equiv. nativo de `AgentMemory.sync_vault()` → nº de documentos).
//! - paso 4 `_generate_fallback` → documenter nativo:
//!   `reconstruct_gitless`/`reconstruct_git` → `persister::build_create_args`
//!   → `cortex_services::note::NoteService::create` (write de la nota).
//!
//! Mapeo de memoria (glue documentado, brief T4 §4): el oráculo usa
//! `AgentMemory.store_pr_context(ctx, lint, audit, test)`; el stage nativo
//! usa `PRService::store_pr_context` con un `StageEpisodicMemory` sobre el
//! JSONL episódico y un embedder determinista `feature_embed` (hashing-trick,
//! DIM 64 — el runtime del pipeline no carga el modelo ONNX del CLI).
//! Sin `memory_jsonl` configurado los pasos de memoria degradan a skip con
//! log — espejo del `except: logger.warning` del oráculo.
//!
//! Divergencias documentadas (P6/P9):
//! - El oráculo genera el fallback con `generate_pr_docs` (DocGenerator); el
//!   flujo nativo reemplaza ese par por el persister documenter, que exige
//!   una sesión del PR (`find_for_pr`); sin sesión ⇒ "Fallback generation
//!   skipped." y un fallo del persister (sesión corrupta / repo git ausente)
//!   propaga a ERROR "Documentation stage error: …".
//! - `DocVerifier.verify_from_list` nativo nunca lanza: los errores van en
//!   `result.errors`; el fallback a sessions-dir del oráculo se dispara
//!   exactamente cuando esa lista no está vacía.

use std::collections::BTreeMap;
use std::path::{Path, PathBuf};

use chrono::Utc;
use cortex_app::doc_verifier::DocVerifier;
use cortex_app::documenter::persister::{self, CreateArgs};
use cortex_app::documenter::spec_loader::load_spec;
use cortex_app::documenter::{reconstruct_git, reconstruct_gitless};
use cortex_app::episodic::{AppendParams, MemoryEntry, NativeEpisodicStore};
use cortex_app::pr::{PRContext, PRService};
use cortex_app::session::service::SessionService;
use cortex_app::session::VerificationHookResult;
use cortex_app::workitems::EpisodicMemoryRequest;
use cortex_services::note::{NoteCreate, NoteService};
use cortex_services::{EpisodicPort, EpisodicRequest, SemanticPort};

use crate::domain::context::PipelineContext;
use crate::domain::types::{StageResult, StageStatus, StageType};

/// Stage de documentación real: verifica docs de agente, indexa si existen
/// y genera una nota de sesión fallback (persister nativo) si no.
pub struct DocumentationStage {
    /// `block_on_failure` del oráculo (default false: docs se fomentan, no se
    /// fuerzan).
    pub block_on_failure: bool,
    /// `SessionService` del workspace: `SessionService::new(SessionStorage::
    /// new(layout.sessions_dir()), &layout.repo_root)`.
    pub session_service: SessionService,
    /// `pr_ctx: PRContext | None` del oráculo. `None` ⇒ se salta el store del
    /// PR context y el fallback (espejo exacto del oráculo).
    pub pr_ctx: Option<PRContext>,
    /// JSONL episódico (`NativeEpisodicStore`) para el glue de memoria.
    /// `None` ⇒ pasos de memoria degradan a skip con log (no-bloqueante).
    pub memory_jsonl: Option<PathBuf>,
}

impl DocumentationStage {
    pub fn new(session_service: SessionService) -> Self {
        Self {
            block_on_failure: false,
            session_service,
            pr_ctx: None,
            memory_jsonl: None,
        }
    }

    pub fn with_block_on_failure(mut self, value: bool) -> Self {
        self.block_on_failure = value;
        self
    }

    pub fn with_pr_ctx(mut self, value: PRContext) -> Self {
        self.pr_ctx = Some(value);
        self
    }

    pub fn with_memory_jsonl(mut self, value: impl Into<PathBuf>) -> Self {
        self.memory_jsonl = Some(value.into());
        self
    }

    /// Cuerpo del stage: `Result<(has_docs, fallback_path), String>` — el
    /// `Err` es la "unexpected exception" del oráculo → ERROR.
    fn run(&self, ctx: &PipelineContext) -> Result<(bool, Option<String>), String> {
        // Paso 1: PR context enriquecido en memoria episódica (best-effort).
        self.store_pr_with_results(ctx);

        // Paso 2: verificar docs de agente (con fallback sessions-dir).
        let has_docs = self.verify_docs(ctx);

        if has_docs {
            return Ok((true, None));
        }

        // Paso 4: sin docs ⇒ nota de sesión fallback vía persister nativo.
        let fallback = self.generate_fallback(ctx)?;
        Ok((false, fallback))
    }

    /// `_store_pr_with_results`: status de Lint/Tests/Security Audit de
    /// stages previos → `PRService::store_pr_context` (memoria episódica).
    fn store_pr_with_results(&self, ctx: &PipelineContext) {
        let Some(pr_ctx) = self.pr_ctx.as_ref() else {
            return; // oráculo: `if self._pr_ctx is not None`
        };
        let Some(jsonl) = self.memory_jsonl.as_deref() else {
            eprintln!(
                "[Documentation] PR context storage skipped: no episodic \
                 memory configured (memory_jsonl)"
            );
            return;
        };
        let status = |stage: &str| -> Option<String> {
            ctx.stage_outputs
                .get(stage)
                .and_then(|m| m.get("status"))
                .and_then(|v| v.as_str())
                .map(String::from)
        };
        let lint = status("Lint");
        let audit = status("Security Audit");
        let tests = status("Tests");

        let mut memory = StageEpisodicMemory::load(Some(jsonl));
        let sink: &mut dyn cortex_app::workitems::EpisodicSink = &mut memory;
        let mut svc = PRService::new(&ctx.vault_path, Some(sink));
        match svc.store_pr_context(pr_ctx, lint.as_deref(), audit.as_deref(), tests.as_deref()) {
            Ok(_) => {}
            Err(e) => eprintln!("[Documentation] Could not store PR context: {e}"),
        }
    }

    /// `_verify_docs`: `DocVerifier.verify_from_list(changed_files)` con
    /// fallback no-bloqueante a sessions-dir no vacío si falla la verificación.
    fn verify_docs(&self, ctx: &PipelineContext) -> bool {
        let changed: Vec<String> = match &self.pr_ctx {
            Some(p) => p.files_changed.clone(),
            None => ctx.changed_files.clone(),
        };
        let verifier = DocVerifier::new(&ctx.vault_path);
        let result = verifier.verify_from_list(&changed);
        if result.errors.is_empty() {
            return result.has_agent_docs;
        }
        eprintln!(
            "[Documentation] Doc verification failed (non-blocking): {:?}",
            result.errors
        );
        let sessions_dir = ctx.vault_path.join("sessions");
        sessions_dir.is_dir()
            && std::fs::read_dir(&sessions_dir)
                .map(|mut rd| rd.next().is_some())
                .unwrap_or(false)
    }

    /// `_index_docs`: rebuild del índice semántico nativo (equiv. nativo de
    /// `sync_vault`); devuelve el nº de documentos indexados; error ⇒ warn +
    /// 0 (como el oráculo).
    fn index_docs(&self, ctx: &PipelineContext) -> i64 {
        match cortex_app::semantic::SemanticIndex::build(&ctx.vault_path) {
            Ok(idx) => idx.docs.len() as i64,
            Err(e) => {
                eprintln!("[Documentation] Vault sync failed: {e}");
                0
            }
        }
    }

    /// `_generate_fallback`: nota de sesión vía documenter nativo. Sin pr_ctx
    /// o sin sesión del PR ⇒ `Ok(None)` (skipped); fallos del persister o del
    /// write ⇒ `Err` (→ ERROR del stage).
    fn generate_fallback(&self, ctx: &PipelineContext) -> Result<Option<String>, String> {
        if self.pr_ctx.is_none() {
            return Ok(None);
        }
        let (record, _kind) = self.session_service.find_for_pr(
            None,
            Some(ctx.commit_sha.as_str()),
            Some(ctx.source_branch.as_str()),
        );
        let Some(record) = record else {
            eprintln!(
                "[Documentation] No session found for PR #{}, fallback skipped",
                ctx.pr_number
            );
            return Ok(None);
        };
        let spec = load_spec(Path::new(&record.spec_path));
        let verification_results: Vec<VerificationHookResult> = Vec::new();
        let reconstruction = if record.is_gitless() {
            reconstruct_gitless(&record, &spec, verification_results)
        } else {
            reconstruct_git(
                &record,
                &spec,
                self.session_service.repo_root(),
                verification_results,
            )
        }
        .map_err(|e| format!("reconstruct: {e}"))?;
        let (create_args, _warnings) = persister::build_create_args(&reconstruction);
        let path = self
            .write_fallback_note(ctx, create_args)
            .map_err(|e| format!("note write: {e}"))?;
        Ok(Some(path.display().to_string()))
    }

    /// Write de la nota de sesión: `CreateArgs` del persister → kwargs
    /// canónicos de `NoteService.create` (P12A-5) sobre el vault del ctx.
    fn write_fallback_note(
        &self,
        ctx: &PipelineContext,
        create_args: CreateArgs,
    ) -> Result<PathBuf, String> {
        let args = note_create_from_args(create_args)?;
        let mut semantic = StageSemanticPort;
        let mut episodic = StageEpisodicMemory::load(self.memory_jsonl.as_deref());
        let mut svc = NoteService::new(&ctx.vault_path, &mut semantic, &mut episodic);
        svc.create(args, Utc::now())
    }
}

impl crate::orchestrator::PipelineStage for DocumentationStage {
    fn name(&self) -> &str {
        "Documentation"
    }
    fn stage_type(&self) -> StageType {
        StageType::Documentation
    }
    fn block_on_failure(&self) -> bool {
        self.block_on_failure
    }
    fn execute(&self, ctx: &mut PipelineContext) -> StageResult {
        let started = std::time::Instant::now();
        let outcome = self.run(ctx);
        let duration_ms = started.elapsed().as_millis() as i64;
        match outcome {
            Ok((true, _)) => {
                // Paso 3: indexar los docs encontrados (equiv. `sync_vault`).
                let doc_count = self.index_docs(ctx);
                StageResult {
                    stage_type: StageType::Documentation,
                    stage_name: "Documentation".into(),
                    status: StageStatus::Passed,
                    message: format!("Agent documentation found and indexed ({doc_count} docs)."),
                    artifacts: BTreeMap::from([
                        ("has_agent_docs".into(), serde_json::json!(true)),
                        ("indexed".into(), serde_json::json!(doc_count)),
                    ]),
                    duration_ms,
                    timestamp: Utc::now(),
                }
            }
            Ok((false, Some(path))) => {
                let status = if self.block_on_failure {
                    StageStatus::Failed
                } else {
                    StageStatus::Passed
                };
                StageResult {
                    stage_type: StageType::Documentation,
                    stage_name: "Documentation".into(),
                    status,
                    message: format!("No agent docs found. Fallback generated: {path}"),
                    artifacts: BTreeMap::from([
                        ("has_agent_docs".into(), serde_json::json!(false)),
                        ("fallback_path".into(), serde_json::json!(path)),
                    ]),
                    duration_ms,
                    timestamp: Utc::now(),
                }
            }
            Ok((false, None)) => {
                let status = if self.block_on_failure {
                    StageStatus::Failed
                } else {
                    StageStatus::Passed
                };
                StageResult {
                    stage_type: StageType::Documentation,
                    stage_name: "Documentation".into(),
                    status,
                    message: "No agent docs found. Fallback generation skipped.".into(),
                    artifacts: BTreeMap::from([
                        ("has_agent_docs".into(), serde_json::json!(false)),
                        ("fallback_path".into(), serde_json::Value::Null),
                    ]),
                    duration_ms,
                    timestamp: Utc::now(),
                }
            }
            Err(e) => StageResult {
                stage_type: StageType::Documentation,
                stage_name: "Documentation".into(),
                status: StageStatus::Error,
                message: format!("Documentation stage error: {e}"),
                artifacts: BTreeMap::from([("error".into(), serde_json::json!(e))]),
                duration_ms,
                timestamp: Utc::now(),
            },
        }
    }
}

// ── Memoria glue (brief T4 §4): puertos nativos ligeros ────────────────────

/// Embedder determinista del stage (sin ONNX): hashing trick sobre n-gramas
/// de caracteres (n=1..3) a un vector fijo DIM=64, normalizado L2. El runtime
/// del pipeline no carga el modelo ONNX del CLI; este embedder es el "memory
/// glue" documentado del stage.
fn feature_embed(text: &str) -> Vec<f64> {
    const DIM: usize = 64;
    let mut v = vec![0.0f64; DIM];
    let chars: Vec<char> = text.to_lowercase().chars().collect();
    for n in 1..=3 {
        if chars.len() < n {
            break;
        }
        for window in chars.windows(n) {
            let key: String = window.iter().collect();
            let h = fnv1a(&key);
            let idx = (h % (DIM as u64 * 2)) as usize;
            if idx < DIM {
                v[idx] += 1.0;
            } else {
                v[idx - DIM] -= 1.0;
            }
        }
    }
    let norm: f64 = v.iter().map(|x| x * x).sum();
    if norm > 0.0 {
        let l = norm.sqrt();
        for x in &mut v {
            *x /= l;
        }
    }
    v
}

/// FNV-1a (64-bit) — hash determinista estable entre corridas.
fn fnv1a(s: &str) -> u64 {
    let mut h: u64 = 0xcbf2_9ce4_8422_2325;
    for b in s.bytes() {
        h ^= u64::from(b);
        h = h.wrapping_mul(0x0000_0100_0000_01b3);
    }
    h
}

/// Puerto semántico del write de la nota: el índice vectorial nativo exige
/// el embedder ONNX del runtime (CLI), que el pipeline no carga; la
/// indexación queda delegada al runtime (divergencia P6/P9 documentada — el
/// contrato file-on-disk se cumple con el writer canónico `build_note`).
struct StageSemanticPort;

impl SemanticPort for StageSemanticPort {
    fn index_file(&mut self, _rel_path: &str) -> Result<bool, String> {
        Ok(true)
    }
    fn sync(&mut self) -> Result<usize, String> {
        Ok(0)
    }
}

/// Glue de memoria episódica del stage: `NativeEpisodicStore` (JSONL) con el
/// embedder determinista `feature_embed`. Sin JSONL configurado (o ilegible)
/// ⇒ no-op Ok: la memoria es best-effort y NUNCA bloquea la stage.
struct StageEpisodicMemory {
    store: Option<NativeEpisodicStore>,
}

impl StageEpisodicMemory {
    fn load(jsonl: Option<&Path>) -> Self {
        match jsonl {
            Some(path) => match NativeEpisodicStore::load(path) {
                Ok(store) => Self { store: Some(store) },
                Err(e) => {
                    eprintln!("[Documentation] episodic store {path:?}: {e}");
                    Self { store: None }
                }
            },
            None => Self { store: None },
        }
    }

    fn append_params(req: EpisodicRequest) -> AppendParams {
        let mut params = AppendParams::new(req.content);
        params.memory_type = req.memory_type;
        params.tags = req.tags;
        params.files = req.files;
        params.extra_metadata = Some(req.extra_metadata.into_iter().collect());
        params
    }
}

impl cortex_app::workitems::EpisodicSink for StageEpisodicMemory {
    fn add_memory(&mut self, req: EpisodicMemoryRequest) -> Result<MemoryEntry, String> {
        let store = self
            .store
            .as_mut()
            .ok_or_else(|| "episodic store no configurado".to_string())?;
        let mut params = AppendParams::new(req.content);
        params.memory_type = req.memory_type;
        params.tags = req.tags;
        params.files = req.files;
        params.extra_metadata = Some(req.extra_metadata.into_iter().collect());
        store.append(params, &mut |s: &str| Ok(feature_embed(s)))
    }
}

impl EpisodicPort for StageEpisodicMemory {
    fn add(&mut self, req: EpisodicRequest) -> Result<(), String> {
        let Some(store) = self.store.as_mut() else {
            return Ok(());
        };
        let params = Self::append_params(req);
        store
            .append(params, &mut |s: &str| Ok(feature_embed(s)))
            .map(|_| ())
    }
}

// ── Conversión CreateArgs → NoteCreate (P12A-5) ────────────────────────────

fn note_create_from_args(args: CreateArgs) -> Result<NoteCreate, String> {
    let tasks = args
        .tasks
        .into_iter()
        .map(|t| serde_json::to_value(t).map_err(|e| e.to_string()))
        .collect::<Result<Vec<_>, _>>()?;
    Ok(NoteCreate {
        title: args.title,
        spec_summary: args.spec_summary,
        changes_made: args.changes_made,
        files_touched: args.files_touched,
        key_decisions: args.key_decisions,
        next_steps: args.next_steps,
        tags: args.tags,
        sync_vault: args.sync_vault,
        remember: args.remember,
        handoff: args.handoff,
        blockers: args.blockers,
        verified_state: args.verified_state,
        unverified_claims: args.unverified_claims,
        suggested_skills: args.suggested_skills,
        cortex_telemetry: None,
        task_type: args.task_type,
        tasks,
        tasks_total: args.tasks_total as i64,
        tasks_done: args.tasks_done as i64,
        tasks_skipped: args.tasks_skipped as i64,
        gitless: args.gitless,
        phase_line: args.phase_line,
        evidence_by_phase: args
            .evidence_by_phase
            .into_iter()
            .map(|(p, v)| (p.as_str().to_string(), v.join(", ")))
            .collect(),
    })
}
