# Estructura — `cortex/services`

## Para qué existe esta carpeta

cortex.services --------------- Domain service layer for Cortex.

## Árbol interno (código, sin `__pycache__`)

```
services/
├── __init__.py
├── note_service.py
├── pr_service.py
├── session_service.py
└── spec_service.py
```

## Archivos Python cubiertos aquí

| Archivo | Líneas | Síntesis observada |
|---|---:|---|
| `cortex/services/__init__.py` | 41 | cortex.services --------------- Domain service layer for Cortex. |
| `cortex/services/note_service.py` | 245 | cortex.services.note_service ---------------------------- Domain service for creating and persisting *session notes*. |
| `cortex/services/pr_service.py` | 179 | cortex.services.pr_service --------------------------- Domain service for storing PR context and generating fallback documentation. |
| `cortex/services/session_service.py` | 33 | Deprecated alias for :mod:`cortex.services.note_service`. |
| `cortex/services/spec_service.py` | 298 | cortex.services.spec_service ----------------------------- Domain service for creating and persisting implementation specifications. |

## Relaciones de la carpeta

### Recibe de (unión de imports `cortex.*` de los módulos de este nivel)

- `cortex.documentation`
- `cortex.documentation.data`
- `cortex.documentation.writers`
- `cortex.models`
- `cortex.services.note_service`
- `cortex.services.pr_service`
- `cortex.services.spec_service`
- `cortex.session.models`

### Envía a (módulos `cortex.*` que importan a este nivel)

- `cortex.__init__`
- `cortex.core`
- `cortex.documenter.persistence`
- `cortex.services`
- `cortex.services.session_service`

---
Fuente: árbol de `cortex/` + AST de imports. No se usó documentación previa.
