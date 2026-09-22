# Estructura — `cortex/autopilot`

## Para qué existe esta carpeta

cortex.autopilot — Policy + hooks layer over the cortex.session primitive.

## Árbol interno (código, sin `__pycache__`)

```
autopilot/
├── detectors/
│   ├── ambiguous.py
│   ├── base.py
│   └── default.py
├── pi/
│   ├── extensions/
│   │   └── cortex-autopilot.ts
│   └── skills/
│       └── using-cortex-autopilot/
│           └── SKILL.md
├── skills/
│   ├── cortex-autopilot-finish.md
│   └── using-cortex-autopilot.md
├── __init__.py
├── cli.py
├── config.py
├── doctor.py
├── errors.py
├── lifecycle.py
├── mcp_tools.py
├── models.py
├── policies.py
└── service.py
```

## Archivos Python cubiertos aquí

| Archivo | Líneas | Síntesis observada |
|---|---:|---|
| `cortex/autopilot/__init__.py` | 34 | cortex.autopilot — Policy + hooks layer over the cortex.session primitive. |
| `cortex/autopilot/cli.py` | 355 | cortex.autopilot.cli — Typer subapp for ``cortex autopilot ...`` commands. |
| `cortex/autopilot/config.py` | 69 | cortex.autopilot.config — Optional configuration for Autopilot. |
| `cortex/autopilot/detectors/ambiguous.py` | 63 | cortex.autopilot.detectors.ambiguous — Ambiguous-request detector. |
| `cortex/autopilot/detectors/base.py` | 78 | cortex.autopilot.detectors.base — Detector protocol and resolution logic. |
| `cortex/autopilot/detectors/default.py` | 298 | cortex.autopilot.detectors.default — Built-in detectors. |
| `cortex/autopilot/doctor.py` | 176 | cortex.autopilot.doctor — Diagnostic toolkit for the Autopilot installation. |
| `cortex/autopilot/errors.py` | 37 | cortex.autopilot.errors — Exceptions raised by the Autopilot module. |
| `cortex/autopilot/lifecycle.py` | 154 | cortex.autopilot.lifecycle — Request/result types for AutopilotService. |
| `cortex/autopilot/mcp_tools.py` | 182 | cortex.autopilot.mcp_tools — MCP tool wrappers for Autopilot. |
| `cortex/autopilot/models.py` | 85 | cortex.autopilot.models — Domain models for detectors and policies. |
| `cortex/autopilot/policies.py` | 374 | cortex.autopilot.policies — Consolidated policy layer for the Autopilot module. |
| `cortex/autopilot/service.py` | 445 | cortex.autopilot.service — AutopilotService over the Session primitive. |

## Relaciones de la carpeta

### Recibe de (unión de imports `cortex.*` de los módulos de este nivel)

- `cortex.autopilot.config`
- `cortex.autopilot.detectors.ambiguous`
- `cortex.autopilot.detectors.base`
- `cortex.autopilot.detectors.default`
- `cortex.autopilot.errors`
- `cortex.autopilot.lifecycle`
- `cortex.autopilot.models`
- `cortex.autopilot.policies`
- `cortex.autopilot.service`
- `cortex.session.errors`
- `cortex.session.hooks`
- `cortex.session.models`
- `cortex.session.service`
- `cortex.session.storage`
- `cortex.workspace.layout`

### Envía a (módulos `cortex.*` que importan a este nivel)

- `cortex.autopilot`
- `cortex.autopilot.cli`
- `cortex.autopilot.detectors.ambiguous`
- `cortex.autopilot.detectors.base`
- `cortex.autopilot.detectors.default`
- `cortex.autopilot.doctor`
- `cortex.autopilot.lifecycle`
- `cortex.autopilot.mcp_tools`
- `cortex.autopilot.policies`
- `cortex.autopilot.service`
- `cortex.cli.main`
- `cortex.mcp.server`

---
Fuente: árbol de `cortex/` + AST de imports. No se usó documentación previa.
