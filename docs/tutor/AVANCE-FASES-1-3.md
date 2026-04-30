# Documentación de Implementación: Fases 1-3

## Fecha: 2026-04-30

---

## Fase 1: Infraestructura del Tutor (Engine + CLI)

### Archivos creados

| Archivo | Propósito |
| --- | --- |
| `cortex/tutor/__init__.py` | Módulo raíz, exporta `TutorEngine` |
| `cortex/tutor/engine.py` | Motor TUI: menú, navegación, loop interactivo |
| `cortex/tutor/topics/__init__.py` | Registry de tópicos con lazy imports |

### Decisiones técnicas

1. **`TutorTopic` como Protocol** (structural typing): Los tópicos no necesitan heredar de una clase base. Cualquier clase que tenga las propiedades y el método `render()` es válida. Esto permite que cada tópico sea independiente y testeable.

2. **`_safe_console()` factory**: Se descubrió que en Windows con codepage cp1252, `rich` no puede renderizar emojis Unicode. La solución fue:
   - Llamar a `SetConsoleOutputCP(65001)` via ctypes para cambiar la consola a UTF-8.
   - Reconfigurar `sys.stdout` con `encoding="utf-8"` y `errors="replace"`.
   - Crear la Console con `force_terminal=True` para forzar el renderer ANSI en vez del legacy Win32.

3. **Acceso directo por slug**: `cortex tutor pipeline` funciona sin abrir el menú, buscando por el slug del tópico.

4. **Registro en CLI**: Los comandos `tutor` y `hint` se registraron en `cortex/cli/main.py` justo después de `agent-guidelines` (zona de onboarding/help).

---

## Fase 2: Tópicos del Tutor (Contenido)

### Archivos creados

| Archivo | Slug | Contenido |
| --- | --- | --- |
| `cortex/tutor/topics/getting_started.py` | `start` | Guía de 7 pasos para arrancar |
| `cortex/tutor/topics/commands.py` | `commands` | Cheatsheet en tabla rich (12 comandos) |
| `cortex/tutor/topics/workflow.py` | `workflow` | Modelo tripartito: sync → SDDwork → documenter |
| `cortex/tutor/topics/pipeline.py` | `pipeline` | 4 stages, módulos intercambiables, enforcement |
| `cortex/tutor/topics/vault.py` | `vault` | Estructura de carpetas, qué va a Git |
| `cortex/tutor/topics/enterprise.py` | `enterprise` | 2 niveles, promoción, topologías |
| `cortex/tutor/topics/ide_integration.py` | `ide` | IDEs soportados, inject, merge seguro |

### Principios de diseño del contenido

- **Máximo 20-25 líneas** por tópico en terminal.
- Cada tópico termina con **link a documentación extendida** (`📖 docs/guides/...`).
- Se usa **rich Panel** con colores por categoría (verde=start, amarillo=commands, azul=workflow, rojo=pipeline, etc.).
- Los comandos se muestran en `[cyan]` para que sean inmediatamente identificables.

---

## Fase 3: Sistema Hint Contextual

### Archivos creados

| Archivo | Propósito |
| --- | --- |
| `cortex/tutor/hint.py` | `ProjectState` + `HintEngine` + `Hint` dataclass |

### Cómo funciona

1. **`ProjectState.detect(path)`** inspecciona el filesystem:
   - ¿Existe `config.yaml`? ¿`vault/`? ¿`.cortex/`? ¿`.cortex/org.yaml`?
   - Cuenta specs, sessions y docs totales en el vault.
   - Detecta si hay workflows GitHub y configuración MCP.

2. **`HintEngine.get_hint(state)`** evalúa 8 niveles de prioridad:
   - Nivel 0: No inicializado → sugiere `cortex setup agent`
   - Nivel 1: Sin specs → sugiere `cortex create-spec`
   - Nivel 2: Specs sin sessions → sugiere `cortex save-session`
   - Nivel 3: Vault creciendo sin CI → sugiere `cortex setup pipeline`
   - Nivel 4: Vault grande sin enterprise → sugiere `cortex setup enterprise`
   - Nivel 5: Enterprise sin promotions → sugiere `cortex promote-knowledge`
   - Nivel 6: Sin IDE conectado → sugiere `cortex inject`
   - Nivel 7: Todo bien → muestra estadísticas

3. El primer hint cuya condición sea `True` es el que se muestra.

### Validación

```
$ cortex hint  (en proyecto con config.yaml pero sin specs)
┌──────── 📝 No hay especificaciones creadas ────────┐
│ Antes de codear, creá una spec...                   │
│   $ cortex create-spec --title "Mi Feature" ...     │
└─────────────────────────────────────────────────────┘

$ cortex tutor commands
┌──────── 📋 COMANDOS ESENCIALES ─────────────────────┐
│ cortex setup agent   │ Inicializar Cortex...         │
│ cortex create-spec   │ Crear especificación...       │
│ ...                                                  │
└──────────────────────────────────────────────────────┘
```

Todos los tópicos y el hint fueron probados exitosamente en Windows con consola cp1252.

---

## Estado actual

- [x] Fase 1: Infraestructura (engine, protocol, CLI registration)
- [x] Fase 2: 7 tópicos (getting_started, commands, workflow, pipeline, vault, enterprise, ide)
- [x] Fase 3: Sistema hint (ProjectState, HintEngine, 8 niveles)
- [ ] Fase 4: Documentación extendida (`docs/guides/*.md`)
