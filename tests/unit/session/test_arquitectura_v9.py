"""Guardia de arquitectura V9 (Obra 01 P8): session no depende de documenter.

La primitiva Session es de nivel inferior; ``cortex.documenter`` la
consume. Ningún módulo de ``cortex.session`` puede importar
``cortex.documenter`` en runtime (los hints van por TYPE_CHECKING).
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_session_no_importa_documenter_en_runtime() -> None:
    codigo = (
        "import sys\n"
        "import cortex.session\n"
        "import cortex.session.quality_gates\n"
        "import cortex.session.service\n"
        "import cortex.session.storage\n"
        "leaks = sorted(m for m in sys.modules if m.startswith('cortex.documenter'))\n"
        "assert not leaks, f'cortex.session arrastró módulos de documenter: {leaks}'\n"
    )
    proc = subprocess.run(
        [sys.executable, "-c", codigo], cwd=REPO_ROOT,
        capture_output=True, text=True, timeout=120,
    )
    assert proc.returncode == 0, proc.stderr


def test_sin_imports_de_documenter_en_fuentes_de_session() -> None:
    patron = re.compile(r"^\s*(?:from|import)\s+cortex\.documenter", re.MULTILINE)
    ofensores = []
    for py in (REPO_ROOT / "cortex" / "session").rglob("*.py"):
        texto = py.read_text(encoding="utf-8")
        for i, linea in enumerate(texto.splitlines(), start=1):
            if patron.match(linea) and "TYPE_CHECKING" not in linea:
                # permitir imports dentro de bloques TYPE_CHECKING (indentados)
                if not linea.startswith((" ", "\t")):
                    ofensores.append(f"{py.relative_to(REPO_ROOT)}:{i}: {linea.strip()}")
    assert not ofensores, f"imports runtime prohibidos:\n" + "\n".join(ofensores)
