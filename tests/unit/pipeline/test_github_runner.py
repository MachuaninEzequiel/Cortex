"""Tests del workflow YAML generado por :class:`GithubRunner`.

Bug #7 (deep review 2026-08): el coverage gate leía
``/tmp/test-output.txt`` que NADIE escribía (coverage siempre 0) y el
security gate venía neutralizado de fábrica (``pip-audit || true``).
Estos tests congelan la corrección: el step de tests guarda su output
donde el gate lo lee, y pip-audit corre sin cortocircuito.
"""

from __future__ import annotations

import yaml

from cortex.pipeline.domain.types import StageType
from cortex.pipeline.runners.github import GitHubActionsRunner


def _runner() -> GitHubActionsRunner:
    return GitHubActionsRunner()


class TestCoverageGate:
    def test_step_tests_guarda_output_donde_el_gate_lee(self) -> None:
        """El output de pytest debe aterrizar en /tmp/test-output.txt."""
        out = _runner().generate_pr_workflow([StageType.TEST], min_coverage=80)

        assert "tee /tmp/test-output.txt" in out
        # El exit code real debe sobrevivir al pipe (no enmascarar fallos).
        assert "PIPESTATUS[0]" in out
        # Y el gate sigue leyendo exactamente ese archivo.
        assert "open('/tmp/test-output.txt')" in out

    def test_sin_min_coverage_no_genera_gate_de_cobertura(self) -> None:
        out = _runner().generate_pr_workflow([StageType.TEST], min_coverage=0)
        assert "Check Coverage Gate" not in out


class TestSecurityGate:
    def test_default_no_neutraliza_pip_audit(self) -> None:
        out = _runner().generate_pr_workflow([StageType.SECURITY_SCAN])
        assert "pip-audit || true" not in out
        assert "run: pip-audit" in out

    def test_audit_cmd_custom_se_respeta_verbatim(self) -> None:
        out = _runner().generate_pr_workflow(
            [StageType.SECURITY_SCAN], audit_cmd="safety check --short"
        )
        assert "run: safety check --short" in out


class TestYamlGenerado:
    def test_workflow_completo_parsea_como_yaml_valido(self) -> None:
        out = _runner().generate_pr_workflow(
            [StageType.LINT, StageType.TEST, StageType.SECURITY_SCAN],
            min_coverage=75,
        )
        data = yaml.safe_load(out)
        assert isinstance(data, dict)
        assert "jobs" in data
        job = next(iter(data["jobs"].values()))
        steps = job["steps"]
        nombres = [s.get("name", "") for s in steps]
        assert any("Tests" in n for n in nombres)
        assert any("Check Coverage Gate" in n for n in nombres)
        assert any("Security Audit" in n for n in nombres)
