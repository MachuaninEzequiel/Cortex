"""Fixes B3/B4 del review cli (Obra 05 Fase C).

B3: has_any_filter recibía scope/project_id hardcodeados, ignorando los
del usuario → el dispatch cambiaba según combinación de flags.
B4: --format json|compact sin filtros estructurales se ignoraba en
silencio (salida legacy). Ahora --format manda siempre; --json queda
como alias legacy funcional con la salida histórica.
"""

from __future__ import annotations

from cortex.cli._search_filters import has_any_filter


class TestB3Dispatch:
    def test_scope_enterprise_solo_cuenta_como_estructural(self) -> None:
        assert has_any_filter(
            doc_type=[], exclude_doc_type=[], status=[], tag=[], tag_any=[],
            max_age_days=None,
            project_id=None,
            strict=False,
            scope="enterprise",
        ), "scope enterprise explícito debe activar el path estructural"

    def test_project_id_solo_cuenta_como_estructural(self) -> None:
        assert has_any_filter(
            doc_type=[], exclude_doc_type=[], status=[], tag=[], tag_any=[],
            max_age_days=None,
            project_id="acme",
            strict=False,
            scope="local",
        )

    def test_sin_flags_sigue_siendo_legacy(self) -> None:
        assert not has_any_filter(
            doc_type=[], exclude_doc_type=[], status=[], tag=[], tag_any=[],
            max_age_days=None,
            project_id=None,
            strict=False,
            scope="local",
        )


# ── ruteo real del comando search (call-site en cli/main.py) ───────────────


from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from cortex.cli.main import app

runner = CliRunner()


def _fake_memory() -> MagicMock:
    mem = MagicMock()
    mem.workspace_root = Path("/tmp")
    return mem


def _correr_search(args: list[str], tmp_path: Path):
    mem = _fake_memory()
    llamadas = {"enricher": 0, "filters": None, "legacy": 0}

    class FakeEnricher:
        def __init__(self, **kwargs):
            llamadas["enricher"] += 1

        def enrich(self, work, *, top_k=None, filters=None):
            llamadas["filters"] = filters
            from cortex.models import EnrichedContext, WorkContext

            return EnrichedContext(
                work=WorkContext(source="manual", changed_files=[], keywords=[], search_queries=[]),
                items=[], total_searches=0, total_raw_hits=0,
                total_items=0, total_chars=0, within_budget=True,
            )

    mem.retrieve.return_value.unified_hits = []
    with (
        patch("cortex.cli.main._load_memory", return_value=mem),
        patch("cortex.context_enricher.enricher.ContextEnricher", FakeEnricher),
    ):
        resultado = runner.invoke(
            app,
            ["search", "query demo", *args],
        )
    assert resultado.exit_code == 0, resultado.output
    return resultado, llamadas


class TestRuteoReal:
    def test_tag_mas_scope_enterprise_va_a_estructural(self, tmp_path: Path) -> None:
        _, llamadas = _correr_search(["--tag", "auth", "--scope", "enterprise"], tmp_path)
        assert llamadas["enricher"] == 1, "tag+scope debe ir por el path estructural"

    def test_scope_solo_ahora_tambien_es_estructural(self, tmp_path: Path) -> None:
        _, llamadas = _correr_search(["--scope", "enterprise"], tmp_path)
        assert llamadas["enricher"] == 1, "B3: --scope solo caía al legacy"

    def test_format_compact_sin_filtros_no_se_ignora(self, tmp_path: Path) -> None:
        resultado, llamadas = _correr_search(["--format", "compact"], tmp_path)
        assert llamadas["enricher"] == 1, "B4: --format debía mandar al path estructural"

    def test_json_legacy_se_mantiene_compat(self, tmp_path: Path) -> None:
        _, llamadas = _correr_search(["--json"], tmp_path)
        assert llamadas["enricher"] == 0, "--json mantiene la salida legacy (compat)"
