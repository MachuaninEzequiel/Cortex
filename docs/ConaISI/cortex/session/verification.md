# cortex/session/verification.py

## Qué tiene adentro

- **Ruta de código:** `cortex/session/verification.py` (156 líneas).
- **Módulo Python:** `cortex.session.verification`.
- **Docstring del módulo:** cortex.session.verification — Run :class:`VerificationHook` commands.
- **Clases definidas:**
  - `VerificationRunner`
    - Execute :class:`VerificationHook` commands and collect results.
    - Métodos públicos/especiales: `__init__`, `repo_root`, `run_hook`, `run_all`
    - Métodos internos: `_compose_output`
- **Constantes / símbolos de módulo:** `_TIMEOUT_EXIT_CODE`, `__all__`

## Para qué sirve

cortex.session.verification — Run :class:`VerificationHook` commands.

The :class:`VerificationRunner` executes the hooks declared in a spec and
captures their results into :class:`VerificationHookResult` instances.
It is consumed by the documenter's reconstruction module (Phase 01 /
T1.4) but is intentionally decoupled from it — no documenter, spec
loading, vault, memory or git dependency lives here.

Design contract:

- Every hook gets a result. Hook failures (non-zero exit, timeout,
  output overflow) produce a result with ``passed=False`` and never
  raise.
- Infrastructure failures (``shell`` not found, ``OSError`` other than
  permission) bubble up as :class:`subprocess.SubprocessError` — they
  signal a broken environment and the caller decides how to surface
  them.
- ``shell=True`` is used by design: hooks come from the spec, which is
  owned by the user. If the spec is malicious the system is already
  compromised — see Phase 01 §3.5 design notes.
- The working directory is always *repo_root*; environment variables
  are inherited.

## Relaciones

### Recibe de

- `cortex.session.models` (MAX_VERIFICATION_OUTPUT_BYTES, VerificationHook, VerificationHookResult)
- Dependencias externas/stdlib: `logging`, `subprocess`, `time`, `__future__`, `collections.abc`, `datetime`, `pathlib`

### Envía a

- `cortex.ci.validator`
- `cortex.cli.ci`
- `cortex.documenter.reconstruction`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 156.
Docstrings de símbolos públicos:
- `VerificationRunner.run_hook`: Execute *hook* and return its :class:`VerificationHookResult`.
- `VerificationRunner.run_all`: Run every hook sequentially in input order.

---
Fuente: código de `cortex/session/verification.py` (AST + grafo de imports internos). No se usó documentación previa.
