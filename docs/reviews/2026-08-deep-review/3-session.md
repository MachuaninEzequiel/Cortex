# Review — Subsistema `cortex/session` (+ `cortex/services/session_service.py`)

Revisor: rev-session. Solo lectura. Alcance: `cortex/session/**` y `cortex/services/session_service.py`.

---

## 1. Propósito y arquitectura interna

El paquete `cortex.session` implementa la **primitiva Session** de la arquitectura "Pluggable Middle": una unidad de desarrollo que se abre cuando `cortex-sync` persiste un spec y se cierra con `cortex finish-session`, acumulando checkpoints (log append-only de actividad de agentes/hooks), resultados de hooks de verificación, tareas granulares y el snapshot git del repo.

### Módulos

| Módulo | Responsabilidad |
|---|---|
| `models.py` (459 l) | Modelos Pydantic: `SessionRecord` (raíz), `Checkpoint` (frozen), `VerificationHook`/`VerificationHookResult` (frozen), `Task`; enums `SessionStatus`, `SessionMode`, `CheckpointSource`, `TaskStatus`. Enforcea invariantes de ciclo de vida a nivel validación. |
| `errors.py` (52 l) | Jerarquía plana bajo `SessionError`: `SessionNotFound`, `SessionAlreadyExists`, `InvalidStateTransition`, `SessionStorageCorrupted`, `NoActiveSession`. |
| `storage.py` (297 l) | Persistencia YAML en `.cortex/sessions/<id>.yaml` + puntero `active.txt`. Escritura atómica (tmp + fsync + `os.replace` con retry ante errores transitorios de Windows/AV) y locks por-path para concurrencia del ThreadPoolExecutor del MCP server. |
| `git.py` (145 l) | Wrappers subprocess de git con timeout 10s (`_GIT_SUBPROCESS_TIMEOUT_SECONDS`, git.py:29). Variantes estrictas (`get_head_commit`) y soft (`try_*`). `is_git_repo` usa `rev-parse --is-inside-work-tree`. |
| `service.py` (456 l) | `SessionService`: API pública. Ciclo de vida (open/checkpoint/close/abandon), tareas (`add_task`, `update_task_status`, `list_tasks`), diff, `infer_mode`, id-únicos con sufijo `-2/-3`, y escritura best-effort de `.cortex/session.lock` para extensiones IDE externas (`cortex-net.ts`). |
| `verification.py` (155 l) | `VerificationRunner`: ejecuta comandos de verificación declarados en specs con `shell=True`, cwd=repo_root, timeout por hook; nunca levanta por fallo del hook (capturado como resultado `passed=False`, exit_code=-1 en timeout). |
| `quality_gates.py` (195 l) | `review_checkpoint`: revisión pura de 2 etapas de checkpoints de subagentes (compliance con spec + calidad). Devuelve `ReviewVerdict` con acción `accept/redelegate/warn`. Expuesto como tool MCP `cortex_review_checkpoint`. |
| `proposal.py` (182 l) | Modelos puros `Proposal`/`Alternative` + `format_proposal_card` (tarjeta Markdown). Sin I/O; consumida por MCP tool `cortex_emit_proposal` y usada para anclar el gate temporal `required → create_spec`. |
| `hooks/installer.py` (183 l) | Protocolo `HookAdapter` + `HookInstaller` (registry/dispatcher) + `default_installer()` con import lazy de adapters. |
| `hooks/adapters/*` | 4 adaptadores IDE: `claude_code` (.claude/settings.json PostToolUse con marker `_cortex_managed`), `cursor` (git post-commit con sentinel markers — no es Cursor-específico), `opencode` (.opencode/hooks.md), `pi` (recetas justfile). Todos con install/uninstall/status idempotentes y `|| true` anti-bloqueo. |
| `services/session_service.py` (32 l) | **Alias deprecado**: re-exporta `NoteService` como `SessionService` legacy, emite `DeprecationWarning` al importar. |

## 2. Flujo de datos y puntos de entrada/salida

**Entradas (quiénes llaman):**
- `cortex/core.py:60-61,282,629` — `CortexController` crea `SessionService` y expone `checkpoint()`.
- `cortex/mcp/server.py` — tools `cortex_emit_proposal` (usa `format_proposal_card`, server.py:1937), `cortex_review_checkpoint` (usa `quality_gates.review_checkpoint`, server.py:2433); el flujo autopilot llega vía `cortex/autopilot/service.py:71-72`.
- `cortex/cli/session.py`, `cortex/cli/session_tui.py`, `cortex/cli/ci.py`, `cortex/cli/main.py` — CLI.
- `cortex/documenter/reconstruction.py` + `persistence.py` — corren `VerificationRunner`, leen `is_gitless`, reconstruyen la nota.
- `cortex/ci/*` (validator, review_session, session_matcher) y `cortex/autopilot/*` — consumen storage/service/models.
- Extensiones IDE externas leen `<repo>/.cortex/session.lock` sin pasar por MCP (service.py:_write_session_lock).

**Salidas (a quién llama / qué produce):**
- Archivos: `.cortex/sessions/<session_id>.yaml`, `active.txt`, `.cortex/session.lock`, y artefactos IDE (`.claude/settings.json`, `.git/hooks/post-commit`, `.opencode/hooks.md`, `justfile`).
- Git: subprocesses (`rev-parse`, `diff --name-status`) contra `repo_root`.

## 3. Invariantes y decisiones de diseño importantes

1. **Ciclo de vida estricto en el modelo** (models.py:_validate_status_invariants): OPEN ⇒ `closed_at/end_commit/documenter_decision` todos None; terminal ⇒ los tres no-None. El service muta vía `model_dump → update → model_validate` (service.py close) para que el validator corra sobre el estado final, no mid-mutation.
2. **Gitless mode por sentinel**: `GITLESS_COMMIT_PLACEHOLDER` = 40 ceros (models.py:47) pasa la regex de SHA pero nunca coincide con commit real. `is_gitless` (models.py, property) hace branch al documenter/close/diff. Consumidores DEBEN comparar contra la constante, no heurísticas.
3. **Idempotencia de `open()`** (service.py:~190): si existe sesión OPEN con el mismo id se devuelve la existente en vez de crear `-2` — mitiga reintentos duplicados del cliente MCP (incidente appfutbol 2026-05-22, referenciado en storage.py, quality_gates.py y proposal.py).
4. **Checkpoints inmutables, sesiones mutables**: `Checkpoint`/`VerificationHookResult` frozen; `SessionRecord` mutable con `validate_assignment`. Append-only durante OPEN.
5. **Escritura atómica + locks por path** (storage.py:_path_lock/_atomic_replace): serializa escritores concurrentes del mismo archivo; retry exponencial ante winerror 5/32 y errno 13/16.
6. **Verificación "never raises"** por fallo de hook; infraestructura rota sí propaga. `shell=True` asumido seguro porque el spec lo controla el usuario.
7. **Hooks IDE son best-effort**: todo comando termina en `>/dev/null 2>&1 || true`; instalar/desinstalar jamás bloquea el workflow del usuario.
8. **Mode inference pura** (service.py:infer_mode): sin checkpoints→BYO; solo CI_BOT→CI_REVIEW; subset de fuentes Cortex→MANAGED; resto→OBSERVED.
9. **Quality gates sin I/O**, con wildcard de scope vacío y whitelist de artefactos de proceso (`.cortex/vault/...`) para no penalizar checkpoints Deep Track.

## 4. Bugs potenciales y riesgos (con file:line)

1. **Lost-update en read-modify-write concurrente** — service.py:`checkpoint()` (~línea 265-285) y `add_task`/`update_task_status`: hacen `load → mutar lista in-place → save`. El lock de storage.py solo serializa el *write* final, no el ciclo load-mutate-save. Dos workers del ThreadPoolExecutor del MCP server haciendo checkpoint simultáneo: ambos cargan la misma versión, cada uno agrega su checkpoint, el segundo `save` pisa al primero → **se pierde un checkpoint silenciosamente**. Es exactamente el escenario de doble-dispatch documentado en storage.py (docstring de módulo). Riesgo alto dado que el incidente ya ocurrió antes.
2. **TOCTOU en `open()` y `save_new`** — service.py:open (~190-215) chequea `exists`/carga existente fuera de lock; `_make_unique_session_id` (service.py:~445) hace check-then-act. Dos opens paralelos del mismo spec pueden ambos elegir `base-2` y uno recibe `SessionAlreadyExists` crudo (no traducido a retry ni a devolver la existente). Baja probabilidad, pero rompe la promesa de idempotencia.
3. **`close()` puede quedar imposible** — service.py:close (~300): si la sesión NO es gitless y git se rompe después del open (repo borrado, index.lock pegado, timeout), `git.get_head_commit` lanza `GitError` y la sesión **no se puede cerrar ni abandonar** (abandon llama a close). No hay path degradado simétrico al del open. Riesgo real: el comentario de git.py:25-28 documenta que estos stalls pasan en producción.
4. **`CORTEX_CODE_DESIGNER` ausente de `_CORTEX_SOURCES`** — service.py:57-64 vs models.py:CheckpointSource: un checkpoint del designer hace que la sesión se infiera OBSERVED en vez de MANAGED. Parece omisión (el designer es un agente Cortex de primera clase según ide/adapters). Afecta clasificación de notas del documenter.
5. **`update_task_status`: docstring vs código** — service.py:update_task_status (~370): el docstring dice "terminal statuses stamp completed_at", pero solo se estampa para DONE; SKIPPED/BLOCKED quedan con completed_at None. El modelo lo permite, así que no explota, pero la semántica temporal queda inconsistente y el documenter pierde timings.
6. **`checkpoint_index` sin validar límites** — service.py:update_task_status acepta cualquier índice ≥0; puede apuntar fuera de `record.checkpoints` (dangling reference para el documenter).
7. **Whitelist de proceso demasiado laxa** — quality_gates.py:_is_process_artifact (~135): match por prefijo plano. Un artifact como `.cortex/vault/designs/../../../src/secrets.py` o `.cortex/vault/sessions-backup/x` pasa como "artefacto de proceso" y bypasea Stage 1. Además `Path(path).as_posix().lstrip("./")` (quality_gates.py:139) usa `lstrip` por caracteres: `..` inicial se come igual (no grave aquí, pero frágil).
8. **Stage 2 débil** — quality_gates.py:_stage_2_quality: el requisito de claim >10 chars aplica a *cualquier* verified_claim, no solo al que menciona tests; un claim largo irrelevante satisface el gate aunque `"tests ok"` sea la única evidencia de test. Placeholder scan limitado a `note` (documentado, pero fácil de evadir poniendo TBD en claims).
9. **`session.lock` sin atomicidad** — service.py:_write_session_lock (~100): `write_bytes` directo, sin tmp+replace ni lock, mientras storage.py hace todo lo posible por atomicidad. Lectores externos (`cortex-net.ts`) pueden leer archivos a medio escribir. Mitigado: es best-effort por diseño y el formato es una línea corta.
10. **Timeout con shell=True mata el shell, no los hijos** — verification.py:run_hook: `subprocess.run(..., timeout=...)` con `shell=True` mata el shell pero procesos nietos (p.ej. test runner lanzado desde script) pueden quedar huérfanos consumiendo CPU. Caveat conocido de Python; no hay process-group kill.
11. **Adapters cursor: chequeo `.git` literal** — hooks/adapters/cursor.py:_require_git_repo: falla en worktrees/submodules donde `.git` es archivo, contradiciendo el criterio correcto de git.py:is_git_repo. También: `install` levanta ValueError (contrato lo permite), pero `uninstall`/`status` no requieren repo — asimetría menor.
12. **claude_code adapter: uninstall no tolera settings corruptos** — claude_code.py:install/uninstall llaman `_load` que lanza ValueError ante JSON inválido; solo `status` lo captura. Un settings.json corrupto bloquea desinstalar.
13. **Código muerto**: `NoActiveSession` (errors.py) está definida y exportada en `__init__.py` pero **nunca se levanta** en todo el paquete (la usada es `autopilot.errors.NoActiveSessionError`, distinta). Solo aparece en tests/unit/session/test_errors.py.
14. **Alias deprecado con warning en import-time** — services/session_service.py:19: `warnings.warn` a nivel módulo dispara al importar aunque no se use nada; rompe herramientas que traten DeprecationWarning como error y penaliza imports transitivos. Mejor lazy o `__getattr__` PEP 562.
15. **Tmp files huérfanos** — storage.py: si el proceso muere entre `open(tmp)` y replace, queda `<id>.yaml.tmp` para siempre; no hay GC. Menor, pero ensucia el dir de sesiones (y `list_all` glob solo `*.yaml`, así que no rompe listado).
16. **Duplicación masiva en adapters** — cursor.py/opencode.py/pi.py repiten byte-a-byte `_read`, `_render`, `_strip_block`, y el esqueleto completo de install/uninstall/status (≈80 líneas × 3). Sólo cambian path, marcadores y bloque. Refactor obvio: clase base `SentinelBlockAdapter`.
17. **`run_at` capturado antes de ejecutar** — verification.py:run_hook toma `datetime.now(UTC)` antes del subprocess; el timestamp representa "inicio" no "fin"; trivial pero conviene documentarlo.
18. **`list_all` re-valida todo** — storage.py:list_all carga y valida cada YAML completo por listing; O(n·validación). OK para decenas de sesiones, degradará con cientos+ (TUI y CI lo llaman seguido).

## 5. Deudas y oportunidades de refactor

- **Locking transaccional**: extraer un helper `mutate(session_id, fn)` en storage/service que tome el lock por-path alrededor de load→mutate→save eliminaría los bugs 1-2 de un tirón.
- **Base class para adapters sentinel-block** (ver 16) reduciría ~240 líneas duplicadas a una.
- **Unificar detección de repo** entre cursor adapter y git.py.
- `infer_mode` y `_CORTEX_SOURCES` deberían derivar del enum (excluir CI_BOT/IDE_HOOK/USER_SKILL/MANUAL) en vez de hardcodear una frozenset que ya se quedó desactualizada.
- `services/session_service.py` debería migrarse a lazy-deprecation (PEP 562) o eliminarse si no quedan consumidores.
- Tests: cobertura unitaria buena por módulo (tests/unit/session/: test_models, test_storage, test_service, test_tasks, test_quality_gates, test_verification, test_git, hooks/), pero no vi tests de concurrencia para el lost-update.

## 6. Preparación para un cambio grande — qué tocaría primero, qué es frágil

1. **Primero**: arreglar el locking de read-modify-write (bug 1) — cualquier feature nueva que toque checkpoints/tareas hereda el race. Es cambio local (storage.py + service.py) y bien testeable.
2. **Segundo**: deduplicar adapters con clase base ANTES de agregar más IDEs; hoy cada nuevo adapter copia ~150 líneas.
3. **Tercero**: decidir el fate de `CORTEX_CODE_DESIGNER` en `_CORTEX_SOURCES` y de `NoActiveSession` (borrar o usar) — barato ahora, caro después de refactor del service.
4. **Frágil**: el patrón `model_dump → dict.update → model_validate` en `close()`/`update_task_status` es correcto pero delicado — cualquier campo nuevo de close-time debe sumarse al dict.update manualmente o el invariant validator lo rechaza en runtime con mensajes crípticos.
5. **Frágil**: `GITLESS_COMMIT_PLACEHOLDER` como centinela dentro de un campo tipado SHA — funciona pero obliga a TODA feature nueva que toque commits a conocer el centinela (docstring de models.py:40-46 lo admite). Un campo `git_available: bool` explícito sería más robusto, pero implica migración de YAMLs existentes.
6. **Frágil**: contratos implícitos con afuera: formato de `.cortex/session.lock` (consumido por cortex-net.ts con trim), marcadores sentinel en justfile/post-commit/hooks.md (los usuarios pueden romperlos editando), y el header fijo de la proposal card (parseado visualmente por MCP clients).

### Salud general
**Buena (7/10).** Arquitectura clara, separación pura/I/O ejemplar (proposal, quality_gates, verification sin dependencias), invariantes fuertes en modelos, manejo defensivo de concurrencia y Windows en storage, y decisiones documentadas con referencias a incidentes reales. Los puntos en contra son el race de lost-update en checkpoint/tasks, el cierre imposible ante fallo tardío de git, y ~250 líneas de duplicación en adapters. Nada es bloqueante para un cambio grande, pero el locking y la dedup deberían ir primero.
