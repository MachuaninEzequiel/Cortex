# Estructura — `cortex/tutor`

## Para qué existe esta carpeta

cortex.tutor ------------ Offline interactive tutorial and contextual hint system. Zero tokens consumed — all content is static and local.

## Árbol interno (código, sin `__pycache__`)

```
tutor/
├── topics/
│   ├── __init__.py
│   ├── commands.py
│   ├── enterprise.py
│   ├── getting_started.py
│   ├── ide_integration.py
│   ├── pipeline.py
│   ├── vault.py
│   └── workflow.py
├── __init__.py
├── engine.py
└── hint.py
```

## Archivos Python cubiertos aquí

| Archivo | Líneas | Síntesis observada |
|---|---:|---|
| `cortex/tutor/__init__.py` | 11 | cortex.tutor ------------ Offline interactive tutorial and contextual hint system. Zero tokens consumed — all content is static and local. |
| `cortex/tutor/engine.py` | 233 | cortex.tutor.engine ------------------- TUI engine for the interactive Cortex tutor. Handles menu rendering, topic navigation, and the main loop. |
| `cortex/tutor/hint.py` | 218 | cortex.tutor.hint ----------------- Contextual hint engine that inspects the current project state and suggests the most relevant next action. Zero tokens consumed. |
| `cortex/tutor/topics/__init__.py` | 35 | cortex.tutor.topics ------------------- Registry of all built-in tutor topics. Each topic module exposes a class that satisfies the TutorTopic protocol. |
| `cortex/tutor/topics/commands.py` | 63 | Tópico: Comandos Esenciales. |
| `cortex/tutor/topics/enterprise.py` | 54 | Tópico: Enterprise Memory — Memoria Corporativa. |
| `cortex/tutor/topics/getting_started.py` | 45 | Tópico: Primeros Pasos. |
| `cortex/tutor/topics/ide_integration.py` | 55 | Tópico: Integración IDE — Model Context Protocol. |
| `cortex/tutor/topics/pipeline.py` | 55 | Tópico: Pipeline CI/CD — DevSecDocOps. |
| `cortex/tutor/topics/vault.py` | 53 | Tópico: Vault — Tu Base de Conocimiento. |
| `cortex/tutor/topics/workflow.py` | 51 | Tópico: Flujo de Trabajo — Modelo Tripartito. |

## Relaciones de la carpeta

### Recibe de (unión de imports `cortex.*` de los módulos de este nivel)

- `cortex.tutor.engine`
- `cortex.workspace.layout`

### Envía a (módulos `cortex.*` que importan a este nivel)

- `cortex.tutor`

---
Fuente: árbol de `cortex/` + AST de imports. No se usó documentación previa.
