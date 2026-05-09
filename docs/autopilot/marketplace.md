# Cortex Autopilot — Marketplace y Packaging

**Versión:** 0.1.0  
**Fecha:** 2026-05-09

---

## 1. Resumen

Cortex Autopilot se distribuye como un plugin multi-harness compatible con los formatos de plugin de facto del ecosistema.  Cada manifesto `plugin.json` describe los assets (skills, hooks) y los requisitos del runtime.

El plugin **instala** la capa Autopilot (hooks IDE + skills) pero **no reemplaza** el flujo manual de Cortex (`cortex-sync`, `cortex-SDDwork`, `cortex-documenter`).  El usuario puede desinstalarlo en cualquier momento sin dejar rastros.

---

## 2. Formatos soportados

| Harness | Directorio de plugin | Adapter | Estado |
|---|---|---|---|
| Cursor | `.cursor-plugin/` | `cursor` | ✅ Disponible |
| Claude Code | `.claude-plugin/` | `claude-code` | ✅ Disponible |
| Codex | `.codex-plugin/` | `codex` | ✅ Disponible |
| OpenCode | `.opencode-plugin/` | `opencode` | ✅ Disponible |
| Pi | `.pi-plugin/` | `pi` | ✅ Disponible |

---

## 3. Estructura del manifesto

Cada `plugin.json` sigue la convención de Superpowers (estándar de facto):

```json
{
  "name": "cortex-autopilot",
  "version": "0.1.0",
  "description": "Autonomous workflow layer for Cortex cognitive memory",
  "author": "DevSecDocOps",
  "homepage": "https://github.com/MachuaninEzequiel/Cortex",
  "skills": {
    "directory": "cortex/autopilot/skills"
  },
  "hooks": {
    "directory": "cortex/autopilot/hooks"
  },
  "requires": {
    "python": ">=3.10",
    "cortex": ">=2.0.0"
  }
}
```

### Campos obligatorios

| Campo | Descripción |
|---|---|
| `name` | Identificador del plugin |
| `version` | Semver |
| `skills.directory` | Ruta relativa a la carpeta de skills de Autopilot |
| `hooks.directory` | Ruta relativa a la carpeta de hooks de Autopilot |
| `requires.python` | Versión mínima de Python |
| `requires.cortex` | Versión mínima de Cortex |

---

## 4. Instalación

### 4.1 Instalar en un workspace

```bash
# Instalar hook para Cursor
cortex autopilot install --ide cursor

# Instalar hook para Claude Code
cortex autopilot install --ide claude-code

# Instalar hook para Pi
cortex autopilot install --ide pi
```

### 4.2 Qué hace `install`

1. Obtiene el adapter correspondiente del registry.
2. Ejecuta `adapter.install(project_root)`.
3. Crea/modifica el archivo de configuración del IDE (ej. `.cursorrules`, `.claude/autopilot-hook.md`).
4. Genera un backup con sufijo `.autopilot-backup` antes de modificar.

### 4.3 Idempotencia

Si el hook ya está instalado, el comando retorna una lista vacía de archivos modificados y no duplica los bloques.

---

## 5. Desinstalación

### 5.1 Desinstalar de un workspace

```bash
cortex autopilot uninstall --ide cursor
cortex autopilot uninstall --ide claude-code
cortex autopilot uninstall --ide pi
```

### 5.2 Qué hace `uninstall`

1. Obtiene el adapter del registry.
2. Ejecuta `adapter.uninstall(project_root)`.
3. Elimina **solo** los bloques delimitados por el marcador `<!-- AUTOPILOT-<NAME> -->`.
4. Restaura el backup `.autopilot-backup` si existe.

### 5.3 Limpieza

La desinstalación no elimina:
- El workspace Cortex (`.cortex/`)
- Las session notes o specs ya creadas
- El vault o índices de memoria

Solo remueve los hooks IDE inyectados por Autopilot.

---

## 6. Wrappers cross-platform

Los hooks usan wrappers Python en lugar de bash puro para garantizar compatibilidad Windows sin WSL:

- **Unix:** `cortex/autopilot/hooks/run_hook.sh`
- **Windows:** `cortex/autopilot/hooks/run_hook.cmd`

Ambos delegan a `python -m cortex.autopilot.hooks.<name>`.

---

## 7. Requisitos

- Python >= 3.10
- Cortex >= 2.0.0 (con módulo `cortex.autopilot`)
- Git (para detección de `project_root`)
- **Sin dependencia externa obligatoria** (no requiere API keys ni servicios en la nube para operar)

---

## 8. Compatibilidad por harness

| Feature | Cursor | Claude Code | Codex | OpenCode | Pi |
|---|---|---|---|---|---|
| `session_start` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `session_finish` | ✅ | ✅ | ✅ | ✅ | ✅ |
| Backup automático | ✅ | ✅ | ✅ | ✅ | ✅ |
| Wrapper cross-platform | ✅ | ✅ | ✅ | ✅ | ✅ |
| Merge settings (JSON) | ❌ | ❌ | ❌ | ❌ | ✅ |

> **Nota:** Pi requiere merge de `settings.json`; los demás adapters escriben bloques en archivos de texto plano.

---

## 9. Marketplace (futuro)

En futuras versiones, los manifestos podrían publicarse en un marketplace centralizado.  El formato `plugin.json` está diseñado para ser parseable por cualquier gestor de plugins compatible con Superpowers.

Para listar los plugins compatibles disponibles en el repositorio local:

```python
from cortex.autopilot.packaging import list_compatible_plugins

manifests = list_compatible_plugins()
for m in manifests:
    print(m.name, m.version)
```

---

## 10. Troubleshooting

### `Error: Unknown adapter: xyz`

El adapter no está registrado en `cortex/autopilot/adapters/registry.py`.  Verifica que el nombre coincida con los adapters listados arriba.

### Hook no detectado por doctor

Doctor busca marcadores específicos en los archivos de config del IDE.  Si instalaste el hook manualmente (sin `cortex autopilot install`), el formato del marcador podría no coincidir.

### Backup no restaurado

`uninstall` busca archivos con sufijo `.autopilot-backup`.  Si borraste ese backup manualmente, la restauración no será posible.
