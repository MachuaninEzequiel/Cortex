# Estructura — `cortex/security`

## Para qué existe esta carpeta

Cortex security utilities.

## Árbol interno (código, sin `__pycache__`)

```
security/
├── __init__.py
└── paths.py
```

## Archivos Python cubiertos aquí

| Archivo | Líneas | Síntesis observada |
|---|---:|---|
| `cortex/security/__init__.py` | 6 | Cortex security utilities. |
| `cortex/security/paths.py` | 64 | cortex.security.paths --------------------- Centralised path-safety helpers for Cortex. |

## Relaciones de la carpeta

### Recibe de (unión de imports `cortex.*` de los módulos de este nivel)

- `cortex.security.paths`

### Envía a (módulos `cortex.*` que importan a este nivel)

- `cortex.mcp.tools.search`
- `cortex.security`
- `cortex.semantic.vault_reader`
- `cortex.workitems.service`

---
Fuente: árbol de `cortex/` + AST de imports. No se usó documentación previa.
