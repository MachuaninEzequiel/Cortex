"""Tests de integracion para los comandos setup post-Fase 6.

Verifica que ``cortex setup full`` y ``cortex setup agent`` comparten el
helper ``select_ide_interactive`` y respetan ``--ide`` + ``--non-interactive``
sin colgarse en prompts.
"""
from __future__ import annotations

from unittest.mock import patch

from typer.testing import CliRunner

from cortex.cli.main import app

runner = CliRunner()


def _fake_summary() -> dict:
    """Summary minimal para pasar format_summary sin tocar disco."""
    return {
        "project_name": "test-project",
        "language": "python",
        "package_manager": "uv",
        "layout_mode": "new",
        "workspace_root": ".cortex",
        "created": [],
        "skipped": [],
        "warnings": [],
    }


# ---------------------------------------------------------------------------
# setup full — Fase 6 cierra la asimetria
# ---------------------------------------------------------------------------


def test_setup_full_non_interactive_skips_ide_prompt(tmp_path):
    """``cortex setup full --non-interactive --git-depth 50`` no debe prompt-ear.

    Si el usuario no pasa --ide, en non-interactive el helper devuelve None
    y el orchestrator no configura ningun IDE — eso es CI-safe por diseño.
    """
    # Mock orchestrator para no ejecutar setup real
    with patch("cortex.setup.orchestrator.SetupOrchestrator") as mock_orch_class, \
         patch("cortex.cli._setup_helpers.typer.prompt") as mock_prompt:
        mock_orch = mock_orch_class.return_value
        mock_orch.run.return_value = _fake_summary()

        result = runner.invoke(app, ["setup", "full", "--non-interactive", "--git-depth", "50"])

    assert result.exit_code == 0, result.output
    mock_prompt.assert_not_called()  # NUNCA debe haber promptaeado nada
    # Y el orchestrator debe haberse invocado con ide=None
    call_kwargs = mock_orch.run.call_args.kwargs
    assert call_kwargs["ide"] is None


def test_setup_full_with_ide_flag_skips_prompt(tmp_path):
    """``cortex setup full --ide claude_code --non-interactive --git-depth 50``
    no debe prompt-ear y debe pasar claude_code al orchestrator."""
    with patch("cortex.setup.orchestrator.SetupOrchestrator") as mock_orch_class, \
         patch("cortex.cli._setup_helpers.typer.prompt") as mock_prompt:
        mock_orch = mock_orch_class.return_value
        mock_orch.run.return_value = _fake_summary()

        result = runner.invoke(app, [
            "setup", "full", "--ide", "claude_code",
            "--non-interactive", "--git-depth", "50",
        ])

    assert result.exit_code == 0, result.output
    mock_prompt.assert_not_called()
    call_kwargs = mock_orch.run.call_args.kwargs
    assert call_kwargs["ide"] == "claude_code"


# ---------------------------------------------------------------------------
# setup agent — paridad con setup full post-Fase 6
# ---------------------------------------------------------------------------


def test_setup_agent_now_supports_non_interactive_flag(tmp_path):
    """Fase 6 agrega --non-interactive a setup_agent (paridad con setup_full)."""
    with patch("cortex.setup.orchestrator.SetupOrchestrator") as mock_orch_class, \
         patch("cortex.cli._setup_helpers.typer.prompt") as mock_prompt:
        mock_orch = mock_orch_class.return_value
        mock_orch.run.return_value = _fake_summary()

        result = runner.invoke(app, [
            "setup", "agent", "--non-interactive", "--git-depth", "50",
        ])

    assert result.exit_code == 0, result.output
    mock_prompt.assert_not_called()
    call_kwargs = mock_orch.run.call_args.kwargs
    assert call_kwargs["ide"] is None


def test_setup_agent_with_ide_flag_no_prompt(tmp_path):
    """``cortex setup agent --ide opencode`` no debe prompt-ear."""
    with patch("cortex.setup.orchestrator.SetupOrchestrator") as mock_orch_class, \
         patch("cortex.cli._setup_helpers.typer.prompt") as mock_prompt:
        mock_orch = mock_orch_class.return_value
        mock_orch.run.return_value = _fake_summary()

        result = runner.invoke(app, [
            "setup", "agent", "--ide", "opencode",
            "--non-interactive", "--git-depth", "50",
        ])

    assert result.exit_code == 0, result.output
    mock_prompt.assert_not_called()
    call_kwargs = mock_orch.run.call_args.kwargs
    assert call_kwargs["ide"] == "opencode"


# ---------------------------------------------------------------------------
# Garantia: ambos comandos comparten el helper (no duplicacion)
# ---------------------------------------------------------------------------


def test_setup_agent_calls_select_ide_helper():
    """setup_agent debe invocar select_ide_interactive (no implementar prompt inline)."""
    with patch("cortex.cli._setup_helpers.select_ide_interactive", return_value=None) as mock_helper, \
         patch("cortex.setup.orchestrator.SetupOrchestrator") as mock_orch_class:
        mock_orch_class.return_value.run.return_value = {"created": [], "skipped": [], "warnings": []}
        runner.invoke(app, ["setup", "agent", "--non-interactive", "--git-depth", "50"])

    mock_helper.assert_called_once()


def test_setup_full_calls_select_ide_helper():
    """setup_full debe invocar select_ide_interactive (post-Fase 6)."""
    with patch("cortex.cli._setup_helpers.select_ide_interactive", return_value=None) as mock_helper, \
         patch("cortex.setup.orchestrator.SetupOrchestrator") as mock_orch_class:
        mock_orch_class.return_value.run.return_value = {"created": [], "skipped": [], "warnings": []}
        runner.invoke(app, ["setup", "full", "--non-interactive", "--git-depth", "50"])

    mock_helper.assert_called_once()
