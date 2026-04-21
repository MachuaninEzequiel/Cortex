from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from cortex.setup.orchestrator import SetupMode, SetupOrchestrator
from cortex.webgraph.setup import (
    get_missing_webgraph_dependencies,
    install_missing_webgraph_dependencies,
    install_webgraph,
)


def test_install_webgraph_creates_only_webgraph_area(tmp_path: Path) -> None:
    with patch("cortex.webgraph.setup.install_missing_webgraph_dependencies", return_value=(True, [])):
        ok = install_webgraph(tmp_path, interactive=False)

    assert ok is True
    assert (tmp_path / ".cortex" / "webgraph").exists()
    assert (tmp_path / ".cortex" / "webgraph" / "cache").exists()
    assert not (tmp_path / "vault").exists()


def test_setup_orchestrator_webgraph_does_not_create_agent_directories(tmp_path: Path) -> None:
    with patch("cortex.webgraph.setup.install_missing_webgraph_dependencies", return_value=(True, [])):
        orchestrator = SetupOrchestrator(root=tmp_path)
        summary = orchestrator.run(mode=SetupMode.WEBGRAPH)

    assert ".cortex/webgraph/ (configured)" in summary["created"]
    assert not (tmp_path / "vault").exists()
    assert not (tmp_path / ".memory").exists()


def test_missing_dependencies_detector_returns_list() -> None:
    missing = get_missing_webgraph_dependencies()

    assert isinstance(missing, list)


def test_install_missing_dependencies_returns_success_when_nothing_missing() -> None:
    with patch("cortex.webgraph.setup.get_missing_webgraph_dependencies", return_value=[]):
        ok, missing = install_missing_webgraph_dependencies()

    assert ok is True
    assert missing == []


def test_install_missing_dependencies_invokes_pip_when_needed() -> None:
    with patch(
        "cortex.webgraph.setup.get_missing_webgraph_dependencies",
        side_effect=[["flask"], []],
    ), patch("cortex.webgraph.setup.subprocess.check_call") as check_call:
        ok, missing = install_missing_webgraph_dependencies()

    assert ok is True
    assert missing == []
    check_call.assert_called_once()


def test_install_webgraph_returns_false_if_auto_install_fails(tmp_path: Path) -> None:
    with patch(
        "cortex.webgraph.setup.install_missing_webgraph_dependencies",
        return_value=(False, ["flask"]),
    ):
        ok = install_webgraph(tmp_path, interactive=False)

    assert ok is False
    assert not (tmp_path / ".cortex" / "webgraph").exists()
