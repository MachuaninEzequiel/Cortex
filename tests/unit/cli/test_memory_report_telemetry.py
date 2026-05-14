"""Tests for ``cortex memory-report --telemetry`` (Fase 05 deuda)."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from cortex.cli.main import app

runner = CliRunner()


@pytest.fixture
def fake_layout(tmp_path: Path):
    """Return a SimpleNamespace mimicking WorkspaceLayout, plus paths."""
    layout = SimpleNamespace(workspace_root=tmp_path)
    return layout


@pytest.fixture
def fake_service():
    """Minimal stand-in for EnterpriseReportingService.build_memory_report."""

    class FakeReport:
        project_root = "/tmp/proj"
        enterprise_enabled = False
        sources = []

        class _Promo:
            enabled = False
            warnings = []

        promotion = _Promo()

        def model_dump(self, **kw):
            return {
                "project_root": self.project_root,
                "enterprise_enabled": self.enterprise_enabled,
                "sources": [],
                "promotion": {"enabled": False, "warnings": []},
            }

        def model_dump_json(self, **kw):
            return json.dumps(self.model_dump())

    return FakeReport()


def _patch_layout_and_service(fake_layout, fake_service):
    """Patch resolve and reporting service to inject fakes into the CLI."""
    return (
        patch(
            "cortex.cli.main.WorkspaceLayout.discover",
            return_value=fake_layout,
        ),
        patch(
            "cortex.enterprise.reporting.EnterpriseReportingService.from_project_root",
            return_value=SimpleNamespace(
                build_memory_report=lambda scope: fake_service,
            ),
        ),
    )


def test_memory_report_without_telemetry_omits_section(
    fake_layout, fake_service, tmp_path: Path
) -> None:
    p1, p2 = _patch_layout_and_service(fake_layout, fake_service)
    with p1, p2:
        result = runner.invoke(
            app, ["memory-report", "--project-root", str(tmp_path)]
        )
    assert result.exit_code == 0
    assert "Retrieval Telemetry" not in result.stdout


def test_memory_report_with_telemetry_empty(
    fake_layout, fake_service, tmp_path: Path
) -> None:
    p1, p2 = _patch_layout_and_service(fake_layout, fake_service)
    with p1, p2:
        result = runner.invoke(
            app,
            [
                "memory-report",
                "--project-root", str(tmp_path),
                "--telemetry",
            ],
        )
    assert result.exit_code == 0
    assert "Retrieval Telemetry" in result.stdout
    assert "enrichments: 0" in result.stdout


def test_memory_report_with_telemetry_populated(
    fake_layout, fake_service, tmp_path: Path
) -> None:
    # Seed a telemetry JSONL with one enrichment and one citation.
    events_dir = tmp_path / ".cortex"
    events_dir.mkdir()
    events_path = events_dir / "enrichment-events.jsonl"
    events_path.write_text(
        json.dumps({
            "event_type": "enrichment",
            "run_id": "abc",
            "timestamp": "2099-01-01T00:00:00+00:00",
            "latency_ms": 50,
            "total_searches": 1, "total_raw_hits": 1,
            "total_items": 1, "total_chars": 100, "within_budget": True,
            "items_offered": [
                {"source_id": "item-1", "matched_by": ["topic_search"]}
            ],
        }) + "\n" +
        json.dumps({
            "event_type": "citation",
            "run_id": "abc",
            "timestamp": "2099-01-01T00:00:01+00:00",
            "source_id": "item-1",
        }) + "\n",
        encoding="utf-8",
    )
    p1, p2 = _patch_layout_and_service(fake_layout, fake_service)
    with p1, p2:
        result = runner.invoke(
            app,
            [
                "memory-report",
                "--project-root", str(tmp_path),
                "--telemetry",
                "--since-days", "0",  # 0 means "no filter"
            ],
        )
    # With since_days=0, the cutoff is now; events at 2099 still pass.
    assert result.exit_code == 0
    assert "Retrieval Telemetry" in result.stdout


def test_memory_report_json_output_with_telemetry(
    fake_layout, fake_service, tmp_path: Path
) -> None:
    p1, p2 = _patch_layout_and_service(fake_layout, fake_service)
    with p1, p2:
        result = runner.invoke(
            app,
            [
                "memory-report",
                "--project-root", str(tmp_path),
                "--telemetry",
                "--json",
            ],
        )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert "telemetry" in payload
    assert payload["telemetry"]["enrichments"] == 0
