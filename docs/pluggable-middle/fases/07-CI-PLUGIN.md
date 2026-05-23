# Fase 07 — CI Plugin (validación de PR contra Session)

> **Estado:** ⏸ Pendiente · **Bloqueada por:** Fase 04 (Sessions + Documenter completos) · **Bloquea:** Nada · **Esfuerzo estimado:** ~3-4 semanas (3 niveles secuenciales)

---

## 0. Metadatos

| Campo | Valor |
|---|---|
| Fase número | 07 |
| Nombre | CI Plugin |
| Versión del plan | 1.0 |
| Dependencias | Fase 04 cerrada (Sessions, documenter modes, verification hooks). |
| Output principal | Subcomando `cortex ci` con 3 niveles de funcionalidad incrementales (validación pasiva → PR comment → review session). Workflow templates para GitHub Actions y GitLab CI. |
| Breaking changes | Ninguno en Nivel 1 y 2. Nivel 3 agrega un nuevo `CheckpointSource.CI_BOT` (compatible — sólo agrega un valor al enum). |

---

## 0.1 Estructura por niveles

Esta fase entrega **tres niveles independientes** que se construyen secuencialmente:

| Nivel | Esfuerzo | Entrega | Cierra |
|---|---|---|---|
| **Nivel 1** — Validación pasiva | ~1 semana | `cortex ci validate-pr` (CLI agnóstico) + workflow templates | Equipos pueden gatekeeper PRs hoy |
| **Nivel 2** — PR comment formatter | ~3 días sobre L1 | `--format pr-comment` + Markdown emitter | PRs reciben resúmenes legibles |
| **Nivel 3** — Review session first-class | ~2 semanas sobre L2 | `cortex ci open-review-session`, nuevo `CheckpointSource.CI_BOT`, integración modelo Cortex | El PR review queda persistido en el vault como cualquier otro trabajo |

Cada nivel cierra con sus propios Completion Verification Commands (ver §6). Es válido **mergear/release después de cada nivel** si el equipo decide pausar; los niveles son autónomos.

---

## 1. Required Reading

### 1.1 Contexto del plan

- [`fases/README.md`](README.md) — Quality Charter.
- [`../ARQUITECTURA-PLUGGABLE-MIDDLE.md`](../ARQUITECTURA-PLUGGABLE-MIDDLE.md) §5 (Session), §8 (verification hooks).
- [`fases/01-DOCUMENTER-RECONSTRUCTION.md`](01-DOCUMENTER-RECONSTRUCTION.md) §7.2 (algoritmo de reconstrucción — base de qué validamos en un PR).

### 1.2 Código existente que vas a tocar o necesitas conocer

Leé enteros:

- `cortex/session/service.py` — `SessionService` (read API: get_active, list, get, compute_diff).
- `cortex/session/storage.py` — buscar sesiones por commit.
- `cortex/session/verification.py` — `VerificationRunner` (re-usar para correr hooks contra el PR HEAD).
- `cortex/session/models.py` — `SessionRecord`, `Checkpoint`, `CheckpointSource`, `VerificationHookResult`.
- `cortex/documenter/reconstruction.py` — `_scope_cross_check` (validación archivos vs scope del spec; re-usar).
- `cortex/documenter/spec_loader.py` — `load_spec` (re-usar para validar verification_hooks).
- `cortex/cli/session.py` — patrón para agregar un subapp nuevo (`hooks` se agregó así en Fase 03).
- `cortex/cli/main.py` — `finish_session` para inspirarse en el patrón de output JSON.

Leé bajo demanda:

- Tests de Sessions, Documenter, hooks adapters — patrones de fixtures.

### 1.3 Documentación externa

- **GitHub Actions:**
  - Inputs and outputs: https://docs.github.com/en/actions/creating-actions/about-custom-actions
  - PR context: https://docs.github.com/en/actions/learn-github-actions/contexts#github-context
  - `actions/checkout` con `fetch-depth: 0` (necesario para diffs completos).
- **GitLab CI:** rules + `merge_request_event` triggers.
- **Conventional commits** y standard PR comment markers para deduplicación (`<!-- cortex-pr-summary -->`).

---

## 2. Goal

Al finalizar esta fase (los 3 niveles):

### Nivel 1 entrega

1. **`cortex ci validate-pr`** — comando CLI provider-agnóstico que:
   - Acepta un diff (por path `--diff <file>`, por commits `--base <sha> --head <sha>`, o auto-detectado del repo actual).
   - Encuentra la `SessionRecord` correspondiente (por matching de `start_commit` con base, o `start_branch` con el nombre del PR branch, o flag explícito `--session <id>`).
   - Carga el spec asociado y corre las validaciones del documenter:
     - **Scope**: cada archivo del diff está en `files_in_scope`?
     - **Hooks**: los `verification_hooks` declarados pasan en HEAD?
     - **Unimplemented**: hay archivos en `files_in_scope` que el diff NO toca?
   - Retorna exit code (0 = OK, 1 = warnings, 2 = blocked).
   - Output `--format json` por default, con `--format text` para humanos.
2. **GitHub Actions workflow template** en `templates/ci/github-actions-cortex-validate.yml` (copiable por usuarios a `.github/workflows/`).
3. **GitLab CI template** en `templates/ci/gitlab-ci-cortex-validate.yml`.
4. **Bitbucket Pipelines template** (opcional bonus).
5. Tests E2E con un repo simulado tras un PR ficticio.

### Nivel 2 entrega (sobre N1)

6. **`--format pr-comment`** emite Markdown listo para postear como PR comment, con:
   - Resumen del session note (título, files touched, hooks pasados, ADRs sugeridos).
   - Tabla de scope drift (si la hay).
   - Bloque de blockers (si hooks fallan).
   - Sentinel comment marker (`<!-- cortex-pr-summary -->`) para deduplicación.
7. Workflow templates extendidos con un step que postea el comment (usando `gh pr comment` o equivalente en GitLab).
8. Tests del Markdown emitter (snapshot tests).

### Nivel 3 entrega (sobre N2)

9. **Nuevo `CheckpointSource.CI_BOT`** en `cortex.session.models` (compatible — sólo agrega un enum value).
10. **`cortex ci open-review-session`** — abre una Session de revisión vinculada al PR (con `spec_path` apuntando al PR description o al spec original, y `start_commit` = base de la PR).
11. **`cortex ci report-checkpoint`** — emite un checkpoint con `source=CI_BOT` con los hooks pasados, scope drift, claims verificados.
12. **`cortex ci close-review-session [--status closed|handoff]`** — cierra la review session (sin invocar el documenter — la sesión queda como "review only" y vive aparte de la session de desarrollo).
13. Workflow templates de Nivel 3 que ejecutan el ciclo open → checkpoint → close en el PR lifecycle.
14. Tests E2E que validan el ciclo entero.
15. **Decisión arquitectónica documentada** en `docs/architecture/review-sessions.md` sobre la relación review-session ↔ implementation-session.

**Lo que NO se hace en esta fase:**

- ❌ NO se implementa un GitHub App / OAuth listener server-side. El plugin es **stateless CLI**; el provider (GitHub/GitLab) lo invoca vía Actions/CI.
- ❌ NO se invade el modelo Session con conceptos PR-specific. El "review session" reusa la primitiva existente; solo agrega un `CheckpointSource`.
- ❌ NO se hace un Web UI de review sessions (eso es Fase 06 extendida).
- ❌ NO se acopla a un provider específico. La capa de glue (`gh pr comment`, GitLab API, etc.) vive en el workflow template, no en el CLI.

---

## 3. Decisiones de diseño clave

### 3.1 ¿Provider-agnóstico desde el día 1?

**Decisión:** sí. El CLI `cortex ci validate-pr` acepta inputs genéricos (`--diff`, `--base`, `--head`, `--base-branch`, `--pr-number`, `--pr-author`) y emite outputs genéricos (JSON, text, Markdown). Los workflows YAML específicos de provider son **plantillas que llaman al CLI**, no glue interno.

Razones:
- Es más barato testear un CLI puro que mockear la API de GitHub.
- Soporta GitLab/Bitbucket/Forgejo/etc. con el mismo CLI; solo la plantilla YAML cambia.
- Mantiene Cortex como librería, no como SaaS.

### 3.2 ¿Cómo se asocia un PR a una `SessionRecord`?

**Decisión:** orden de prioridad:
1. Flag explícito: `cortex ci validate-pr --session 2026-05-17_x` (override absoluto).
2. Auto-detección por **base commit**: buscar SessionRecords cuyo `start_commit` coincide con el `--base <sha>` del PR.
3. Auto-detección por **branch name**: buscar SessionRecords cuyo `start_branch` coincide con el `--head-branch <name>`.
4. Fallback: el comando emite un warning estructurado (`session_match: "none"`) y aún corre las verificaciones genéricas (lint, type) declaradas en spec ambiente. Si no hay spec asociado, sale con exit 2 (blocked) y mensaje accionable: "Run `cortex create-spec` and open a Session before requesting CI validation".

### 3.3 ¿Exit codes?

**Decisión:**
- `0`: validación pasa sin warnings.
- `1`: validación pasa con warnings (scope drift no bloqueante, hooks no-requeridos fallaron, sesión asociada en HANDOFF).
- `2`: validación bloqueada (hook requerido falló; session asociada en ABANDONED; spec sin hooks; archivos en scope no implementados).
- `3`: error interno (no es un fail de validación — git error, IO error, etc.).

Esto coincide con la convención CI (exit 0 = green; exit ≥1 = red). Workflows YAML mapean exit 1 a "warn" vía `continue-on-error: true` o el equivalente.

### 3.4 ¿Output formats?

**Decisión:**
- `json` (default): machine-readable; estable; documentado.
- `text`: human-readable, una línea por verificación; ANSI colors si stdout es TTY.
- `pr-comment` (N2): Markdown con sentinel marker.
- `github-checks` (opcional N2 bonus): JSON formato de [GitHub Checks API](https://docs.github.com/en/rest/checks).

### 3.5 ¿Nivel 3: cómo modelar la "review session"?

**Tres opciones evaluadas:**

| Opción | Cambios al modelo | Pros | Contras |
|---|---|---|---|
| **A.** Nuevo `SessionStatus.UNDER_REVIEW` | invasiva (afecta enum + validation + storage + UI) | Estado explícito de review | Confunde con el lifecycle existente de Sessions |
| **B.** Nuevo `CheckpointSource.CI_BOT` + Session "review" como cualquier otra | mínima (1 enum value) | Reusa todo lo existente; el "review" es semánticamente una Session con checkpoints de CI_BOT | Hay 2 Sessions paralelas para un mismo trabajo (implementation + review); ¿confunde a usuarios? |
| **C.** Nueva primitiva `ReviewRecord` separada | aislada (sin tocar Session) | Modelo limpio; sin ambiguity con el dev workflow | Duplica plumbing (storage, CLI, MCP tools) |

**Decisión recomendada: Opción B**. Razones:
- Minimal change al modelo (1 enum value).
- Las review-sessions tienen el mismo lifecycle que las dev-sessions (open → checkpoint → close); la primitiva ya está perfecta.
- El "2 sessions paralelas" se mitiga con UX: la review session tiene un naming explícito (`2026-05-17_pr-NNN-review`) y la TUI/CLI la marca con `mode=CI_REVIEW` (un valor más en el `SessionMode` enum, derivado al close cuando todos los checkpoints son CI_BOT).

El plan de Nivel 3 implementa Opción B. Si en T7.C.1 el ejecutor encuentra una razón fuerte para A o C, **debe documentarla en el Progress Log y consultar antes de implementar**.

### 3.6 ¿Naming del subcomando?

**Decisión:** `cortex ci` (no `cortex pr`, no `cortex github-action`, no `cortex validate`). Razones:
- Genérico: cubre cualquier provider.
- Corto y memorable.
- Espacio para subcomandos futuros (`cortex ci status`, `cortex ci release-check`, etc.).

### 3.7 ¿Tests E2E reales contra GitHub?

**Decisión:** NO. Los workflow templates se mantienen en `templates/ci/` como recursos estáticos; los tests verifican el **CLI internamente** (subprocess-friendly outputs, exit codes, JSON estable). Los workflows en sí se validan con `act` (local runner) o manualmente — no como parte de `pytest`.

---

## 4. Task Breakdown

### Nivel 0 — Diseño y scaffolding

#### T7.0.1 — Subcomando scaffold

**Archivos a crear:**
- `cortex/cli/ci.py` (módulo nuevo)

**Archivos a modificar:**
- `cortex/cli/main.py` — registrar `ci_app`.

**API esperada:**

```python
"""cortex.cli.ci — CI plugin (Phase 07, Pluggable Middle).

Subcomandos:
    validate-pr           — validación pasiva (Nivel 1)
    open-review-session   — apertura de Session de revisión (Nivel 3)
    report-checkpoint     — emisión de checkpoint CI_BOT (Nivel 3)
    close-review-session  — cierre de Session de revisión (Nivel 3)
"""
from __future__ import annotations
import typer

ci_app = typer.Typer(
    name="ci",
    help="CI plugin: validate PRs against Cortex Sessions.",
    no_args_is_help=True,
)
```

**Definition of Done T7.0.1:** `cortex ci --help` muestra el panel; aún sin subcomandos implementados.

---

### Nivel 1 — Validación pasiva

#### T7.A.1 — `cortex ci validate-pr` core logic

**Archivos a crear:**
- `cortex/ci/__init__.py` (módulo de lógica core)
- `cortex/ci/validator.py` (validador principal)
- `cortex/ci/session_matcher.py` (heurísticas de matching PR ↔ Session)
- `cortex/ci/result.py` (dataclasses de output)

**Archivos a modificar:**
- `cortex/cli/ci.py` — agregar `validate_pr_command`.

**API esperada en `cortex/ci/validator.py`:**

```python
from dataclasses import dataclass, field
from pathlib import Path
from cortex.session.models import SessionRecord, VerificationHookResult
from cortex.documenter.spec_loader import LoadedSpec


@dataclass(frozen=True)
class ValidationInput:
    diff_text: str
    base_commit: str | None         # ← e.g. main HEAD sha
    head_commit: str | None         # ← e.g. PR HEAD sha
    base_branch: str | None         # ← e.g. "main"
    head_branch: str | None         # ← e.g. "feature/x"
    pr_number: int | None
    pr_author: str | None
    repo_root: Path
    explicit_session_id: str | None  # ← --session <id>


@dataclass(frozen=True)
class ScopeDriftFinding:
    path: Path
    reason: str  # "out_of_scope" | "unimplemented"


@dataclass(frozen=True)
class ValidationResult:
    session_match: str  # "explicit" | "by_commit" | "by_branch" | "none"
    matched_session: SessionRecord | None
    spec: LoadedSpec | None
    files_in_diff: list[Path]
    scope_drift: list[ScopeDriftFinding]
    verification_results: list[VerificationHookResult]
    blockers: list[str]   # human-readable
    warnings: list[str]
    exit_code: int        # 0 / 1 / 2 / 3
    summary_text: str


class CiValidator:
    """Validates a PR against the matching Session + spec."""

    def __init__(self, session_service, verification_runner, repo_root: Path): ...

    def validate(self, input: ValidationInput) -> ValidationResult:
        """Pipeline:
        1. Match Session (explicit/commit/branch/none).
        2. If matched: load spec.
        3. Parse diff → file list.
        4. Scope cross-check (re-using cortex.documenter.reconstruction._scope_cross_check).
        5. Run verification hooks (re-using VerificationRunner).
        6. Compute exit code from blockers/warnings.
        7. Assemble ValidationResult.
        """
```

**`session_matcher.py`:**

```python
def find_session_for_pr(
    storage: SessionStorage,
    *,
    explicit_session_id: str | None,
    base_commit: str | None,
    head_branch: str | None,
) -> tuple[SessionRecord | None, str]:   # (record, match_type)
    """Returns (record, match_type). match_type is "explicit"|"by_commit"|"by_branch"|"none"."""
```

**CLI surface (`cortex/cli/ci.py`):**

```bash
cortex ci validate-pr \
    [--diff <file>] \
    [--base-commit <sha>] \
    [--head-commit <sha>] \
    [--base-branch <name>] \
    [--head-branch <name>] \
    [--pr-number <int>] \
    [--pr-author <username>] \
    [--session <id>] \
    [--format json|text] \
    [--project-root <path>]
```

**Tests obligatorios (`tests/unit/ci/test_validator.py`):**

- `test_match_by_explicit_session_id`
- `test_match_by_base_commit`
- `test_match_by_head_branch`
- `test_no_match_returns_none`
- `test_scope_drift_detected`
- `test_unimplemented_files_detected`
- `test_verification_hook_pass_yields_exit_0`
- `test_verification_hook_required_fail_yields_exit_2`
- `test_verification_hook_optional_fail_yields_exit_1`
- `test_session_handoff_yields_exit_1_with_warning`
- `test_session_abandoned_yields_exit_2`
- `test_no_session_and_no_spec_yields_exit_2_with_action`
- `test_json_output_schema_stable`
- `test_text_output_human_readable`

**Definition of Done T7.A.1:**
- 14+ tests verdes.
- `mypy --strict --follow-imports=silent cortex/ci/` limpio.
- `ruff check cortex/ci/` limpio.

---

#### T7.A.2 — Helper de diff parsing

**Archivos a crear:**
- `cortex/ci/diff_io.py` — parsers de diff input.

**API:**

```python
def read_diff_from_args(
    diff_file: Path | None,
    base_commit: str | None,
    head_commit: str | None,
    repo_root: Path,
) -> str:
    """Resolve the diff text from the various input modes.

    Priority:
    1. --diff file → read raw bytes, decode as utf-8.
    2. --base-commit + --head-commit → invoke `git diff <base>..<head>`.
    3. Auto: current branch's diff against the configured trunk (main/master).
    """
```

Reusar `cortex.session.git.diff` cuando posible.

**Tests (`tests/unit/ci/test_diff_io.py`):**

- `test_read_diff_from_file`
- `test_read_diff_from_commits`
- `test_auto_detect_trunk_main`
- `test_auto_detect_trunk_master`
- `test_missing_diff_file_raises`

**Definition of Done T7.A.2:** 5 tests verdes.

---

#### T7.A.3 — Templates de workflows YAML

**Archivos a crear:**
- `templates/ci/github-actions-cortex-validate.yml`
- `templates/ci/gitlab-ci-cortex-validate.yml`
- `templates/ci/bitbucket-pipelines-cortex-validate.yml` (opcional bonus)
- `templates/ci/README.md` (cómo usar las plantillas — copy-paste path, env vars necesarias, troubleshooting).

**GitHub Actions template (núcleo):**

```yaml
# templates/ci/github-actions-cortex-validate.yml
name: Cortex PR Validation
on:
  pull_request:
    types: [opened, synchronize, reopened]

jobs:
  cortex-validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0  # required for diff against base
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.13"
      - name: Install Cortex
        run: pip install cortex-memory   # or: pip install -e .
      - name: Run Cortex CI validation
        id: cortex
        run: |
          cortex ci validate-pr \
            --base-commit "${{ github.event.pull_request.base.sha }}" \
            --head-commit "${{ github.event.pull_request.head.sha }}" \
            --base-branch "${{ github.event.pull_request.base.ref }}" \
            --head-branch "${{ github.event.pull_request.head.ref }}" \
            --pr-number "${{ github.event.pull_request.number }}" \
            --pr-author "${{ github.event.pull_request.user.login }}" \
            --format json
        # exit code:
        # 0 = pass; 1 = warnings (job is yellow); 2 = blocked (job is red)
```

**Definition of Done T7.A.3:** templates están en disco; el README de templates explica cada paso; un usuario puede copy-paste a su repo y queda funcional.

---

#### T7.A.4 — Tests E2E Nivel 1

**Archivos a crear:**
- `tests/e2e/test_ci_validate_pr.py`

**Escenarios:**

```python
@pytest.mark.e2e
class TestCiValidatePrLevel1:
    def test_pr_with_matching_session_and_hooks_pass(tmp_repo_with_session):
        """Happy path: PR diff is in scope; hooks pass; exit 0."""

    def test_pr_with_scope_drift_yields_warning(...):
        """Diff touches a file outside files_in_scope; exit 1; scope_drift in JSON."""

    def test_pr_with_failing_required_hook_yields_block(...):
        """A required hook fails; exit 2; blocker in JSON."""

    def test_pr_with_no_matching_session_yields_actionable_error(...):
        """No Session matches base_commit or branch; exit 2; clear message."""

    def test_pr_with_handoff_session_yields_warning(...):
        """Session is in HANDOFF; exit 1 with warning."""
```

**Definition of Done T7.A.4:** 5+ escenarios verdes.

---

#### T7.A.5 — Documentación Nivel 1

**Archivos a modificar:**
1. `README.md` — agregar §"CI Plugin" describiendo `cortex ci validate-pr`.
2. `docs/architecture/pluggable-middle-overview.md` §9 — agregar `cortex ci` a la lista de surfaces.
3. `docs/pluggable-middle/MIGRATION-FROM-TRIPARTITO.md` §4.2 — agregar `cortex ci validate-pr` a la tabla de "what's new".
4. `docs/architecture/ci-plugin.md` (nuevo) — referencia técnica del CI plugin (sólo Nivel 1 en este punto).

**Definition of Done T7.A.5:** docs actualizadas; el README sufficiently describe Nivel 1.

---

#### Cierre Nivel 1 — Completion Verification (intermedio)

```bash
# 1. Tests
pytest tests/unit/ci/ tests/e2e/test_ci_validate_pr.py --no-cov -v
# expected: all green

# 2. mypy + ruff
mypy --strict --follow-imports=silent cortex/ci/ cortex/cli/ci.py
ruff check cortex/ci/ cortex/cli/ci.py
# expected: clean

# 3. CLI smoke (en un repo con sesión activa y hooks declarados)
cortex ci validate-pr --base-commit HEAD~5 --head-commit HEAD --format text
# expected: human-readable output con scope check + hooks status

# 4. Templates están disponibles
ls templates/ci/
# expected: github-actions-cortex-validate.yml, gitlab-ci-..., README.md
```

**Si Nivel 1 cierra y el equipo decide pausar:** el progreso queda usable. Continuar a Nivel 2 cuando haya capacidad.

---

### Nivel 2 — PR comment formatter

#### T7.B.1 — Markdown emitter

**Archivos a crear:**
- `cortex/ci/markdown_formatter.py`

**API:**

```python
def render_pr_comment(result: ValidationResult, *, marker: str = "<!-- cortex-pr-summary -->") -> str:
    """Render a ValidationResult as Markdown ready for `gh pr comment`.

    The output starts and ends with the sentinel marker so the workflow can
    deduplicate (replace prior comment on subsequent runs).
    """
```

**Estructura esperada del comment:**

```markdown
<!-- cortex-pr-summary -->
### Cortex PR validation · `2026-05-17_jwt-refresh`

**Status:** PASS · 0 blockers · 0 warnings

#### Files in scope ✓
- `src/auth.py` (modified)
- `tests/auth_test.py` (modified)

#### Verification hooks
- ✓ tests (2.3s)
- ✓ types (0.8s)
- ⏸ lint (skipped — non-required)

#### ADR candidates
- _none surfaced_

<sub>Generated by [Cortex CI](https://github.com/.../cortex) at 2026-05-17 14:32 UTC · rerun this job to refresh.</sub>
<!-- cortex-pr-summary -->
```

Variaciones:
- Status `WARN`: amarillo (sin emoji custom — usar texto).
- Status `BLOCKED`: bloque de "Blockers" expandido con cada blocker.
- Si no se encontró Session: bloque de "No matching Session — action required" con instrucciones.

**Tests (`tests/unit/ci/test_markdown_formatter.py`):**

- `test_renders_marker_at_start_and_end`
- `test_status_pass_format`
- `test_status_warn_includes_warnings_section`
- `test_status_blocked_includes_blockers_section`
- `test_no_session_match_includes_action_hint`
- `test_long_file_list_truncates_with_more_link`
- Snapshot tests con casos canónicos.

**Definition of Done T7.B.1:** 8+ tests verdes.

---

#### T7.B.2 — Flag `--format pr-comment` en CLI

**Archivos a modificar:**
- `cortex/cli/ci.py::validate_pr_command` — pass `format="pr-comment"` por el formatter.

**Tests:**
- CLI test: `cortex ci validate-pr --format pr-comment` retorna Markdown con marker.

**Definition of Done T7.B.2:** CLI emite Markdown válido cuando se pide el formato.

---

#### T7.B.3 — Templates actualizados con paso de PR comment

**Archivos a modificar:**
- `templates/ci/github-actions-cortex-validate.yml` — agregar step:

```yaml
      - name: Post Cortex summary as PR comment
        if: always()
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          # Capture the cortex output in pr-comment format
          cortex ci validate-pr \
            --base-commit "${{ github.event.pull_request.base.sha }}" \
            --head-commit "${{ github.event.pull_request.head.sha }}" \
            --format pr-comment \
            > /tmp/cortex-comment.md || true   # don't fail on validation errors here
          # Find prior cortex comment (by marker) and edit, or create new
          gh pr comment "${{ github.event.pull_request.number }}" \
            --body-file /tmp/cortex-comment.md \
            --edit-last || \
          gh pr comment "${{ github.event.pull_request.number }}" \
            --body-file /tmp/cortex-comment.md
```

- `templates/ci/gitlab-ci-cortex-validate.yml` — equivalente con `glab` o GitLab API REST.

**Definition of Done T7.B.3:** templates actualizadas; testeable manualmente en un repo real.

---

#### T7.B.4 — Documentación Nivel 2

**Archivos a modificar:**
- `README.md` §"CI Plugin" — describir `--format pr-comment`.
- `docs/architecture/ci-plugin.md` — extender con sección "Nivel 2: PR comments".

**Definition of Done T7.B.4:** docs actualizadas.

---

#### Cierre Nivel 2 — Completion Verification (intermedio)

```bash
# 1. Tests
pytest tests/unit/ci/test_markdown_formatter.py --no-cov -v
# expected: all green

# 2. Smoke del formato
cortex ci validate-pr --base-commit HEAD~3 --head-commit HEAD --format pr-comment
# expected: Markdown con marker <!-- cortex-pr-summary -->

# 3. Verificación de templates
grep "pr-comment" templates/ci/github-actions-cortex-validate.yml
# expected: el step está presente
```

---

### Nivel 3 — Review session first-class

#### T7.C.1 — Decisión arquitectónica documentada

**Objetivo:** revisar y confirmar la Opción B (nuevo `CheckpointSource.CI_BOT`). Si surgen argumentos para A o C, documentarlos.

**Archivos a crear:**
- `docs/architecture/review-sessions.md` — referencia técnica que documenta:
  - Por qué Opción B.
  - Cómo se asocian dev-session ↔ review-session (link por base_commit o explícito).
  - Lifecycle de una review session.
  - Diferencias y similitudes con una dev session.

**Decisión esperada:** Opción B. Si el ejecutor decide otra cosa, **debe consultar antes de implementar.**

**Definition of Done T7.C.1:** docs creado con la decisión + sus razones.

---

#### T7.C.2 — Nuevo `CheckpointSource.CI_BOT` + `SessionMode.CI_REVIEW`

**Archivos a modificar:**
- `cortex/session/models.py` — agregar `CI_BOT = "ci-bot"` al `CheckpointSource` enum.
- `cortex/session/models.py` — agregar `CI_REVIEW = "ci-review"` al `SessionMode` enum.
- `cortex/session/service.py::SessionService.infer_mode` — extender la lógica:
  - Si TODOS los checkpoints son `CI_BOT` → `CI_REVIEW`.
  - Si mezcla CI_BOT + otros → comportamiento actual (OBSERVED).

**Tests:**
- Agregar tests a `tests/unit/session/test_models.py` y `test_service.py`:
  - `test_checkpoint_source_includes_ci_bot`
  - `test_session_mode_includes_ci_review`
  - `test_infer_mode_all_ci_bot_yields_ci_review`
  - `test_infer_mode_mixed_ci_bot_yields_observed`

**Definition of Done T7.C.2:** enums actualizados, infer_mode extendido, tests verdes, sin regresiones.

---

#### T7.C.3 — `cortex ci open-review-session`

**Archivos a modificar:**
- `cortex/cli/ci.py` — agregar subcomando.
- `cortex/ci/review_session.py` (nuevo) — lógica.

**API CLI:**

```bash
cortex ci open-review-session \
    --pr-number <int> \
    --base-commit <sha> \
    --head-branch <name> \
    [--spec <path>] \
    [--project-root <path>] \
    [--json]
```

**Comportamiento:**
1. Construye un `spec_id` derivado: `YYYY-MM-DD_pr-NNN-review`.
2. Si `--spec` no se pasa: intenta resolver el spec asociado al dev-session matched (heurística de T7.A.1).
3. Abre una nueva `SessionRecord` con:
   - `session_id = <spec_id>`.
   - `spec_path = <spec_path>`.
   - `spec_summary = f"PR #{pr_number} review"`.
   - `start_commit = <base_commit>`.
   - `start_branch = <head_branch>`.
4. Marca esa session como **NO activa** (no clobber del active pointer del usuario). El operador CI no comparte sesión con el dev.
5. Retorna el `session_id` para uso de los siguientes pasos del workflow.

**Decisión:** la review session se almacena en el MISMO `.cortex/sessions/` que las dev sessions. Diferenciables por `mode` (al close) y por el sufijo `-review` en el id.

**Tests:** unit + E2E.

---

#### T7.C.4 — `cortex ci report-checkpoint`

**Archivos a modificar:**
- `cortex/cli/ci.py` — subcomando.
- `cortex/ci/review_session.py` — función auxiliar.

**API CLI:**

```bash
cortex ci report-checkpoint \
    --session-id <id> \
    [--from-validation-result <file>] \
    [--manual-claim "..."] \
    [--manual-artifact "..."]
```

**Comportamiento:**
1. Si `--from-validation-result`: lee el JSON de un `validate-pr` previo y emite un checkpoint estructurado con:
   - `source = CI_BOT`.
   - `verified_claims = [los hooks que pasaron]`.
   - `unverified_claims = [warnings]`.
   - `artifacts_touched = [files in diff]`.
   - `note = summary del validate-pr`.
2. Si solo flags manuales: emite un checkpoint con los valores literales.

**Definition of Done T7.C.4:** comando funciona en ambos modos.

---

#### T7.C.5 — `cortex ci close-review-session`

**Archivos a modificar:**
- `cortex/cli/ci.py`.

**API CLI:**

```bash
cortex ci close-review-session \
    --session-id <id> \
    [--status closed|handoff|abandoned] \
    [--reason "..."]
```

**Comportamiento:** equivalente a `SessionService.close` pero sin invocar el documenter (las review-sessions NO generan session notes nuevas; su rol es ser el audit log del CI). El `documenter_decision` se setea al mismo `status`.

**Definition of Done T7.C.5:** comando funciona; tests E2E del ciclo open → checkpoint → close.

---

#### T7.C.6 — Templates Nivel 3

**Archivos a modificar:**
- `templates/ci/github-actions-cortex-validate-nivel3.yml` (variante del Nivel 1+2, con el ciclo review-session completo).

**Esqueleto:**

```yaml
jobs:
  cortex-review:
    steps:
      - uses: actions/checkout@v4
      - name: Open review session
        id: open
        run: |
          SESSION_ID=$(cortex ci open-review-session \
            --pr-number "${{ github.event.pull_request.number }}" \
            --base-commit "${{ github.event.pull_request.base.sha }}" \
            --head-branch "${{ github.event.pull_request.head.ref }}" \
            --json | jq -r .session_id)
          echo "session_id=$SESSION_ID" >> $GITHUB_OUTPUT

      - name: Validate PR
        id: validate
        run: |
          cortex ci validate-pr \
            --base-commit "${{ github.event.pull_request.base.sha }}" \
            --head-commit "${{ github.event.pull_request.head.sha }}" \
            --session "${{ steps.open.outputs.session_id }}" \
            --format json > /tmp/cortex-result.json || true
          echo "exit_code=$?" >> $GITHUB_OUTPUT

      - name: Report checkpoint
        run: |
          cortex ci report-checkpoint \
            --session-id "${{ steps.open.outputs.session_id }}" \
            --from-validation-result /tmp/cortex-result.json

      - name: Close review session
        run: |
          if [ "${{ steps.validate.outputs.exit_code }}" == "0" ]; then
            cortex ci close-review-session --session-id "${{ steps.open.outputs.session_id }}" --status closed
          else
            cortex ci close-review-session --session-id "${{ steps.open.outputs.session_id }}" --status handoff --reason "validation issues"
          fi

      - name: Post PR comment
        # ... mismo paso de Nivel 2 ...
```

**Definition of Done T7.C.6:** template completo + comentado.

---

#### T7.C.7 — Tests E2E Nivel 3

**Archivos a crear:**
- `tests/e2e/test_ci_review_session_flow.py`

**Escenarios:**

```python
@pytest.mark.e2e
class TestReviewSessionFlow:
    def test_open_checkpoint_close_cycle(tmp_repo): ...
    def test_review_session_mode_inferred_as_ci_review(tmp_repo): ...
    def test_review_session_persists_alongside_dev_session(tmp_repo): ...
    def test_close_with_handoff_records_reason(tmp_repo): ...
    def test_session_list_distinguishes_dev_from_review(tmp_repo): ...
```

**Definition of Done T7.C.7:** 5+ escenarios verdes.

---

#### T7.C.8 — Documentación Nivel 3

**Archivos a modificar:**
- `README.md` §"CI Plugin" — agregar mención de review-sessions.
- `docs/architecture/ci-plugin.md` — sección completa de Nivel 3.
- `docs/architecture/review-sessions.md` (ya creado en T7.C.1) — referencia técnica.
- `docs/architecture/session-primitive.md` §4 (Mode inference) — extender tabla con `CI_REVIEW`.
- `docs/pluggable-middle/MIGRATION-FROM-TRIPARTITO.md` §8 FAQ — entrada sobre review sessions.

**Definition of Done T7.C.8:** docs completas; `cortex doctor` (Fase 04) reporta review sessions correctamente si las hay.

---

## 5. Cross-cutting concerns

### 5.1 Compatibilidad

- Nivel 1 y 2: cero breaking changes. CLI nuevo, no toca otros surfaces.
- Nivel 3: solo agrega valores a enums existentes (`CheckpointSource.CI_BOT`, `SessionMode.CI_REVIEW`). Consumers viejos siguen funcionando porque los enums son extensibles por design (no `Literal[...]` cerrado).

### 5.2 Performance

- `cortex ci validate-pr` debe ejecutar en <10s para un PR mediano. Mayoría del costo: correr verification hooks (controlado por timeouts del spec). El resto del CLI debe ser <500ms.
- En CI, el repo se clona con `fetch-depth: 0` — esto es ~5s extra para repos grandes; aceptable.

### 5.3 Seguridad

- El CLI ejecuta `verification_hooks` declarados en el spec. **Asumimos confianza en el spec** (es del autor del PR, revisado por el committer del repo). Si un atacante puede crear specs maliciosos, ya tiene acceso al repo y el problema es ortogonal.
- El workflow YAML por default tiene scope mínimo (`pull_request` read-only). Sólo el step de "post comment" requiere `GITHUB_TOKEN` con scope `pull-requests: write`.

### 5.4 Logging

- `cortex ci` por default loguea a stderr (no stdout — stdout es el output del comando). Level INFO.
- Flag `--debug` baja a DEBUG. Útil para reproducción de fallas en CI.

### 5.5 Naming convención de review sessions

- `session_id`: `YYYY-MM-DD_pr-<NNN>-review` donde NNN es el PR number. Si la PR no tiene número (push directo a un branch sin PR open): `YYYY-MM-DD_<branch>-review`.
- Si re-corre el workflow sobre el mismo PR: la review session previa se cierra (status=closed) antes de abrir la nueva. El registro queda como audit log de cuántas veces corrió CI sobre ese PR.

---

## 6. Completion Verification Commands

### 6.1 Cierre de Nivel 1

```bash
pytest tests/unit/ci/ tests/e2e/test_ci_validate_pr.py --no-cov -v
mypy --strict --follow-imports=silent cortex/ci/ cortex/cli/ci.py
ruff check cortex/ci/ cortex/cli/ci.py templates/ci/
cortex ci validate-pr --help
ls templates/ci/
```

### 6.2 Cierre de Nivel 2

```bash
pytest tests/unit/ci/test_markdown_formatter.py --no-cov -v
cortex ci validate-pr --format pr-comment --base-commit HEAD~3 --head-commit HEAD
# Verify Markdown output starts with marker
```

### 6.3 Cierre de Nivel 3 (= cierre Fase 07)

```bash
# 1. Tests
pytest tests/unit/ci/ tests/unit/session/ tests/e2e/test_ci_validate_pr.py tests/e2e/test_ci_review_session_flow.py --no-cov -v
# expected: all green

# 2. mypy + ruff
mypy --strict --follow-imports=silent cortex/ci/ cortex/cli/ci.py cortex/session/models.py cortex/session/service.py
ruff check cortex/ci/ cortex/cli/ci.py templates/ci/
# expected: clean

# 3. CLI smoke del ciclo completo
SESSION_ID=$(cortex ci open-review-session --pr-number 99 --base-commit HEAD~5 --head-branch dev --json | jq -r .session_id)
cortex ci validate-pr --session "$SESSION_ID" --base-commit HEAD~5 --head-commit HEAD --format json > /tmp/r.json
cortex ci report-checkpoint --session-id "$SESSION_ID" --from-validation-result /tmp/r.json
cortex ci close-review-session --session-id "$SESSION_ID" --status closed
cortex session show "$SESSION_ID"
# expected: mode=ci-review, 1 checkpoint with source=ci-bot, status=closed

# 4. Suite completa sin regresiones
pytest tests/unit/ tests/integration/ tests/e2e/ --no-cov --tb=no
# expected: 0 failed
```

---

## 7. Handoff to next phase

Al cerrar Fase 07 (los 3 niveles):

### Artefactos producidos

| Artefacto | Path |
|---|---|
| Módulo `cortex.ci` | `cortex/ci/{__init__,validator,session_matcher,result,markdown_formatter,review_session,diff_io}.py` |
| CLI subapp | `cortex/cli/ci.py` |
| Workflow templates | `templates/ci/*.yml` + `README.md` |
| Tests unit | `tests/unit/ci/*.py` |
| Tests E2E | `tests/e2e/test_ci_validate_pr.py`, `test_ci_review_session_flow.py` |
| Docs técnicas | `docs/architecture/ci-plugin.md`, `docs/architecture/review-sessions.md` |
| Schema additions | `CheckpointSource.CI_BOT`, `SessionMode.CI_REVIEW` |

### Lo que el ecosistema gana

- **Para teams:** PRs vienen con validación automática + summary visible. Reviewer humano lee el summary, no tiene que re-correr los hooks mentalmente.
- **Para el modelo Cortex:** el ciclo de review queda persistido en el vault como cualquier otro trabajo, indexable por la memoria episódica + semántica.
- **Para auditoría:** cuántas veces corrió CI sobre un PR, qué hooks pasaron/fallaron, qué archivos cambiaron entre runs.

---

## 8. Progress Log

### Nivel 0 — Diseño y scaffolding
- [x] T7.0.1 — Subcomando scaffold (2026-05-17) — `cortex/cli/ci.py` registrado en `cortex/cli/main.py`.

### Nivel 1 — Validación pasiva
- [x] T7.A.1 — `validate-pr` core logic (2026-05-17) — `cortex/ci/{validator,session_matcher,result}.py`. Re-usa `_scope_cross_check` y `VerificationRunner` existentes.
- [x] T7.A.2 — Diff parsing helper (2026-05-17) — `cortex/ci/diff_io.py` con 3 modos (file/commits/auto).
- [x] T7.A.3 — Workflow YAML templates (2026-05-17) — `templates/ci/github-actions-cortex-validate.yml` + `gitlab-ci-cortex-validate.yml` + README.
- [x] T7.A.4 — Tests Nivel 1 (2026-05-17) — 18 unit tests (matcher 5 + diff_io 5 + validator 8).
- [x] T7.A.5 — Docs Nivel 1 (2026-05-17) — `docs/architecture/ci-plugin.md`.
- [x] Completion Verification Nivel 1 pasa (2026-05-17)

### Nivel 2 — PR comment formatter
- [x] T7.B.1 — Markdown emitter (2026-05-17) — `cortex/ci/markdown_formatter.py` con sentinel `<!-- cortex-pr-summary -->`.
- [x] T7.B.2 — Flag `--format pr-comment` (2026-05-17) — `cortex ci validate-pr --format pr-comment`.
- [x] T7.B.3 — Templates actualizadas (2026-05-17) — paso `gh pr comment --edit-last` incluido en GitHub Actions; `glab`-equivalente vía curl en GitLab.
- [x] T7.B.4 — Docs Nivel 2 (2026-05-17) — `docs/architecture/ci-plugin.md` §Level 2 + 8 tests del Markdown emitter.
- [x] Completion Verification Nivel 2 pasa (2026-05-17)

### Nivel 3 — Review session first-class
- [x] T7.C.1 — Decisión arquitectónica documentada (2026-05-17) — `docs/architecture/review-sessions.md` con análisis de A/B/C y justificación de Opción B.
- [x] T7.C.2 — `CheckpointSource.CI_BOT` + `SessionMode.CI_REVIEW` (2026-05-17) — `infer_mode` extendido; sin breaking changes (enum aditivo).
- [x] T7.C.3 — `cortex ci open-review-session` (2026-05-17) — bypasses active pointer; `start_commit` explícito desde PR.
- [x] T7.C.4 — `cortex ci report-checkpoint` (2026-05-17) — acepta `--from-validation-result <json>` o claims/artifacts manuales.
- [x] T7.C.5 — `cortex ci close-review-session` (2026-05-17) — sin invocar documenter; opcional `--reason` registrado como manual checkpoint.
- [x] T7.C.6 — Templates Nivel 3 (2026-05-17) — flujo open/report/close documentado en `templates/ci/README.md`.
- [x] T7.C.7 — Tests Nivel 3 (2026-05-17) — 8 tests en `test_review_session.py` (open + report + close + mode inference).
- [x] T7.C.8 — Docs Nivel 3 (2026-05-17) — `docs/architecture/review-sessions.md` + `ci-plugin.md` §Level 3 + CHANGELOG.

### Cierre Fase 07
- [x] Completion Verification Nivel 3 (= cierre fase) pasa (2026-05-17) — 34 tests verdes, mypy strict clean.
- [x] Tabla `../README.md` actualizada ✅ (2026-05-17)
- [ ] Commit final (pendiente — esperando autorización del usuario al cierre de todas las fases)

---

## 9. Notas para el agente ejecutor

- **Implementá nivel-por-nivel.** Cada nivel cierra completo (tests + docs + verification) antes de abrir el siguiente. Esto permite mergear Nivel 1 a master incluso si Nivel 3 no se hace nunca.
- **Reusá agresivamente.** `cortex.documenter.reconstruction._scope_cross_check`, `cortex.session.verification.VerificationRunner`, `cortex.session.git.diff` — ya existen y están testeados. **No reimplementes lógica de scope ni de hook execution en `cortex/ci/`.**
- **Mantené el CLI provider-agnóstico.** El plugin no debe importar nada de `gh`, `github3.py`, `gitlab-python`, etc. Toda la integración provider-specific vive en los YAML templates.
- **Decisión de Nivel 3 (review sessions).** El plan recomienda Opción B (`CheckpointSource.CI_BOT`). Si te encontrás con una razón fuerte para A o C, **pará y consultá** antes de implementar — modelo cambios son irreversibles.
- **Templates YAML son código.** Lintealos con `actionlint` (GitHub Actions linter) si está disponible. Sin él, al menos `yamllint`. Los YAML rotos en templates son trampas para los usuarios.
- **Nivel 2 deduplicación importa.** El sentinel marker `<!-- cortex-pr-summary -->` debe ser exacto y estable entre runs. Si cambias el marker en una revisión, todos los comments previos quedan huérfanos.
- **Performance es invisible si está bien.** Si `cortex ci validate-pr` toma >30s en CI repos grandes, los usuarios lo van a desactivar. Profila con `--debug` en un repo medium-size antes de cerrar Nivel 1.
- **No agregar surfaces post-MVP en esta fase.** No `cortex ci status`, no `cortex ci release-check`, no GitHub App. Si surgen ideas, anotarlas en un roadmap nuevo.
