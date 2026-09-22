# Estructura — `cortex/workspace`

## Para qué existe esta carpeta

cortex.workspace --------------- Workspace layout resolution for Cortex projects.

## Árbol interno (código, sin `__pycache__`)

```
workspace/
├── __init__.py
└── layout.py
```

## Archivos Python cubiertos aquí

| Archivo | Líneas | Síntesis observada |
|---|---:|---|
| `cortex/workspace/__init__.py` | 38 | cortex.workspace --------------- Workspace layout resolution for Cortex projects. |
| `cortex/workspace/layout.py` | 565 | cortex.workspace.layout ----------------------- Central workspace path resolver for Cortex. |

## Relaciones de la carpeta

### Recibe de (unión de imports `cortex.*` de los módulos de este nivel)

- `cortex.workspace.layout`

### Envía a (módulos `cortex.*` que importan a este nivel)

- `cortex.action_engine.context`
- `cortex.autopilot.config`
- `cortex.autopilot.doctor`
- `cortex.autopilot.service`
- `cortex.cli.ci`
- `cortex.cli.docs_vectorization`
- `cortex.cli.ide`
- `cortex.cli.main`
- `cortex.cli.review_knowledge`
- `cortex.cli.session`
- `cortex.doctor`
- `cortex.enterprise.knowledge_promotion`
- `cortex.enterprise.reporting`
- `cortex.git_policy`
- `cortex.ide`
- `cortex.ide.adapters.opencode`
- `cortex.ide.prompts`
- `cortex.mcp.server`
- `cortex.setup.orchestrator`
- `cortex.tutor.hint`
- `cortex.webgraph.cache`
- `cortex.webgraph.cli`
- `cortex.webgraph.episodic_source`
- `cortex.webgraph.federation`
- `cortex.webgraph.semantic_source`
- `cortex.webgraph.server`
- `cortex.webgraph.service`
- `cortex.webgraph.setup`
- `cortex.workspace`

---
Fuente: árbol de `cortex/` + AST de imports. No se usó documentación previa.
