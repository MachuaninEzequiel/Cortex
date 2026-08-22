"""Tests golden de naming para :class:`WorkItemService`.

Bug #10 (deep review 2026-08): ``import_item`` persiste via el writer
canónico con template ``HU-{external_id}.md`` (routing.py), pero
``get_item_note`` buscaba ``hu/{slug(item_id)}.md`` — nunca encontraba
las notas que él mismo escribía. Este test congela el naming correcto.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cortex.workitems.models import TrackedItem, WorkItemKind, WorkItemSource
from cortex.workitems.providers.base import WorkItemProvider
from cortex.workitems.service import WorkItemService


class FakeProvider(WorkItemProvider):
    """Provider mínimo que devuelve items sintéticos."""

    def source_name(self) -> str:
        return "fake"

    def is_configured(self) -> bool:
        return True

    def get_item(self, external_id: str) -> TrackedItem:
        return TrackedItem(
            id=external_id,
            external_id=external_id,
            source=WorkItemSource.JIRA,
            kind=WorkItemKind.STORY,
            title=f"HU {external_id}",
        )


def _service(tmp_path: Path) -> WorkItemService:
    return WorkItemService(
        vault_path=tmp_path / "vault",
        semantic=_FakeSemantic(),
        episodic=_FakeEpisodic(),
        providers={"fake": FakeProvider()},
    )


class _FakeSemantic:
    def index_file(self, rel_path: str) -> bool:
        return False


class _FakeEpisodic:
    def store(self, **kwargs: object) -> None:  # pragma: no cover - no usado acá
        raise AssertionError


class TestGoldenNaming:
    def test_import_escribe_y_get_encuentra_canonical(self, tmp_path: Path) -> None:
        svc = _service(tmp_path)
        path = svc.import_item("COR-123", provider="fake", remember=False)

        assert path.name == "HU-COR-123.md"
        assert path.parent.name == "hu"

        encontrado = svc.get_item_note("COR-123")
        assert encontrado == path

    def test_external_id_con_caracteres_raros_redondea(self, tmp_path: Path) -> None:
        svc = _service(tmp_path)
        svc.import_item("PROJ-42", provider="fake", remember=False)
        assert svc.get_item_note("PROJ-42").exists()

    def test_legacy_slug_sigue_resolviendo(self, tmp_path: Path) -> None:
        """Notas viejas escritas con slug (si existen) no se pierden."""
        svc = _service(tmp_path)
        hu = tmp_path / "vault" / "hu"
        hu.mkdir(parents=True)
        legacy = hu / "cor-999.md"
        legacy.write_text("---\ntitle: x\n---\n", encoding="utf-8")

        assert svc.get_item_note("COR-999") == legacy

    def test_no_existente_lanza_file_not_found(self, tmp_path: Path) -> None:
        svc = _service(tmp_path)
        with pytest.raises(FileNotFoundError):
            svc.get_item_note("NOPE-1")
