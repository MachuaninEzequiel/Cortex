"""Paridad de campos específicos Local vs Enterprise (deuda V5, Obra 01 P6).

Los 13 tipos documentales definían sus campos dos veces (una por clase
Frontmatter). Tras extraer el mixin compartido, esta relación debe
seguir cumpliéndose EXACTAMENTE igual:

    model_fields(Local) ⊆ model_fields(Enterprise)

(Enterprise agrega campos de gobernanza, nunca quita ni cambia tipos.)
"""

from __future__ import annotations

import importlib

import pytest

DOCTYPES = [
    "adr", "architecture", "changelog", "decision", "design", "glossary",
    "handoff", "hu", "incident", "postmortem", "runbook", "session", "spec",
]


_PREFIJOS = {"adr": "ADR", "hu": "HU"}


def _prefijo(doc_type: str) -> str:
    return _PREFIJOS.get(doc_type, doc_type.capitalize())


@pytest.mark.parametrize("doc_type", DOCTYPES)
def test_enterprise_subeconjunto_superset_de_local(doc_type: str) -> None:
    mod = importlib.import_module(f"cortex.documentation.schemas.{doc_type}")
    local = getattr(mod, f"{_prefijo(doc_type)}Frontmatter")
    ent = getattr(mod, f"{_prefijo(doc_type)}FrontmatterEnterprise")

    campos_local = set(local.model_fields)
    campos_ent = set(ent.model_fields)

    faltan_en_enterprise = campos_local - campos_ent
    assert not faltan_en_enterprise, (
        f"{doc_type}: campos presentes en Local y ausentes en Enterprise: "
        f"{sorted(faltan_en_enterprise)}"
    )


@pytest.mark.parametrize("doc_type", DOCTYPES)
def test_campos_especificos_definidos_una_sola_vez(doc_type: str) -> None:
    """El mixin compartido existe y ambas clases heredan de él."""
    mod = importlib.import_module(f"cortex.documentation.schemas.{doc_type}")
    mixin_name = f"_{_prefijo(doc_type)}Specific"
    assert hasattr(mod, mixin_name), f"Falta el mixin {mixin_name} en {doc_type}.py"

    local = getattr(mod, f"{_prefijo(doc_type)}Frontmatter")
    ent = getattr(mod, f"{_prefijo(doc_type)}FrontmatterEnterprise")
    mixin = getattr(mod, mixin_name)

    assert issubclass(local, mixin)
    assert issubclass(ent, mixin)


def test_defaults_especificos_preservados_adr() -> None:
    """Spot-check: los defaults del mixin ganan sobre las bases comunes."""
    from cortex.documentation.doc_type import DocType
    from cortex.documentation.schemas.adr import (
        ADRFrontmatter,
        ADRFrontmatterEnterprise,
    )

    from datetime import UTC, datetime

    ahora = datetime.now(UTC)
    huella = "a" * 64
    base = {
        "title": "t",
        "created_at": ahora,
        "updated_at": ahora,
        "status": "accepted",
        "fingerprint": huella,
        "adr_number": 3,
    }
    sample = {**base, "vault_scope": "local"}
    fm = ADRFrontmatter(**sample)
    assert fm.doc_type is DocType.ADR
    assert fm.acceptance_criteria_met is False
    assert fm.supersedes == []

    fm_e = ADRFrontmatterEnterprise(
        **{**base, "vault_scope": "enterprise", "owner": "a@b.com", "team": "team-a"},
    )
    assert fm_e.doc_type is DocType.ADR
