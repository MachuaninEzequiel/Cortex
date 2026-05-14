"""Tests for ``make_observer`` helper and remaining defensive paths."""

from __future__ import annotations

import json
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from cortex.context_enricher.telemetry import (
    PersistentObserver,
    _parse_ts,
    _percentile,
    make_observer,
)


# ---------------------------------------------------------------------------
# make_observer
# ---------------------------------------------------------------------------


def test_make_observer_with_workspace_layout(tmp_path: Path) -> None:
    layout = SimpleNamespace(workspace_root=tmp_path)
    obs = make_observer(layout)
    assert obs.enabled
    assert obs.path == (tmp_path / ".cortex" / "enrichment-events.jsonl").resolve()


def test_make_observer_with_project_root_fallback(tmp_path: Path) -> None:
    obs = make_observer(workspace_layout=None, project_root=tmp_path)
    assert obs.path == (tmp_path / ".cortex" / "enrichment-events.jsonl").resolve()


def test_make_observer_defaults_to_cwd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    obs = make_observer()
    assert tmp_path in obs.path.parents


def test_make_observer_respects_config_disabled(tmp_path: Path) -> None:
    layout = SimpleNamespace(workspace_root=tmp_path)
    config = {"retrieval": {"telemetry": {"enabled": False}}}
    obs = make_observer(layout, config=config)
    assert not obs.enabled


def test_make_observer_respects_config_path(tmp_path: Path) -> None:
    layout = SimpleNamespace(workspace_root=tmp_path)
    config = {"retrieval": {"telemetry": {"path": "telemetry/custom.jsonl"}}}
    obs = make_observer(layout, config=config)
    assert str(obs.path).endswith(os.path.join("telemetry", "custom.jsonl"))


def test_make_observer_explicit_enabled_overrides_config(tmp_path: Path) -> None:
    layout = SimpleNamespace(workspace_root=tmp_path)
    config = {"retrieval": {"telemetry": {"enabled": False}}}
    obs = make_observer(layout, enabled=True, config=config)
    assert obs.enabled


def test_make_observer_missing_workspace_layout_attr(tmp_path: Path) -> None:
    """When the layout lacks ``workspace_root`` it falls back to project_root/cwd."""
    layout = SimpleNamespace()  # no workspace_root attr
    obs = make_observer(layout, project_root=tmp_path)
    assert tmp_path in obs.path.parents


def test_make_observer_malformed_telemetry_block_is_ignored(tmp_path: Path) -> None:
    layout = SimpleNamespace(workspace_root=tmp_path)
    # telemetry is a string instead of a dict; should not raise.
    config = {"retrieval": {"telemetry": "broken"}}
    obs = make_observer(layout, config=config)
    assert obs.enabled  # falls back to default True


# ---------------------------------------------------------------------------
# Defensive paths in iter_events / aggregate
# ---------------------------------------------------------------------------


def test_iter_events_disabled_returns_empty(tmp_path: Path) -> None:
    obs = PersistentObserver(tmp_path / "events.jsonl", enabled=False)
    assert obs.iter_events() == []


def test_iter_events_oserror_returns_empty(tmp_path: Path) -> None:
    """If the JSONL file cannot be opened, iter_events returns []."""
    path = tmp_path / "events.jsonl"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps({"event_type": "x"}) + "\n", encoding="utf-8")
    obs = PersistentObserver(path)

    # Force an OSError on open by replacing Path.open with one that raises.
    real_open = Path.open

    def boom(self, *args, **kwargs):
        if self == path:
            raise OSError("permission denied")
        return real_open(self, *args, **kwargs)

    with patch.object(Path, "open", boom):
        assert obs.iter_events() == []


def test_parse_ts_invalid_string_returns_none() -> None:
    assert _parse_ts("not-a-date") is None


def test_parse_ts_non_string_returns_none() -> None:
    assert _parse_ts(None) is None
    assert _parse_ts(42) is None
    assert _parse_ts([]) is None


def test_percentile_empty_returns_zero() -> None:
    assert _percentile([], 0.5) == 0.0


def test_percentile_single_value() -> None:
    assert _percentile([42], 0.95) == 42.0


def test_percentile_interpolates() -> None:
    # Median of [10, 20, 30, 40, 50] is 30.
    assert _percentile([10, 20, 30, 40, 50], 0.5) == 30.0


def test_iter_events_skips_blank_lines(tmp_path: Path) -> None:
    """A JSONL with blank lines should be readable and skip them."""
    path = tmp_path / "events.jsonl"
    path.parent.mkdir(exist_ok=True)
    path.write_text(
        "\n"  # blank
        + json.dumps({"event_type": "enrichment", "run_id": "a", "timestamp": "x"}) + "\n"
        + "   \n"  # whitespace
        + json.dumps({"event_type": "citation", "run_id": "a", "timestamp": "y", "source_id": "s"}) + "\n",
        encoding="utf-8",
    )
    obs = PersistentObserver(path)
    events = obs.iter_events()
    assert len(events) == 2


def test_detect_citations_skips_items_without_source_id() -> None:
    """Items missing 'source_id' or duplicates are skipped (continue branch)."""
    from cortex.context_enricher.telemetry import detect_citations

    body = "[[item-1]]"
    # First item has source_id=None (should be skipped),
    # second is the real one, third duplicates the second.
    items = [
        {"source_id": None},
        {"source_id": "item-1.md"},
        {"source_id": "item-1.md"},
    ]
    cited = detect_citations(body, items)
    # Only one cited and not duplicated.
    assert cited == ["item-1.md"]
