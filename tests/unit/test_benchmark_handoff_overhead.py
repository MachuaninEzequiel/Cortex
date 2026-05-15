"""Smoke for the handoff overhead benchmark script (Item #17)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "benchmark_handoff_overhead.py"


def _load_script_module():
    spec = importlib.util.spec_from_file_location(
        "_cortex_benchmark_handoff_overhead", SCRIPT_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault(spec.name, module)
    spec.loader.exec_module(module)
    return module


def test_benchmark_main_returns_pass_with_tiny_iterations() -> None:
    """The benchmark must exit 0 (gate PASS) on a fast machine with few iters.

    The mock LLM delay dominates wall time so the validation overhead stays
    well below 10%.
    """
    module = _load_script_module()
    rc = module.main(
        ["--iterations", "5", "--mock-delay", "0.01", "--gate", "30"]
    )
    assert rc == 0


def test_benchmark_main_fails_when_gate_is_zero() -> None:
    module = _load_script_module()
    rc = module.main(
        ["--iterations", "5", "--mock-delay", "0.01", "--gate", "0"]
    )
    assert rc == 1
