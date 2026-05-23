# Autopilot Module Audit — Fase 03 (internal work note)

> **Status:** Auditoría completada para T3.1. Es la base sobre la cual se
> ejecutan T3.2 a T3.13.
>
> **Audiencia:** El agente que ejecute Fase 03. NO es documentación pública.
> NO va en `docs/autopilot/` (eso es user-facing).
>
> **Fuente:** lectura completa de `cortex/autopilot/**` y de los consumers
> externos (`cortex/cli/main.py`, `cortex/mcp/server.py`,
> `tests/unit/test_tripartita_refinada.py`, `cortex/session/service.py`,
> `cortex/session/models.py`).
>
> **Baseline tests:** 1811 passed, 6 skipped, 4 failures preexistentes
> (las 3 de `_subprocess.py:140` y la de symlink en Windows). Confirmadas
> antes de iniciar el refactor.

---

## 0. Resumen ejecutivo

`cortex/autopilot/` hoy es un **submódulo paralelo** con su propia primitiva
de sesión (`AutopilotSessionState` + `StateStore`), su propia persistencia
(`session_writer.py` + `session_builder.py`) y su propio set de adapters
IDE (`adapters/*.py`).

La Fase 03 lo convierte en una **capa fina de políticas + hooks** que
delega a la primitiva canónica `cortex/session/` (Fase 00) y a la
reconstrucción `cortex/documenter/` (Fase 01).

**Lo que se mantiene (por UX continuity y consumers externos):**
- El subapp Typer `cortex/autopilot/cli.py` (importado por `cortex/cli/main.py:142`).
- Las 5 MCP tools `cortex_autopilot_*` en `cortex/autopilot/mcp_tools.py` (importadas por `cortex/mcp/server.py:18-19`).
- La clase `AutopilotService` como entry point (mismo nombre, mismo método público — *signatures cambian de forma controlada*, ver §3).
- Los 5 adapters IDE (relocados, no eliminados — ver §5).

**Lo que se elimina:**
- `cortex/autopilot/state_store.py` (99 LOC) — duplica `cortex/session/storage.py`.
- `cortex/autopilot/session_builder.py` (103 LOC) — duplica `cortex/documenter/reconstruction.py` + renderers.
- `cortex/autopilot/session_writer.py` (226 LOC) — duplica `cortex/documenter/persistence.py` + `NoteService`.
- `cortex/autopilot/models.py` colapsa: `AutopilotCheckpoint`/`AutopilotSessionState`/`SessionDraft` se reemplazan por `cortex.session.Checkpoint` / `SessionRecord`. Sobreviven sólo modelos de **decisión de política** (`DetectionResult`, `PolicyDecision`, etc.).
- `cortex/autopilot/lifecycle.py` (61 LOC) colapsa: request/result models se simplifican porque el state es ahora `SessionRecord`.
- `cortex/autopilot/renderers/*` (245 LOC, 5 archivos) — el documenter ya tiene su propio renderer canónico vía templates Jinja2; los Autopilot renderers eran un "session note generator paralelo".
- `cortex/autopilot/context.py` + `context_budget.py` + `budget_profiles.py` (186 LOC) — se preservan PARCIALMENTE (sólo la idea de "budget profile" como configuración); la lógica de inyección de contexto AgentMemory.enrich() vive en `cortex/context_enricher/` (Fase 04 evalúa fusión).

**Total LOC removed conservadoramente:** ~1100 / 3500 = ~31% del módulo
desaparece. El resto se reescribe como wrapper delgado o se reubica.

---

## 1. Estado actual del módulo

**40 archivos Python, ~3500 LOC, 19 archivos de tests unitarios (~2700 LOC),
3 escenarios E2E.**

### Estructura

```
cortex/autopilot/
├── __init__.py            (6 LOC, vacío)
├── service.py             (455 LOC, AutopilotService — la fachada)
├── lifecycle.py           (61 LOC, request/result Pydantic models)
├── models.py              (97 LOC, domain models)
├── state_store.py         (99 LOC, persistencia JSON en run/autopilot/)
├── session_builder.py     (103 LOC, ensambla SessionDraft + self-review)
├── session_writer.py      (226 LOC, escribe + indexa session notes)
├── mcp_tools.py           (167 LOC, 5 MCP tool wrappers)
├── cli.py                 (348 LOC, 8 Typer commands)
├── config.py              (50 LOC, AutopilotConfig YAML)
├── doctor.py              (273 LOC, 11 diagnostic checks)
├── reporting.py           (56 LOC, session reports)
├── packaging.py           (69 LOC, install/uninstall plugin helpers)
├── delegation.py          (123 LOC, two-stage review engine)
├── context.py             (95 LOC, AgentMemory.enrich wrapper)
├── context_budget.py      (30 LOC, budget profile constants)
├── budget_profiles.py     (61 LOC, runtime budget helpers)
├── registry.py            (32 LOC, generic registry skeleton)
├── errors.py              (8 LOC, AutopilotError + SessionNotFoundError + ConfigError)
│
├── policies/              (143 LOC total)
│   ├── base.py            (34 LOC, AutopilotPolicy Protocol + evaluate_policies)
│   ├── default.py         (69 LOC, Budget/Spec/Docs/HumanApproval policies)
│   └── auto_checkpoint.py (40 LOC, AutoCheckpointPolicy)
│
├── detectors/             (303 LOC total)
│   ├── base.py            (55 LOC, AutopilotDetector Protocol + resolution)
│   ├── default.py         (202 LOC, 5 detectors: Code/Docs/Question/Security/LargeRefactor + Noop)
│   └── ambiguous.py       (46 LOC, AmbiguousRequestDetector)
│
├── renderers/             (245 LOC total)
│   ├── base.py            (11 LOC, SessionRenderer Protocol)
│   ├── implementation.py  (91 LOC)
│   ├── docs_only.py       (52 LOC)
│   ├── minimal.py         (46 LOC)
│   └── fallback_draft.py  (45 LOC)
│
├── hooks/                 (93 LOC Python total + 2 shell wrappers)
│   ├── session_start.py   (49 LOC, emite payload SessionStart al harness IDE)
│   └── session_finish.py  (44 LOC, emite payload SessionFinish)
│
└── adapters/              (437 LOC total)
    ├── base.py            (95 LOC, AutopilotHookAdapter Protocol + utilidades de install)
    ├── claude_code.py     (36 LOC)
    ├── cursor.py          (35 LOC)
    ├── codex.py           (36 LOC)
    ├── opencode.py        (36 LOC)
    ├── pi.py              (139 LOC, más completo: extension TS + skill + settings.json merge)
    ├── platform_detect.py (29 LOC, Platform enum + detect_platform())
    └── registry.py        (31 LOC, get_adapter() / list_adapters())
```

### Persistencia actual

```
<workspace_root>/
└── run/
    └── autopilot/
        ├── sessions/
        │   └── <session_id>.json        (AutopilotSessionState como JSON)
        └── events/
            └── <session_id>.jsonl       (AutopilotEvent append-only)
```

Esto duplica la layer canónica:

```
<workspace_root>/
└── .cortex/
    └── sessions/
        ├── <session_id>.yaml            (SessionRecord como YAML)
        └── active.txt                   (pointer a la sesión activa)
```

---

## 2. Inventario archivo por archivo

Leyenda de destino:

- **DELETE** — el archivo se elimina; su responsabilidad ya existe en la primitiva canónica.
- **REWRITE** — se conserva la ruta y la API pública; el body se reimplementa sobre Sessions.
- **RELOCATE** — el archivo se mueve a otra ruta (en general a `cortex/session/hooks/`).
- **KEEP** — sin cambios materiales (sólo posibles tweaks de imports).
- **MERGE** — fusionado con otro archivo / consolidado.
- **SHRINK** — sigue existiendo, pero pierde responsabilidades.

| Archivo | LOC | Responsabilidad actual | Destino Fase 03 | Notas |
|---|---:|---|---|---|
| `__init__.py` | 6 | Vacío | KEEP | Exporta nada hoy; tras fusion exporta `AutopilotService`, `AutopilotPolicy`, `AutopilotMode`. |
| `service.py` | 455 | `AutopilotService` con `start/preflight/checkpoint/finish/status/build_context/review_delegation` | REWRITE | Delega a `SessionService` + `PolicyEnforcer` + (para `finish --auto`) al `Reconstructor`/`DocumenterPersister` de Fase 01. Elimina el bloque de `_DEFAULT_DETECTORS`/`_DEFAULT_POLICIES` (ahora vive en `policies.py`). Mantiene `from_project_root` factory. |
| `lifecycle.py` | 61 | Pydantic Request/Result models para los métodos de `AutopilotService` | SHRINK | Conserva `Start/Checkpoint/Finish/Status` Request/Result pero referencia `SessionRecord` en lugar de `AutopilotSessionState`. `PreflightRequest/Result` desaparecen (preflight pasa a ser detail interno de `start` o se elimina — ver §11.1). |
| `models.py` | 97 | `AutopilotSessionState`, `AutopilotCheckpoint`, `AutopilotEvent`, `DetectionRequest/Result`, `PolicyDecision`, `SessionDraft`, `HookSessionStartOutput`, `DelegationResult` | SHRINK | **Eliminar:** `AutopilotSessionState`, `AutopilotCheckpoint`, `AutopilotEvent`, `SessionDraft`, `HookSessionStartOutput`. **Conservar:** `DetectionRequest`, `DetectionResult`, `PolicyDecision`, `DelegationResult`. **Reemplazos en consumers:** `AutopilotSessionState` → `SessionRecord`; `AutopilotCheckpoint` → `Checkpoint`. `AutopilotBudgetSnapshot` se mueve a `cortex/autopilot/budget_profiles.py` como dataclass interna. |
| `state_store.py` | 99 | Persistencia JSON + JSONL bajo `run/autopilot/` | **DELETE** | `SessionStorage` (Fase 00) ya provee `save/load/list_all/list_by_status/get_active_session_id`. Los `AutopilotEvent` JSONL no tienen consumidor real (`reporting.py` los muestra pero nadie acciona sobre ellos); se reemplazan por los `checkpoints` de `SessionRecord`. |
| `session_builder.py` | 103 | Selecciona renderer + ejecuta `self_review` con scan de placeholders/file consistency/evidence | **DELETE** | El `Reconstructor` de Fase 01 + el writer Jinja2 del documenter ya producen session notes de mayor calidad (con verification hooks + diff observable). El `self_review` con placeholder scanning era un workaround pre-Sessions; ahora innecesario. |
| `session_writer.py` | 226 | `SessionWriter` Protocol + `VaultSessionWriter` + `IndexingSessionWriter` (decorator que indexa en semantic + episodic) | **DELETE** | `cortex/documenter/persistence.py::DocumenterPersister` (Fase 01) ya hace exactamente esto: persistir + indexar vía `NoteService`. `IndexingSessionWriter` es el único bit valioso, pero su lógica de "rollback transaccional si indexing falla" debería **portarse** al `DocumenterPersister` si no está ya — *verificar al hacer T3.3*. |
| `mcp_tools.py` | 167 | 5 MCP tool wrappers (`start/preflight/checkpoint/finish/status`) | REWRITE | Mantener nombres exactos y schemas de output (consumers como Claude Code los ven). Body delega a la nueva `AutopilotService`. **`preflight`** queda sin operación real si se elimina del service — opciones: (a) keep como no-op con deprecation warning, (b) eliminar pero documentar el breaking change. Decisión: **opción (a)**, consistencia con `cortex_validate_handoff` deprecated. |
| `cli.py` | 348 | 8 Typer commands: `start preflight checkpoint finish status doctor report cleanup install uninstall` | REWRITE | Mantener los 8 commands. `preflight` → no-op con warning. `cleanup` → no-op (no hay JSONL events que rotar). `install/uninstall` → delegan a `cortex session hooks install/uninstall`. Resto delega a `AutopilotService`. |
| `config.py` | 50 | `AutopilotConfig` (YAML opcional en `<workspace_root>/autopilot.yaml`) | SHRINK | Mantener pero **eliminar** `auto_checkpoint_files`, `auto_checkpoint_minutes`, `max_event_jsonl_mb`, `event_rotation_days`, `ide_adapter`. Reducir a: `mode` (observe/assist/autopilot), `default_budget_profile`. Agregar: `hooks_enabled: list[str]` (lista de IDE adapters activos). |
| `doctor.py` | 273 | 11 diagnostic checks (config, run_dir, skills, hooks installed, adapters, mcp_tools, session_indexing, last_finish, budget_warnings, superpowers_conflict, jsonl_rotation) | REWRITE | Mantener pero adaptar: (a) `_check_run_dir` → `_check_sessions_dir` (apunta a `.cortex/sessions/`); (b) `_check_session_indexing` → ya no aplica porque ahora **siempre** persiste vía documenter; (c) `_check_jsonl_rotation` → DELETE (no hay JSONL); (d) `_check_last_finish` → valida `SessionRecord.status` en lugar de `AutopilotSessionState.status`; (e) **agregar** check de policy config. Este archivo se cruza con T3.12 (Doctor extensions). |
| `reporting.py` | 56 | `generate_report(last_n)` itera por `StateStore.list_sessions()` | REWRITE | Reemplazar `StateStore` → `SessionStorage.list_all()` ordenado por `opened_at` desc. Cambia el tipo de retorno (deja de incluir `chars_injected`/`items_retrieved` porque los `budget` ya no se trackean por sesión salvo via política). Posiblemente innecesario — re-evaluar si vale la pena mantener o si `cortex session list` cubre la necesidad. |
| `packaging.py` | 69 | `install_plugin(project_root, adapter_name)` + `uninstall_plugin` + `PluginManifest` | DELETE | El install ahora vive en `cortex/session/hooks/installer.py` (T3.6) usando `HookInstaller`. `PluginManifest` no tiene consumidores reales (la búsqueda de `list_compatible_plugins` recorre `.*-plugin/` que no existe en el repo). |
| `delegation.py` | 123 | `DelegationEngine.review(result, state)` con stage-1 (spec compliance) + stage-2 (quality) | KEEP | Lógica pura, no toca persistencia. Reemplazar `state: AutopilotSessionState` → `state: SessionRecord`. **Re-evaluar** si Fase 03 lo necesita realmente — `review_delegation` en `service.py` lo invoca pero ningún consumer actual lo dispara desde CLI/MCP. Opción: marcar `delegation.py` como "deferred to Fase 04" y dejar el método del service comentado. |
| `context.py` | 95 | `fetch_context(state, memory)` envuelve `AgentMemory.enrich()` aplicando budget profile | DELETE (recomendado) | Vive en `cortex.context_enricher` ya. El método `AutopilotService.build_context` no tiene consumer actual (CLI no lo expone, MCP tampoco). **Decisión:** marcar como removed; si Fase 04 quiere re-introducir budget-aware context, lo hace allí. |
| `context_budget.py` | 30 | `BUDGET_PROFILES` dict + `get_budget_profile()` + `profile_for_task_type()` | KEEP | Los profiles siguen siendo útiles para `AutopilotPolicy` (max chars/items por tipo de task). Si se elimina `context.py`, este archivo queda como **mero data**. Considerar mover los profiles a `policies.py`. |
| `budget_profiles.py` | 61 | `apply_budget(enriched, profile_name)` y `profile_for_state(state)` | DELETE | Acoplado a `context.py` y `AutopilotBudgetSnapshot`. Si `context.py` desaparece, este también. |
| `registry.py` | 32 | `Registry[T]` genérico + aliases vacíos | DELETE | No tiene callers. Era un skeleton para Fase 01 que nunca se usó. |
| `errors.py` | 8 | `AutopilotError`, `SessionNotFoundError`, `ConfigError` | SHRINK | `SessionNotFoundError` ya no aplica (la API delega a `cortex.session.errors.SessionNotFound`). Conservar `AutopilotError` y `ConfigError`. Reemplazar usos de `cortex.autopilot.errors.SessionNotFoundError` por la versión canónica. |
| `policies/base.py` | 34 | `AutopilotPolicy` Protocol + `evaluate_policies` + `most_restrictive` | MERGE | Migrar al nuevo `cortex/autopilot/policies.py` (T3.2). El Protocol se reescribe con la nueva API (`on_session_open`/`on_checkpoint`/`on_pre_close`). |
| `policies/default.py` | 69 | `BudgetPolicy`, `DocumentationRequiredPolicy`, `SpecRequiredPolicy`, `HumanApprovalPolicy` | MERGE | Migrar a `policies.py`. Adaptar para que reciban `SessionRecord` en lugar de `AutopilotSessionState`. Algunos pierden sentido (`DocumentationRequiredPolicy` ya está implícito en el documenter; `SpecRequiredPolicy` ya está implícito en `cortex session open` que requiere spec). Re-evaluar one-by-one. |
| `policies/auto_checkpoint.py` | 40 | `AutoCheckpointPolicy` (>5 files sin checkpoint o >10min sin checkpoint) | MERGE | Se integra a `policies.py`. Sigue siendo valioso (es lo único que justifica `assist` vs `observe`). |
| `detectors/base.py` | 55 | `AutopilotDetector` Protocol + `resolve_detectors` | KEEP | La lógica de detección queda fuera de la fusion (los detectors son específicos del flujo "user request → spec auto-generation" que sigue siendo Autopilot territory). Sólo cambia el `state` argument type (`AutopilotSessionState` → `SessionRecord` o `None`). |
| `detectors/default.py` | 202 | 5 detectores + Noop | KEEP | Idem `base.py`. |
| `detectors/ambiguous.py` | 46 | `AmbiguousRequestDetector` | KEEP | Idem. |
| `renderers/base.py` | 11 | `SessionRenderer` Protocol | **DELETE** | Renderer vive en el documenter ahora (Jinja templates). |
| `renderers/implementation.py` | 91 | Renderer para fast-code/deep-code/security | **DELETE** | Idem. |
| `renderers/docs_only.py` | 52 | Renderer para docs-only | **DELETE** | Idem. |
| `renderers/minimal.py` | 46 | Renderer minimal | **DELETE** | Idem. |
| `renderers/fallback_draft.py` | 45 | Renderer de último recurso | **DELETE** | Idem. |
| `hooks/session_start.py` | 49 | Script CLI que emite payload SessionStart al harness IDE | **DELETE** | Es un wrapper alrededor de `AutopilotService.status() + adapter.emit_session_start()`. Los hooks de Fase 03 son **input** (IDE → cortex checkpoint), no **output** (cortex → IDE bootstrap). La direccionalidad cambia. |
| `hooks/session_finish.py` | 44 | Idem para SessionFinish | **DELETE** | Idem. |
| `hooks/run_hook.sh` + `run_hook.cmd` | — | Shell wrappers que invocan los scripts Python anteriores | **DELETE** | Sin consumidor tras eliminar los Python hooks. |
| `adapters/base.py` | 95 | `AutopilotHookAdapter` Protocol + `_write_with_backup` + `format_session_start_output` | RELOCATE → `cortex/session/hooks/adapters/base.py` | Pero **la API cambia** (ver T3.6): el nuevo `HookAdapter` Protocol no expone `emit_session_start` (los hooks de Fase 03 son *triggers*, no formatters). Sólo `install/uninstall/status`. Las utilidades `_write_with_backup` / `_remove_autopilot_blocks` se preservan. |
| `adapters/claude_code.py` | 36 | Instala bloque markdown en `.claude/autopilot-hook.md` | RELOCATE → `cortex/session/hooks/adapters/claude_code.py` (T3.7) | **Pero el comportamiento cambia.** Hoy instala un markdown estático con instrucciones para el LLM; el nuevo adapter instala un **hook PostToolUse JSON nativo en settings.json** que invoca `cortex session checkpoint`. Reescritura completa, sólo el nombre sobrevive. |
| `adapters/cursor.py` | 35 | Instala bloque en `.cursorrules` | RELOCATE → `cortex/session/hooks/adapters/cursor.py` (T3.8) | **Comportamiento cambia.** Nuevo: instala `.git/hooks/post-commit` que invoca `cortex session checkpoint` con `\|\| true`. El `.cursorrules` actual lo dejamos en paz (es para que el LLM lea instrucciones, no para checkpointing). |
| `adapters/codex.py` | 36 | Instala bloque en `.codex/autopilot.md` | **DELETE** | Fase 03 §10 lista los 3 IDEs in-scope (Claude Code, Cursor, Pi). Codex queda **fuera** explícitamente. El bloque markdown actual no aporta nada que justifique mantenerlo. |
| `adapters/opencode.py` | 36 | Instala bloque en `.opencode/hooks.md` | **DELETE** | Idem Codex — fuera de scope Fase 03. |
| `adapters/pi.py` | 139 | Copia extension TS + skill markdown + merge `.pi/settings.json` | RELOCATE → `cortex/session/hooks/adapters/pi.py` (T3.9) | El más complejo. **Decisión:** preservar el código de install/uninstall casi tal cual (es robusto y bien testeado) pero reorientar el "extension TS" para que en su evento `onCommit` invoque `cortex session checkpoint` en lugar de `cortex autopilot ...`. La extension TS real vive en `cortex-pi/.pi/agents/` — actualizar ahí también si corresponde. |
| `adapters/platform_detect.py` | 29 | `Platform` enum + `detect_platform()` | KEEP (relocar) | Útil para `cortex session hooks status --auto-detect`. Mover a `cortex/session/hooks/platform_detect.py`. |
| `adapters/registry.py` | 31 | `_ADAPTERS` dict + `get_adapter()` + `list_adapters()` + `get_adapter_for_current_platform()` | RELOCATE → `cortex/session/hooks/installer.py` (T3.6) | Se fusiona dentro del `HookInstaller` nuevo. |

---

## 3. Consumidores externos a preservar

### 3.1 Importadores fuera de `cortex/autopilot/` (no-tests)

| Archivo consumer | Línea | Importa | Acción |
|---|---:|---|---|
| `cortex/cli/main.py` | 142 | `from cortex.autopilot.cli import app as autopilot_app` | **PRESERVAR**. La nueva `cli.py` debe seguir exponiendo `app`. |
| `cortex/mcp/server.py` | 18 | `from cortex.autopilot.mcp_tools import AutopilotMCPTools` | **PRESERVAR** clase + métodos `start/preflight/checkpoint/finish/status`. |
| `cortex/mcp/server.py` | 19 | `from cortex.autopilot.service import AutopilotService` | **PRESERVAR** clase + factoría `from_project_root`. |

### 3.2 Tests fuera de `tests/unit/autopilot/` que importan del módulo

| Test | Imports | Acción |
|---|---|---|
| `tests/unit/test_tripartita_refinada.py` (líneas 111-198) | `AutopilotSessionState`, `SessionDraft`, `IndexingSessionWriter` | **REESCRIBIR** este test. Las tres clases desaparecen; el test debe probar la nueva ruta `SessionRecord` + `DocumenterPersister`. Como es un test que valida la Tripartita Refinada (parte central de la arquitectura), no se puede simplemente eliminar — hay que migrarlo a las APIs nuevas. Tarea adicional a hacer dentro de T3.3. |

### 3.3 Tests dentro de `tests/unit/autopilot/` (19 archivos, ~2700 LOC)

| Test | LOC | Cobertura | Estado tras Fase 03 |
|---|---:|---|---|
| `test_models.py` | 179 | `AutopilotSessionState`, `AutopilotCheckpoint`, etc. | **DELETE en mayor parte** (las clases mueren). Conservar solo los tests de `DetectionResult`/`PolicyDecision`/`DelegationResult`. |
| `test_state_store.py` | 111 | `StateStore` | **DELETE** (clase eliminada). |
| `test_session_builder.py` | 168 | `SessionBuilder` + self_review | **DELETE** (clase eliminada). |
| `test_session_writer.py` | 231 | `VaultSessionWriter` + `IndexingSessionWriter` | **DELETE** + migrar lo valioso a `tests/unit/documenter/test_persistence.py` (especialmente la lógica de rollback transaccional). |
| `test_renderers.py` | 134 | 4 renderers | **DELETE** (clases eliminadas). |
| `test_service.py` | 206 | `AutopilotService.start/preflight/checkpoint/finish/status` | **REESCRIBIR** sobre la nueva API (delegando a SessionService mockeado). |
| `test_cli.py` | 211 | 8 Typer commands | **REESCRIBIR** (commands sobreviven, internals cambian). |
| `test_mcp_tools.py` | 110 | 5 MCP tools | **REESCRIBIR**. |
| `test_doctor.py` | 157 | 11 checks de doctor | **REESCRIBIR** (algunos checks se eliminan, otros cambian de target). |
| `test_policies.py` | 150 | 4 policies + auto_checkpoint | **MIGRAR** a `tests/unit/autopilot/test_policy_consolidated.py` (T3.2). |
| `test_detectors.py` | 136 | 6 detectores + resolución | **KEEP** (sólo ajustes de imports). |
| `test_delegation.py` | 159 | `DelegationEngine` | **KEEP** si se decide preservar `delegation.py`; **DELETE** si se difiere. |
| `test_context_budget.py` | 230 | `apply_budget`, profiles | **DELETE** (módulo eliminado). |
| `test_packaging.py` | 124 | `PluginManifest`, install/uninstall | **DELETE** (módulo eliminado). |
| `test_adapters.py` | 189 | 4 adapters | **REESCRIBIR** sobre la nueva API de `HookAdapter` y las nuevas semánticas. |
| `test_pi_adapter.py` | 226 | `PiAutopilotAdapter` | **REESCRIBIR** (preserva 80% del código). |
| `test_platform_detect.py` | 34 | `detect_platform()` | **KEEP** (sólo ajustar path import). |
| `test_skills_assets.py` | 97 | Verificación de assets de skills | Revisar al hacer T3.13 — puede quedar como está si los assets siguen viviendo donde estaban. |
| `__init__.py` | 0 | — | KEEP. |

### 3.4 Tests E2E (3 archivos en `tests/e2e/scenarios/`)

| Test | Cubre | Estado tras Fase 03 |
|---|---|---|
| `test_autopilot_basic.py` | Smoke del flujo Autopilot start → checkpoint → finish | **REESCRIBIR**. Reemplazar la creación manual de `AutopilotSessionState` por flujo real `cortex_create_spec` → `cortex_autopilot_checkpoint` → `cortex_finish_session`. |
| `test_autopilot_budget.py` | Budget enforcement bajo distintos modos | **REVISAR**. Si se elimina `build_context`, este test pierde objeto. Opción: limitarlo a verificar que `AutopilotPolicy.budget_profile` se respeta en la nueva forma (vía `PolicyEnforcer`). |
| `test_autopilot_finish.py` | Finish con `--auto` persistiendo el session note | **REESCRIBIR**. Validar que delega correctamente a `cortex finish-session`. |

**Nuevo E2E:** `tests/e2e/test_observed_flow.py` (T3.11) — escenario completo del modo Observed.

### 3.5 Documentación interna existente sobre Autopilot

- `docs/autopilot/README.md` y subdirectorios (`fase-01-skeleton-del-modulo/`, `fase-02-servicio-de-ciclo-de-vida/`, `fase-03-cli-headless/`, `fase-05-mcp-tools-autopilot/`, `fase-07-hook-adapters/`, etc.) son el plan **histórico** de construcción de Autopilot.
- **Decisión:** NO eliminar; agregar un banner al README explicando que la Fase 03 del proyecto Pluggable Middle (no confundir con las "fases" propias de Autopilot) refactorizó el módulo como capa sobre `cortex/session/`. La docs antigua queda como referencia histórica.
- T3.13 actualiza `docs/autopilot/README.md` con el banner y un link al doc maestro `ARQUITECTURA-PLUGGABLE-MIDDLE.md`.

---

## 4. Eliminaciones confirmadas

Los siguientes archivos se eliminan sin migración del contenido (su responsabilidad ya está cubierta por la primitiva canónica o por el documenter):

```
cortex/autopilot/state_store.py            (cubierto por cortex/session/storage.py)
cortex/autopilot/session_builder.py        (cubierto por cortex/documenter/reconstruction.py + renderers Jinja)
cortex/autopilot/session_writer.py         (cubierto por cortex/documenter/persistence.py + NoteService)
cortex/autopilot/packaging.py              (reemplazado por cortex/session/hooks/installer.py)
cortex/autopilot/registry.py               (sin callers; era un skeleton sin uso)
cortex/autopilot/context.py                (lógica AgentMemory.enrich() ya en cortex/context_enricher/)
cortex/autopilot/budget_profiles.py        (acoplado a context.py)
cortex/autopilot/renderers/base.py
cortex/autopilot/renderers/docs_only.py
cortex/autopilot/renderers/implementation.py
cortex/autopilot/renderers/minimal.py
cortex/autopilot/renderers/fallback_draft.py
cortex/autopilot/hooks/session_start.py    (la direccionalidad de los hooks cambia — Fase 03 §3.3)
cortex/autopilot/hooks/session_finish.py
cortex/autopilot/hooks/run_hook.sh
cortex/autopilot/hooks/run_hook.cmd
cortex/autopilot/adapters/codex.py         (fuera de scope Fase 03)
cortex/autopilot/adapters/opencode.py      (fuera de scope Fase 03)
```

**Antes de borrar cada uno:** `Grep` exhaustivo del repo confirmando que no quedan imports huérfanos (Fase 03 §5.2). Los hits en `docs/autopilot/**` son aceptables (docs históricas) y se preservan.

---

## 5. Reubicaciones (RELOCATE)

Los archivos siguientes cambian de path como parte de la creación del nuevo `cortex/session/hooks/` (T3.6 a T3.9):

```
cortex/autopilot/adapters/base.py             → cortex/session/hooks/adapters/_base.py
                                                 (sólo las utilidades _write_with_backup,
                                                  _remove_autopilot_blocks. El Protocol
                                                  AutopilotHookAdapter NO se reusa — el
                                                  Protocol nuevo HookAdapter de T3.6 tiene
                                                  semántica distinta y vive en installer.py)

cortex/autopilot/adapters/claude_code.py      → cortex/session/hooks/adapters/claude_code.py
                                                 (reescribe el body — ver §2 fila claude_code.py)

cortex/autopilot/adapters/cursor.py           → cortex/session/hooks/adapters/cursor.py
                                                 (reescribe el body)

cortex/autopilot/adapters/pi.py               → cortex/session/hooks/adapters/pi.py
                                                 (preserva ~80% del install/uninstall)

cortex/autopilot/adapters/platform_detect.py  → cortex/session/hooks/platform_detect.py

cortex/autopilot/adapters/registry.py         → cortex/session/hooks/installer.py
                                                 (fusionado con HookInstaller nuevo)
```

---

## 6. Mantener con tweaks mínimos

```
cortex/autopilot/errors.py            (sólo eliminar SessionNotFoundError)
cortex/autopilot/detectors/base.py
cortex/autopilot/detectors/default.py
cortex/autopilot/detectors/ambiguous.py
cortex/autopilot/context_budget.py    (sólo data; quizás mover a policies.py)
```

---

## 7. Reescribir manteniendo API pública

Estos archivos conservan su path y su superficie pública pero el body se reimplementa para delegar a la primitiva canónica:

```
cortex/autopilot/__init__.py    (ahora exporta AutopilotService, AutopilotPolicy, AutopilotMode)
cortex/autopilot/service.py     (núcleo del refactor — T3.3)
cortex/autopilot/lifecycle.py   (Pydantic models simplificados)
cortex/autopilot/models.py      (modelos de decisión únicamente)
cortex/autopilot/mcp_tools.py   (T3.5)
cortex/autopilot/cli.py         (T3.4)
cortex/autopilot/config.py      (T3.2 — simplificado a 2 fields + hooks list)
cortex/autopilot/doctor.py      (T3.12)
cortex/autopilot/reporting.py   (re-evaluar si vale la pena mantener; default: sí, simplificado)
```

---

## 8. Nueva consolidación: `cortex/autopilot/policies.py`

T3.2 crea un único archivo `policies.py` que fusiona:

- `policies/base.py` (Protocol + evaluación)
- `policies/default.py` (4 policies)
- `policies/auto_checkpoint.py`

API expuesta:

```python
class AutopilotMode(StrEnum):
    OBSERVE = "observe"
    ASSIST = "assist"
    AUTOPILOT = "autopilot"

@dataclass(frozen=True)
class AutopilotPolicy:
    mode: AutopilotMode
    budget_profile: str = "fast_code"
    pre_commit_verification: bool = False    # solo autopilot
    out_of_scope_warning: bool = True        # assist+
    auto_checkpoint_threshold_files: int = 5 # AutoCheckpointPolicy
    auto_checkpoint_threshold_minutes: int = 10

    @classmethod
    def from_config(cls, cfg: AutopilotConfig) -> AutopilotPolicy: ...

@dataclass(frozen=True)
class EnforcementResult:
    allowed: bool
    severity: Literal["proceed", "warn", "block"]
    reason: str

class PolicyEnforcer:
    def __init__(self, policy: AutopilotPolicy) -> None: ...
    def on_session_open(self, session: SessionRecord) -> EnforcementResult: ...
    def on_checkpoint(self, session: SessionRecord, checkpoint: Checkpoint) -> EnforcementResult: ...
    def on_pre_close(self, session: SessionRecord) -> EnforcementResult: ...
```

Las `policies/default.py` actuales (`BudgetPolicy`, `SpecRequiredPolicy`, etc.) se convierten en **métodos privados** de `PolicyEnforcer` o helpers en `policies.py`. No hace falta exponerlas individualmente — el caller solo ve `PolicyEnforcer`.

Tras T3.2, el subdirectorio `cortex/autopilot/policies/` se elimina (sus 3 archivos se fusionaron en `policies.py`).

---

## 9. Migración del state local

`run/autopilot/sessions/*.json` + `run/autopilot/events/*.jsonl` quedan **huérfanos** tras la fusión. Como no hay usuarios reales del módulo Autopilot, **no hace falta migración de datos**. El `cortex doctor` lo detecta y sugiere `rm -rf run/autopilot/` con confirmación explícita.

Decisión a tomar en T3.12: ¿se elimina automáticamente o sólo se reporta?
**Recomendación:** sólo reportar. El usuario decide.

---

## 10. Plan de ejecución secuencial (dependencias)

El orden recomendado evita refactors en cadena:

```
T3.1 ─────────► (este documento)
              │
              ▼
T3.2 ─────► policies.py (consolida 3 archivos, no toca service)
              │
              ▼
T3.6 ─────► cortex/session/hooks/ (Protocol + installer GENÉRICO, no IDE-specific)
              │
              ├────────► T3.7 (Claude Code adapter)
              ├────────► T3.8 (Cursor adapter)
              └────────► T3.9 (Pi adapter)
              │
              ▼
T3.10 ────► CLI cortex session hooks ... (necesita los 3 adapters listos)
              │
              ▼
T3.3 ─────► service.py reescrito (necesita policies + opcionalmente hooks ready)
              │
              ├────────► T3.4 (CLI delega a nueva service)
              └────────► T3.5 (MCP tools delegan a nueva service)
              │
              ▼
T3.11 ────► Tests E2E Observed (necesitan hooks instalables + service nuevo)
              │
              ▼
T3.12 ────► Doctor extensions
              │
              ▼
T3.13 ────► Documentación + Progress Log final
```

**Punto crítico de no-regresión:** entre T3.3 y T3.4/T3.5, todos los tests existentes en `tests/unit/autopilot/test_service.py`, `test_cli.py`, `test_mcp_tools.py` están **rotos** porque las clases viejas (`AutopilotSessionState`, `StateStore`) no existen. Ejecutar la **reescritura de los tests en el mismo commit** que cambia el código, NO dejarlos rotos entre commits granulares.

---

## 11. Riesgos y decisiones abiertas

### 11.1 ¿Qué hacer con `preflight`?

`AutopilotService.preflight()` y `cortex autopilot preflight` y `cortex_autopilot_preflight` (MCP) ejecutan detección de task type + evaluación de políticas SIN cambiar persistencia. En la nueva arquitectura:

- El task type ya no es relevante para el flujo (no hay renderer selection — el documenter usa siempre el mismo template).
- Las políticas se evalúan en hooks del lifecycle (`on_session_open`, `on_checkpoint`).
- La detección de "ambiguous request" sigue siendo útil para advertir al usuario antes de empezar.

**Opciones:**

(a) **Eliminar `preflight`** del service/CLI/MCP. Breaking change explícito.
(b) **Convertir `preflight` en un no-op con `DeprecationWarning`** y mantener la signature por UX continuity.
(c) **Convertir `preflight` en un comando de "dry-run"** que ejecuta los detectores sobre el spec activo y devuelve recomendaciones (sin persistir).

**Recomendación:** **opción (c)**. Da valor real (alerta de ambigüedad antes de empezar) sin romper consumers. Detectores y `resolve_detectors` quedan justificados.

### 11.2 ¿Borrar `delegation.py`?

`DelegationEngine` y `review_delegation` no tienen consumer real (ningún CLI command, ninguna MCP tool, ningún subagent los dispara). Es código muerto.

**Opciones:**

(a) **DELETE** completo + sus tests.
(b) **KEEP** pero marcar como experimental / undocumented.

**Recomendación:** **opción (a)**. Si Fase 04 necesita two-stage review, se reintroduce con scope claro.

### 11.3 ¿Mantener `reporting.py`?

`cortex autopilot report --last N` lista sesiones recientes. Pero `cortex session list` (de Fase 00) ya cubre esto.

**Recomendación:** **DELETE** + eliminar el comando `cortex autopilot report`. Lo que se pierde es la columna "chars_injected/items_retrieved" que ya no se trackea por sesión. Si alguien la quiere, la vuelve a agregar.

### 11.4 ¿`AutopilotService.build_context` sobrevive?

Tiene cero callers (CLI no lo expone, MCP tampoco). Sólo se invoca internamente desde tests.

**Recomendación:** **DELETE** + eliminar `context.py` + `budget_profiles.py`. -186 LOC.

### 11.5 ¿Cómo manejar el modo `observe` sin hooks instalados?

Si el usuario hace `cortex autopilot start --mode observe` pero no instaló ningún hook IDE, el modo es **inerte**: la session existe pero nadie emite checkpoints.

**Decisión:** está OK. El doctor advierte (`hooks_installed: []` + acción `cortex session hooks install --ide <name>`). El modo "funciona" en el sentido de que la session se crea; sólo no produce enrichment.

### 11.6 ¿Las CLI `cortex autopilot install --ide` y `cortex session hooks install --ide` conviven o una redirige?

**Decisión:** ambas existen. `cortex autopilot install --ide X` es un **alias semántico** de `cortex session hooks install --ide X` (T3.4). Internamente delega. UX continuity para usuarios que ya conocen el comando viejo (que no existen, pero la consistencia es barata).

### 11.7 ¿Qué pasa con el "extension TypeScript" de Pi?

El adapter Pi instala una extension TypeScript en `.pi/extensions/cortex-autopilot.ts`. Su contenido vive en `cortex/pi/extensions/cortex-autopilot.ts` (path dentro del paquete). Hoy esa extension llama a `cortex autopilot ...` en sus event handlers.

**Decisión:** actualizar la extension TS para que invoque `cortex session checkpoint --source ide-hook ...` directamente. Hay que verificar si `cortex/pi/extensions/` existe en el repo o si se referencia desde `cortex-pi/.pi/extensions/`. (Glob `cortex/pi/extensions/cortex-autopilot.ts` durante T3.9.)

### 11.8 ¿`AutopilotEvent` JSONL desaparece sin reemplazo?

Los `AutopilotEvent` (start, preflight, checkpoint, finish, context, delegation_review) eran un log estructurado del lifecycle, escrito como JSONL. Tras la fusion:

- Los eventos `checkpoint` se reemplazan por los `Checkpoint` de `SessionRecord`.
- Los eventos `start`/`finish` se reemplazan por el lifecycle del propio `SessionRecord`.
- Los eventos `preflight`/`context`/`delegation_review` desaparecen con sus métodos.

**Decisión:** se acepta la pérdida del JSONL. Lo que queda en `SessionRecord` cubre las necesidades de observability del 95% de los casos. Si en el futuro hace falta más telemetría, vive en `cortex/observability/`, no en Autopilot.

---

## 12. Checklist de "go" para T3.2

Antes de empezar T3.2 (consolidar `policies.py`), confirmar:

- [x] Documento `autopilot-audit.md` creado.
- [x] Inventario completo (40 archivos catalogados).
- [x] Decisiones abiertas listadas en §11 con recomendaciones.
- [x] Baseline tests verde (1811 passed + 4 preexistentes confirmados, 2026-05-16).
- [x] Consumidores externos identificados (`cortex/cli/main.py:142`, `cortex/mcp/server.py:18-19`, `tests/unit/test_tripartita_refinada.py`).
- [x] API target conocida (`cortex/session/service.py::SessionService`).
- [x] Plan secuencial validado (§10).

**Decisiones en §11 aún no confirmadas con el usuario**: 11.1 (preflight), 11.2 (delegation), 11.3 (reporting), 11.4 (build_context).

Estas decisiones son **internas** al refactor y consistentes con la
arquitectura. Si el usuario pide lo contrario, ajustar en el progress log
de la fase y volver a este documento.

---

## 13. Estimación de LOC tras la fusión

| Bloque | LOC pre-fase | LOC post-fase | Delta |
|---|---:|---:|---:|
| `cortex/autopilot/` (núcleo) | ~3500 | ~1100 | **−2400** |
| `cortex/session/hooks/` (nuevo) | 0 | ~600 | +600 |
| `tests/unit/autopilot/` | ~2700 | ~1400 | −1300 |
| `tests/unit/session/hooks/` (nuevo) | 0 | ~500 | +500 |
| `tests/e2e/` (incluye Observed) | (3 escenarios autopilot) | (3 + 1 observed) | +1 escenario, similar LOC |
| **TOTAL repo delta** | — | — | **~−2000 LOC netos** |

Es un refactor que **reduce código** del repo en ~2000 LOC mientras
agrega funcionalidad nueva (modo Observed E2E). Consistente con el
Quality Charter §2.1 "cero deuda técnica" — los archivos que se eliminan
eran exactamente esa deuda.

---

## 14. Notas para el ejecutor de T3.2 en adelante

1. **Antes de eliminar un archivo:** correr `Grep` exhaustivo desde la raíz del repo. Si aparece importado en `cortex/**.py` (no en docs/tests viejos), redirigir el import o postponer la eliminación. Commit aparte por eliminación, con mensaje claro `chore(autopilot): remove X (replaced by Y in Phase 03)`.

2. **Tests de no-regresión:** después de cada Tn.x, correr al menos:
   ```
   pytest tests/unit/autopilot/ tests/unit/session/ tests/e2e/test_byo_flow.py tests/e2e/test_managed_flow.py --no-cov -q
   ```
   Si rompe algo no relacionado, investigar en el momento. NO dejar tests rojos entre commits.

3. **Cambios en `.cortex/skills/*.md` y `.cortex/subagents/*.md`:**
   Si una task de Fase 03 toca alguno (probable en T3.13 para documentar `cortex autopilot install --ide`), actualizar el `render_*()` correspondiente en `cortex/setup/cortex_workspace.py` y correr `pytest tests/unit/ide/test_adapters_phase4.py --no-cov -q`. El hash test compara SHA-256.

4. **`canonical_tools.py`:** si Fase 03 agrega una MCP tool nueva (improbable —los hooks generan eventos vía CLI, no nuevas MCP tools), registrarla en `cortex/ide/canonical_tools.py` (Literal[...] + dict `_TOOL_NAME_BY_IDE`).

5. **Performance de hooks:** un hook git post-commit que tarda >500ms es molesto. T3.8 debe medir y, si es necesario, hacer fire-and-forget (`&` en bash, `Start-Process -NoWait` en pwsh).

6. **Seguridad:** los scripts instalados por los adapters NO deben contener tokens ni paths privados. Sólo invocaciones a `cortex` (que ya está en el PATH si el usuario tiene Cortex instalado).

7. **Reglas anti-error preservadas de Fase 02:**
   - No dejar trailing `"""` en archivos `.md` por copy-paste.
   - No tocar los 4 tests preexistentes que fallan.
   - Tests con `typer.Exit` usan `pytest.raises(typer.Exit)`.
