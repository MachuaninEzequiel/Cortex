"""Tests Obra 04 Fase E — `cortex reindex` + bilingual setup template."""

from __future__ import annotations

import json
from pathlib import Path

import yaml
from typer.testing import CliRunner

from cortex.cli.main import app

runner = CliRunner()


def _make_project(tmp_path: Path) -> Path:
    """Minimal Cortex project: config.yaml + vault with one doc."""
    root = tmp_path / "proj"
    vault = root / "vault" / "decisions"
    vault.mkdir(parents=True)
    (root / ".cortex").mkdir()
    (root / "config.yaml").write_text(
        yaml.safe_dump(
            {
                "episodic": {
                    "persist_dir": str(root / ".memory" / "chroma"),
                    "embedding_model": "all-MiniLM-L6-v2",
                    "embedding_backend": "onnx",
                },
                "semantic": {"vault_path": str(vault.parent)},
            }
        ),
        encoding="utf-8",
    )
    (vault / "ADR-001.md").write_text(
        "---\ntitle: ADR-001\ntags: [decision]\n---\n\nElegimos Redis para el cache.\n",
        encoding="utf-8",
    )
    return root


def test_reindex_dry_run_touches_nothing(tmp_path: Path) -> None:
    root = _make_project(tmp_path)
    before = sorted(str(p.relative_to(root)) for p in root.rglob("*"))
    result = runner.invoke(
        app, ["reindex", "--project-root", str(root), "--dry-run"]
    )
    assert result.exit_code == 0
    assert "[dry-run]" in result.stdout
    after = sorted(str(p.relative_to(root)) for p in root.rglob("*"))
    assert before == after


def test_reindex_rebuilds_cache_with_backup_and_rollback_assets(tmp_path: Path) -> None:
    root = _make_project(tmp_path)
    vectors = root / ".cortex" / "vectors"
    vectors.mkdir(parents=True)
    (vectors / "index.json").write_text("{}", encoding="utf-8")  # pre-existing cache

    result = runner.invoke(app, ["reindex", "--project-root", str(root)])
    assert result.exit_code == 0, result.output
    backups = list((root / ".cortex").glob("vectors.backup-*"))
    assert len(backups) == 1, "pre-existing cache must be moved to a backup dir"
    # the OLD cache content lives in the backup...
    assert (backups[0] / "index.json").read_text(encoding="utf-8") == "{}"
    # ...and a FRESH cache was rebuilt in place with model identity.
    new_index = json.loads((vectors / "index.json").read_text(encoding="utf-8"))
    assert new_index.get("model_name") == "all-MiniLM-L6-v2"


def test_reindex_prune_old_caches(tmp_path: Path) -> None:
    root = _make_project(tmp_path)
    old1 = root / ".cortex" / "vectors.backup-20200101-000000"
    old2 = root / ".cortex" / "vectors.backup-20200201-000000"
    for d in (old1, old2):
        d.mkdir(parents=True)
        (d / "junk").write_text("x", encoding="utf-8")

    result = runner.invoke(
        app,
        ["reindex", "--project-root", str(root), "--prune-old-caches"],
    )
    assert result.exit_code == 0, result.output
    assert not old1.exists() and not old2.exists()
    remaining = list((root / ".cortex").glob("vectors.backup-*"))
    assert len(remaining) <= 1  # only the backup created by THIS run


def test_reindex_missing_config_errors(tmp_path: Path) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    result = runner.invoke(app, ["reindex", "--project-root", str(empty)])
    assert result.exit_code == 1


def test_setup_template_is_bilingual_by_default(tmp_path: Path) -> None:
    """New projects get the per-language block (es -> e5-large)."""
    from cortex.setup.templates import render_config_yaml
    from cortex.setup.detector import EnvInfo, ProjectContext, StackInfo

    ctx = ProjectContext(
        root=tmp_path,
        stack=StackInfo(language="python", project_name="demo"),
        env=EnvInfo(has_openai_key=False),
    )
    rendered = render_config_yaml(ctx)
    data = yaml.safe_load(rendered)
    emb = data["embedding"]
    assert emb["per_language"]["es"]["model"] == "intfloat/multilingual-e5-large"
    assert emb["backend"] == "fastembed"
