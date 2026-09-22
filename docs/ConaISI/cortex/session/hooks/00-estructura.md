# Estructura — `cortex/session/hooks`

## Para qué existe esta carpeta

cortex.session.hooks — IDE-hook installer system for the Observed mode.

## Árbol interno (código, sin `__pycache__`)

```
hooks/
├── adapters/
│   ├── __init__.py
│   ├── claude_code.py
│   ├── cursor.py
│   ├── opencode.py
│   └── pi.py
├── __init__.py
└── installer.py
```

## Archivos Python cubiertos aquí

| Archivo | Líneas | Síntesis observada |
|---|---:|---|
| `cortex/session/hooks/__init__.py` | 43 | cortex.session.hooks — IDE-hook installer system for the Observed mode. |
| `cortex/session/hooks/installer.py` | 184 | cortex.session.hooks.installer — Generic hook installer infrastructure. |

## Relaciones de la carpeta

### Recibe de (unión de imports `cortex.*` de los módulos de este nivel)

- `cortex.session.hooks.installer`

### Envía a (módulos `cortex.*` que importan a este nivel)

- `cortex.autopilot.doctor`
- `cortex.cli.ide`
- `cortex.cli.session`
- `cortex.session.hooks`
- `cortex.session.hooks.adapters.claude_code`
- `cortex.session.hooks.adapters.cursor`
- `cortex.session.hooks.adapters.opencode`
- `cortex.session.hooks.adapters.pi`

---
Fuente: árbol de `cortex/` + AST de imports. No se usó documentación previa.
