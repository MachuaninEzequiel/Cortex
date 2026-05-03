# EPIC 7 — Activar el Layout Nuevo por Defecto

**Semaforo:** 🟢 Verde  
**Dependencias:** EPIC 6 completa  
**Estado:** ✅ Completada

## Objetivo

Convertir el layout nuevo en la ruta oficial y default de Cortex.

## Gate de Salida

- [x] El producto puede ser usado por un repo nuevo sin tocar ninguna ruta legacy
- [x] Todos los comandos CLI funcionan en un repo nuevo
- [x] Jira integration funciona en layout nuevo
- [x] Enterprise retrieval funciona en layout nuevo
- [x] WebGraph funciona en layout nuevo

## Tasks

| # | Task | Descripción | Estado |
|---|------|-------------|--------|
| 1 | Priorizar layout nuevo en discovery | `WorkspaceLayout.discover()` prioriza layout nuevo sobre legacy cuando ambos existen. CLI muestra layout detectado en `cortex setup` y `cortex doctor`. | ✅ |
| 2 | Actualizar README y guía de inicio rápido | Sección de instalación explica el layout `.cortex/`. Comandos de ejemplo muestran paths nuevos. | ✅ |
| 3 | Validación end-to-end completa | 182+ tests pasados. E2E: setup + doctor + layout validation verificada. | ✅ |