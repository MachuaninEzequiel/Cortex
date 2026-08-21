# Revisión: `cortex/autopilot` + `cortex/ci`

Revisor: rev-autopilot-ci (subagente). Solo lectura; no se modificó nada del repo.
Alcance: 20 archivos, ~3.142 líneas. Verificación: `uv run pytest tests/unit/autopilot tests/unit/ci` → **169 tests, todos pasan**.

---

## 1. Propósito y arquitectura

### cortex.autopilot — capa de política + hooks sobre la primitiva Session

Tras el refactor "Phase 03 / Pluggable Middle", autopilot ya NO implementa su propio ciclo de vida: es un **orquestador delgado** que aplica una política declarativa (`AutopilotPolicy`, dataclass congelada) sobre el ciclo de vida canónico de `cortex.session.service.SessionService`.

Módulos y responsabilidades:

| Módulo | Responsabilidad |
|---|---|
| `service.py` (444) | `AutopilotService`: start (adopta sesión activa), preflight (dry-run de detectores), checkpoint, finish (manual o vía documenter), status. Factory `from_project_root`. |
| `policies.py` (373) | Vocabulario de decisión: `AutopilotMode` (observe/assist/autopilot), `EnforcementSeverity/Result`, `AutopilotPolicy` (+validación `__post_init__`, `from_config`), `PolicyEnforcer` con hooks `on_session_open` / `on_checkpoint` / `on_pre_close`. |
| `detectors/base.py` | Protocolo `AutopilotDetector` + `resolve_detectors`: pipeline de clasificación de tarea con reglas de precedencia (seguridad > ambiguo > mayor confianza, tie-break conservador). |
| `detectors/default.py` | 6 detectores heurísticos por keywords/extensiones: CodeChange, DocsOnly, QuestionOnly, SecuritySensitive, LargeRefactor, Noop. |
| `detectors/ambiguous.py` | Detector de requests vagos (<8 palabras + verbo vago + sin referencia a archivo). |
| `lifecycle.py` | Modelos Pydantic request/result para cada operación (`Autopilot*Request/Result`). |
| `models.py` | Vocabulario del decision-layer: `DetectionRequest/Result`; `PolicyDecision` queda solo "para tests legacy". |
| `config.py` | Lee `.cortex/workspace-root/autopilot.yaml` → `AutopilotConfig` (pydantic, defaults seguros). |
| `cli.py` (354) | Typer subapp `cortex autopilot {start,preflight,checkpoint,finish,status,doctor}`; install/uninstall eliminados en Fase 04 (delegan en `cortex session hooks`). |
| `mcp_tools.py` | `AutopilotMCPTools`: adaptadores MCP (`cortex_autopilot_{start,preflight,checkpoint,finish,status}`) que devuelven strings legibles. |
| `doctor.py` | Diagnóstico read-only: config, sessions_dir escribible, adapters conocidos, hooks instalados, última sesión, construcción del servicio. |

### cortex.ci — validación provider-agnóstica de PRs contra Session + spec (Phase 07)

Paquete de lógica pura (la CLI vive en `cortex/cli/ci.py`, fuera del scope):

| Módulo | Responsabilidad |
|---|---|
| `validator.py` (265) | `CiValidator.validate`: orquesta matcher → spec loader → scope cross-check → verification hooks → `ValidationResult` con status pass/warn/blocked y exit codes 0/1/2/3. |
| `session_matcher.py` | Resuelve la sesión dueña del PR: explícito > base_commit > head_branch > none. |
| `diff_io.py` | Resuelve el texto del diff: `--diff file` > `git diff base..head` > auto-detección de trunk (main/master). |
| `result.py` | Dataclasses congelados `ValidationInput`, `ScopeDriftFinding`, `ValidationResult` (+ `to_json_dict` schema estable). |
| `markdown_formatter.py` | `render_pr_comment`: comentario Markdown para PR, delimitado por sentinela `<!-- cortex-pr-summary -->`. |
| `review_session.py` | Helpers Level 3: sesiones de revisión audit-only abiertas por CI (`CI_BOT`), sin robar el puntero active, cerradas sin documenter. |

## 2. Flujo de datos / entradas y salidas

**Quién llama a autopilot:**
- CLI: `cortex/cli/main.py:142-144` registra `autopilot_app`.
- MCP: `cortex/mcp/server.py:268-269, 764-819, 1488-1509` construye el servicio y expone las 5 tools.
- Doctor global: `cortex/doctor.py:368-415` usa `load_autopilot_config` + `AutopilotPolicy` para validar el yaml.
- Tests e2e: `tests/e2e/scenarios/test_autopilot_*.py`.

**A quién llama autopilot:** `cortex.workspace.layout.WorkspaceLayout`, `cortex.session.{service,storage,models,errors,git,verification,hooks}`, `cortex.core.AgentMemory` (lazy, solo en `finish(auto=True)`), `cortex.documenter.{reconstruction,persistence}`, `cortex.context_enricher` (solo documentalmente, vía `KNOWN_BUDGET_PROFILES`).

**Quién llama a cortex.ci:** únicamente `cortex/cli/ci.py` (`validate-pr` Level 1; `open-review-session` / `report-checkpoint` / `close-review-session` Level 3).

**A quién llama cortex.ci:** `cortex.session.storage.SessionStorage` (vía matcher), `cortex.documenter.reconstruction._scope_cross_check` (helper privado), `cortex.documenter.spec_loader.load_spec`, `cortex.session.verification.VerificationRunner`, `cortex.session.git.diff`.

## 3. Invariantes y decisiones de diseño

1. **SessionService es la única fuente de verdad**: los modelos de autopilot referencian `SessionRecord` canónico; los paralelos fueron borrados (ver docstrings de fase en `models.py`, `lifecycle.py`, `errors.py`). `errors.SessionNotFoundError` queda como alias deprecado (`errors.py:29`).
2. **Autopilot no abre sesiones**: `start()` solo adopta la activa (`service.py:126-141`); abrir es trabajo de `cortex create-spec`. `NoActiveSessionError` si no hay.
3. **El enforcer es stateless y puro** respecto de la política inmutable; devuelve listas de `EnforcementResult` y el llamador decide cómo agregarlas (`policies.py:60-70`). Todas las comparaciones horarias usan UTC aware (`policies.py:399-405`); `SessionRecord` rechaza datetimes naive (`session/models.py:131-135`).
4. **Modo ⇒ banderas derivadas**: OBSERVE apaga warnings, AUTOPILOT enciende `pre_commit_verification` (`from_config` policies.py:238-258; `_policy_with_mode` service.py:407-420). La coherencia se fuerza al reconstruir la política, no se guarda estado extra.
5. **Bloqueo único fuerte**: en AUTOPILOT, cerrar sin ningún checkpoint con verified_claims → BLOCK (`policies.py:366-382`). Todo lo demás son WARN.
6. **Detección = función pura** de (user_request, changed_files); no consulta estado de sesión (`models.py:33-41`).
7. **CI nunca promueve la review-session a active** y captura `base_commit` explícito en vez de HEAD del checkout (`review_session.py:39-61`) — decisión deliberada documentada en línea.
8. **Exit code como gate**: 0/1/2/3 mapean pass/warn/blocked/error (`validator.py:27-30`), consumido por la CLI con `raise typer.Exit(result.exit_code)`.
9. **JSON estable**: `ValidationResult.to_json_dict()` es contrato para workflows/dashboards (`result.py:71-113`); el formatter de Markdown opera sobre el mismo objeto.

## 4. Bugs potenciales y riesgos (con evidencia)

1. **Falsos positivos por substring matching en seguridad** — `SecuritySensitiveDetector.SECURITY_FILES` con `"key"`, `"token"`, `"role"`, `"hash"`, `"salt"` y chequeo `kw in f_lower` (`detectors/default.py:170-186`): `keyboard.ts`, `monkeypatch.py`, `tokenizer.py`, `dashboard.py` disparan task_type=security con confidence 0.8, que **gana siempre** por la regla de override (`detectors/base.py:80-82`). Mismo patrón en keywords del request ("hash" está dentro de "smashed"). En un futuro uso real del preflight esto bloquearía/ruta mal tareas inocentes.
2. **Excepciones de detectores tragadas en silencio** — `resolve_detectors` hace `except Exception: continue` sin log (`detectors/base.py:40-42`). Un detector roto se ve idéntico a uno que no opina; imposible diagnosticar.
3. **Matcher CI sensible al orden y colisiones** — `find_session_for_pr` devuelve el **primer** record cuyo `start_commit == base_commit` o `start_branch == head_branch` (`session_matcher.py:34-43`); el orden viene de `storage.list_all()` sin criterio. Dos ramas/PRs desde el mismo base, o rebases, producen matches arbitrarios. Además el match `by_branch` ignora si la sesión ya está CLOSED de un PR anterior.
4. **`except Exception` en explicit-id** — `session_matcher.py:30-31` convierte *cualquier* error (JSON corrupto, permisos) en `("none")`, enmascarando fallos reales como "no hay sesión".
5. **Acceso a privados entre módulos (3 sitios)**:
   - `validator.py:48`: `self._sessions._storage` (reconocido con noqa).
   - `review_session.py:53,60`: `service._make_unique_session_id` + `service._storage.save_new` para bypass del puntero active.
   - `service.py:374-376`: `memory._note_service` y `memory._vault_path_resolved` para armar el `DocumenterPersister`.
   Cualquier renombre interno de Session/AgentMemory rompe CI y el flujo finish(auto=True).
6. **Import cruzado de helper privado** — `validator.py:14` importa `_scope_cross_check` de `cortex.documenter.reconstruction`. Debería ser público o vivir en un módulo compartido.
7. **EXIT_ERROR/"error" inalcanzable en el validator** — `EXIT_ERROR=3` y el Literal `"error"` (`validator.py:30`, `result.py:16`) jamás se asignan dentro de `validate()`; cualquier excepción interna sube como traceback sin result. El código 3 solo lo produce la CLI ante `DiffResolutionError`. Un consumidor del JSON no verá nunca status="error".
8. **Parser de diff con huecos** — `_parse_files_from_diff` (`validator.py:196-220`) solo mira prefijos `+++ b/` y `--- a/`: diffs binarios ("Binary files ... differ"), renames puros (sin ---/+++ cuando similarity 100%), y paths quoteados (`"\303\251.py"`) no se detectan → scope-drift silencioso. El manejo de `--- a/` añade el path antes de saber si hay `+++ b/` correspondiente (funciona por dedupe posterior, pero contradice su propio comentario).
9. **Mutación de estado en `start()`** — `service.py:134-137` reemplaza `self._policy` y `self._enforcer` permanentemente cuando el request trae modo: una llamada `start(mode="observe")` baja las banderas para todas las operaciones siguientes del mismo servicio (el MCP server comparte una instancia global, `mcp/server.py:268`). Además descarta flags custom que el policy original tuviera (p.ej. `pre_commit_verification=True` construido a mano).
10. **`_looks_security_sensitive` duplicado** — la keyword-set de seguridad existe dos veces: `_SECURITY_KEYWORDS` en `policies.py:88-107` y `SECURITY_FILES/SECURITY_KEYWORDS` en `SecuritySensitiveDetector` (`default.py:160-190`). Ya divergen (uno tiene "auth", el otro también "vulnerability"/"csrf"...). Cambiar uno no cambia el otro.
11. **Config tolerante a typos de clave** — `AutopilotConfig(**raw)` con pydantic default `extra="ignore"` (`config.py:17`): `auto_checkpoint_filez: 10` en el yaml se ignora en silencio; doctor solo reporta el typo de `mode` (`cortex/doctor.py:409-415`), no de claves ni perfiles (el perfil cae a default silenciosamente, `policies.py:246-250`).
12. **CLI sin catch-all** — `cli.py` solo captura `NoActiveSessionError`/`AutopilotError`; errores del documenter, storage o git en `finish --auto` llegan al usuario como traceback Python crudo.
13. **Doctor marca ok=False si no hay hooks instalados** — `doctor.py:96-105`: una instalación fresca sin IDE hooks reporta `report.ok=False` y aparece en `warnings`, mezclando "informativo" con "roto".
14. **Warning temporal puede ser confuso** — `on_checkpoint` compara `datetime.now(UTC)` contra el timestamp del checkpoint anterior (`policies.py:352-365`): en sesiones retomadas tras horas, el primer checkpoint nuevo siempre advierte "X minutes since previous checkpoint" aunque el usuario recién vuelva a trabajar. Cosmético pero ruidoso.
15. **Lookup de hook por nombre** — `validator.py:118-124` busca el `required` original por nombre del hook; specs con nombres duplicados resuelven al primero. Menor, pero el comment admite que `VerificationHookResult` perdió el flag (deuda de modelo).

## 5. Código muerto, duplicación y deuda

- **`PolicyDecision`** (`models.py:63-77`): declarado "legacy preservado para tests"; solo lo usan sus tests. Candidato a borrado junto con `test_models.py`.
- **`DetectionRequest.git_diff_stat`** (`models.py:39`): se propaga en `service.preflight` (`service.py:200`) pero **ningún detector lo lee**; la CLI además no tiene opción para pasarlo. Campo muerto end-to-end.
- **`DetectionRequest.session_state: Any`** (`models.py:42`): bolsa libre sin consumidores en los detectores builtin.
- **`lifecycle.py:139-140`**: hack `_ = SessionStatus` para silenciar unused-import — señal de que el re-export debería hacerse explícito o quitarse.
- **`AmbiguousRequestDetector.FILE_EXTS` sin punto** ("py","ts") vs `CodeChangeDetector.CODE_EXTS` con punto (".py"): convenciones inconsistentes para el mismo problema (`ambiguous.py:31` vs `default.py:20`).
- **Duplicación scope-drift**: la lógica fuera-de-scope existe tres veces con semántica distinta: `PolicyEnforcer.on_checkpoint` (comparación naive de sets, `policies.py:333-342`), `_scope_cross_check` (documenter), y el consumo que hace ci/validator. Consolidar en un único helper público.
- **Duplicación trunk-detection/git**: `diff_io._detect_trunk` usa `subprocess.run` directo (`diff_io.py:73-84`) mientras el resto del módulo usa `cortex.session.git`; ese wrapper debería ofrecer `branch_exists`.
- **CLI preflight no expone `--diff-stat`** ni el MCP tool aprovecha `git_diff_stat`: la parte "archivos cambiados" del pipeline es inalcanzable desde los puntos de entrada reales salvo tests.
- **Deuda de fases**: abundantes comentarios "Phase 03/04/T3.x" que ya vencieron (p.ej. `doctor.py` módulo entero autodenominado stub hasta T3.12; `cli.py:56-58` referencia T3.6). Vale hacer una pasada de limpieza narrativa.

## 6. Preparación para un cambio grande — qué tocaría primero

Frágil (orden de fragilidad):
1. **Los accesos a privados** (§4.5): son las 3 líneas más probables de romperse ante cualquier refactor de session/core. Exponer APIs públicas mínimas: `SessionService.create_detached(...)`, `AgentMemory.note_service` property, y publicar `_scope_cross_check`.
2. **`start()` mutando la política del servicio** (§4.9): con instancias long-lived (MCP server) es un bug de comportamiento latente. Hacer la política efectiva inmutable por operación.
3. **Heurísticas de detectores** (§4.1): todo el valor del preflight depende de estas regex/keywords; hoy generan security-false-positivos que ganan por diseño del resolver. Antes de exponer preflight a usuarios reales, word-boundary matching + tests de FP.
4. **Matcher de CI** (§4.3/4.4): desempatar por `opened_at` más reciente y distinguir sesiones ya cerradas; sino el Level 1 va a validar el PR contra la sesión equivocada.

Sólido y no tocar:
- El núcleo `PolicyEnforcer` + `AutopilotPolicy` está bien testeado (`test_policy_consolidated.py`), es stateless y puro: base firme.
- `ValidationResult.to_json_dict` y el markdown formatter son simples, deterministas y cubiertos.
- `diff_io` es pequeño y correcto para diffs de texto normales.

Plan sugerido de primera oleada (1 PR chico c/u):
(a) logging en `resolve_detectors`; (b) públicas las 3 fronteras privadas; (c) `start()` sin mutación; (d) matcher con desempate determinista; (e) borrar PolicyDecision/git_diff_stat/session_state muertos.

## 7. Salud general

**Buena (7/10).** Arquitectura post-refactor coherente: autopilot es genuinamente delgado, los contratos request/result están tipados, hay 169 tests unitarios verdes y separación clara lógica-pura vs CLI. Los riesgos concentrados son acoples a privados, heurística de detectores con FPs estructurales, y determinismo del matcher de CI — todos localizados y baratos de corregir antes de crecer el subsistema.
