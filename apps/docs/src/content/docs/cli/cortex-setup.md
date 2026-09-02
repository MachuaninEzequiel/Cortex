---
title: cortex init & cortex setup
description: Inicialización de proyectos, plantillas de configuración y perfiles de onboarding.
---

Cortex provee dos comandos para inicializar y configurar un repositorio: `cortex init` (inicialización directa) y `cortex setup` (asistente de perfiles guiado).

---

## `cortex init`

Inicializa la estructura base `.cortex/` en el directorio de trabajo actual con la configuración por defecto:

```bash
cortex init
```

### Archivos Creados:
* `.cortex/config.yaml`: Configuración de memoria episódica, semántica, búsqueda híbrida y LLM.
* `.cortex/workspace.yaml`: Definición de layout del espacio de trabajo.
* `.cortex/vault/architecture.md`: Plantilla inicial de arquitectura del proyecto.
* `.cortex/memory/`: Directorio de persistencia episódica.
* `.cortex/sessions/`: Directorio de almacenamiento de sesiones.

---

## `cortex setup`

El comando `cortex setup` ejecuta un análisis contextual del repositorio (detecta stack de lenguajes, frameworks, herramientas de git y editores presentes) y configura el perfil óptimo de Cortex.

```bash
cortex setup [OPCIONES]
```

---

## Opciones de `cortex setup`

| Flag | Tipo | Descripción |
| :--- | :---: | :--- |
| `--dry-run` | `bool` | Simula la configuración sin escribir ningún archivo en disco. |
| `--non-interactive` | `bool` | Ejecuta el setup sin solicitar confirmaciones en consola. |
| `--ide <IDE>` | `string` | Configura automáticamente el editor especificado (`cursor`, `claude_code`, `vscode`, `pi`, `codex`). |
| `--git-depth <N>` | `int` | Profundidad de análisis del historial de Git. |

---

## Perfiles de Configuración

* **`agent` (Predeterminado):** Optimizado para desarrolladores individuales trabajando con agentes de IA locales (Claude Code, Cursor, Pi).
* **`team`:** Habilita reglas de retención compartida y plantillas de handoff estructuradas.
* **`enterprise`:** Genera además el archivo `.cortex/org.yaml` con flujos de revisión obligatoria de conocimiento y auditoría estricta.

### Ejemplo con Dry-Run
```bash
cortex setup --dry-run
```
Salida:
```text
🧠 Cortex — [dry-run] Setup agent profile (simulation)

[dry-run] crearía: .cortex/workspace.yaml
[dry-run] crearía: .cortex/config.yaml
[dry-run] crearía: .cortex/org.yaml
[dry-run] crearía: .cortex/vault/architecture.md

✅ Dry-run complete — no changes were made.
```
