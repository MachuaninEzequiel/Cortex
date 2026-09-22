# Estructura — `cortex/session`

## Para qué existe esta carpeta

cortex.session — Session primitive for the Pluggable Middle architecture.

## Árbol interno (código, sin `__pycache__`)

```
session/
├── hooks/
│   ├── adapters/
│   │   ├── __init__.py
│   │   ├── claude_code.py
│   │   ├── cursor.py
│   │   ├── opencode.py
│   │   └── pi.py
│   ├── __init__.py
│   └── installer.py
├── __init__.py
├── errors.py
├── git.py
├── models.py
├── proposal.py
├── quality_gates.py
├── service.py
├── storage.py
└── verification.py
```

## Archivos Python cubiertos aquí

| Archivo | Líneas | Síntesis observada |
|---|---:|---|
| `cortex/session/__init__.py` | 53 | cortex.session — Session primitive for the Pluggable Middle architecture. |
| `cortex/session/errors.py` | 49 | cortex.session.errors — Domain exceptions for the Session primitive. |
| `cortex/session/git.py` | 146 | cortex.session.git — Minimal subprocess wrappers for git commands. |
| `cortex/session/hooks/__init__.py` | 43 | cortex.session.hooks — IDE-hook installer system for the Observed mode. |
| `cortex/session/hooks/adapters/__init__.py` | 17 | cortex.session.hooks.adapters — Bundled IDE hook adapters. |
| `cortex/session/hooks/adapters/claude_code.py` | 214 | cortex.session.hooks.adapters.claude_code — Claude Code hook adapter. |
| `cortex/session/hooks/adapters/cursor.py` | 201 | cortex.session.hooks.adapters.cursor — Git post-commit hook adapter. |
| `cortex/session/hooks/adapters/opencode.py` | 180 | cortex.session.hooks.adapters.opencode — opencode IDE hook adapter. |
| `cortex/session/hooks/adapters/pi.py` | 173 | cortex.session.hooks.adapters.pi — Pi Coding Agent hook adapter. |
| `cortex/session/hooks/installer.py` | 184 | cortex.session.hooks.installer — Generic hook installer infrastructure. |
| `cortex/session/models.py` | 460 | cortex.session.models — Pydantic models for the Session primitive. |
| `cortex/session/proposal.py` | 183 | cortex.session.proposal — Interactive proposal primitive (Phase 09.A+). |
| `cortex/session/quality_gates.py` | 203 | cortex.session.quality_gates — Two-stage review of subagent checkpoints. |
| `cortex/session/service.py` | 526 | cortex.session.service — Public API for the Session primitive. |
| `cortex/session/storage.py` | 359 | cortex.session.storage — File-based persistence for ``SessionRecord``. |
| `cortex/session/verification.py` | 156 | cortex.session.verification — Run :class:`VerificationHook` commands. |

## Relaciones de la carpeta

### Recibe de (unión de imports `cortex.*` de los módulos de este nivel)

- `cortex.session`
- `cortex.session.errors`
- `cortex.session.models`
- `cortex.session.storage`

### Envía a (módulos `cortex.*` que importan a este nivel)

- `cortex.autopilot.cli`
- `cortex.autopilot.doctor`
- `cortex.autopilot.errors`
- `cortex.autopilot.lifecycle`
- `cortex.autopilot.mcp_tools`
- `cortex.autopilot.policies`
- `cortex.autopilot.service`
- `cortex.ci.diff_io`
- `cortex.ci.result`
- `cortex.ci.review_session`
- `cortex.ci.session_matcher`
- `cortex.ci.validator`
- `cortex.cli.ci`
- `cortex.cli.session`
- `cortex.cli.session_tui`
- `cortex.core`
- `cortex.documentation.schemas.spec`
- `cortex.documenter.adr_evaluator`
- `cortex.documenter.contradiction_detector`
- `cortex.documenter.interactive`
- `cortex.documenter.persistence`
- `cortex.documenter.reconstruction`
- `cortex.documenter.spec_loader`
- `cortex.mcp.schemas`
- `cortex.services.spec_service`
- `cortex.session`
- `cortex.session.quality_gates`
- `cortex.session.service`
- `cortex.session.storage`
- `cortex.session.verification`

---
Fuente: árbol de `cortex/` + AST de imports. No se usó documentación previa.
