"""Helpers compartidos para tests E2E de Cortex.

Todas las funciones operan sobre un directorio de trabajo (`cwd`) y usan
subprocess para ejecutar la CLI como un usuario real.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import yaml


# ---------------------------------------------------------------------------
# Ejecución de CLI
# ---------------------------------------------------------------------------


def run_cortex(
    cwd: Path,
    *args: str,
    check: bool = True,
    timeout: int = 60,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess:
    """Ejecuta `cortex <args>` en el directorio `cwd`.

    Siempre setea CORTEX_ENV=sandbox para evitar que Cortex descubra
    configuraciones del repo padre.

    Primero intenta el binario `cortex`; si no está disponible, fallback a
    `python -m cortex.cli.main`.
    """
    merged_env = {**(env or {}), "CORTEX_ENV": "sandbox", "PYTHONIOENCODING": "utf-8"}

    # Intentar binario cortex primero
    try:
        cmd = ["cortex", *args]
        return subprocess.run(
            cmd,
            cwd=str(cwd),
            check=check,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            env={**os.environ, **merged_env},
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    # Fallback a módulo
    cmd = [sys.executable, "-m", "cortex.cli.main", *args]
    return subprocess.run(
        cmd,
        cwd=str(cwd),
        check=check,
        capture_output=True,
        text=True,
        timeout=timeout,
        env={**os.environ, **merged_env},
    )


# ---------------------------------------------------------------------------
# Validación de YAMLs
# ---------------------------------------------------------------------------


def assert_valid_config_yaml(path: Path) -> None:
    """Parsea YAML en `path` y valida contra CortexConfig."""
    from cortex.core import CortexConfig

    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    try:
        CortexConfig.model_validate(raw)
    except Exception as exc:
        raise AssertionError(f"Invalid config.yaml at {path}: {exc}") from exc


def assert_valid_org_yaml(path: Path) -> None:
    """Parsea YAML en `path` y valida contra EnterpriseOrgConfig."""
    from cortex.enterprise.models import EnterpriseOrgConfig

    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    try:
        EnterpriseOrgConfig.model_validate(raw)
    except Exception as exc:
        raise AssertionError(f"Invalid org.yaml at {path}: {exc}") from exc


# ---------------------------------------------------------------------------
# Vault
# ---------------------------------------------------------------------------


def assert_vault_has_documents(vault_path: Path, min_count: int = 1) -> None:
    """Asegura que `vault_path` contenga al menos `min_count` archivos .md."""
    md_files = list(vault_path.rglob("*.md"))
    if len(md_files) < min_count:
        raise AssertionError(
            f"Expected at least {min_count} .md files in {vault_path}, "
            f"found {len(md_files)}"
        )


# ---------------------------------------------------------------------------
# ChromaDB
# ---------------------------------------------------------------------------


def count_chroma_documents(persist_dir: Path, collection_name: str = "cortex_episodic") -> int:
    """Abre ChromaDB en `persist_dir` y retorna el conteo de documentos.

    Usa la API moderna: chromadb.PersistentClient(path=...) (ChromaDB >= 0.5).
    Retorna 0 si la colección no existe o el directorio está vacío.
    """
    try:
        import chromadb

        client = chromadb.PersistentClient(path=str(persist_dir))
        collection = client.get_or_create_collection(collection_name)
        return collection.count()
    except Exception:
        return 0


# ---------------------------------------------------------------------------
# Fixtures de proyectos
# ---------------------------------------------------------------------------


def copy_fixture_project(fixture_name: str, dest: Path) -> Path:
    """Copia `tests/e2e/fixtures/<fixture_name>/` a `dest`.

    Retorna el path del proyecto copiado (`dest / fixture_name`).
    """
    repo_root = Path(__file__).resolve().parents[2]
    source = repo_root / "tests" / "e2e" / "fixtures" / fixture_name
    if not source.exists():
        raise FileNotFoundError(f"Fixture not found: {source}")

    target = dest / fixture_name
    shutil.copytree(source, target)
    return target
