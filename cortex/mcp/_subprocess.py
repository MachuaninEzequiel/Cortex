"""Defensive subprocess helpers for the Cortex MCP server.

Fase 1 — Capa 3 del plan multi-IDE & MCP hardening.

Razon de existir:

El MCP server ejecuta subprocesos (`git diff`, etc.) dentro de sus handlers.
Sin proteccion, una llamada que se cuelga (rama inexistente, lock de git,
antivirus de Windows escaneando .git/) bloquea el event loop async del
server entero, causando el incidente del 2026-05-15.

Este modulo provee un helper unico ``safe_run`` que:

1. Aplica timeout enforced (no se puede colgar indefinidamente).
2. En Windows, usa ``creationflags=CREATE_NEW_PROCESS_GROUP`` para evitar
   procesos zombie con handles del pipe MCP cuando el padre muere.
3. Envuelve TODAS las exceptions en un ``Result`` estructurado — nunca
   propaga al handler MCP.
4. Devuelve un ``Result`` con ``ok: bool``, ``stdout``, ``stderr``,
   ``returncode``, ``error``. El caller siempre tiene un objeto sobre el
   que decidir.

Tambien provee ``git_branch_exists`` como pre-validacion barata para
``cortex_verify_session_claims`` y otros handlers que dependen de una
rama base.
"""
from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Result:
    """Outcome of a defensive subprocess call.

    Attributes:
        ok:         True si el proceso termino con returncode == 0 sin
                    excepciones. False en cualquier otro caso (timeout,
                    crash, comando no encontrado, etc.).
        stdout:     stdout capturado (string, ``""`` si no hay).
        stderr:     stderr capturado (string, ``""`` si no hay).
        returncode: codigo de salida del proceso, o ``None`` si nunca corrio.
        error:      mensaje de error de alto nivel cuando ``ok`` es False.
                    None si ``ok`` es True.
    """

    ok: bool
    stdout: str
    stderr: str
    returncode: int | None
    error: str | None


def _windows_creation_flags() -> int:
    """``CREATE_NEW_PROCESS_GROUP`` en Windows, 0 en otros OS.

    En Windows, sin este flag, matar el proceso padre puede dejar el hijo
    como zombie con handles abiertos del pipe stdio del MCP. Con el flag,
    el hijo corre en su propio grupo y se limpia limpiamente.
    """
    if sys.platform != "win32":
        return 0
    return getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)


def safe_run(
    cmd: list[str],
    *,
    cwd: Path | str | None = None,
    timeout: float = 10.0,
    env: dict[str, str] | None = None,
) -> Result:
    """Run a subprocess defensively. NEVER raises.

    Args:
        cmd:      Lista de argumentos del proceso (no string concatenado;
                  evita shell injection).
        cwd:      Working directory para el proceso.
        timeout:  Maximo segundos a esperar. Si timeout, ``Result.ok`` es
                  False y ``Result.error`` indica timeout.
        env:      Variables de entorno opcionales (None hereda del padre).

    Returns:
        ``Result`` estructurado. Nunca lanza exceptions al caller.
    """
    if not cmd:
        return Result(ok=False, stdout="", stderr="", returncode=None, error="empty command")

    creationflags = _windows_creation_flags()
    try:
        completed = subprocess.run(
            cmd,
            cwd=str(cwd) if cwd is not None else None,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
            creationflags=creationflags,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        # exc.stdout / exc.stderr pueden ser bytes o str segun la version
        stdout = _decode_capture(exc.stdout)
        stderr = _decode_capture(exc.stderr)
        return Result(
            ok=False,
            stdout=stdout,
            stderr=stderr,
            returncode=None,
            error=f"timeout after {timeout:.1f}s running {cmd[0]}",
        )
    except FileNotFoundError:
        return Result(
            ok=False,
            stdout="",
            stderr="",
            returncode=None,
            error=f"command not found: {cmd[0]}",
        )
    except PermissionError as exc:
        return Result(
            ok=False,
            stdout="",
            stderr="",
            returncode=None,
            error=f"permission denied running {cmd[0]}: {exc}",
        )
    except OSError as exc:
        return Result(
            ok=False,
            stdout="",
            stderr="",
            returncode=None,
            error=f"OS error running {cmd[0]}: {exc}",
        )

    if completed.returncode != 0:
        return Result(
            ok=False,
            stdout=completed.stdout or "",
            stderr=completed.stderr or "",
            returncode=completed.returncode,
            error=f"{cmd[0]} exited with code {completed.returncode}",
        )

    return Result(
        ok=True,
        stdout=completed.stdout or "",
        stderr=completed.stderr or "",
        returncode=0,
        error=None,
    )


def _decode_capture(value: bytes | str | None) -> str:
    """Devuelve string seguro a partir de captures que pueden ser bytes o None."""
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def git_branch_exists(branch: str, *, cwd: Path | str, timeout: float = 2.0) -> bool:
    """Pre-validar que una rama git existe ANTES de invocar ``git diff``.

    Mucho mas barato que un diff completo. Sin esta validacion, llamar
    ``git diff <base> -- `` con una rama inexistente bloquea el subprocess
    hasta el timeout completo (cuando podriamos haber fallado en 100ms).

    Args:
        branch:  Nombre de rama (e.g. "main", "master").
        cwd:     Directorio del repo.
        timeout: Maximo para el rev-parse.

    Returns:
        True si la rama existe (rev-parse retorna 0). False en cualquier
        otro caso (no existe, no es un repo, git no esta, etc.).
    """
    result = safe_run(
        ["git", "rev-parse", "--verify", branch],
        cwd=cwd,
        timeout=timeout,
    )
    return result.ok
