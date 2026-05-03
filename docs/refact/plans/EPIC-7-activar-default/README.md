# EPIC 7 — Activar el Layout Nuevo por Defecto

**Semaforo:** 🟢 Verde  
**Dependencias:** EPIC 6 completa  

## Objetivo

Convertir el layout nuevo en la ruta oficial y default de Cortex.

## Gate de Salida

- [ ] El producto puede ser usado por un repo nuevo sin tocar ninguna ruta legacy
- [ ] Todos los comandos CLI funcionan en un repo nuevo
- [ ] Jira integration funciona en layout nuevo
- [ ] Enterprise retrieval funciona en layout nuevo
- [ ] WebGraph funciona en layout nuevo

## Tasks

| # | Task | Descripción | Estado |
|---|------|-------------|--------|
| 1 | Priorizar layout nuevo en discovery | `WorkspaceLayout.discover()` prioriza layout nuevo sobre legacy cuando ambos existen. Actualizar mensajes de CLI para mostrar layout detectado. | ⬜ |
| 2 | Actualizar README y guía de inicio rápido | Sección de instalación explica el layout `.cortex/`. Comandos de ejemplo muestran paths nuevos. | ⬜ |
| 3 | Validación end-to-end completa | Ejecutar los 19 escenarios de la Matriz de Validación Mínima (Sección 13 del REFAC). Documentar resultados. | ⬜ |