<div align="center">

# Contribuir a Cortex

¡Gracias por tu interés! Somos un proyecto open-source enfocado en **DevSecDocOps Governance para AI Agents** con soporte **Enterprise Memory Productization**. Esta guía cubre todo lo que necesitás saber para contribuir efectivamente.

</div>

---

## Tabla de Contenidos

- [Código de Conducta](#código-de-conducta)
- [Setup de Desarrollo](#setup-de-desarrollo)
- [Arquitectura del Proyecto](#arquitectura-del-proyecto)
- [Estándares de Código](#estándares-de-código)
- [Flujo de Trabajo Git](#flujo-de-trabajo-git)
- [Testing](#testing)
- [Áreas de Contribución](#áreas-de-contribución)
- [Comunidad y Soporte](#comunidad-y-soporte)

---

## Código de Conducta

Esperamos **profesionalismo, empatía y respeto** en todas las interacciones. Bienvenimos devs de todos los niveles. El feedback debe ser directo pero constructivo, y admitir errores es fuerza, no debilidad.

**Zero tolerance para:** acoso, discriminación, spam, comportamiento tóxico en PRs/issues, o intentos de introducir código malicioso. Reportar violaciones directamente a los maintainers.

---

## Setup de Desarrollo

**Prerrequisitos:** Python 3.11+, Git 2.30+, pip 22.0+

```bash
# 1. Fork el repo en GitHub, luego clonar TU fork
git clone https://github.com/TU-USUARIO/cortex.git
cd cortex
git remote add upstream https://github.com/MachuaninEzequiel/Cortex.git

# 2. Crear entorno virtual e instalar en modo desarrollo
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\Activate.ps1

pip install -e ".[dev]"

# 3. Instalar pre-commit hooks (obligatorio)
pre-commit install

# 4. Verificar que todo funciona
ruff check .
pytest
mypy cortex/

# 5. (Opcional) Inicializar el workspace para corridas locales
cortex setup agent

# 6. (Opcional) Setup enterprise para contribuir a módulos enterprise
cortex setup enterprise --preset small-company --non-interactive
```

Si los tres checks pasan sin errores, estás listo. El módulo
`cortex.documentation.*` corre con `mypy --strict` (ver `pyproject.toml`).

---

## Arquitectura del Proyecto

Cortex sigue una arquitectura modular en capas con la primitiva **Session**
como pivote del ciclo de vida (Pluggable Middle), una capa enterprise
superpuesta y un plugin de CI provider-agnostic:

```text
┌─────────────────────────────────────────────────────────────────┐
│   CLI Layer (Typer) — session, ci, autopilot, docs, webgraph,   │
│                       pr-context, hu, setup, …                  │
├─────────────────────────────────────────────────────────────────┤
│   cortex-sync  →  Session (open)  →  middle (Managed/Observed/  │
│                                       BYO)  →  cortex-documenter│
│   Pluggable Middle: el "middle" es 1 de 3 modos                 │
├─────────────────────────────────────────────────────────────────┤
│   Facade Orchestrator & Services                                │
│   core.py (AgentMemory) + services/ (SpecService, NoteService,  │
│   PRService) + handoff.py (Legacy YAML)                         │
├─────────────────────────────────────────────────────────────────┤
│   Session primitive (cortex.session)        │  CI plugin        │
│   - SessionRecord, Checkpoint, Task         │  (cortex.ci)      │
│   - VerificationHook + Runner               │  validate-pr /    │
│   - SessionService + storage (atomic YAML)  │  review-session   │
│   - hooks/ (claude-code, cursor, opencode,  │                   │
│             pi) + Phase 08 quality_gates    │                   │
├─────────────────────────────────────────────────────────────────┤
│   Documenter Reconstruction (cortex.documenter)                 │
│   load → diff → hooks → scope → contradictions → handoff →      │
│   status → persist (ADR evaluator + interactive UI + self-rev)  │
├─────────────────────────────────────────────────────────────────┤
│   Autopilot (thin) — policies + lifecycle over SessionService   │
├──────────────────────────────┬──────────────────────────────────┤
│   Episodic (ChromaDB)        │   Semantic Memory (Vault MD)     │
├──────────────────────────────┴──────────────────────────────────┤
│   Retrieval Engine (Adaptive RRF)                               │
│   - hybrid_search, intent, budget_resolver (Phase 08 task-aware)│
├─────────────────────────────────────────────────────────────────┤
│   Enterprise Memory Layer (org.yaml, promotion, reporting,      │
│                            multi-level retrieval + CI gov)      │
├──────────────────────────────┬──────────────────────────────────┤
│   Embedder Factory           │   Async Context Enricher         │
├──────────────────────────────┴──────────────────────────────────┤
│   MCP Server  +  WebGraph  +  IDE adapters (Claude Code,        │
│                                Cursor, opencode, Codex, Pi)     │
└─────────────────────────────────────────────────────────────────┘
```

**Módulos clave y su responsabilidad:**

| Módulo | Responsabilidad |
| --- | --- |
| `core.py` | Fachada principal (`AgentMemory`). Solo delega a servicios. |
| `services/spec_service.py` | Validación + persistencia de specs (incluye `verification_hooks`, `proposal_mode`, `with_tasks`). |
| `services/note_service.py` | Persistencia transaccional de session notes (rollback si la indexación falla — Fase 08). `SessionService` queda como alias deprecated. |
| `services/pr_service.py` | Intake de PRs y fallback docs. |
| `session/models.py` | `SessionRecord`, `Checkpoint`, `VerificationHook`, `Task`, enums `SessionStatus`/`SessionMode`/`CheckpointSource`/`TaskStatus`. |
| `session/service.py` | `SessionService`: open / checkpoint / close / list / abandon / tasks. Inferencia de modo al cerrar. |
| `session/storage.py` | Persistencia atómica YAML en `.cortex/sessions/`. |
| `session/git.py` | Wrapper de git para HEAD / branch / diff (con placeholder gitless). |
| `session/verification.py` | `VerificationRunner` con timeout, truncation y exit-code reporting. |
| `session/proposal.py` | Fase 09.A: gate del proposal de `cortex-sync`. |
| `session/quality_gates.py` | Fase 08: `cortex_review_checkpoint` (spec compliance + quality). |
| `session/hooks/` | Adapters de IDE hooks (claude-code, cursor, opencode, pi) + installer idempotente. |
| `documenter/reconstruction.py` | Algoritmo de 8 pasos (load → diff → hooks → scope → contradictions → handoff → status → persist). |
| `documenter/persistence.py` | `DocumenterPersister` + self-review (Fase 08). |
| `documenter/interactive.py` | UI guiada con `rich` (Fase 04). |
| `documenter/adr_evaluator.py` | Sugerencia de ADRs desde checkpoints. |
| `ci/validator.py` | `CiValidator` + `validate_pull_request` (Phase 07). |
| `ci/session_matcher.py` | Resolución PR → Session. |
| `ci/diff_io.py` | Resolución del diff (file / commits / branches). |
| `ci/markdown_formatter.py` | PR-comment sticky con sentinel marker. |
| `ci/review_session.py` | Level 3: review sessions CI-owned (modo `CI_REVIEW`). |
| `autopilot/policies.py` | `AutopilotPolicy`, `PolicyEnforcer`, modos observe/assist/autopilot. |
| `autopilot/service.py` | `AutopilotService` — wrapper delgado sobre `SessionService`. |
| `cli/session.py` | Sub-app `cortex session ...`. |
| `cli/session_tui.py` | TUI viva con `rich` (Fase 06). `render_layout` es función pura testeable. |
| `cli/ci.py` | Sub-app `cortex ci ...` (Phase 07). |
| `cli/_unicode_fallback.py` | Degrade a ASCII en consolas legacy (cp1252). |
| `documentation/` | Sistema canónico de escritura (doc_type, schemas, templates Jinja2, writers, routing). Bajo `mypy --strict`. |
| `handoff.py` | `AgentHandoff` schema — kept para Legacy YAML mode (single-agent IDEs como Codex). |
| `enterprise/config.py` | Carga y validación de `.cortex/org.yaml`. |
| `enterprise/models.py` | Modelos Pydantic de topología enterprise. |
| `enterprise/retrieval_service.py` | Retrieval multi-nivel (local + enterprise). |
| `enterprise/knowledge_promotion.py` | Pipeline de promoción auditable. |
| `enterprise/reporting.py` | Observabilidad y reporting enterprise. |
| `pipeline/` | Abstracciones formales para CI/CD y DevSecDocOps. |
| `episodic/memory_store.py` | Interfaz con ChromaDB para eventos. |
| `semantic/vault_reader.py` | Lee archivos Markdown del Vault. |
| `retrieval/hybrid_search.py` | Búsqueda adaptativa RRF con pesos dinámicos. |
| `retrieval/intent.py` | Detección de intención de búsqueda. |
| `embedders/factory.py` | Instanciación perezosa de backends. |
| `context_enricher/` | Resolución asíncrona concurrente de contexto + `budget_resolver` task-aware (Fase 08). |
| `setup/orchestrator.py` | Orquestador de setup (Agent/Pipeline/Full/Enterprise/WebGraph). |
| `setup/cortex_workspace.py` | Renderer de skills/subagents canonicales y `WorkspaceLayout`. |
| `webgraph/service.py` | Grafos de conocimiento + nodos enterprise. |
| `mcp/server.py` | Servidor MCP — expone tools de sesión, CI, retrieval, autopilot y documenter. |

**Cómo encaja todo:** un cambio típico modifica `session/`, `documenter/`
o `ci/` para la lógica nueva, **agrega `verification_hooks` al spec**
de la feature, y agrega tests en `tests/unit/<modulo>/` + un escenario
e2e en `tests/e2e/test_<flow>_flow.py`. La doc canónica del módulo
toca, idealmente, `docs/architecture/` o `docs/pluggable-middle/`.

---

## Estándares de Código

Usamos **Ruff** para linting/formateo y **Mypy** para type checking. Los pre-commit hooks corren esto automáticamente.

**Reglas de oro:**

- **Type hints siempre.** Toda función pública debe tener tipos explícitos.
- **Docstrings en Google Style** para funciones públicas. Incluir Args, Returns, Raises.
- **Pydantic para datos.** No usar dicts sin tipado para configuración o modelos.
- **Logging, no prints.** Usar `logger = logging.getLogger(__name__)` para debug.
- **Excepciones específicas.** Nunca capturar `Exception` a secas sin re-lanzar o loggear.
- **Comentarios que explican el _por qué_, no el _qué_.**

**Convenciones de nomenclatura:**

| Elemento | Convención | Ejemplo |
| --- | --- | --- |
| Funciones/variables | `snake_case` | `retrieve_memory()` |
| Clases | `PascalCase` | `AgentMemory` |
| Constantes | `UPPER_SNAKE` | `DEFAULT_TOP_K` |
| Archivos | `snake_case` | `hybrid_search.py` |
| Tests | `test_<modulo>_<comportamiento>` | `test_retrieval_fuses_both_sources` |
| Tasks (Fase 09.C) | `T<n>` / `T<n>.<n>...` | `T1`, `T1.2`, `T3.4.1` |

**Reglas Pluggable Middle:**

- **Nunca dupliques persistencia de sesión.** La fuente de verdad es
  `cortex.session.SessionService` + `SessionStorage`. Si necesitás
  mutar el estado de una Session, andá por ahí.
- **Verification hooks son obligatorios en specs nuevos.** Si tu PR
  agrega un comando o feature, declarálo con
  `cortex create-spec --verification-hook ...`. El CI plugin lo va a
  correr automáticamente.
- **Checkpoints sobre handoff YAML.** El contrato inter-agente es
  `cortex_session_checkpoint` con `CheckpointSource`. `AgentHandoff` /
  `cortex_validate_handoff` se mantienen sólo para el modo Legacy
  (Codex/single-agent), con `DeprecationWarning`.
- **Doctor primero.** Antes de pedir review, corré `cortex doctor` —
  emite secciones `[sessions]`, `[autopilot]` y `[pluggable_middle]`
  que cubren los gates principales.

**Reglas Enterprise adicionales:**

- Los modelos enterprise van en `cortex/enterprise/models.py` o `promotion_models.py`.
- Toda configuración enterprise se lee via `cortex/enterprise/config.py`, no directamente.
- Los presets se definen en `cortex/setup/enterprise_presets.py`.

---

## Flujo de Trabajo Git

```bash
# Siempre crear una rama desde main actualizado
git checkout main
git pull upstream main
git checkout -b feat/nombre-descriptivo   # o fix/, docs/, test/, refactor/
```

**Commits:** seguimos [Conventional Commits](https://www.conventionalcommits.org/):

```
feat(retrieval): add BM25 fallback when vector search returns empty
fix(episodic): restore timestamp in memory retrieval
docs(readme): update CLI reference with new commands
test(enricher): add coverage for graph expansion strategy
feat(enterprise): add regulated-organization preset
fix(promotion): handle duplicate fingerprints in review
```

Un commit = un cambio lógico. PRs pequeños y enfocados siempre ganan.

---

## Testing

**Objetivo de coverage: >85%.** Nunca hacer merge de un PR que lo baje.

```bash
pytest                                          # Suite completa
pytest --cov=cortex --cov-report=term-missing  # Con coverage
pytest tests/unit/retrieval/ -v                # Un módulo específico
pytest -k "rrf"                                # Por nombre de test
pytest -k "enterprise"                         # Tests enterprise

# Suites Pluggable Middle / Phase work
pytest tests/unit/session/                      # Primitiva Session
pytest tests/unit/documenter/                   # Reconstrucción
pytest tests/unit/ci/                           # CI plugin Phase 07
pytest tests/unit/cli/                          # CLI sessions + TUI + ci
pytest tests/e2e/test_managed_flow.py \
       tests/e2e/test_observed_flow.py \
       tests/e2e/test_byo_flow.py \
       tests/e2e/test_proposal_flow.py          # End-to-end por modo
```

Nuestra suite está dividida en `tests/unit/`, `tests/integration/` y `tests/e2e/`. Usamos *Hypothesis* para property-based testing en algoritmos complejos. Los tests del módulo `cortex.documentation.*` corren bajo `mypy --strict`.

**Qué hace un buen test:**

- Sigue el patrón **Arrange / Act / Assert**
- Tiene nombre descriptivo: `test_hybrid_search_fuses_results_from_both_sources`
- Incluye docstring si el caso no es obvio (especialmente para regresiones)
- Usa los fixtures de `conftest.py`, no crea dependencias ad-hoc

---

## Áreas de Contribución

### Good First Issues _(para empezar)_

Buscá el label `good-first-issue` en los issues: pequeños bug fixes, mejoras en docs, tests adicionales, o mejoras en mensajes de error.

### Help Wanted (Contributors Experimentados)

| Área | Feature | Complejidad |
| --- | --- | --- |
| **Pluggable Middle** | Adapter de IDE hook nuevo (Aider, Continue, Zed) | Media |
| **CI plugin** | Provider adicional (CircleCI, Buildkite, Azure Pipelines) | Media |
| **Documenter** | Mejoras en `contradiction_detector` (más allá de keyword-based) | Media-Alta |
| **Sessions TUI** | Keyboard interactivity (filtros, navegación, diff completo) | Media |
| **Enterprise** | Mejoras en presets por industria (healthcare, fintech) | Media |
| **Retrieval** | Optimización de pesos RRF multi-nivel | Media-Alta |
| **WebGraph** | Enriquecimiento de nodos enterprise en visualización | Media |
| **Observabilidad** | Dashboard HTML/UI para `memory-report` | Media-Alta |
| **Integraciones** | Plugins para Azure DevOps, Linear, GitHub Issues | Media |
| **Migration** | Herramientas de migración desde setups legacy | Baja-Media |

### Estado del Roadmap: Pluggable Middle

```text
✅ Phase 00 — Foundations: primitiva Session + storage + git + verification runner
✅ Phase 01 — Documenter Reconstruction: pipeline de 8 pasos + ADR evaluator
✅ Phase 02 — SDDwork Migration: checkpoints en lugar de YAML inline
✅ Phase 03 — Autopilot Fusion: autopilot como wrapper delgado sobre Sessions
✅ Phase 04 — Interactive Mode Polish: `finish-session --interactive` con rich
✅ Phase 05 — opencode hook adapter
✅ Phase 06 — Sessions TUI (`cortex session watch`)
✅ Phase 07 — CI plugin (`cortex ci validate-pr` + review sessions)
✅ Phase 08 — Managed Quality Gates (review checkpoint, self-review, budget,
              conditional templates, transactional rollback)
✅ Phase 09 — SDD Refinement
  - 09.A: Proposal step (`--proposal-mode`)
  - 09.B: Designer subagent (Deep Track: explorer → designer → implementer)
  - 09.C: Tasks granular (`--with-tasks`, `cortex session task ...`)
```

### Estado del Roadmap: Enterprise Memory Productization

```text
🚧 Onda 1: Fundación (estabilización)
  - E1: Modelo organizacional enterprise (.cortex/org.yaml)
  - E2: Retrieval multi-nivel base (Local + Corporate)

🚧 Onda 2: Operabilidad (estabilización)
  - E3: Promotion pipeline de conocimiento (Manual/CI-driven)
  - E4: Gobernanza y CI enterprise (Políticas automáticas)

🚧 Onda 3: Productización (estabilización)
  - E5: Setup enterprise interactivo (Wizard guiado)
  - E6: Observabilidad y Reporting de salud de memoria

🚧 Onda 4: Hardening (estabilización)
  - E7: Presets, documentación, hardening y adopción

🔮 Siguiente: Integraciones avanzadas, dashboards visuales, plugins de terceros
```

---

## Comunidad y Soporte

**¿Necesitás ayuda?** Antes de abrir un issue, revisá el README y buscá en issues existentes. Para preguntas generales usá **Discussions**.

**Para reportar un bug**, incluí: descripción del problema, pasos para reproducirlo, comportamiento esperado vs actual, y tu entorno (OS, Python version, Cortex version). Adjuntá logs o error traces si los tenés.

**Para proponer una feature**, describí el problema que resuelve, la solución que imaginás, y si consideraste alternativas.

---

<div align="center">

Al contribuir, acordás que tus aportes serán licenciados bajo la **MIT License** de este repositorio.

_Contribuir a open-source es un acto de generosidad. Valoramos calidad sobre cantidad, PRs pequeños y enfocados, preguntas sobre suposiciones, y empatía con usuarios y otros devs._

**Gracias por ser parte de Cortex.**

</div>
