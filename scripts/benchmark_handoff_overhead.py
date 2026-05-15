"""Benchmark: handoff validation overhead (Item #17 PLAN-DEUDA-RESIDUAL).

Measures the Cortex-side overhead of the handoff validation gate. The LLM
side is simulated with a fixed-delay mock so the comparison isolates the
parse + pydantic validate + dispatch cost in ``CortexMCPServer``.

Usage:
    python scripts/benchmark_handoff_overhead.py

Exits with status 0 when overhead < 10 % (Plan 07 §4 gate); 1 otherwise.
The script does not touch real LLMs, vaults, or MCP transports.
"""

from __future__ import annotations

import argparse
import sys
import time
from typing import Any

from cortex.handoff import AgentHandoff
from cortex.mcp.server import CortexMCPServer


AGENTS = [
    "cortex-sync",
    "cortex-code-explorer",
    "cortex-code-implementer",
    "cortex-documenter",
]


def _sample_handoff(agent: str) -> str:
    handoff = AgentHandoff(
        agent=agent,  # type: ignore[arg-type]
        status="complete",
        verified_claims=["claim 1", "claim 2"],
        unverified_claims=[],
        artifacts_produced=[],
        context_for_next=["next step"],
        suggested_adr=False,
        suggested_adr_reason="",
        suggested_context_terms=[],
    )
    return handoff.to_yaml()


def _build_server() -> CortexMCPServer:
    server = CortexMCPServer.__new__(CortexMCPServer)
    server._called_tools = set()  # type: ignore[attr-defined]
    return server


def _bench_with_validation(
    server: CortexMCPServer, iterations: int, mock_delay: float
) -> float:
    start = time.perf_counter()
    for _ in range(iterations):
        for agent in AGENTS:
            yaml_text = _sample_handoff(agent)
            args: dict[str, Any] = {
                "handoff_yaml": yaml_text,
                "expected_agent": agent,
            }
            server._validate_handoff_text(args)
            time.sleep(mock_delay)
    return time.perf_counter() - start


def _bench_without_validation(iterations: int, mock_delay: float) -> float:
    start = time.perf_counter()
    for _ in range(iterations):
        for agent in AGENTS:
            _sample_handoff(agent)
            time.sleep(mock_delay)
    return time.perf_counter() - start


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iterations", type=int, default=100)
    parser.add_argument(
        "--mock-delay",
        type=float,
        default=0.005,
        help="Simulated per-step LLM delay in seconds (default 5ms).",
    )
    parser.add_argument(
        "--gate",
        type=float,
        default=10.0,
        help="Pass/fail overhead threshold in percent (default 10).",
    )
    args = parser.parse_args(argv)

    server = _build_server()
    t_with = _bench_with_validation(server, args.iterations, args.mock_delay)
    t_without = _bench_without_validation(args.iterations, args.mock_delay)
    if t_without <= 0:
        print("Mock delay too low to measure overhead reliably.")
        return 1
    overhead_pct = (t_with - t_without) / t_without * 100

    print(f"Iterations:           {args.iterations} × {len(AGENTS)} agents")
    print(f"Mock LLM delay:       {args.mock_delay * 1000:.2f} ms")
    print(f"Without validation:   {t_without:.3f}s")
    print(f"With validation:      {t_with:.3f}s")
    print(f"Overhead:             {overhead_pct:+.2f}%")
    print(f"Gate (< {args.gate}%):       {'PASS' if overhead_pct < args.gate else 'FAIL'}")
    return 0 if overhead_pct < args.gate else 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
