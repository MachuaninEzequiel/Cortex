# Fase 12 - Packaging y Marketplace

**Fuente:** `docs/autopilot/README.md`
**Estado:** Pendiente de ejecucion

## Introduccion de la fase

En esta fase se lleva a cabo lo definido en el plan global para `Fase 12 - Packaging y Marketplace`. El cuerpo operativo de la fase se copia directamente desde `docs/autopilot/README.md` para mantener la especificacion sin reinterpretaciones.

Al terminar la realizacion de esta fase, es obligatorio documentar lo desarrollado dentro de esta misma carpeta en un archivo `REALIZACION.md`. Esa realizacion debe incluir decisiones tomadas, archivos modificados, tests ejecutados, desviaciones respecto del plan, riesgos residuales y pendientes.

## Nota obligatoria para agentes implementadores

Esta nota baja a esta fase las reglas del item 18 del plan global. Es obligatoria antes de implementar.

### Reglas generales heredadas del item 18

- **No improvises.** Segui el alcance exacto de esta fase y no agregues campos, servicios ni adapters fuera de lo definido.
- **No saltees tests.** La fase no esta completa hasta cumplir su gate de salida.
- **Usa `WorkspaceLayout`.** No hardcodees `.cortex/`, `config.yaml`, `vault/` ni rutas legacy.
- **Cada archivo nuevo debe tener test unitario correspondiente** cuando la fase cree codigo runtime.
- **Si algo no esta claro, pregunta antes de asumir.** La racionalizacion es el enemigo del Autopilot.

### Aplicacion especifica en esta fase

- No publiques ni empaquetes antes de pasar evals y tener al menos un adapter probado end-to-end.
- El plugin debe instalar Autopilot, no reemplazar Cortex base.
- Install y uninstall deben ser limpios y documentados.
- No agregues dependencia externa obligatoria.

## Plan operativo original

## Fase 12 - Packaging y Marketplace

### Objetivo

Preparar distribucion como plugin oficial. Los formatos de plugin deben ser compatibles con los estandares de facto del ecosistema.

### Archivos a crear

```text
.codex-plugin/plugin.json
.claude-plugin/plugin.json
.cursor-plugin/plugin.json
docs/autopilot/marketplace.md
```

### Formato de `plugin.json`

Superpowers (184k stars) ha establecido formatos de plugin que son estandares de facto. El `plugin.json` de Cortex Autopilot debe seguir la misma estructura para que usuarios de Superpowers puedan adoptar Cortex sin friccion:

```json
{
  "name": "cortex-autopilot",
  "version": "0.1.0",
  "description": "Autonomous workflow layer for Cortex cognitive memory",
  "author": "DevSecDocOps",
  "homepage": "https://github.com/MachuaninEzequiel/Cortex",
  "skills": {
    "directory": "skills"
  },
  "hooks": {
    "directory": "hooks"
  },
  "requires": {
    "python": ">=3.10",
    "cortex": ">=2.0.0"
  }
}
```

Nota para el implementador: verificar que el formato actual de Superpowers no haya cambiado al momento de implementar esta fase. Los formatos evolucionan.

### Regla

El plugin debe instalar Autopilot, no reemplazar Cortex base.

### Checklist

- [x] Manifest incluye metadata clara.
- [x] Skills apuntan a carpeta Autopilot.
- [x] Hooks usan wrapper Python cross-platform.
- [x] Documentar install/uninstall.
- [x] Versionar compatibilidad por harness.
- [x] Formato compatible con ecosistema Superpowers.

### Gate de salida

- Instalacion limpia en workspace nuevo.
- Desinstalacion limpia.
- Sin dependencia externa obligatoria.

---

