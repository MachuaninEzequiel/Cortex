# Estructura — `cortex/brain`

## Para qué existe esta carpeta

cortex.brain — DEPRECATED (dueño, 2026-08-25 — doc 12 §4.2).

## Árbol interno (código, sin `__pycache__`)

```
brain/
├── __init__.py
├── chat.py
├── cli.py
├── router.py
└── tools.py
```

## Archivos Python cubiertos aquí

| Archivo | Líneas | Síntesis observada |
|---|---:|---|
| `cortex/brain/__init__.py` | 19 | cortex.brain — DEPRECATED (dueño, 2026-08-25 — doc 12 §4.2). |
| `cortex/brain/chat.py` | 147 | DEPRECATED (2026-08-25, doc 12 §4.2): ver cortex/brain/__init__.py. |
| `cortex/brain/cli.py` | 38 | DEPRECATED (2026-08-25, doc 12 §4.2): ver cortex/brain/__init__.py. |
| `cortex/brain/router.py` | 61 | DEPRECATED (2026-08-25, doc 12 §4.2): ver cortex/brain/__init__.py. |
| `cortex/brain/tools.py` | 176 | DEPRECATED (2026-08-25, doc 12 §4.2): ver cortex/brain/__init__.py. |

## Relaciones de la carpeta

### Recibe de (unión de imports `cortex.*` de los módulos de este nivel)

- `cortex.action_engine.context`
- `cortex.brain.router`
- `cortex.brain.tools`

### Envía a (módulos `cortex.*` que importan a este nivel)

- `cortex.brain`
- `cortex.brain.chat`
- `cortex.cli.main`

---
Fuente: árbol de `cortex/` + AST de imports. No se usó documentación previa.
