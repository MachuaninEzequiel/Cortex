#!/usr/bin/env python3
"""
Cortex BlackBox Probe - Git Activity & ADR Drift Observer
=========================================================
Auditor pasivo de actividad git. Registra cada commit realizado en el proyecto,
evaluando:
1. Condición: ¿El commit fue asistido por Cortex (sesión activa) o fue RAW?
2. Deriva Arquitectónica: ¿Se modificaron componentes críticos sin referencia o actualización de ADRs?
3. Volumen de cambio: Archivos y líneas modificadas para correlación con telemetría MCP.

Totalmente seguro: No bloquea commits ni modifica el historial de git.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

PROBE_DIR = Path(__file__).resolve().parent
REPO_ROOT = PROBE_DIR.parent.parent  # ConaISI/.cortex-probe/ -> REPO_ROOT (o .cortex-probe/ -> REPO_ROOT)
DATA_DIR = PROBE_DIR / "data"
GIT_EVENTS_FILE = DATA_DIR / "git_events.jsonl"
CONFIG_PATH = PROBE_DIR / "config.json"


def run_git(args: List[str], cwd: Path) -> str:
    try:
        res = subprocess.run(
            ["git"] + args,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        return res.stdout.strip()
    except Exception:
        return ""


def find_repo_root() -> Path:
    # Intenta encontrar la raíz del repo git
    curr = Path.cwd()
    while curr != curr.parent:
        if (curr / ".git").exists():
            return curr
        curr = curr.parent
    return Path.cwd()


def get_active_cortex_session(repo_root: Path) -> Optional[Dict[str, Any]]:
    """Inspecciona si hay una sesión activa de Cortex (Python o Rust)."""
    sessions_dir = repo_root / ".cortex" / "sessions"
    if not sessions_dir.exists():
        return None

    try:
        yaml_files = sorted(sessions_dir.glob("*.yaml"), key=lambda f: f.stat().st_mtime, reverse=True)
        if not yaml_files:
            return None

        latest_file = yaml_files[0]
        # Si fue modificado en las últimas 3 horas, consideramos que puede haber sesión activa
        if time.time() - latest_file.stat().st_mtime > 3 * 3600:
            return None

        content = latest_file.read_text(encoding="utf-8", errors="ignore")
        is_open = "status: open" in content or "status: active" in content or "status: \"open\"" in content
        
        session_id = latest_file.stem
        return {
            "session_id": session_id,
            "file": str(latest_file.relative_to(repo_root)),
            "is_open": is_open
        }
    except Exception:
        return None


def audit_adr_compliance(repo_root: Path, files_changed: List[str], commit_msg: str) -> Dict[str, Any]:
    """Evalúa cumplimiento de ADRs vs Deriva Arquitectónica."""
    # Buscar directorio de ADRs
    adr_candidates = [
        repo_root / ".cortex" / "vault" / "adrs",
        repo_root / ".cortex" / "adrs",
        repo_root / "docs" / "adr",
        repo_root / "docs" / "adrs"
    ]
    adr_dir = next((d for d in adr_candidates if d.exists()), None)
    has_adrs = adr_dir is not None and any(adr_dir.glob("*.md"))

    # Archivos que tocan arquitectura o configuración central
    arch_patterns = ["Cargo.toml", "package.json", "go.mod", "pom.xml", "requirements.txt",
                     "architecture", "infra", "docker", "schema", "database", "auth", "middleware"]

    touches_architecture = any(any(pat in f.lower() for pat in arch_patterns) for f in files_changed)
    touches_adr = any("adr" in f.lower() for f in files_changed)
    mentions_adr = "adr" in commit_msg.lower() or "decisión" in commit_msg.lower() or "rfc" in commit_msg.lower()

    if not has_adrs or not touches_architecture:
        return {
            "compliant": True,
            "touches_architecture": touches_architecture,
            "drift_detected": False,
            "reason": "Cambio de código estándar o sin ADRs en repositorio"
        }

    # Si toca arquitectura y hay ADRs en el repo:
    if touches_adr or mentions_adr:
        return {
            "compliant": True,
            "touches_architecture": True,
            "drift_detected": False,
            "reason": "Modificación arquitectónica acompañada o referenciada en ADR"
        }
    else:
        return {
            "compliant": False,
            "touches_architecture": True,
            "drift_detected": True,
            "reason": "Alerta de Deriva: Modificación arquitectónica sin actualización de ADRs"
        }


def record_current_commit():
    try:
        repo_root = find_repo_root()
        commit_hash = run_git(["rev-parse", "HEAD"], repo_root)
        if not commit_hash:
            return

        author = run_git(["log", "-1", "--pretty=format:%an"], repo_root)
        commit_date = run_git(["log", "-1", "--pretty=format:%cI"], repo_root)
        commit_msg = run_git(["log", "-1", "--pretty=format:%s"], repo_root)

        files_output = run_git(["diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD"], repo_root)
        files_changed = [f.strip() for f in files_output.splitlines() if f.strip()]

        shortstat = run_git(["diff-tree", "--shortstat", "HEAD~1", "HEAD"], repo_root)

        # Determinar sesión activa de Cortex
        session_info = get_active_cortex_session(repo_root)
        condition = "cortex_assisted" if (session_info and session_info.get("is_open")) else "raw_unassisted"

        # Auditoría de ADRs
        adr_audit = audit_adr_compliance(repo_root, files_changed, commit_msg)

        DATA_DIR.mkdir(parents=True, exist_ok=True)

        event = {
            "timestamp": time.time(),
            "iso_time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "commit_hash": commit_hash[:10],
            "full_hash": commit_hash,
            "author": author,
            "commit_date": commit_date,
            "message": commit_msg[:120],
            "condition": condition,
            "cortex_session": session_info,
            "files_count": len(files_changed),
            "files_sample": files_changed[:10],
            "stats": shortstat,
            "adr_compliance": adr_audit
        }

        with open(GIT_EVENTS_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")

    except Exception:
        # Cero fallos visibles para el usuario
        pass


if __name__ == "__main__":
    record_current_commit()
