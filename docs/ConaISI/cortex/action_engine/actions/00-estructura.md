# Estructura — `cortex/action_engine/actions`

## Para qué existe esta carpeta

Catálogo v1 del ActionEngine (plan §3.3).

## Árbol interno (código, sin `__pycache__`)

```
actions/
├── __init__.py
└── catalog.py
```

## Archivos Python cubiertos aquí

| Archivo | Líneas | Síntesis observada |
|---|---:|---|
| `cortex/action_engine/actions/__init__.py` | 52 | Catálogo v1 del ActionEngine (plan §3.3). |
| `cortex/action_engine/actions/catalog.py` | 396 | Catálogo v1 del ActionEngine (plan §3.3) — 10 acciones sobre servicios existentes. |

## Relaciones de la carpeta

### Recibe de (unión de imports `cortex.*` de los módulos de este nivel)

- `cortex.action_engine.actions.catalog`
- `cortex.action_engine.context`
- `cortex.action_engine.models`
- `cortex.action_engine.registry`

### Envía a (módulos `cortex.*` que importan a este nivel)

- `cortex.action_engine.actions`
- `cortex.cli.next`

---
Fuente: árbol de `cortex/` + AST de imports. No se usó documentación previa.
