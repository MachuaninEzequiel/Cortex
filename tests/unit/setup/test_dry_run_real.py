"""Bug #13: run(dry_run=True) NO debe crear NADA en disco (plan 01 §4).

Antes: SetupOrchestrator.run(dry_run=True) ejecutaba los pasos mutadores
igual y creaba 46 ítems reales en modo AGENT. Ahora los flujos no-
enterprise registran el plan en ``created`` sin tocar disco.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cortex.setup.orchestrator import SetupMode, SetupOrchestrator


@pytest.mark.parametrize("mode", [SetupMode.AGENT, SetupMode.PIPELINE, SetupMode.WEBGRAPH])
def test_dry_run_crea_cero_archivos(tmp_path: Path, mode: SetupMode) -> None:
    orch = SetupOrchestrator(root=tmp_path)
    summary = orch.run(mode, non_interactive=True, dry_run=True, git_depth=0)

    archivos = [p for p in tmp_path.rglob("*") if p.is_file()]
    assert archivos == [], f"dry-run creó archivos reales: {archivos[:5]}"
    assert summary["created"], "el plan debe quedar registrado en created"
    assert all(c.startswith("[dry-run]") for c in summary["created"])


def test_run_real_si_crea(tmp_path: Path) -> None:
    """Sanity opuesto: sin dry-run SÍ crea (mismo modo, mismo repo)."""
    orch = SetupOrchestrator(root=tmp_path)
    summary = orch.run(SetupMode.AGENT, non_interactive=True, dry_run=False, git_depth=0)
    creados = [c for c in summary["created"] if not c.startswith("[dry-run]")]
    assert creados
