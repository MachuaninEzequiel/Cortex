# Estructura — `cortex/tui`

## Para qué existe esta carpeta

cortex.tui — pantallas rich del Home/acciones/sesión/búsqueda (Obra 05 Fase D).

## Árbol interno (código, sin `__pycache__`)

```
tui/
├── __init__.py
└── core.py
```

## Archivos Python cubiertos aquí

| Archivo | Líneas | Síntesis observada |
|---|---:|---|
| `cortex/tui/__init__.py` | 23 | cortex.tui — pantallas rich del Home/acciones/sesión/búsqueda (Obra 05 Fase D). |
| `cortex/tui/core.py` | 326 | Núcleo de la TUI Home (Obra 05 Fase D, plan §4.2/§4.3). |

## Relaciones de la carpeta

### Recibe de (unión de imports `cortex.*` de los módulos de este nivel)

- `cortex.action_engine.context`
- `cortex.action_engine.i18n`
- `cortex.action_engine.learning`
- `cortex.action_engine.models`
- `cortex.action_engine.runner`
- `cortex.action_engine.scheduler`
- `cortex.action_engine.store`
- `cortex.tui.core`

### Envía a (módulos `cortex.*` que importan a este nivel)

- `cortex.tui`

---
Fuente: árbol de `cortex/` + AST de imports. No se usó documentación previa.
