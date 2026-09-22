# cortex/session/service.py

## Qué tiene adentro

- `SessionService(storage, repo_root)`: API de ciclo de vida de `SessionRecord`.
- Lectura: `get`, `get_active`, `list`, `path_for`, `active_pointer_path`, `find_for_pr` (prioridad id explícito → `start_commit` → `start_branch`).
- Escritura: `open`, `checkpoint`, `close`, tasks (`add_task`, `update_task_status`, `list_tasks`), `save_new_record`.
- `infer_mode` estático: managed / observed / byo / ci-review según `CheckpointSource`.
- Lock de presentación: escribe/borra `<repo_root>/.cortex/session.lock` (texto plano del id) para extensiones IDE (`cortex-net.ts`). Best-effort, no es fuente de verdad.
- IDs únicos: stem de spec `YYYY-MM-DD_<slug>` + `-2`, `-3` si colisiona.
- Gitless: SHA `GITLESS_COMMIT_PLACEHOLDER` (40 ceros).
- Close solo acepta status terminales `closed|handoff|abandoned`. Mutaciones revalidan el modelo dump→update→validate.

## Para qué sirve

Primitiva de sesión del “Pluggable Middle”: une create-spec → trabajo (checkpoints) → documenter/finish. CLI, MCP, Autopilot, CI y core hablan con este servicio, no con YAML crudo.

## Relaciones

### Recibe de

- `SessionStorage` (YAML en `layout.sessions_dir`).
- `cortex.session.git` (rev-parse, branch, commit).
- Modelos `SessionRecord`, `Checkpoint`, `Task`, enums.
- Errores `InvalidStateTransition`, `SessionNotFound`.

### Envía a

- `AgentMemory` (delega open/checkpoint/close/list).
- `SpecService` (abre sesión al crear spec).
- `autopilot.service`, `cli.session`, `cli.session_tui`, `cli.ci`, `ci.validator`, `ci.review_session`, `documenter.persistence`, `documenter.reconstruction`.
- Archivo `session.lock` y YAML de sesión.

### Notas de implementación observadas en el código

- Puntero activo stale → `get_active()` retorna `None`; `cortex doctor` es quien lo denuncia.
- Fuentes “Cortex agents” para mode inference: sync, SDDwork, explorer, implementer, designer.

---
Fuente: lectura de `cortex/session/service.py`. No se usó documentación previa.
