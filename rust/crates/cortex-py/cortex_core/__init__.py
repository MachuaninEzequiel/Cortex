"""Fachada del núcleo nativo Rust de Cortex (Obra 03, migración incremental).

El extension-module ``_native`` se compila e instala en el venv con::

    .venv/bin/python -m maturin develop --release -m rust/crates/cortex-py/Cargo.toml

Si no está compilado, ``import cortex_core._native`` falla con ImportError.
Las rutas calientes de Python lo usan SOLO cuando ``CORTEX_NATIVE=1`` y el
módulo está presente; el default SIEMPRE es la ruta pura Python (paridad,
HANDOFF §TAREA-RUST R5.6).
"""

from __future__ import annotations

__all__ = ["__version__", "native_available"]

__version__ = "0.1.0"


def native_available() -> bool:
    """True si el módulo nativo Rust está compilado e importable."""
    try:
        from cortex_core import _native  # noqa: F401
    except ImportError:
        return False
    return True
