//! Backend nativo de la familia SPEC (SpecBackend) sobre `cortex-services`
//! (SpecService: validación, hooks, guard proposal, apertura de sesión).
//!
//! Ports indexadores: el índice semántico nativo no expone inserción
//! incremental (build inmutable); el spec creado aparece en `cortex search`
//! en el próximo `cortex reindex`. Documentado (deuda P12) — NO se finge
//! paridad de indexado.

use crate::handlers_spec::{SpecBackend, SpecCreateRequest, SpecError, SpecResultMirror};
use cortex_app::session::SessionRecord;
use cortex_services::spec::{HookInput, SpecCreate, SpecService};
use cortex_services::{EpisodicPort, SemanticPort};
use std::path::{Path, PathBuf};

/// Ports mínimos: sin inserción incremental en el índice semántico.
struct NoopSemantic;
impl SemanticPort for NoopSemantic {
    fn index_file(&mut self, _rel_path: &str) -> Result<bool, String> {
        // El índice se reconstruye en `cortex reindex` (P12).
        Ok(false)
    }
    fn sync(&mut self) -> Result<usize, String> {
        Ok(0)
    }
}

struct NoopEpisodic;
impl EpisodicPort for NoopEpisodic {
    fn add(&mut self, _request: cortex_services::EpisodicRequest) -> Result<(), String> {
        // La memoria episódica del spec se registra vía `cortex remember`
        // (el store nativo no expone append público aquí).
        Ok(())
    }
}

/// Backend de producción: crea el spec en el vault y abre la sesión.
pub struct NativeSpecBackend {
    root: PathBuf,
}

impl NativeSpecBackend {
    pub fn new(root: &Path) -> Self {
        Self {
            root: root.to_path_buf(),
        }
    }
}

impl SpecBackend for NativeSpecBackend {
    fn create_spec_note(&mut self, req: &SpecCreateRequest) -> Result<SpecResultMirror, SpecError> {
        let cfg = super::read_config_yaml(&self.root);
        let vault = super::vault_path(&self.root, &cfg);

        let mut semantic = NoopSemantic;
        let mut episodic = NoopEpisodic;
        let mut service = SpecService::new(&vault, &mut semantic, &mut episodic);

        // Apertura de sesión automática (como el oráculo create-spec).
        let storage =
            cortex_app::session::SessionStorage::new(self.root.join(".cortex").join("sessions"));
        let session_service =
            cortex_app::session::service::SessionService::new(storage, &self.root);
        service = service.with_session_opener(&session_service);

        let hooks: Vec<HookInput> = req
            .verification_hooks
            .iter()
            .map(|v| HookInput::Dict(v.clone()))
            .collect();

        let create = SpecCreate {
            title: req.title.clone(),
            goal: req.goal.clone(),
            requirements: req.requirements.clone(),
            files_in_scope: req.files_in_scope.clone(),
            constraints: req.constraints.clone(),
            acceptance_criteria: req.acceptance_criteria.clone(),
            tags: req.tags.clone(),
            verification_hooks: hooks,
            sync_vault: req.sync_vault,
            remember: false,
            proposal_mode: req.proposal_mode.clone(),
            proposal_confirmed: req.proposal_confirmed,
            with_tasks: false,
        };

        let result = service
            .create(create, chrono::Utc::now())
            .map_err(SpecError::Value)?;
        Ok(SpecResultMirror {
            path: result.path.display().to_string(),
            session_gitless: result.session.as_ref().map(SessionRecord::is_gitless),
        })
    }
}
