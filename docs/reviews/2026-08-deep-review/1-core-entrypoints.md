# Revisión: cortex core, entrypoints, pipeline y hooks

**Scope:** `cortex/__init__.py`, `core.py`, `models.py`, `doctor.py`, `runtime_context.py`, `git_policy.py`, `handoff.py`, `feedback_loop.py`, `memory_decay.py`, `doc_generator.py`, `doc_validator.py`, `doc_verifier.py`, `pr_capture.py`, `cortex/pipeline/**`, `cortex/hooks/**` (~6.240 líneas).
**Modo:** solo lectura. Todas las citas son file:line verificadas.

---

## 1. Propósito y arquitectura interna

### 1.1 `cortex/__init__.py` (83 líneas) — fachada pública del paquete
Reexporta la API estable: `AgentMemory`, infraestructura (`EpisodicMemoryStore`, `VaultReader`, `HybridSearch`), servicios de dominio (`SpecService`, `NoteService`, `SessionService`, `PRService`), embedders (Strategy) y el pipeline completo (`PipelineOrchestrator`, stages types). Declara `__version__ = "0.5.0"` (`__init__.py:50`) mientras el docstring dice "v2.4 — Pipeline Module Architecture" (`__init__.py:7`) — dos esquemas de versión divergentes.

### 1.2 `cortex/core.py` (905 líneas) — `AgentMemory`, la fachada central
- **Config Pydantic** (`core.py:71-126`): `EpisodicConfig` (persist_dir, embedding backend onnx/local/openai, namespace_mode project/branch/custom), `SemanticConfig`, `RetrievalConfig`, `LLMConfig`, `JiraIntegrationConfig`, `DocumenterConfig`, todos anidados en `CortexConfig`.
- **`AgentMemory.__init__` (`core.py:157-307`)** es el wiring point hexagonal:
  1. Descubre `WorkspaceLayout` desde CWD o desde un `config_path` explícito.
  2. Resuelve `workspace_root`, `repo_root`, `project_root` (alias deprecated de workspace_root, `core.py:209-214`, documentado en `core.py:797-809`).
  3. Detecta runtime context: `project_id` (slug), `git_branch`, `git_repo`; carga enterprise config/topology.
  4. Inyecta infraestructura en servicios de dominio: `SpecService` (con `SessionService`), `NoteService`, `PRService`; `WorkItemService` lazy (`_get_workitem_service`, `core.py:876-888`).
- **API**: `remember/store_memory/retrieve/forget/stats` (memoria episódica + RRF híbrido con filtro post-hoc por branch, `core.py:430-441`), vault (`create_note`, `sync_vault`), delegación completa a SpecService/NoteService/PRService, sesión primitiva (open/checkpoint/close/list/tasks, `core.py:596-705`), PR workflow, work items Jira, y `enrich()` (`core.py:815-860`) que instancia `ContextObserver`+`ContextEnricher` per-call.
- Errores de setup en español con emoji (`core.py:194-197`): decisión de UX deliberada pero inconsistente con el resto del código en inglés.

### 1.3 `cortex/models.py` (407 líneas) — contratos compartidos
- `MemoryEntry` (con `confidence` tri-state verified/asserted/contradicted), `SemanticDocument` (con metadatos enterprise y chunking), `EpisodicHit`, `UnifiedHit` (RRF, computed fields `display_*`), `RetrievalResult.to_prompt()`.
- DevSecDocOps: `PRContext` (con heurísticas `hu_references`, `has_db_changes`, `has_api_changes`), `GeneratedDoc`.
- Context Enricher: `WorkContext`, `EnrichedItem`, `EnrichedContext.to_prompt_format(compact/expand)`.

### 1.4 `cortex/runtime_context.py` (58 líneas)
Utilidades puras: `slugify`, `_run_git_command` (timeout 5s, nunca lanza), `detect_git_branch` (fallback `"no-git-branch"`), `detect_git_repo_path`, `resolve_episodic_persist_dir` (namespace branch → `memory/branches/<slug>`, custom → `memory/custom/<slug>`).

### 1.5 `cortex/git_policy.py` (111 líneas)
Constantes gitignore por layout (`RECOMMENDED_/NEW_LAYOUT_/LEGACY_GITIGNORE_PATTERNS`) + `recommended_gitignore_snippet(layout|project_root)` y `gitignore_contains(root, pattern)` (match exacto de línea, sin glob semantics). Consumido por `doctor.py` y el CLI de setup.

### 1.6 `cortex/handoff.py` (138 líneas) — schema legacy deprecado
`AgentHandoff` (Pydantic, `agent` como Literal de 7 nombres canónicos, `status` complete/partial/blocked) + `ArtifactProduced`. Deprecado desde Phase 02: el estado canónico es ahora `SessionRecord` (`handoff.py:6-19`). Se mantiene solo para el "Legacy YAML mode" del documenter (IDEs single-agent tipo Codex). `_KNOWN_AGENTS` duplica el Literal; `is_known_agent` solo se usa en tests.

### 1.7 `cortex/feedback_loop.py` (510 líneas) — aprendizaje de utilidad
- `ImplicitFeedbackAnalyzer`: overlap keyword/file/entity (Jaccard), score ponderado 0.4/0.4/0.2, umbral útil ≥0.3.
- `ExplicitFeedback` (GitHub reactions via `parse_github_reaction`, ratings de usuario).
- `FeedbackCollector`: agrega contadores por memory_id, recalcula usefulness, `get_boost` mapea [0.5, 1.5].
- `FeedbackEnricherIntegration`: aplica boost a items tipo dict.
- **Estado 100% en memoria** (dicts), sin persistencia.

### 1.8 `cortex/memory_decay.py` (404 líneas) — relevancia temporal
- `DecayConfig` con half_life (default 168h); `__post_init__` recalcula `decay_rate = 0.5^(1/half_life)`.
- `PERMANENT_TYPES`/`PERMANENT_TAGS` eximen ADRs/arquitectura/runbooks del decay.
- `MemoryDecay.calculate_decay_factor`: decay exponencial solo después de `min_age_hours` (24h), con floor 0.10. `apply_to_hits` devuelve pares ordenados. `ScoringWithDecay` añade multi-match boost (hasta +45%, capped 1.0). `EnricherDecayConfig` puentea hacia `ContextEnricherConfig`.

### 1.9 `cortex/doctor.py` (925 líneas) — diagnóstico del workspace
`run_doctor(project_root, scope)` produce `DoctorReport` con ~25 checks: config YAML (valida con `CortexConfig.model_validate`), vault, episodic store (warn en CI vía `GITHUB_ACTIONS`), workspace v2, git, gitignore layout-aware, webgraph deps, validación batch del vault con `DocValidator`, sesiones (`_validate_sessions`: puntero activo, parse-all, invariantes OPEN/terminal, múltiples OPEN), autopilot policy (detecta typos de modo que `from_config` silencia), hooks IDE instalados + checkpoints ide-hook, salud Pluggable Middle (imports del documenter, VerificationRunner, MCP tools grepped **por texto** del server.py, `doctor.py:626-650`), y empresa (org.yaml, vault-enterprise, alineación branch-isolation/scope, promoción).

### 1.10 `cortex/doc_generator.py` (210 líneas) — docs fallback
`DocGenerator` genera **solo session notes** fallback cuando el PR no trae docs de agente. Template simple con placeholders `{{key}}` y regex cleanup. `_meets_adr_criteria` implementa la aproximación machine-level del filtro Tripartita Refinada (3 criterios por keywords) pero **no se usa** en `generate_all` (`doc_generator.py:144-165` lo documenta como "available for future use").

### 1.11 `cortex/doc_validator.py` (207 líneas)
`DocValidator.validate_file/batch`: frontmatter YAML obligatorio (warning si falta, error si inválido), title requerido (warning), date/created (info), extracción wikilinks/embeds Obsidian, check de embeds rotos (warning).

### 1.12 `cortex/doc_verifier.py` (213 líneas)
`DocVerifier.verify_from_diff(base_branch|changed_files)`: partición mutuamente excluyente new/modified/deleted ∪= vault_files (contrato documentado en `doc_verifier.py:87-93`). `has_agent_docs = bool(new or modified)` — deletions solas NO cuentan como docs.

### 1.13 `cortex/pr_capture.py` (197 líneas)
`capture_from_github()` (env vars GITHUB_*/PR_*), `capture_manual(...)`, `capture_from_json/save_context`, `enrich_with_pipeline` (inmutable). Detección heurística de migraciones DB y cambios API por nombre de archivo. `_run_git` ignora returncode (silencioso).

### 1.14 `cortex/pipeline/**` — DevSecDocOps
- **domain/** (puro, sin I/O): `StageType`/`StageStatus` enums, `StageResult` frozen dataclass, `PipelineReport` (passed/failed_stages/summary/to_markdown/to_dict), `PipelineContext` dataclass mutable con `stage_outputs` para comunicación inter-stage, `PipelineStage` Protocol estructural (`runtime_checkable`, contrato "MUST NOT raise", `protocols.py:72-76`).
- **orchestrator.py**: ejecuta stages en orden, propaga status a `ctx.stage_outputs`, gate enforcement: aborta y marca SKIPPED los restantes si falla un stage con `block_on_failure` y `abort_early=True`.
- **stages/**: `SecurityStage` (pip-audit/npm audit JSON parsing), `LintStage` (ruff/eslint/go/rust autodetectado por extensiones de changed_files), `TestStage` (pytest+cobertura regex `TOTAL ... %`), `DocumentationStage` (verifica docs → indexa; sino → fallback; guarda PRContext con resultados de stages previos leyendo `stage_outputs` por nombre hardcodeado `"Lint"`, `"Tests"`, `"Security Audit"`).
- **runners/github.py**: `GitHubActionsRunner` genera workflow YAML completo (checkout fetch-depth 0, cache `.memory/chroma`, capture → gates → search → sync-vault → auto-commit vault → artifacts).

### 1.15 `cortex/hooks/**`
`CortexHook.capture` decorator (guarda input+output como memoria, trunca args a 200 chars, usa `inspect.signature.bind_partial`) y `CortexLangChainCallback` (duck-typed, NO hereda `BaseCallbackHandler`; no-ops requeridos en `agent_hooks.py:149-153`).

---

## 2. Flujo de datos y puntos de entrada/salida

```
Consumidores externos            Este subsistema                Dependencias hacia afuera
─────────────────────            ────────────────────           ─────────────────────────
CLI (cli/main.py)         ─────▶ AgentMemory (core)      ─────▶ EpisodicMemoryStore / VaultReader /
cortex.mcp.server (tools) ─────▶   · retrieve/remember           HybridSearch (retrieval/)
documenter, services      ─────▶   · create_spec_note...       SessionStorage/session.service,
setup/, autopilot doctor  ─────▶ doctor.run_doctor             enterprise.config, workspace.layout,
CI (GitHub Actions)       ─────▶ pr_capture → PipelineOrchestrator→ stages → subprocess (pytest/ruff/
                                   ↘ runners.github (YAML gen)    pip-audit/npm) y DocVerifier/
context_enricher.enricher ─────▶ memory_decay + feedback_loop    DocGenerator (fallback docs)
LangChain/CrewAI agents   ─────▶ hooks.agent_hooks
```

- **Entradas**: config.yaml (workspace discovery), env vars GH, git subprocesses, changed files, feedback de usuario/GitHub.
- **Salidas**: RetrievalResult/EnrichedContext para prompts LLM, archivos markdown al vault, DoctorCheck reports, StageResults/markdown PR comments, YAML workflows, memorias episódicas en Chroma.
- `DocumentationStage` es el punto de acople pipeline↔memoria: inyecta `AgentMemory` completo y llama `store_pr_context`/`sync_vault`/`generate_pr_docs` (`documentation.py:136-188`).
- `feedback_loop` y `memory_decay` se consumen **solo** desde `context_enricher/enricher.py:217-271` y `async_enricher.py:341-370`.
- `handoff` se consume desde documenter, mcp/server, setup/cortex_workspace (modo legacy).

---

## 3. Invariantes y decisiones de diseño importantes

1. **Fachada estable**: `AgentMemory` no cambia su API aunque la lógica migre a servicios (contrato explícito `core.py:16-17`). Delegación pura en spec/note/PR workflows.
2. **Hexagonal con DI manual**: infraestructura construida en `__init__` e inyectada; cada servicio testeable independiente.
3. **Layout dual** (legacy vs `.cortex/` nuevo) atraviesa todo: paths, gitignore patterns, doctor checks. `project_root` es alias intencionalmente engañoso de `workspace_root` hasta EPIC 7.
4. **Pipeline desacoplado por Protocol estructural**, no herencia; dominio puro separado de stages/runners; comunicación inter-stage vía dict compartido, no dependencias directas.
5. **Docs-first con fallback**: el flujo preferido es que el agente escriba docs; Cortex solo verifica e indexa, y genera fallback mínimo (`doc_generator.py:1-31`). El fallback marca `status: fallback` en frontmatter.
6. **Confianza tri-state** (verified/asserted/contradicted) fluye de MemoryEntry a EnrichedItem a prompts (`models.py:160`, `models.py:366`).
7. **Gitless mode soportado**: doctor trata la ausencia de git como info, no fallo (`doctor.py:661-697`).
8. **Doctor nunca muta estado crítico… excepto** `_validate_enterprise_promotion` que hace `mkdir(parents=True)` en el vault empresarial (`doctor.py:907`) — ver bugs.
9. **Deprecación por fases**: handoff YAML y `SessionService` alias mantienen compatibilidad; remoción reservada para major version.

---

## 4. Bugs potenciales (con evidencia)

### B1. `create_decay_config(decay_rate=...)` es ignorado — API rota
`memory_decay.py:56-60`: `__post_init__` **siempre** sobrescribe `decay_rate` desde `half_life_hours` (si >0). `create_decay_config(decay_rate=1.0)` ("no decay", docstring `memory_decay.py:367-368`) produce efectivamente rate≈0.9959 (half-life 168h default). Además `decay_rate or 0.995` (`memory_decay.py:371`) convierte `decay_rate=0.0` en 0.995.

### B2. FeedbackCollector instanciado fresco en cada enrich — el "aprendizaje" no persiste
`context_enricher/enricher.py:259` (y `async_enricher.py:368`): `collector = FeedbackCollector()` dentro del método → todo historial de boost/explicit feedback vive exactamente una llamada. `get_usefulness` siempre devuelve 0.5 entre runs; `parse_github_reaction` y `record_feedback` no tienen caller productivo. Es funcionalidad decorativa.

### B3. Workflow generado: coverage gate siempre lee un archivo que nadie escribe
`runners/github.py:271-276`: el step "Check Coverage Gate" lee `/tmp/test-output.txt`, pero el step "Tests" corre `{test_cmd}` **sin redirigir salida a ese archivo** (`github.py:285-288`). Resultado: `COVERAGE=0` → cualquier `min_coverage>0` hace fallar todo PR. Gate muerto/roto out-of-the-box.

### B4. Workflow generado: security gate neutralizado por su propio default
`github.py:62` default `audit_cmd="pip-audit || true"` + `continue-on-error: true` (`github.py:224`) hacen que `steps.security.outcome` sea siempre success → el gate "Check Security Gate" (`github.py:233-237`) jamás falla con la configuración por defecto.

### B5. Filtro de branch post-fusión desperdicia top_k
`core.py:430-441`: en `namespace_mode == "branch"`, se recupera top_k global y luego se filtran hits de otras ramas **después** del RRF. Si 4/5 hits son de otra rama, el usuario recibe 1 resultado. El filtrado debería ocurrir antes/en la búsqueda (el store ya namespacea por directorio, pero la colección Chroma parece compartida — doble mecanismo parcialmente redundante).

### B6. Empresas de servicio nuevas por llamada en retrieve() enterprise
`core.py:407-421`: cada `retrieve()` con scope enterprise construye un `EnterpriseRetrievalService` nuevo (re-abre stores/embedders). Costoso en rutas hot (MCP server, enricher).

### B7. Acoplamiento frágil por nombre de stage
`stages/documentation.py:142-144` lee `ctx.get_stage_output("Lint"/"Tests"/"Security Audit", ...)` con strings hardcodeados que deben coincidir con las properties `name` de los stages (`lint.py:59`, `test.py:52`, `security.py:58`). Renombrar un stage rompe silenciosamente el almacenamiento de resultados del PR (queda None, sin error). No hay constante compartida ni key por StageType.

### B8. `_is_python_project` escanea el directorio padre del vault
`stages/security.py:148-152`: además de changed files, hace `ctx.vault_path.parent.glob("*.toml")` — asume que vault_path está en la raíz del proyecto. Con vault absoluto fuera del repo, detecta el lenguaje equivocado. Efecto secundario no documentado y no testeado.

### B9. `cmd.split()` rompe comandos con argumentos complejos
`lint.py:86`, `security.py:79`, `test.py:79`: shlex ausente. Comandos con comillas/rutas con espacios (`npm run lint -- --format "json"`) se parten mal. También ignoran `cwd=` — corren en el CWD del proceso, no en repo root (los stages no reciben repo_root en PipelineContext; solo vault_path).

### B10. Doctor muta el filesystem (side effect inesperado)
`doctor.py:905-913`: `_validate_enterprise_promotion` crea `<enterprise_vault>/.cortex/promotion/` con mkdir parents. Un comando de diagnóstico read-only que escribe en el vault del usuario (y puede crear dirs en un path montado read-only → check falla por permisos, no por salud).

### B11. `PRContext.hu_references` genera falsos positivos masivos
`models.py:221-237`: patrón `#(\d+)` captura **cualquier** número de issue/PR en el body y lo convierte en `HU-<n>`; `HU[-_]?(\d+)` sobre "HUGE-123"... no matchea por el `\b`? no hay \b — "HUMAN-1" → matchea `HU` + requiere dígitos inmediatos: "HU" seguido de "MAN-1"? `HU[-_]?(\d+)` sobre "HUMAN": H-U-M... no, M no es dígito ni -/_ → no matchea. Pero `#123` en "fixes #123" sí se vuelve HU-123 aunque sea issue de GitHub, y `user story 5`/`us-5` también. Además el chequeo `pattern.startswith(r"\b([A-Z]")` (`models.py:233`) es un hack frágil acoplado al texto literal del patrón.

### B12. `has_agent_docs` ignora deletions y el fallback de DocumentationStage es demasiado laxo
- `doc_verifier.py:145`: si el PR solo borra/modifica-nombre docs, `has_agent_docs=False` → se genera fallback redundante.
- `stages/documentation.py:166-168`: si `DocVerifier` lanza (p.ej. vault relativo raro), cae a "existe vault/sessions con contenido" → casi siempre True en repos maduros → falso PASS que salta indexeo real.

### B13. `MemoryDecay.get_stats` divide mal con timestamps ausentes
`memory_decay.py:291-293`: `avg_age_hours` y `avg_decay_factor` dividen por `len(hits)` pero solo acumulan cuando `timestamp` truthy → promedios diluidos incorrectos si algún hit no tiene timestamp. Además `stats["at_floor"]` cuenta `decay <= floor` incluyendo permanentes cuyo factor es 1.0 solo si floor≥1 — ok, pero `applying_decay`/`no_decay` pueden sumar != total.

### B14. Redundancia muerta en `should_decay`
`memory_decay.py:133-142`: tras los dos returns False, la línea final `return "permanent" not in tags_lower` es inalcanzable-como-False: "permanent" ∈ PERMANENT_TAGS, ya cubierto por el intersecto de línea 138. Código confuso más que bug.

### B15. `DocValidator` comparación de paths por string
`doc_validator.py:111`: `str(path).startswith(str(self.vault_path))` — falsos positivos de prefijo (`vaultX/file.md` empieza con `vault`), y luego `relative_to` lanzaría ValueError sin catch. Análogo: `doc_verifier.py:172-177` usa `relative_to` correcto pero `_get_vault_relative` devuelve None para vault absoluto fuera de root aunque `__init__` (`doc_verifier.py:74-76`) reasigna root al parent del vault — comportamiento sutil poco obvio.

### B16. `CortexLangChainCallback` no subclasea BaseCallbackHandler
`hooks/agent_hooks.py:115`: duck typing. LangChain moderno pasa `run_id`/`run_manager` y serializa callbacks; handlers custom sin la base class funcionan en muchos paths pero pierden `ignore_llm` metadata y pueden romper con `raise_error`/tracing habilitado. Sin tests ni lock a versión de langchain.

### B17. `retrieve(use_embeddings=False)` no deshabilita embeddings semánticos de forma garantizada
El parámetro se pasa al retriever, pero el branch-filtering posterior y el scope enterprise usan los mismos flags; verificado solo superficialmente — riesgo medio, requiere test.

### Menores
- `orchestrator.py:90`: `time.monotonic()` llamado y descartado (dead code); `orchestrator.py:29-30`: `if TYPE_CHECKING: pass` muerto.
- `core.py:176,187`: `from pathlib import Path as _P` duplicado dentro de ramas del mismo método.
- `core.py:893`: mensaje de error sugiere `cortex init` pero `runtime_context`/doctor sugieren `cortex setup full --non-interactive` — mensajes inconsistentes.
- `models.py:112`: `.strip("# ")` strip por caracteres, no por prefijo ("#Título" → "Título" ok, "##x" → "x", pero "# hola" deja espacio inicial... en realidad quita espacios también; menor).
- `RetrievalResult.intent: object | None` (`models.py:144`) tipado débil (evita import circular a costa de type-safety).
- `pr_capture._run_git` ignora returncode (`pr_capture.py:38-44`): diffs vacíos indistinguibles de errores; `int(os.environ["PR_NUMBER"])` puede lanzar ValueError sin manejo (`pr_capture.py:100`).
- `GITHUB_SHA` es el merge commit en PRs de GH, no el head SHA — `commit_sha` puede no corresponder al diff calculado (`pr_capture.py:106`).
- Cache del workflow apunta a `.memory/chroma` (`github.py:125,167`) pero el layout nuevo guarda en `.cortex/memory/` → cache inefectivo en repos nuevos.
- `git_policy.gitignore_contains` compara líneas exactas; un pattern equivalente con trailing slash distinto o `**` no matchea → doctor reporta faltantes inexistentes.
- `doctor.py:96-98`: `import os` a mitad de función; estilo.
- `handoff.py:65-74`: `_KNOWN_AGENTS` set + Literal duplican la lista canónica (dos fuentes de verdad).
- Emoji corrupto en source: `feedback_loop.py:127` contiene bytes inválidos ("Ignore" con replacement char).

---

## 5. Código muerto y duplicación

- **Muerto/no usado en producción**: `is_known_agent` + `_KNOWN_AGENTS` (`handoff.py:65-74,136-138`, solo tests); `_meets_adr_criteria` (`doc_generator.py:184-210`, declaradamente "for future use"); `FeedbackEnricherIntegration` y `parse_github_reaction` (ningún caller en cortex/); `DocVerifier._git_diff_files` (`doc_verifier.py:179-186`, solo se usa `_git_diff_status`); `MemoryDecay.apply_to_hits/get_stats` y `ScoringWithDecay` (sin callers; el enricher usa `calculate_decay_factor` directo); `create_decay_config` (sin callers); `DecayConfig.max_multimatch_boost` (`memory_decay.py:54`, declarado, nunca leído — el boost real está hardcodeado en `ScoringWithDecay:337-342`).
- **Duplicación**:
  - Parsing de env vars GH: `pr_capture.capture_from_github` vs `PipelineContext.from_env` (`pipeline/domain/context.py:114-139`) reimplementan la misma lectura con defaults ligeramente distintos (`GITHUB_EVENT_PR_TITLE` extra, `GITHUB_ACTOR` fallback).
  - Heurísticas de detección: `models.PRContext.has_db_changes/has_api_changes` (`models.py:239-249`) vs `pr_capture._detect_db_migrations/_detect_api_changes` (`pr_capture.py:70-91`) — indicadores similares pero no idénticos, dos fuentes de verdad.
  - Enricher síncrono vs asíncrono repiten los bloques decay+feedback casi idénticos (fuera de scope pero causa raíz de la duplicación de FeedbackCollector).
  - `_validate_vault` vs `_validate_enterprise_vault` en `doctor.py:713-738` vs `856-885`: misma lógica copy-paste con nombres de check distintos.
- **Sin tests dedicados**: no existen `tests/unit/pipeline*`, ni tests de `hooks/`, `feedback_loop.py`, `memory_decay.py`, `pr_capture.py` (solo `tests/unit/pr/test_pr_context.py` cubre modelos). El pipeline — pieza de CI gating — tiene cobertura cero directa.

---

## 6. Deudas y oportunidades de refactor

1. **Persistir feedback**: mover `FeedbackCollector` a storage en workspace (`session.lock`-style JSONL) y singleton por AgentMemory; hoy es un no-op caro (B2).
2. **Unificar configuración de decay**: `DecayConfig.__post_init__` debe respetar `decay_rate` explícito o eliminar el parámetro; alinear docstring (dice 0.99/~10% día, default es 0.995) (`memory_decay.py:35-41`).
3. **Stage keys por tipo, no por nombre**: reemplazar strings `"Lint"/"Tests"/"Security Audit"` por `StageType` como clave de `stage_outputs` (B7).
4. **Extraer `repo_root`/`cwd` a PipelineContext** y pasar `cwd=` a los subprocess de stages (B9); usar `shlex.split`.
5. **Duplicar menos**: `PipelineContext.from_env` debería llamar `capture_from_github()` y proyectar; heurísticas DB/API en un solo módulo.
6. **Doctor puro**: inyectar un flag `dry_run`/separar checks de escritura (B10); deduplicar `_validate_vault`/`_validate_enterprise_vault` con parámetro `(name_prefix, vault)`.
7. **Versionado coherente**: `__version__ 0.5.0` vs narrativa "v2.x" en docstrings.
8. **Tipar `RetrievalResult.intent`** con TYPE_CHECKING import del modelo de intent real.
9. **Handoff**: generar el Literal desde `_KNOWN_AGENTS` (o viceversa) para una sola fuente de verdad.
10. **Workflow runner**: testear el YAML generado con actionlint/pytest golden files; arreglar coverage-file redirect y defaults contradictorios (B3/B4).

---

## 7. Preparación para un cambio grande — qué tocar primero, qué es frágil

**Frágil (alto riesgo de ruptura silenciosa):**
1. `core.AgentMemory.__init__` — constructor monolítico que descubre layout, carga enterprise, y construye 5 servicios. Cualquier cambio de layout/wiring toca aquí. Primero extraer un `AgentMemoryComponents` dataclass o factory para poder variar wiring sin tocar 150 líneas.
2. Nombres de stage como contrato inter-stage (B7) — renombrar `"Lint"` rompe el almacenamiento de resultados sin tests que lo detecten.
3. `WorkspaceLayout.discover` implícito desde CWD (`core.py:170-190`) — comportamiento depende del directorio actual; fuente #1 de sorpresas en CLIs y MCP.
4. `doctor` grep textual de `server.py` para validar MCP tools (`doctor.py:631-632`) — se rompe con cualquier refactor del server (renombrar tools, split de archivos) produciendo warnings falsos.
5. Regex de parsing de outputs de terceros: coverage `%` entero only (`test.py:192`), pytest summary lines en inglés, npm/pip-audit JSON shapes — cualquier upgrade de tooling rompe gates silenciosamente (retornan None → pasan).

**Orden sugerido para un cambio grande:**
1. Tests de caracterización para pipeline (stages + orchestrator con subprocesses fakeados) — hoy cero cobertura.
2. Corregir B1/B2/B3/B7 (bugs de API pública y gating real).
3. Introducir constantes de stage-key + `repo_root` en contexto.
4. Recién entonces refactor de `core.__init__` y del dual-layout.

**Evaluación de salud general:** núcleo sólido (core/models/runtime_context están limpios, bien documentados, DI razonable). Pipeline bien diseñado en su dominio puro pero sin tests y con gates de CI generados rotos. `feedback_loop` y partes de `memory_decay` son efectivamente código decorativo/muerto en producción. Doctor es exhaustivo pero con side effects. Salud: **media** — buena arquitectura, ejecución inconsistente en los bordes.
