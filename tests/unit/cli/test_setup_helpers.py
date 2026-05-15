"""Tests para cortex.cli._setup_helpers (Fase 6 plan multi-IDE & MCP hardening).

El helper ``select_ide_interactive`` centraliza la seleccion de IDE para
``cortex setup full`` y ``cortex setup agent``. Cierra la asimetria
pre-Fase 6 donde solo ``setup_agent`` tenia prompt interactivo.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest

from cortex.cli._setup_helpers import select_ide_interactive

# ---------------------------------------------------------------------------
# Path 1: --ide explicito (CLI flag), sin prompt
# ---------------------------------------------------------------------------


def test_provided_ide_returned_as_is_interactive_mode():
    """Si el usuario paso --ide, no prompt-ear (incluso en modo interactivo)."""
    with patch("cortex.cli._setup_helpers.typer.prompt") as mock_prompt:
        result = select_ide_interactive(provided_ide="claude_code", non_interactive=False)
    assert result == "claude_code"
    mock_prompt.assert_not_called()


def test_provided_ide_returned_as_is_noninteractive_mode():
    """--ide tiene precedencia sobre --non-interactive."""
    with patch("cortex.cli._setup_helpers.typer.prompt") as mock_prompt:
        result = select_ide_interactive(provided_ide="opencode", non_interactive=True)
    assert result == "opencode"
    mock_prompt.assert_not_called()


# ---------------------------------------------------------------------------
# Path 2: --non-interactive sin --ide -> None (no prompt)
# ---------------------------------------------------------------------------


def test_noninteractive_without_ide_returns_none_no_prompt():
    """CI-friendly: --non-interactive sin --ide devuelve None sin prompt."""
    with patch("cortex.cli._setup_helpers.typer.prompt") as mock_prompt:
        result = select_ide_interactive(provided_ide=None, non_interactive=True)
    assert result is None
    mock_prompt.assert_not_called()


# ---------------------------------------------------------------------------
# Path 3: modo interactivo (default) — menu numerado
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_supported_ides():
    """Mock get_supported_ides para que los tests no dependan del registry real."""
    fake_list = ["claude_code", "opencode", "codex", "pi"]
    with patch("cortex.cli._setup_helpers.cortex_ide.get_supported_ides", return_value=fake_list):
        yield fake_list


def test_interactive_choice_zero_returns_none(mock_supported_ides):
    """Ingresar '0' (default) devuelve None (skip IDE)."""
    with patch("cortex.cli._setup_helpers.typer.prompt", return_value="0"):
        result = select_ide_interactive(provided_ide=None, non_interactive=False)
    assert result is None


def test_interactive_choice_by_number(mock_supported_ides):
    """Ingresar '1' devuelve el primer IDE soportado."""
    with patch("cortex.cli._setup_helpers.typer.prompt", return_value="1"):
        result = select_ide_interactive(provided_ide=None, non_interactive=False)
    assert result == "claude_code"


def test_interactive_choice_by_name(mock_supported_ides):
    """Ingresar el nombre exacto devuelve ese IDE."""
    with patch("cortex.cli._setup_helpers.typer.prompt", return_value="opencode"):
        result = select_ide_interactive(provided_ide=None, non_interactive=False)
    assert result == "opencode"


def test_interactive_choice_invalid_number_returns_none(mock_supported_ides):
    """Numero fuera de rango devuelve None con mensaje de warning."""
    with patch("cortex.cli._setup_helpers.typer.prompt", return_value="99"):
        result = select_ide_interactive(provided_ide=None, non_interactive=False)
    assert result is None


def test_interactive_choice_invalid_name_returns_none(mock_supported_ides):
    """Nombre que no es IDE soportado devuelve None."""
    with patch("cortex.cli._setup_helpers.typer.prompt", return_value="some-random-name"):
        result = select_ide_interactive(provided_ide=None, non_interactive=False)
    assert result is None


def test_interactive_choice_last_index(mock_supported_ides):
    """El ultimo numero del menu devuelve el ultimo IDE de la lista."""
    n = len(mock_supported_ides)
    with patch("cortex.cli._setup_helpers.typer.prompt", return_value=str(n)):
        result = select_ide_interactive(provided_ide=None, non_interactive=False)
    assert result == mock_supported_ides[-1]


# ---------------------------------------------------------------------------
# Garantia critica: en modo interactivo SE LISTAN todos los IDEs soportados
# ---------------------------------------------------------------------------


def test_interactive_mode_displays_full_supported_list(mock_supported_ides, capsys):
    """El menu interactivo debe listar TODOS los IDEs soportados con su numero."""
    with patch("cortex.cli._setup_helpers.typer.prompt", return_value="0"):
        select_ide_interactive(provided_ide=None, non_interactive=False)

    captured = capsys.readouterr()
    output = captured.out
    for i, ide_name in enumerate(mock_supported_ides, 1):
        assert f"{i}. {ide_name}" in output, (
            f"Menu debe listar el IDE {ide_name} con su indice {i}"
        )
    assert "0. Skip IDE configuration" in output
