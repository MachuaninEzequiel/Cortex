"""Fuente única de ``devsecdocops.sh`` (deuda V7, Obra 01 fase P6).

El script vivía en DOS fuentes que podían divergir: el archivo real
``scripts/devsecdocops.sh`` y una copia embebida en
``cortex/setup/templates.py`` (que ya había drift-eado escapes y cabecera).

Regla: ``scripts/devsecdocops.sh`` es LA fuente; la constante
``DEVSECDOCSOPS_SCRIPT`` debe ser idéntica byte a byte. Si editás uno,
regenerá el otro (o corré el test para ver el diff).
"""

from __future__ import annotations

from pathlib import Path

from cortex.setup.templates import DEVSECDOCSOPS_SCRIPT

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = REPO_ROOT / "scripts" / "devsecdocops.sh"


def test_constante_embebida_coincide_byte_a_byte_con_el_script() -> None:
    real = SCRIPT_PATH.read_text(encoding="utf-8")
    assert DEVSECDOCSOPS_SCRIPT == real, (
        "DEVSECDOCSOPS_SCRIPT divergió de scripts/devsecdocops.sh. "
        "El archivo es la fuente única: regenerá el literal en "
        "cortex/setup/templates.py desde el .sh."
    )


def test_script_tiene_shebang_y_comandos_esperados() -> None:
    assert DEVSECDOCSOPS_SCRIPT.startswith("#!/usr/bin/env bash")
    for comando in ("capture", "store", "search", "generate", "full"):
        assert comando in DEVSECDOCSOPS_SCRIPT
