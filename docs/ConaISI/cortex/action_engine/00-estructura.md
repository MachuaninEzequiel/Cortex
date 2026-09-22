# Estructura — `cortex/action_engine`

## Para qué existe esta carpeta

cortex.action_engine — motor de acciones con aprendizaje (Obra 05).

## Árbol interno (código, sin `__pycache__`)

```
action_engine/
├── actions/
│   ├── __init__.py
│   └── catalog.py
├── __init__.py
├── context.py
├── i18n.py
├── learning.py
├── metrics.py
├── models.py
├── registry.py
├── runner.py
├── scheduler.py
├── signals.py
└── store.py
```

## Archivos Python cubiertos aquí

| Archivo | Líneas | Síntesis observada |
|---|---:|---|
| `cortex/action_engine/__init__.py` | 31 | cortex.action_engine — motor de acciones con aprendizaje (Obra 05). |
| `cortex/action_engine/actions/__init__.py` | 52 | Catálogo v1 del ActionEngine (plan §3.3). |
| `cortex/action_engine/actions/catalog.py` | 396 | Catálogo v1 del ActionEngine (plan §3.3) — 10 acciones sobre servicios existentes. |
| `cortex/action_engine/context.py` | 69 | Contexto de servicios para las acciones del catálogo (Obra 05 Fase B). |
| `cortex/action_engine/i18n.py` | 75 | i18n ES/EN del ActionEngine y Home (Obra 05 Fase E). |
| `cortex/action_engine/learning.py` | 27 | Paso APRENDER v0 del ActionEngine (plan §3.6). |
| `cortex/action_engine/metrics.py` | 62 | Métrica de éxito del dueño (Obra 05 Fase E, plan §3.6). |
| `cortex/action_engine/models.py` | 129 | Modelos del ActionEngine (Obra 05 Fase B, §3.2 del plan). |
| `cortex/action_engine/registry.py` | 30 | Registry del ActionEngine (plan §3.2). |
| `cortex/action_engine/runner.py` | 132 | Runner del ActionEngine (Obra 05 Fase B). |
| `cortex/action_engine/scheduler.py` | 100 | Registry y scheduler del ActionEngine (Obra 05 Fase B, plan §3.4). |
| `cortex/action_engine/signals.py` | 85 | Señales de feedback real para el score del scheduler (Obra 05 Fase E). |
| `cortex/action_engine/store.py` | 135 | Persistencia del ActionEngine (Obra 05 Fase B). |

## Relaciones de la carpeta

### Recibe de (unión de imports `cortex.*` de los módulos de este nivel)

- `cortex.action_engine.models`
- `cortex.action_engine.registry`
- `cortex.action_engine.runner`
- `cortex.action_engine.scheduler`
- `cortex.action_engine.signals`
- `cortex.action_engine.store`
- `cortex.workspace.layout`

### Envía a (módulos `cortex.*` que importan a este nivel)

- `cortex.action_engine`
- `cortex.action_engine.actions`
- `cortex.action_engine.actions.catalog`
- `cortex.action_engine.learning`
- `cortex.action_engine.metrics`
- `cortex.action_engine.registry`
- `cortex.action_engine.runner`
- `cortex.action_engine.scheduler`
- `cortex.brain.chat`
- `cortex.brain.tools`
- `cortex.cli.next`
- `cortex.tui.core`

---
Fuente: árbol de `cortex/` + AST de imports. No se usó documentación previa.
