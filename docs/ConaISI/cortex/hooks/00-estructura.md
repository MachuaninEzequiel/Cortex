# Estructura — `cortex/hooks`

## Para qué existe esta carpeta

(sin docstring de paquete; reexportes)

## Árbol interno (código, sin `__pycache__`)

```
hooks/
├── __init__.py
└── agent_hooks.py
```

## Archivos Python cubiertos aquí

| Archivo | Líneas | Síntesis observada |
|---|---:|---|
| `cortex/hooks/__init__.py` | 4 | reexportes / marcador de paquete |
| `cortex/hooks/agent_hooks.py` | 159 | cortex.hooks.agent_hooks ------------------------ DEPRECATED (dueño, 2026-08-25 — doc 12 §4.4): módulo huérfano — ni templates, ni IDE adapters, ni setup lo referencian; los hooks vigentes viven en cortex/setup/session_hooks (gate P8: 38/38). Se elimina en la baja de Python. |

## Relaciones de la carpeta

### Recibe de (unión de imports `cortex.*` de los módulos de este nivel)

- `cortex.core`
- `cortex.hooks.agent_hooks`

### Envía a (módulos `cortex.*` que importan a este nivel)

- `cortex.hooks`

---
Fuente: árbol de `cortex/` + AST de imports. No se usó documentación previa.
