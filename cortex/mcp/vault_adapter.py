"""Adaptador ``VaultLike`` mínimo sobre un path del workspace.

Fuente única del adaptador que antes estaba duplicado inline dentro de
``_write_design_note_text`` y ``_write_doc_text`` (deuda V6 del plan de
transformación, docs/transformacion/01-PODA-Y-LIMPIEZA.md).

Los writers canónicos solo necesitan ``path`` e ``index_file``; la
indexación semántica real la hace el caller vía ``memory.sync_vault()``,
por eso ``index_file`` es un no-op explícito.
"""

from __future__ import annotations

from pathlib import Path


class PathVault:
    """Implementación mínima de :class:`VaultLike` sobre un directorio."""

    def __init__(self, root: Path) -> None:
        self._root = root

    @property
    def path(self) -> Path:
        return self._root

    def index_file(self, rel_path: str) -> bool:  # noqa: ARG002
        return False
