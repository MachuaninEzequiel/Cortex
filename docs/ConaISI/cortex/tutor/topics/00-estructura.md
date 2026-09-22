# Estructura — `cortex/tutor/topics`

## Para qué existe esta carpeta

cortex.tutor.topics ------------------- Registry of all built-in tutor topics. Each topic module exposes a class that satisfies the TutorTopic protocol.

## Árbol interno (código, sin `__pycache__`)

```
topics/
├── __init__.py
├── commands.py
├── enterprise.py
├── getting_started.py
├── ide_integration.py
├── pipeline.py
├── vault.py
└── workflow.py
```

## Archivos Python cubiertos aquí

| Archivo | Líneas | Síntesis observada |
|---|---:|---|
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

- (sin imports internos en este nivel)

### Envía a (módulos `cortex.*` que importan a este nivel)

- (ningún otro módulo de `cortex/` importa estos módulos por nombre)

---
Fuente: árbol de `cortex/` + AST de imports. No se usó documentación previa.
