"""E2E scenarios: budget and context metrics per profile.

Cierre Obra 07 (T5): actualizado a la arquitectura post-recatorización.

- El contrato estático de presupuestos vive hoy en
  ``cortex.context_enricher.budget_resolver`` (gateado también por
  ``tests/unit/context_enricher/test_budget_resolver.py``); el viejo
  ``cortex.autopilot.context_budget`` fue eliminado.
- El ``StateStore`` de ``.cortex/run/autopilot/sessions/*.json`` ya no
  existe: la detección se expone en el payload ``--json`` de ``preflight``
  y el presupuesto se resuelve en retrieval vía ``resolve_budget_profile``.

Valida que cada task type respeta su contrato de presupuesto:
- question-only: cero items/carácteres
- docs-only: bajo
- fast-code: moderado
- deep-code: amplio (+ razón de deep track en preflight)
"""
from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from cortex.autopilot.cli import app
from cortex.context_enricher.budget_resolver import resolve_budget_profile

runner = CliRunner()


class TestBudgetProfiles:
    """Validate static budget profile contracts (budget_resolver actual)."""

    def test_question_only_zero_budget(self) -> None:
        prof = resolve_budget_profile("question-only")
        assert prof["top_k"] == 0
        assert prof["max_chars"] == 0

    def test_docs_only_low_budget(self) -> None:
        prof = resolve_budget_profile("docs-only")
        assert prof["top_k"] == 3
        assert prof["max_chars"] == 1200

    def test_fast_code_moderate_budget(self) -> None:
        prof = resolve_budget_profile("fast-code")
        assert prof["top_k"] == 5
        assert prof["max_chars"] == 2000

    def test_deep_code_allows_more_context(self) -> None:
        prof = resolve_budget_profile("deep-code")
        assert prof["top_k"] == 8
        assert prof["max_chars"] == 3500

    def test_unknown_task_falls_back_to_default(self) -> None:
        unknown = resolve_budget_profile("some-future-type")
        default = resolve_budget_profile(None)
        assert unknown == default
        assert unknown["top_k"] == 5


class TestDetectionAtRuntime:
    """La detección que alimenta el presupuesto se expone en preflight."""

    def test_question_only_detected(
        self, autopilot_workspace: Path, autopilot_session: str
    ) -> None:
        del autopilot_session  # la detección es stateless; sesión no requerida
        r = runner.invoke(
            app,
            [
                "preflight",
                "--project-root",
                str(autopilot_workspace),
                "--request",
                "What is the auth flow?",
                "--json",
            ],
        )
        assert r.exit_code == 0, r.output
        data = json.loads(r.output)
        assert data["task_type"] == "question-only"

    def test_deep_code_records_reason(
        self, autopilot_workspace: Path, autopilot_session: str
    ) -> None:
        files = [f"m{i}.py" for i in range(6)]
        cmd = [
            "preflight",
            "--project-root",
            str(autopilot_workspace),
            "--request",
            "Migrate legacy modules to new architecture",
            "--json",
        ]
        for f in files:
            cmd.extend(["--file", f])
        r = runner.invoke(app, cmd)
        assert r.exit_code == 0, r.output
        data = json.loads(r.output)
        assert data["task_type"] == "deep-code"
        # La razón del deep track hoy viaja en el propio payload.
        assert len(data.get("reason", "")) > 0

    def test_profile_mapping_consistency(self) -> None:
        """Every task type maps to its known budget envelope."""
        esperados = {
            "question-only": (0, 0),
            "docs-only": (3, 1200),
            "fast-code": (5, 2000),
            "deep-code": (8, 3500),
            "security": (8, 3500),
            "ambiguous": (3, 1500),
            "noop": (0, 0),
        }
        for task_type, (top_k, max_chars) in esperados.items():
            profile = resolve_budget_profile(task_type)
            assert (profile["top_k"], profile["max_chars"]) == (
                top_k,
                max_chars,
            ), f"{task_type} -> {(profile['top_k'], profile['max_chars'])}"
